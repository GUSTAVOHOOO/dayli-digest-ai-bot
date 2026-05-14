import asyncio
import hashlib
import json
import os
from typing import List, Optional
try:
    from telegram import Bot
    from telegram.error import RetryAfter
    from telegram.constants import ParseMode
except ImportError:
    Bot = None

    class RetryAfter(Exception):
        retry_after = 0

    class ParseMode:
        HTML = "HTML"
from src.models.article import Article
from src.models.digest import DigestItem, DigestLink, ScoreBreakdown
from src.models.cluster import TopicCluster
from src.processors.clustering import cluster_analyzed_items
from src.processors.trend_engine import rank_trend_clusters
from src.utils.logger import get_logger
from src.utils.config_loader import load_env
from src.utils.metrics import emit_metric, measure_stage, metric_dispatch_sent

# Ensure env is loaded
load_env()
log = get_logger(__name__)

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
DIGEST_CATEGORY_SECTIONS = {
    "top_trends": "Top Trends",
    "emerging_repositories": "Emerging Repositories",
    "important_papers": "Important Papers",
    "ai_engineering": "AI Engineering",
    "agent_ecosystem": "Agent Ecosystem",
    "infrastructure": "Infrastructure",
    "breaking_news": "Breaking News",
}

class TelegramDispatcher:
    """Handles sending messages to Telegram with rate limiting and flood protection."""

    def __init__(self):
        if not BOT_TOKEN:
            log.error("telegram_token_missing")
            self.bot = None
        elif Bot is not None:
            self.bot = Bot(token=BOT_TOKEN)
        else:
            log.error("telegram_package_missing")
            self.bot = None
        self.rate_limit_delay = 1.0  # seconds between messages

    async def _send_single(self, chat_id: int, text: str) -> bool:
        """Sends a single message to a chat."""
        if not self.bot:
            log.error("send_failed_token_missing")
            return False

        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
            return True
        except RetryAfter as e:
            log.warning("flood_wait", seconds=e.retry_after)
            await asyncio.sleep(e.retry_after)
            return await self._send_single(chat_id, text)
        except Exception as e:
            log.error("send_message_error", chat_id=chat_id, error=str(e))
            return False

    async def send_message(self, chat_id: int, text: str) -> bool:
        """Async interface for sending a single message."""
        return await self._send_single(chat_id, text)

    async def send_messages(self, chat_id: int, messages: List[str]) -> int:
        """Sends multiple messages with rate limiting."""
        sent = 0
        for msg in messages:
            success = await self._send_single(chat_id, msg)
            if success:
                sent += 1
                if sent < len(messages):
                    await asyncio.sleep(self.rate_limit_delay)
            else:
                log.error("message_send_failed", chat_id=chat_id, index=sent)

        log.info("messages_sent", chat_id=chat_id, sent=sent, total=len(messages))
        return sent

    def send_messages_sync(self, chat_id: int, messages: List[str]) -> int:
        """Sync wrapper for sending messages, suitable for Celery workers."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        try:
            return loop.run_until_complete(self.send_messages(chat_id, messages))
        finally:
            # We don't close the loop if we didn't create it
            pass

from datetime import datetime
from src.celery_app import app
from src.storage.sqlite import get_articles_by_date, save_article
from src.storage.redis_cache import (
    acquire_realtime_alert_lock,
    release_digest_lock,
    release_dispatch_schedule_lock,
)


def select_digest_articles(
    articles: List[Article],
    max_items: int,
    min_score: float,
) -> List[Article]:
    """Filters and ranks articles for the consolidated digest."""
    eligible = [article for article in articles if article.score >= min_score]
    eligible.sort(key=lambda article: article.score, reverse=True)
    return eligible[:max_items]


def article_to_digest_item(article: Article) -> DigestItem:
    """Builds a DigestItem from a processed Article and its validated analysis JSON."""
    analysis = _load_analysis(article)
    score_breakdown = analysis.get("score_breakdown")
    if not isinstance(score_breakdown, dict):
        score_breakdown = {}
    category = _category_to_section(analysis.get("category") or article.source)
    key_points = analysis.get("key_points") or []
    why_it_matters = analysis.get("why_it_matters") or article.summary or ""

    return DigestItem(
        title=article.title or "Sem titulo",
        category=category,
        tier=analysis.get("tier") or _score_to_tier(article.score),
        importance=article.score,
        why_it_matters=why_it_matters,
        key_points=key_points,
        worth_testing=bool(analysis.get("worth_testing", False)),
        testing_reason=analysis.get("summary") or "",
        links=[DigestLink(url=article.url, title=article.title, source=article.source)],
        score_breakdown=ScoreBreakdown(
            relevance=float(
                score_breakdown.get(
                    "implementation_value",
                    analysis.get("implementation_value", 0.0),
                )
                or 0.0
            ),
            novelty=float(analysis.get("novelty", 0.0) or 0.0),
            source_quality=float(analysis.get("authority", 0.0) or 0.0),
            urgency=float(score_breakdown.get("momentum", 0.0) or 0.0),
            extra={
                "technical_depth": float(analysis.get("technical_depth", 0.0) or 0.0),
                "noise_risk": float(analysis.get("noise_risk", 0.0) or 0.0),
                "cross_source_validation": float(
                    score_breakdown.get("cross_source_validation", 0.0) or 0.0
                ),
            },
        ),
    )


def cluster_to_digest_item(cluster: TopicCluster) -> DigestItem:
    """Builds a DigestItem from a ranked TopicCluster."""
    top_item = max(cluster.items, key=lambda item: float(item.get("score", 0.0) or 0.0), default={})
    analysis = _json_dict(top_item.get("analysis_json")) if top_item else {}
    category = _category_to_section(analysis.get("category") or top_item.get("source"))
    links = _cluster_links(cluster)
    signals = cluster.trend_signals or cluster.correlation_signals

    return DigestItem(
        title=cluster.topic_name or str(top_item.get("title") or "Sem titulo"),
        category=category,
        tier=cluster.tier,
        importance=cluster.final_score,
        why_it_matters=analysis.get("why_it_matters") or str(top_item.get("summary") or ""),
        key_points=signals,
        worth_testing=bool(analysis.get("worth_testing", False)),
        testing_reason=analysis.get("summary") or "",
        links=links,
        score_breakdown=ScoreBreakdown(
            relevance=float(analysis.get("implementation_value", 0.0) or 0.0),
            novelty=float(analysis.get("novelty", 0.0) or 0.0),
            source_quality=float(analysis.get("authority", 0.0) or 0.0),
            urgency=float(analysis.get("momentum", 0.0) or 0.0),
            extra={
                "cross_source_validation": cluster.cross_source_validation,
                "trend_score": cluster.trend_score,
                "correlation_boost": cluster.correlation_boost,
            },
        ),
    )


def _cluster_links(cluster: TopicCluster) -> List[DigestLink]:
    links = []
    seen = set()
    for item in cluster.items:
        for raw_link in item.get("links") or []:
            if not isinstance(raw_link, dict):
                continue
            url = str(raw_link.get("url") or "")
            if not url or url in seen:
                continue
            seen.add(url)
            links.append(DigestLink(
                url=url,
                title=raw_link.get("title") or item.get("title"),
                source=raw_link.get("source") or item.get("source"),
            ))
    return links


def _load_analysis(article: Article) -> dict:
    if not article.analysis_json:
        return {}
    try:
        data = json.loads(article.analysis_json)
    except (TypeError, json.JSONDecodeError) as e:
        log.warning("dispatch_invalid_analysis_json", url=article.url, error=str(e))
        return {}
    if not isinstance(data, dict):
        log.warning("dispatch_invalid_analysis_type", url=article.url)
        return {}
    return data


def _category_to_section(category: Optional[str]) -> str:
    normalized = (category or "").strip().lower().replace("-", "_").replace(" ", "_")
    if normalized in DIGEST_CATEGORY_SECTIONS:
        return DIGEST_CATEGORY_SECTIONS[normalized]
    source_sections = {
        "github": "Emerging Repositories",
        "papers": "Important Papers",
        "arxiv": "Important Papers",
        "blogs": "AI Engineering",
        "youtube": "AI Engineering",
        "twitter": "Breaking News",
    }
    return source_sections.get(normalized, "AI Engineering")


def _score_to_tier(score: float) -> str:
    if score >= 9.0:
        return "S"
    if score >= 7.5:
        return "A"
    if score >= 6.0:
        return "B"
    return "C"


def should_send_realtime_alert(article: Article | dict, analysis: Optional[dict] = None) -> bool:
    """Returns True only for Tier S items with explicit realtime-worthy signals."""
    if isinstance(article, Article):
        article_dict = article.to_dict()
    else:
        article_dict = dict(article)
    if analysis is None:
        analysis = _json_dict(article_dict.get("analysis_json"))

    tier = str(analysis.get("tier") or article_dict.get("tier") or _score_to_tier(float(article_dict.get("score", 0.0) or 0.0)))
    if tier != "S":
        return False

    haystack = " ".join([
        str(article_dict.get("title") or ""),
        str(article_dict.get("summary") or ""),
        str(analysis.get("summary") or ""),
        str(analysis.get("why_it_matters") or ""),
        " ".join(str(point) for point in analysis.get("key_points") or []),
        " ".join(_entity_names(analysis.get("entities") or [])),
    ]).lower()
    realtime_terms = (
        "api",
        "breaking",
        "breakthrough",
        "critical",
        "vulnerability",
        "security",
        "release",
        "major",
        "model",
        "gpt",
        "claude",
        "gemini",
        "llama",
    )
    return any(term in haystack for term in realtime_terms)


def send_realtime_alert(article: Article | dict, chat_id: int = None, date: Optional[str] = None) -> dict:
    """Sends a short realtime alert if the item is Tier S and not already alerted today."""
    if chat_id is None:
        chat_id = int(os.getenv('ADMIN_CHAT_ID', '0'))
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')

    article_obj = article if isinstance(article, Article) else Article.from_dict(article)
    analysis = _load_analysis(article_obj)
    if not should_send_realtime_alert(article_obj, analysis):
        return {"status": "skipped", "reason": "not_realtime_tier_s"}

    alert_key = article_obj.md5_hash or hashlib.md5(article_obj.url.encode()).hexdigest()
    if not acquire_realtime_alert_lock(alert_key, date):
        return {"status": "skipped", "reason": "duplicate_alert"}

    from src.dispatchers.formatter import TelegramFormatter

    item = article_to_digest_item(article_obj)
    reason = analysis.get("why_it_matters") or analysis.get("summary") or item.why_it_matters
    message = TelegramFormatter().format_realtime_alert(item, reason=reason)
    sent = TelegramDispatcher().send_messages_sync(chat_id, [message])
    return {"status": "ok" if sent == 1 else "failed", "sent": sent}


def _json_dict(value) -> dict:
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    try:
        data = json.loads(value)
    except (TypeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _entity_names(entities) -> List[str]:
    names = []
    for entity in entities:
        if isinstance(entity, dict):
            names.append(str(entity.get("name") or entity.get("normalized_name") or ""))
        elif entity:
            names.append(str(entity))
    return names

@app.task(
    name='src.dispatchers.telegram.process_dispatch',
    bind=True,
    acks_late=True,
)
def process_dispatch(self, chat_id: int = None, mark_sent: bool = True, release_pipeline_lock: bool = True):
    """Celery task to dispatch processed articles to Telegram."""
    if chat_id is None:
        chat_id = int(os.getenv('ADMIN_CHAT_ID', '0'))

    today = datetime.now().strftime('%Y-%m-%d')
    min_score = float(os.getenv('DIGEST_MIN_SCORE', '6.0'))
    max_items = int(os.getenv('DIGEST_MAX_ITEMS', '10'))
    max_messages = int(os.getenv('DIGEST_MAX_MESSAGES', '3'))
    
    log.info(
        "dispatch_started",
        chat_id=chat_id,
        date=today,
        min_score=min_score,
        max_items=max_items,
        max_messages=max_messages,
    )

    try:
        with measure_stage("dispatch_load", source="telegram"):
            articles = get_articles_by_date(today, min_score=min_score)

        if not articles:
            log.info("no_articles_to_dispatch", chat_id=chat_id)
            return {"status": "ok", "sent": 0}

        eligible_articles = select_digest_articles(articles, max_items=max_items * 3, min_score=min_score)
        with measure_stage("dispatch_cluster_rank", source="telegram", metadata={"eligible": len(eligible_articles)}):
            clusters = cluster_analyzed_items(eligible_articles)
            ranked_clusters = rank_trend_clusters(clusters)[:max_items]
        selected_urls = {
            item.get("url")
            for cluster in ranked_clusters
            for item in cluster.items
            if item.get("url")
        }
        selected_articles = [article for article in eligible_articles if article.url in selected_urls]
        ignored_count = len(articles) - len(selected_articles)
        digest_items = [cluster_to_digest_item(cluster) for cluster in ranked_clusters]

        from src.dispatchers.formatter import TelegramFormatter
        formatter = TelegramFormatter()
        messages = formatter.format_digest_items(digest_items, today)
        message_limit_exceeded = False
        if len(messages) > max_messages:
            message_limit_exceeded = True
            log.warning(
                "digest_message_limit_exceeded",
                chat_id=chat_id,
                total_messages=len(messages),
                max_messages=max_messages,
            )
            messages = messages[:max_messages]

        dispatcher = TelegramDispatcher()
        with measure_stage("dispatch_send", source="telegram", metadata={"messages": len(messages)}):
            sent_count = dispatcher.send_messages_sync(chat_id, messages)
        metric_dispatch_sent(sent_count, chat_id)

        if mark_sent and sent_count == len(messages) and not message_limit_exceeded:
            for article in selected_articles:
                article.status = 'sent'
                save_article(article)
        elif mark_sent:
            log.warning(
                "dispatch_partial_not_marking_sent",
                chat_id=chat_id,
                sent=sent_count,
                total_messages=len(messages),
            )

        log.info(
            "dispatch_completed",
            chat_id=chat_id,
            considered=len(articles),
            selected=len(selected_articles),
            ignored=ignored_count,
            total_messages=sent_count,
        )
        emit_metric(
            "dispatch_summary",
            count=sent_count,
            source="telegram",
            metadata={
                "considered": len(articles),
                "selected": len(selected_articles),
                "ignored": ignored_count,
                "messages": len(messages),
            },
        )

        return {
            "status": "ok",
            "sent": sent_count,
            "total_articles": len(articles),
            "selected_articles": len(selected_articles),
            "ignored_articles": ignored_count,
        }
    finally:
        release_dispatch_schedule_lock(today)
        if release_pipeline_lock:
            release_digest_lock(today)
