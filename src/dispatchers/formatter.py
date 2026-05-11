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

    def format_article(self, article: 'Article') -> str:
        """Formats a single article as an HTML link and summary."""
        # Note: 'Article' is passed as a dict or object depending on context
        # We'll handle both but usually it's an object in the task
        if isinstance(article, dict):
            url = article.get('url', '')
            title = article.get('title', 'Sem título')
            summary = article.get('summary', '')
        else:
            url = getattr(article, 'url', '')
            title = getattr(article, 'title', 'Sem título')
            summary = getattr(article, 'summary', '')

        truncated_summary = summary[:200] + "…" if summary and len(summary) > 200 else summary or ""

        return f"<a href='{url}'>{title}</a>\n<i>{truncated_summary}</i>"

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
        """Formats the entire digest, potentially splitting into multiple messages."""
        messages = []
        header = self.format_header(date)
        current_message = header

        for category, articles in articles_by_category.items():
            category_header = self.format_category(category)
            category_content = "\n".join(self.format_article(a) for a in articles)
            category_block = f"{category_header}\n{category_content}\n\n"

            if len(current_message) + len(category_block) > 3800:
                if current_message != header:
                    messages.append(current_message.strip())
                    current_message = category_block
                else:
                    # Even the first block is too big? Split it.
                    # This is rare if max_chars is 3800 and items are small.
                    messages.append(current_message.strip())
                    split_parts = self.split_message(category_block, 3800)
                    for part in split_parts[:-1]:
                        messages.append(part)
                    current_message = split_parts[-1] + "\n\n"
            else:
                current_message += category_block

        if current_message.strip():
            messages.append(current_message.strip())

        return messages
