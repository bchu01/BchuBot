import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


CATEGORIES = {"memory", "profile"}
MAX_CONTENT_LENGTH = 2000
MAX_QUERY_LENGTH = 200
DEFAULT_LIMIT = 8


def _db_path():
    override = os.environ.get("BCHUBOT_MEMORY_DB")
    if override:
        return Path(override)
    return Path.home() / ".bchubot" / "memory.sqlite"


@contextmanager
def _connect():
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                key TEXT,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS memories_profile_key
            ON memories(category, key)
            WHERE category = 'profile' AND key IS NOT NULL
            """
        )
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def write_memory(content, category="memory", key=None):
    """Store a long-term memory or a stable profile fact."""
    if not isinstance(content, str) or not content.strip():
        return {"ok": False, "error": "Memory content is required."}
    if len(content) > MAX_CONTENT_LENGTH:
        return {"ok": False, "error": "That memory is too long."}

    category = _normalize_category(category)
    if category is None:
        return {"ok": False, "error": "Category must be 'memory' or 'profile'."}

    key = _normalize_key(key)
    if category == "profile" and key is None:
        return {"ok": False, "error": "A profile key is required, such as 'name'."}

    created_at = datetime.now(timezone.utc).isoformat()
    try:
        with _connect() as connection:
            row_id = _upsert_memory(
                connection,
                category=category,
                key=key,
                content=content.strip(),
                created_at=created_at,
            )
            row = connection.execute(
                """
                SELECT id, category, key, content, created_at
                FROM memories
                WHERE id = ?
                """,
                (row_id,),
            ).fetchone()
        return {"ok": True, "memory": _format_row(row)}
    except Exception:
        return {"ok": False, "error": "Could not write that memory."}


def read_memory(query=None, category=None):
    """Retrieve matching memories. Returns a small subset, never the full store."""
    if query is not None and not isinstance(query, str):
        return {"ok": False, "error": "Query must be text."}
    if isinstance(query, str) and len(query) > MAX_QUERY_LENGTH:
        return {"ok": False, "error": "That search query is too long."}

    if category not in (None, ""):
        category = _normalize_category(category)
        if category is None:
            return {"ok": False, "error": "Category must be 'memory' or 'profile'."}
    else:
        category = None

    try:
        clauses = []
        params = []
        if category:
            clauses.append("category = ?")
            params.append(category)
        if isinstance(query, str) and query.strip():
            clauses.append(
                "(content LIKE ? ESCAPE '\\' OR IFNULL(key, '') LIKE ? ESCAPE '\\')"
            )
            pattern = _like_pattern(query.strip())
            params.extend([pattern, pattern])

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"""
            SELECT id, category, key, content, created_at
            FROM memories
            {where}
            ORDER BY created_at DESC
            LIMIT ?
        """
        params.append(DEFAULT_LIMIT)

        with _connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        return {
            "ok": True,
            "query": query.strip() if isinstance(query, str) and query.strip() else None,
            "category": category,
            "memories": [_format_row(row) for row in rows],
        }
    except Exception:
        return {"ok": False, "error": "Could not read memories."}


def _upsert_memory(connection, category, key, content, created_at):
    if category == "profile":
        existing = connection.execute(
            """
            SELECT id FROM memories
            WHERE category = 'profile' AND key = ?
            """,
            (key,),
        ).fetchone()
        if existing:
            connection.execute(
                """
                UPDATE memories
                SET content = ?, created_at = ?
                WHERE id = ?
                """,
                (content, created_at, existing["id"]),
            )
            return existing["id"]

    cursor = connection.execute(
        """
        INSERT INTO memories (category, key, content, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (category, key if category == "profile" else None, content, created_at),
    )
    return cursor.lastrowid


def _normalize_category(category):
    if category in (None, ""):
        return "memory"
    if not isinstance(category, str):
        return None
    normalized = category.strip().lower()
    if normalized not in CATEGORIES:
        return None
    return normalized


def _normalize_key(key):
    if key in (None, ""):
        return None
    if not isinstance(key, str) or not key.strip():
        return None
    return key.strip().lower()


def _like_pattern(query):
    escaped = (
        query.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )
    return f"%{escaped}%"


def _format_row(row):
    return {
        "id": row["id"],
        "category": row["category"],
        "key": row["key"],
        "content": row["content"],
        "created_at": row["created_at"],
    }


MEMORY_CAPABILITIES = {
    "write_memory": (
        "Stores a long-term memory locally in SQLite, or a stable profile "
        "fact such as name or preference. Does not send memories to the cloud."
    ),
    "read_memory": (
        "Searches local SQLite memories and returns a small matching subset. "
        "Does not load the entire memory database into the conversation."
    ),
}

MEMORY_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "write_memory",
            "description": (
                "Store a long-term fact the user wants remembered. "
                "Use category 'profile' with a key for stable facts "
                "such as name. Use category 'memory' for other notes."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The fact or note to remember.",
                    },
                    "category": {
                        "type": "string",
                        "description": "'memory' or 'profile'. Defaults to memory.",
                    },
                    "key": {
                        "type": "string",
                        "description": (
                            "Required for profile facts, such as 'name' "
                            "or 'preferred_name'."
                        ),
                    },
                },
                "required": ["content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_memory",
            "description": (
                "Search stored memories and profile facts. Always search "
                "before answering questions about the user's preferences "
                "or past notes. Returns a few matches, not the full database."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Words to search for, such as 'coffee'.",
                    },
                    "category": {
                        "type": "string",
                        "description": "Optional filter: 'memory' or 'profile'.",
                    },
                },
                "required": [],
            },
        },
    },
]
