"""SQLite persistence layer for OAuth tokens, audit logs, IP bans, and external MCPs."""

## ---------- (01) STANDARD LIBRARY IMPORTS ----------------------------------------- ##
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

## ---------- (02) THIRD-PARTY IMPORTS ---------------------------------------------- ##
## ---------- (03) LOCAL APPLICATION/LIBRARY-SPECIFIC IMPORTS ----------------------- ##
from ai_mcp_gateway.utils.config import get_config, get_data_dir, get_db_path

## ---------- (04) CONSTANTS -------------------------------------------------------- ##
LOGGER: logging.Logger = logging.getLogger(__name__)
DATA_DIR: Path = get_data_dir()
DB_PATH: Path = get_db_path()
_DB_INITIALIZED: bool = False
_DB_INITIALIZING: bool = False

## ---------- (05) ENUMS ------------------------------------------------------------ ##
# No module-level enums required.

## ---------- (06) CLASS DEFINITIONS ------------------------------------------------ ##
# No module-level classes required.


## ---------- (07) PUBLIC FUNCTIONS ------------------------------------------------- ##
@contextmanager
def get_db_connection(timeout: float = 10.0) -> Generator[sqlite3.Connection, None, None]:
    """Provide a thread-safe SQLite connection with timeout and WAL journal mode."""
    global _DB_INITIALIZED, _DB_INITIALIZING
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    if not _DB_INITIALIZED and not _DB_INITIALIZING:
        _DB_INITIALIZING = True
        try:
            init_db()
            _DB_INITIALIZED = True
        finally:
            _DB_INITIALIZING = False

    conn = sqlite3.connect(db_path, timeout=timeout)
    conn.execute("PRAGMA journal_mode = WAL;")
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    """Initialize SQLite schema, run lightweight column migrations, and purge stale tokens."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS oauth_tokens (
                token TEXT PRIMARY KEY,
                client_name TEXT DEFAULT 'AI Agent',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cursor.execute("PRAGMA table_info(oauth_tokens);")
        token_cols = [row[1] for row in cursor.fetchall()]
        if "client_name" not in token_cols:
            cursor.execute(
                "ALTER TABLE oauth_tokens ADD COLUMN client_name TEXT DEFAULT 'AI Agent';"
            )
        if "last_used_at" not in token_cols:
            cursor.execute("ALTER TABLE oauth_tokens ADD COLUMN last_used_at TIMESTAMP;")
            cursor.execute(
                "UPDATE oauth_tokens SET last_used_at = created_at WHERE last_used_at IS NULL;"
            )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS oauth_refresh_tokens (
                token TEXT PRIMARY KEY,
                client_name TEXT DEFAULT 'AI Agent',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tool_name TEXT,
                params TEXT,
                status TEXT,
                result TEXT,
                client_name TEXT DEFAULT 'AI Agent',
                timestamp TIMESTAMP DEFAULT (datetime('now', 'localtime'))
            )
            """
        )

        cursor.execute("PRAGMA table_info(audit_logs);")
        columns = [row[1] for row in cursor.fetchall()]
        if "client_name" not in columns:
            cursor.execute("ALTER TABLE audit_logs ADD COLUMN client_name TEXT DEFAULT 'AI Agent';")

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS banned_ips (
                ip TEXT PRIMARY KEY,
                reason TEXT DEFAULT 'Malicious Scanner',
                target_path TEXT DEFAULT '',
                hit_count INTEGER DEFAULT 1,
                banned_at TIMESTAMP DEFAULT (datetime('now', 'localtime')),
                expires_at REAL
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS external_mcp_servers (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                repo_url TEXT NOT NULL,
                install_path TEXT NOT NULL,
                runtime TEXT DEFAULT 'python',
                command TEXT,
                args TEXT,
                env_vars TEXT DEFAULT '{}',
                status TEXT DEFAULT 'STOPPED',
                error_message TEXT,
                tools_json TEXT DEFAULT '[]',
                expose_to_server INTEGER DEFAULT 1,
                installed_at TIMESTAMP DEFAULT (datetime('now', 'localtime'))
            )
            """
        )

        conn.commit()

    try:
        cleanup_expired_tokens()
        cleanup_expired_refresh_tokens()
    except sqlite3.Error as err:
        LOGGER.debug("Skipping initial token cleanup: %s", err)


def save_token(token: str, client_name: str = "AI Agent") -> None:
    """Insert or update an OAuth token and its associated AI client name."""
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO oauth_tokens (token, client_name, created_at, last_used_at)
            VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(token) DO UPDATE SET
                client_name = excluded.client_name,
                last_used_at = CURRENT_TIMESTAMP
            """,
            (token, client_name),
        )
        conn.commit()


