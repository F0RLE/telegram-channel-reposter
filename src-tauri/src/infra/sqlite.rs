use crate::domain::chat::models::ChatMessage;
use crate::domain::ports::storage::ChatStorage;
use rusqlite::{params, Connection, Result};
use std::path::PathBuf;

pub struct SqliteChatStorage {
    db_path: PathBuf,
}

impl SqliteChatStorage {
    pub fn new(db_path: PathBuf) -> Result<Self> {
        let storage = Self { db_path };
        storage.init_db().map_err(|e| e)?;
        Ok(storage)
    }

    fn init_db(&self) -> Result<(), rusqlite::Error> {
        let conn = Connection::open(&self.db_path)?;

        // Enable WAL mode for better concurrent read/write performance
        conn.execute_batch(
            "PRAGMA journal_mode=WAL;
             PRAGMA synchronous=NORMAL;
             PRAGMA cache_size=10000;
             PRAGMA temp_store=MEMORY;",
        )?;

        conn.execute(
            "CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp INTEGER NOT NULL
            )",
            [],
        )?;
        Ok(())
    }
}

impl ChatStorage for SqliteChatStorage {
    fn save_message(&self, role: &str, content: &str) -> Result<i64, String> {
        let conn = Connection::open(&self.db_path).map_err(|e| e.to_string())?;
        let timestamp = chrono::Utc::now().timestamp_millis();
        conn.execute(
            "INSERT INTO messages (role, content, timestamp) VALUES (?1, ?2, ?3)",
            params![role, content, timestamp],
        )
        .map_err(|e| e.to_string())?;
        Ok(conn.last_insert_rowid())
    }

    fn get_history(&self, limit: i64) -> Result<Vec<ChatMessage>, String> {
        let conn = Connection::open(&self.db_path).map_err(|e| e.to_string())?;
        let mut stmt = conn
            .prepare("SELECT id, role, content, timestamp FROM messages ORDER BY timestamp DESC LIMIT ?1")
            .map_err(|e| e.to_string())?;

        let message_iter = stmt
            .query_map([limit], |row| {
                Ok(ChatMessage {
                    id: Some(row.get(0)?),
                    role: row.get(1)?,
                    content: row.get(2)?,
                    timestamp: row.get(3)?,
                })
            })
            .map_err(|e| e.to_string())?;

        let mut messages = Vec::new();
        for msg in message_iter {
            messages.push(msg.map_err(|e| e.to_string())?);
        }
        messages.reverse();
        Ok(messages)
    }

    fn clear_history(&self) -> Result<(), String> {
        let conn = Connection::open(&self.db_path).map_err(|e| e.to_string())?;
        conn.execute("DELETE FROM messages", [])
            .map_err(|e| e.to_string())?;
        Ok(())
    }
}
