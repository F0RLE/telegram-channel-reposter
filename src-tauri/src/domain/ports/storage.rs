use crate::domain::chat::models::ChatMessage;
use rusqlite::Result;

pub trait ChatStorage: Send + Sync {
    fn save_message(&self, role: &str, content: &str) -> Result<i64, String>;
    fn get_history(&self, limit: i64) -> Result<Vec<ChatMessage>, String>;
    fn clear_history(&self) -> Result<(), String>;
}
