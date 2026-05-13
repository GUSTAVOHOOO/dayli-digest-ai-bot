import json
import os
import sqlite3
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from datetime import datetime
from typing import Optional
import httpx
from src.storage.redis_cache import get_redis
from src.utils.config_loader import load_env

load_env()

DB_PATH = os.getenv('SQLITE_DB_PATH', 'data/articles.db')
OLLAMA_API = os.getenv('OLLAMA_API_URL', 'http://localhost:11434')

class HealthChecker:
    """Checks the health of all system dependencies."""

    def check_redis(self) -> bool:
        """Pings Redis."""
        try:
            r = get_redis()
            return r.ping()
        except Exception:
            return False

    def check_ollama(self) -> bool:
        """Checks Ollama API availability."""
        try:
            # Short timeout to avoid blocking
            response = httpx.get(f"{OLLAMA_API}/api/tags", timeout=3.0)
            return response.status_code == 200
        except Exception:
            return False

    def check_sqlite(self) -> bool:
        """Verifies SQLite connection and query execution."""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.execute("SELECT 1 FROM processed_articles LIMIT 1")
            conn.close()
            return True
        except Exception:
            return False

    def get_last_digest_sent(self) -> Optional[str]:
        """Retrieves the timestamp of the last sent digest."""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT date_processed FROM processed_articles WHERE status='sent' ORDER BY date_processed DESC LIMIT 1"
            )
            row = cursor.fetchone()
            conn.close()
            return row[0] if row else None
        except Exception:
            return None

    def check_all(self) -> dict:
        """Runs all checks and returns a status report."""
        redis_ok = self.check_redis()
        ollama_ok = self.check_ollama()
        sqlite_ok = self.check_sqlite()
        last_digest = self.get_last_digest_sent()

        return {
            "status": "ok" if all([redis_ok, ollama_ok, sqlite_ok]) else "degraded",
            "redis": redis_ok,
            "ollama": ollama_ok,
            "sqlite": sqlite_ok,
            "last_digest_sent": last_digest,
            "checked_at": datetime.now().isoformat(),
        }

class HealthHandler(BaseHTTPRequestHandler):
    """HTTP handler for the /health endpoint."""
    checker = HealthChecker()

    def do_GET(self):
        if self.path in ['/health', '/']:
            result = self.checker.check_all()
            self.send_response(200 if result['status'] == 'ok' else 503)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress default server logs

def start_health_server(port: int = 8080):
    """Starts the health check server in a background thread."""
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server
