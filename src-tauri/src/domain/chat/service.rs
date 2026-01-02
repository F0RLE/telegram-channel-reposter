//! Chat Domain Service
//!
//! Manages chat history with SQLite and communicates with AI API.

use reqwest::Client;
use rusqlite::{params, Connection, Result};
use std::path::PathBuf;
use std::sync::Mutex;
use tauri::{AppHandle, Manager, Runtime};

use super::models::{ChatApiRequest, ChatApiResponse, ChatAttachment, ChatMessage};

/// Manages chat database operations
pub struct ChatManager {
    db_path: PathBuf,
}

impl ChatManager {
    /// Create a new ChatManager with database initialization
    pub fn new<R: Runtime>(app: &AppHandle<R>) -> Self {
        let app_dir = app
            .path()
            .app_data_dir()
            .expect("failed to get app data dir");
        std::fs::create_dir_all(&app_dir).expect("failed to create app data dir");
        let db_path = app_dir.join("chat.db");

        let manager = Self { db_path };
        manager.init_db().expect("failed to init chat db");
        manager
    }

    fn init_db(&self) -> Result<()> {
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

    /// Save a message to the database
    pub fn save_message(&self, role: &str, content: &str) -> Result<i64> {
        let conn = Connection::open(&self.db_path)?;
        let timestamp = chrono::Utc::now().timestamp_millis();
        conn.execute(
            "INSERT INTO messages (role, content, timestamp) VALUES (?1, ?2, ?3)",
            params![role, content, timestamp],
        )?;
        Ok(conn.last_insert_rowid())
    }

    /// Get chat history with limit
    pub fn get_history(&self, limit: i64) -> Result<Vec<ChatMessage>> {
        let conn = Connection::open(&self.db_path)?;
        let mut stmt = conn.prepare(
            "SELECT id, role, content, timestamp FROM messages ORDER BY timestamp DESC LIMIT ?1",
        )?;

        let message_iter = stmt.query_map([limit], |row| {
            Ok(ChatMessage {
                id: Some(row.get(0)?),
                role: row.get(1)?,
                content: row.get(2)?,
                timestamp: row.get(3)?,
            })
        })?;

        let mut messages = Vec::new();
        for msg in message_iter {
            messages.push(msg?);
        }
        messages.reverse();
        Ok(messages)
    }

    /// Clear all chat history
    pub fn clear_history(&self) -> Result<()> {
        let conn = Connection::open(&self.db_path)?;
        conn.execute("DELETE FROM messages", [])?;
        Ok(())
    }
}

/// State wrapper for Tauri
pub struct ChatState(pub Mutex<ChatManager>);

/// Send message to AI API
pub async fn call_ai_api(
    api_base_url: &str,
    text: &str,
    mode: &str,
    attachments: Vec<ChatAttachment>,
    history: Vec<ChatMessage>,
) -> Result<ChatApiResponse, String> {
    let payload = ChatApiRequest {
        mode: mode.to_string(),
        text: text.to_string(),
        history,
        attachments,
    };

    let api_url = format!("{}/api/chat/send", api_base_url);
    let client = Client::new();

    let res = client
        .post(&api_url)
        .json(&payload)
        .send()
        .await
        .map_err(|e| format!("Failed to connect to API: {}", e))?;

    res.json()
        .await
        .map_err(|e| format!("Failed to parse API response: {}", e))
}