def save_refresh_token(token: str, client_name: str = "AI Agent") -> None:
    """Insert or update an OAuth refresh token and its associated AI client name."""
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO oauth_refresh_tokens (token, client_name, created_at, last_used_at)
            VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(token) DO UPDATE SET
                client_name = excluded.client_name,
                last_used_at = CURRENT_TIMESTAMP
            """,
            (token, client_name),
        )
        conn.commit()


def get_token_client(token: str) -> Optional[str]:
    """Return the AI client label linked to an OAuth token."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT client_name FROM oauth_tokens WHERE token = ?", (token,))
        row = cursor.fetchone()
        return row[0] if row and row[0] else None


def get_refresh_token_client(token: str) -> Optional[str]:
    """Return the AI client label linked to an OAuth refresh token."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT client_name FROM oauth_refresh_tokens WHERE token = ?", (token,))
        row = cursor.fetchone()
        return row[0] if row and row[0] else None


def verify_token(token: str, max_age_seconds: Optional[int] = None) -> bool:
    """Verify Bearer token validity and renew its sliding-window timestamp."""
    if not token:
        return False
    if max_age_seconds is None:
        max_age_seconds = get_config().session.ttl
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT (strftime('%s', 'now') - strftime('%s', COALESCE(last_used_at, created_at)))
            FROM oauth_tokens
            WHERE token = ?
            """,
            (token,),
        )
        row = cursor.fetchone()
        if row is None:
            return False

        age_seconds = row[0] if row[0] is not None else 0
        if max_age_seconds is not None and age_seconds > max_age_seconds:
            cursor.execute("DELETE FROM oauth_tokens WHERE token = ?", (token,))
            conn.commit()
            return False

        cursor.execute(
            "UPDATE oauth_tokens SET last_used_at = CURRENT_TIMESTAMP WHERE token = ?", (token,)
        )
        conn.commit()
        return True


def verify_refresh_token(token: str, max_age_seconds: Optional[int] = None) -> bool:
    """Verify refresh token validity and renew its sliding-window timestamp."""
    if not token:
        return False
    if max_age_seconds is None:
        max_age_seconds = get_config().session.refresh_token_ttl
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT (strftime('%s', 'now') - strftime('%s', COALESCE(last_used_at, created_at)))
            FROM oauth_refresh_tokens
            WHERE token = ?
            """,
            (token,),
        )
        row = cursor.fetchone()
        if row is None:
            return False

        age_seconds = row[0] if row[0] is not None else 0
        if max_age_seconds is not None and age_seconds > max_age_seconds:
            cursor.execute("DELETE FROM oauth_refresh_tokens WHERE token = ?", (token,))
            conn.commit()
            return False

        cursor.execute(
            "UPDATE oauth_refresh_tokens SET last_used_at = CURRENT_TIMESTAMP WHERE token = ?",
            (token,),
        )
        conn.commit()
        return True


def get_active_client_connections() -> Dict[str, Any]:
    """Return active AI client connection metadata and remaining TTL for Dashboard UI."""
    ttl = get_config().session.ttl
    with get_db_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                client_name,
                created_at,
                COALESCE(last_used_at, created_at) as last_used_at,
                (strftime('%s', 'now') - strftime('%s', COALESCE(last_used_at, created_at))) as elapsed_seconds
            FROM oauth_tokens
            ORDER BY last_used_at DESC
            """
        )
        rows = cursor.fetchall()

    seen_clients: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        c_name = row["client_name"] or "AI Agent"
        elapsed = row["elapsed_seconds"] if row["elapsed_seconds"] is not None else 0
        remaining = max(0, ttl - elapsed)
        if c_name not in seen_clients:
            seen_clients[c_name] = {
                "client_name": c_name,
                "created_at": row["created_at"],
                "last_used_at": row["last_used_at"],
                "elapsed_seconds": elapsed,
                "remaining_seconds": remaining,
                "is_expired": remaining == 0,
            }

    category_summary: Dict[str, Optional[Dict[str, Any]]] = {}
    for cat in ("Gemini", "Claude", "ChatGPT"):
        match = None
        for name, data in seen_clients.items():
            if cat.lower() in name.lower():
                match = data
                break
        category_summary[cat] = match

    return {
        "clients": list(seen_clients.values()),
        "summary": category_summary,
        "max_ttl_seconds": ttl,
    }


