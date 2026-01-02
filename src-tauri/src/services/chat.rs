use crate::services::settings::get_settings;
use reqwest::Client;
use rusqlite::{params, Connection, Result};
use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use std::sync::Mutex;
use tauri::{AppHandle, Manager, Runtime, State};

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ChatMessage {
    pub id: Option<i64>,
    pub role: String,
    pub content: String,
    pub timestamp: i64,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ChatAttachment {
    pub name: String,
    pub r#type: String,
    pub size: i64,
    pub data_base64: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ChatApiRequest {
    pub mode: String,
    pub text: String,
    pub history: Vec<ChatMessage>, // Simplified for API
    pub attachments: Vec<ChatAttachment>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ChatApiResponse {
    pub ok: bool,
    pub reply: Option<ChatApiReply>,
    pub error: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ChatApiReply {
    pub text: Option<String>,
    pub r#type: Option<String>,
    pub images: Option<Vec<String>>, // base64 images
}

pub struct ChatManager {
    db_path: PathBuf,
}

impl ChatManager {
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

    pub fn save_message(&self, role: &str, content: &str) -> Result<i64> {
        let conn = Connection::open(&self.db_path)?;
        let timestamp = chrono::Utc::now().timestamp_millis();
        conn.execute(
            "INSERT INTO messages (role, content, timestamp) VALUES (?1, ?2, ?3)",
            params![role, content, timestamp],
        )?;
        Ok(conn.last_insert_rowid())
    }

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

    pub fn clear_history(&self) -> Result<()> {
        let conn = Connection::open(&self.db_path)?;
        conn.execute("DELETE FROM messages", [])?;
        Ok(())
    }
}

pub struct ChatState(pub Mutex<ChatManager>);

#[tauri::command]
pub async fn save_chat_message(
    state: State<'_, ChatState>,
    role: String,
    content: String,
) -> Result<i64, String> {
    state
        .0
        .lock()
        .unwrap()
        .save_message(&role, &content)
        .map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn get_chat_history(
    state: State<'_, ChatState>,
    limit: i64,
) -> Result<Vec<ChatMessage>, String> {
    state
        .0
        .lock()
        .unwrap()
        .get_history(limit)
        .map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn clear_chat_history(state: State<'_, ChatState>) -> Result<(), String> {
    state
        .0
        .lock()
        .unwrap()
        .clear_history()
        .map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn send_message(
    state: State<'_, ChatState>,
    text: String,
    mode: String,
    attachments: Vec<ChatAttachment>,
    history: Vec<ChatMessage>,
) -> Result<ChatApiResponse, String> {
    // 1. Save User Message
    if !text.is_empty() {
        state
            .0
            .lock()
            .unwrap()
            .save_message("user", &text)
            .map_err(|e| e.to_string())?;
    }

    // 2. Prepare Payload
    let payload = ChatApiRequest {
        mode,
        text: text.clone(),
        history,
        attachments,
    };

    // 3. Get API URL from settings
    let api_url = get_settings()
        .map(|s| format!("{}/api/chat/send", s.api_base_url))
        .unwrap_or_else(|_| "http://127.0.0.1:5000/api/chat/send".to_string());

    // 4. Call API
    let client = Client::new();
    let res = client
        .post(&api_url)
        .json(&payload)
        .send()
        .await
        .map_err(|e| format!("Failed to connect to API: {}", e))?;

    let api_res: ChatApiResponse = res
        .json()
        .await
        .map_err(|e| format!("Failed to parse API response: {}", e))?;

    // 5. Save Assistant Message if success
    if api_res.ok {
        if let Some(reply) = &api_res.reply {
            let content = reply.text.clone().unwrap_or_default();
            // If it's an image response, save a placeholder
            state
                .0
                .lock()
                .unwrap()
                .save_message("assistant", &content)
                .map_err(|e| e.to_string())?;
        }
    }

    Ok(api_res)
}
