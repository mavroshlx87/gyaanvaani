import sqlite3
import json
import os
from config.settings import DB_PATH


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    """Create tables if not exists."""
    conn = get_connection()
    conn.execute("""CREATE TABLE IF NOT EXISTS stories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        source TEXT,
        characters TEXT,
        full_story TEXT,
        moral TEXT,
        tags TEXT,
        scenes TEXT,
        status TEXT DEFAULT 'PENDING',
        validation_result TEXT,
        youtube_url TEXT,
        instagram_url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        published_at TIMESTAMP
    )""")
    conn.commit()
    conn.close()


def insert_story(story: dict):
    conn = get_connection()
    conn.execute(
        """INSERT INTO stories (title, source, characters, full_story, moral, tags, status)
           VALUES (?, ?, ?, ?, ?, ?, 'PENDING')""",
        (story["title"], story.get("source", ""),
         json.dumps(story.get("characters", [])),
         story["full_story"], story["moral"],
         json.dumps(story.get("tags", [])))
    )
    conn.commit()
    conn.close()


def get_next_by_status(status: str) -> dict | None:
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM stories WHERE status = ? ORDER BY id LIMIT 1",
        (status,)
    ).fetchone()
    conn.close()
    if row:
        d = dict(row)
        for key in ["characters", "tags", "scenes"]:
            if d.get(key):
                d[key] = json.loads(d[key])
        return d
    return None


def update_status(story_id: int, status: str, **extra_fields):
    conn = get_connection()
    sets = ["status = ?"]
    vals = [status]
    for k, v in extra_fields.items():
        sets.append(f"{k} = ?")
        vals.append(json.dumps(v) if isinstance(v, (dict, list)) else v)
    vals.append(story_id)
    conn.execute(f"UPDATE stories SET {', '.join(sets)} WHERE id = ?", vals)
    conn.commit()
    conn.close()


def count_by_status(status: str) -> int:
    conn = get_connection()
    count = conn.execute(
        "SELECT COUNT(*) FROM stories WHERE status = ?", (status,)
    ).fetchone()[0]
    conn.close()
    return count


# Auto-init on import
init_db()