def revoke_token(token: str) -> None:
    """Delete a token from SQLite immediately."""
    if not token:
        return
    with get_db_connection() as conn:
        conn.execute("DELETE FROM oauth_tokens WHERE token = ?", (token,))
        conn.commit()


def revoke_refresh_token(token: str) -> None:
    """Delete a refresh token from SQLite immediately."""
    if not token:
        return
    with get_db_connection() as conn:
        conn.execute("DELETE FROM oauth_refresh_tokens WHERE token = ?", (token,))
        conn.commit()


def cleanup_expired_tokens(max_age_seconds: Optional[int] = None) -> int:
    """Purge expired OAuth tokens based on session TTL and return deleted count."""
    if max_age_seconds is None:
        max_age_seconds = get_config().session.ttl
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            DELETE FROM oauth_tokens
            WHERE (strftime('%s', 'now') - strftime('%s', COALESCE(last_used_at, created_at))) > ?
            """,
            (max_age_seconds,),
        )
        deleted_count = cursor.rowcount
        conn.commit()
        return deleted_count


def cleanup_expired_refresh_tokens(max_age_seconds: Optional[int] = None) -> int:
    """Purge expired OAuth refresh tokens based on refresh_token_ttl."""
    if max_age_seconds is None:
        max_age_seconds = get_config().session.refresh_token_ttl
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            DELETE FROM oauth_refresh_tokens
            WHERE (strftime('%s', 'now') - strftime('%s', COALESCE(last_used_at, created_at))) > ?
            """,
            (max_age_seconds,),
        )
        deleted_count = cursor.rowcount
        conn.commit()
        return deleted_count


def log_activity(
    tool_name: str,
    params: str,
    status: str,
    result: str,
    client_name: str = "AI Agent",
    timestamp: Optional[str] = None,
) -> None:
    """Record an MCP tool invocation in audit_logs."""
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO audit_logs (tool_name, params, status, result, client_name, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (tool_name, params, status, result, client_name, timestamp),
        )
        conn.commit()


