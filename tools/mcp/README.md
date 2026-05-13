# Project MCP Skills

This folder contains documentation and local configurations for the Model Context Protocol (MCP) servers used in this project.

## Installed Skills (Project Scope)

These are configured in `.gemini/settings.json` and are only active when working on this project.

### 1. 📰 RSS Reader (`rss-reader`)
- **Package:** `@modelcontextprotocol/server-rss`
- **Purpose:** Fetch and parse RSS/Atom feeds for news collection.
- **Usage:** Ask the agent to "Read the latest news from [URL]" or "Check the RSS feed".

### 2. 💬 Telegram (`telegram`)
- **Package:** `mcp-telegram-server`
- **Purpose:** Interact with the Telegram Bot API.
- **Requirement:** Needs a `TELEGRAM_BOT_TOKEN` environment variable.
- **Usage:** "Send a summary of today's news to my Telegram channel".

### 3. 🧠 Sequential Thinking (`thinking`)
- **Package:** `@modelcontextprotocol/server-sequential-thinking`
- **Purpose:** Enhances the agent's reasoning by breaking complex tasks into sequential steps.
- **Usage:** "Use sequential thinking to plan the architecture of the news bot".

### 4. 🐳 Docker Monitoring (`docker`)
- **Package:** `@modelcontextprotocol/server-docker`
- **Purpose:** View container status, logs, and manage Docker services.
- **Usage:** "Show me the logs for the 'redis' container" or "Check if the celery worker is running".

---
*Note: Some skills might require environment variables. You can add them to your `.env` file or directly in `.gemini/settings.json`.*
