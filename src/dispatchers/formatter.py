from typing import List

class TelegramFormatter:
    """Formats articles and digests for Telegram HTML mode."""

    HEADER_TEMPLATE = "🤖 <b>Daily Digest</b> – {date}\n\n"

    def format_header(self, date: str) -> str:
        """Formats the digest header."""
        return self.HEADER_TEMPLATE.format(date=date)

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
        return f"<b>{emoji} {category.upper()}</b>"

    def format_article(self, article: 'Article', category: str) -> str:
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
        
        category_header = f"<b>{emoji} {category.upper()}</b> | Nota: {score:.1f}"
        
        # We don't truncate summary here; split_message will handle it if it exceeds 3800 chars
        return f"{category_header}\n\n<b>{title}</b>\n🔗 <a href='{url}'>Acessar conteúdo</a>\n\n<i>{summary}</i>"

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

