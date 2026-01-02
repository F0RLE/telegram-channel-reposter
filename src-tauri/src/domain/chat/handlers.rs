//! Chat Domain Command Handlers
//!
//! Tauri command handlers for chat functionality.

use super::service::ChatState;
use crate::domain::chat::models::{ChatApiResponse, ChatAttachment, ChatMessage};
use tauri::State;

#[tauri::command]
pub async fn save_chat_message(
    state: State<'_, ChatState>,
    role: String,
    content: String,
) -> Result<i64, String> {
    state
        .0
        .lock()
        .await
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
        .await
        .get_history(limit)
        .map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn clear_chat_history(state: State<'_, ChatState>) -> Result<(), String> {
    state
        .0
        .lock()
        .await
        .clear_history()
        .map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn send_message(
    state: State<'_, ChatState>,
    text: String,
    mode: String,
    attachments: Vec<ChatAttachment>,
) -> Result<ChatApiResponse, String> {
    let manager = state.0.lock().await;

    // 1. Save User Message
    if !text.is_empty() {
        manager
            .save_message("user", &text)
            .map_err(|e| e.to_string())?;
    }

    // 2. Get context (last 10 messages)
    let history = manager.get_history(10).map_err(|e| e.to_string())?;

    // 3. Call AI API (holding lock is acceptable for this single-user app)
    let response = manager
        .send_message(&text, &mode, attachments, history)
        .await
        .map_err(|e| e.to_string())?;

    // 4. Save Assistant Message
    if let Some(reply) = &response.reply {
        if let Some(reply_text) = &reply.text {
            manager
                .save_message("assistant", reply_text)
                .map_err(|e| e.to_string())?;
        }
    }

    Ok(response)
}