def get_recent_logs(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Return most recent audit log records."""
    if limit is None:
        limit = get_config().session.audit_log_limit
    with get_db_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, tool_name, params, status, result, COALESCE(client_name, 'AI Agent') as client_name, timestamp FROM audit_logs ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return [dict(r) for r in cursor.fetchall()]


def get_ai_usage_stats() -> Dict[str, int]:
    """Aggregate audit log counts grouped by AI client provider."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT COALESCE(client_name, 'Other') as client, COUNT(*) as count
            FROM audit_logs
            GROUP BY client_name
            """
        )
        raw_counts = dict(cursor.fetchall())

    gemini_count = 0
    claude_count = 0
    chatgpt_count = 0
    other_count = 0

    for client, count in raw_counts.items():
        c_lower = (client or "").lower()
        if any(k in c_lower for k in ("gemini", "google", "aistudio", "mcp")):
            gemini_count += count
        elif any(k in c_lower for k in ("claude", "anthropic")):
            claude_count += count
        elif any(k in c_lower for k in ("chatgpt", "openai", "gpt")):
            chatgpt_count += count
        else:
            other_count += count

    total_count = gemini_count + claude_count + chatgpt_count + other_count
    return {
        "Gemini": gemini_count,
        "Claude": claude_count,
        "ChatGPT": chatgpt_count,
        "Other": other_count,
        "Total": total_count,
    }


def clear_logs() -> None:
    """Delete all audit log records."""
    with get_db_connection() as conn:
        conn.execute("DELETE FROM audit_logs")
        conn.commit()


def add_or_update_ban(
    ip: str,
    reason: str = "Malicious Scanner",
    target_path: str = "",
    duration_seconds: float = 3600,
) -> None:
    """Insert or refresh an IP ban record and increment hit_count."""
    if not ip:
        return
    expires_at = datetime.now().timestamp() + duration_seconds
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT hit_count FROM banned_ips WHERE ip = ?", (ip,))
        row = cursor.fetchone()
        if row:
            cursor.execute(
                """
                UPDATE banned_ips
                SET hit_count = ?, reason = ?, target_path = ?, expires_at = ?
                WHERE ip = ?
                """,
                (row[0] + 1, reason, target_path, expires_at, ip),
            )
        else:
            cursor.execute(
                """
                INSERT INTO banned_ips (ip, reason, target_path, hit_count, expires_at)
                VALUES (?, ?, ?, 1, ?)
                """,
                (ip, reason, target_path, expires_at),
            )
        conn.commit()


def get_all_banned_ips() -> List[Dict[str, Any]]:
    """Return all persisted banned IP records."""
    with get_db_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM banned_ips ORDER BY banned_at DESC")
        return [dict(r) for r in cursor.fetchall()]


def remove_ban(ip: str) -> None:
    """Remove an IP ban from SQLite."""
    if not ip:
        return
    with get_db_connection() as conn:
        conn.execute("DELETE FROM banned_ips WHERE ip = ?", (ip,))
        conn.commit()


def clear_all_bans() -> None:
    """Delete all IP ban records from SQLite."""
    with get_db_connection() as conn:
        conn.execute("DELETE FROM banned_ips")
        conn.commit()


def save_external_mcp(mcp_dict: Dict[str, Any]) -> None:
    """Insert or replace an external MCP server configuration record."""
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO external_mcp_servers
            (id, name, repo_url, install_path, runtime, command, args, env_vars, status, error_message, tools_json, expose_to_server)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                mcp_dict["id"],
                mcp_dict["name"],
                mcp_dict["repo_url"],
                mcp_dict["install_path"],
                mcp_dict.get("runtime", "python"),
                mcp_dict.get("command", ""),
                mcp_dict.get("args", ""),
                mcp_dict.get("env_vars", "{}"),
                mcp_dict.get("status", "STOPPED"),
                mcp_dict.get("error_message", ""),
                mcp_dict.get("tools_json", "[]"),
                1 if mcp_dict.get("expose_to_server", True) else 0,
            ),
        )
        conn.commit()


def get_all_external_mcps() -> List[Dict[str, Any]]:
    """List all installed external MCP server configurations."""
    with get_db_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM external_mcp_servers ORDER BY installed_at DESC")
        return [dict(r) for r in cursor.fetchall()]


def get_external_mcp(mcp_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single external MCP server configuration by ID."""
    with get_db_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM external_mcp_servers WHERE id = ?", (mcp_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def update_external_mcp_status(
    mcp_id: str,
    status: str,
    tools_json: Optional[str] = None,
    error_message: Optional[str] = None,
    expose_to_server: Optional[bool] = None,
) -> None:
    """Update status, discovered tools JSON, or error message for an external MCP server."""
    with get_db_connection() as conn:
        updates = ["status = ?"]
        params: List[Any] = [status]
        if tools_json is not None:
            updates.append("tools_json = ?")
            params.append(tools_json)
        if error_message is not None:
            updates.append("error_message = ?")
            params.append(error_message)
        if expose_to_server is not None:
            updates.append("expose_to_server = ?")
            params.append(1 if expose_to_server else 0)

        params.append(mcp_id)
        query = f"UPDATE external_mcp_servers SET {', '.join(updates)} WHERE id = ?"
        conn.execute(query, tuple(params))
        conn.commit()


def delete_external_mcp(mcp_id: str) -> None:
    """Delete an external MCP server configuration record."""
    with get_db_connection() as conn:
        conn.execute("DELETE FROM external_mcp_servers WHERE id = ?", (mcp_id,))
        conn.commit()


## ---------- (08) PRIVATE FUNCTIONS ------------------------------------------------ ##
# No private helper functions required.

## ---------- (09) MAIN EXECUTION --------------------------------------------------- ##
# SQLite persistence module only.
