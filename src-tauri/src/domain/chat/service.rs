//! Chat Domain Service
//!
//! Manages chat history and AI communication using Hexagonal Architecture (Ports).

use tauri::async_runtime::Mutex;

use super::models::{ChatApiResponse, ChatAttachment, ChatMessage};
use crate::domain::ports::{ai::AiService, storage::ChatStorage};

/// Manages chat logic, delegating persistence and AI to ports
pub struct ChatManager {
    storage: Box<dyn ChatStorage>,
    ai: Box<dyn AiService>,
}

impl ChatManager {
    /// Create a new ChatManager with injected dependencies
    pub fn new(storage: Box<dyn ChatStorage>, ai: Box<dyn AiService>) -> Self {
        Self { storage, ai }
    }

    /// Save a message to history
    pub fn save_message(&self, role: &str, content: &str) -> Result<i64, String> {
        self.storage.save_message(role, content)
    }

    /// Get chat history
    pub fn get_history(&self, limit: i64) -> Result<Vec<ChatMessage>, String> {
        self.storage.get_history(limit)
    }

    /// Clear all history
    pub fn clear_history(&self) -> Result<(), String> {
        self.storage.clear_history()
    }

    /// Send message to AI and return response
    /// Note: This is now just a proxy to the AI port, but could contain domain logic (e.g. prompt engineering)
    pub async fn send_message(
        &self,
        text: &str,
        mode: &str,
        attachments: Vec<ChatAttachment>,
        history: Vec<ChatMessage>,
    ) -> Result<ChatApiResponse, String> {
        self.ai.send_message(text, mode, attachments, history).await
    }
}

/// State wrapper for Tauri
pub struct ChatState(pub Mutex<ChatManager>);
