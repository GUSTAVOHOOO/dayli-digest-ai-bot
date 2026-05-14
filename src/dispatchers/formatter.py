from html import escape
from typing import Any, Dict, Iterable, List

from src.models.digest import DigestItem, DigestLink


class TelegramFormatter:
    """Formats articles and digests for Telegram HTML mode."""

    HEADER_TEMPLATE = "🤖 <b>Daily Digest</b> – {date}\n\n"
    DIGEST_SECTIONS = (
        "Top Trends",
        "Emerging Repositories",
        "Important Papers",
        "AI Engineering",
        "Agent Ecosystem",
        "Infrastructure",
        "Breaking News",
    )

    def format_header(self, date: str) -> str:
        """Formats the digest header."""
        return self.HEADER_TEMPLATE.format(date=escape(str(date)))

    def format_category(self, category: str) -> str:
        """Formats a category header with emojis."""
        emojis = {
            'github': '🐙',
            'papers': '📄',
            'blogs': '📝',
            'youtube': '📺',
            'twitter': '🐦',
        }
        emoji = emojis.get(category.lower(), '📌')
        return f"<b>{emoji} {escape(category.upper())}</b>"

    def format_article(self, article: 'Article', category: str = 'blogs') -> str:
        """Formats a single article as a complete HTML message."""
        if isinstance(article, dict):
            url = article.get('url', '')
            title = article.get('title', 'Sem título')
            summary = article.get('summary', '')
            score = article.get('score', 0.0)
        else:
            url = getattr(article, 'url', '')
            title = getattr(article, 'title', 'Sem título')
            summary = getattr(article, 'summary', '')
            score = getattr(article, 'score', 0.0)

        emojis = {
            'github': '🐙',
            'papers': '📄',
            'blogs': '📝',
            'youtube': '📺',
            'twitter': '🐦',
        }
        emoji = emojis.get(category.lower(), '📌')
        
        category_header = f"<b>{emoji} {escape(category.upper())}</b> | Nota: {score:.1f}"
        safe_title = escape(title or 'Sem título')
        safe_url = escape(url or '', quote=True)
        safe_summary = escape(summary or '')
        
        # We don't truncate summary here; split_message will handle it if it exceeds 3800 chars
        return f"{category_header}\n\n<b>{safe_title}</b>\n🔗 <a href='{safe_url}'>Acessar conteúdo</a>\n\n<i>{safe_summary}</i>"

    def format_digest_items(
        self,
        items: Iterable[DigestItem | Dict[str, Any]],
        date: str,
        max_chars: int = 3800,
    ) -> List[str]:
        """Formats structured digest items into Telegram-safe HTML messages."""
        digest_items = [self._coerce_digest_item(item) for item in items]
        if not digest_items:
            return self.split_message(
                f"{self.format_header(date)}<i>Nenhum item relevante para o digest de hoje.</i>",
                max_chars,
            )

        lines = [self.format_header(date).strip(), ""]
        for section in self.DIGEST_SECTIONS:
            section_items = [
                item for item in digest_items if item.category.strip().lower() == section.lower()
            ]
            if not section_items:
                continue

            lines.append(f"<b>{escape(section)}</b>")
            for item in section_items:
                lines.extend(self._format_digest_item_lines(item))
                lines.append("")

        uncategorized_items = [
            item
            for item in digest_items
            if item.category.strip().lower()
            not in {section.lower() for section in self.DIGEST_SECTIONS}
        ]
        if uncategorized_items:
            lines.append("<b>Other</b>")
            for item in uncategorized_items:
                lines.extend(self._format_digest_item_lines(item))
                lines.append("")

        return self.split_message("\n".join(lines).strip(), max_chars)

    def format_realtime_alert(self, item: DigestItem | Dict[str, Any], reason: str = "") -> str:
        """Formats a short Telegram-safe Tier S realtime alert."""
        digest_item = self._coerce_digest_item(item)
        lines = [
            "🚨 <b>Realtime Alert</b>",
            f"<b>{escape(digest_item.title or 'Sem titulo')}</b>",
            f"Tier: <b>{escape(digest_item.tier or 'C')}</b> | Score: {digest_item.importance:.1f}",
        ]
        alert_reason = reason or digest_item.why_it_matters or digest_item.testing_reason
        if alert_reason:
            lines.append(f"<b>Motivo:</b> {escape(alert_reason)}")
        if digest_item.links:
            link = digest_item.links[0]
            safe_url = escape(link.url or "", quote=True)
            lines.append(f"<a href='{safe_url}'>Abrir fonte principal</a>")
        return "\n".join(lines)

    def _coerce_digest_item(self, item: DigestItem | Dict[str, Any]) -> DigestItem:
        if isinstance(item, DigestItem):
            return item
        return DigestItem.from_dict(item)

    def _format_digest_item_lines(self, item: DigestItem) -> List[str]:
        lines = [
            f"<b>{escape(item.title or 'Sem titulo')}</b>",
            f"Tier: <b>{escape(item.tier or 'C')}</b> | Score: {item.importance:.1f}",
        ]

        if item.why_it_matters:
            lines.append(f"<b>Why this matters:</b> {escape(item.why_it_matters)}")

        if item.key_points:
            lines.append("<b>Principais sinais:</b>")
            lines.extend(f"- {escape(point)}" for point in item.key_points)

        worth_testing = "sim" if item.worth_testing else "nao"
        testing_line = f"<b>Vale testar:</b> {worth_testing}"
        if item.testing_reason:
            testing_line += f" - {escape(item.testing_reason)}"
        lines.append(testing_line)

        if item.links:
            lines.append("<b>Links:</b>")
            lines.extend(self._format_digest_link(link) for link in item.links)

        return lines

    def _format_digest_link(self, link: DigestLink) -> str:
        label = link.title or link.source or link.url or "link"
        safe_label = escape(label)
        safe_url = escape(link.url or "", quote=True)
        return f"- <a href='{safe_url}'>{safe_label}</a>"

    def split_message(self, content: str, max_chars: int = 3800) -> List[str]:
        """Splits a long message into multiple parts, respecting line boundaries."""
        if len(content) <= max_chars:
            return [content]

        parts = []
        lines = content.split('\n')
        current_part = ""

        for line in lines:
            line_with_newline = line + '\n'
            if len(current_part) + len(line_with_newline) <= max_chars:
                current_part += line_with_newline
            else:
                if current_part:
                    parts.append(current_part.strip())
                if len(line) > max_chars:
                    # Line itself is too long, must truncate
                    truncated = line[:max_chars-3] + "…"
                    parts.append(truncated)
                    current_part = ""
                else:
                    current_part = line_with_newline

        if current_part:
            parts.append(current_part.strip())

        return parts

    def format_digest(self, articles_by_category: dict, date: str) -> List[str]:
        """Formats the digest into a list of individual messages."""
        messages = []
        
        # Start with the header
        messages.append(self.format_header(date).strip())

        for category, articles in articles_by_category.items():
            for a in articles:
                msg = self.format_article(a, category)
                # Ensure it doesn't exceed Telegram's limit
                split_parts = self.split_message(msg, 3800)
                messages.extend(split_parts)

        return messages
