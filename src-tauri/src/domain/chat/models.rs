//! Chat Domain Models
//!
//! Data structures for chat messages, attachments, and API responses.

use serde::{Deserialize, Serialize};
use specta::Type;

/// A chat message stored in the database
#[derive(Debug, Serialize, Deserialize, Clone, Type)]
pub struct ChatMessage {
    pub id: Option<i64>,
    pub role: String,
    pub content: String,
    pub timestamp: i64,
}

/// File attachment for chat messages
#[derive(Debug, Serialize, Deserialize, Type)]
pub struct ChatAttachment {
    pub name: String,
    pub r#type: String,
    pub size: i64,
    pub data_base64: String,
}

/// Request payload for the AI API
#[derive(Debug, Serialize, Deserialize)]
pub struct ChatApiRequest {
    pub mode: String,
    pub text: String,
    pub history: Vec<ChatMessage>,
    pub attachments: Vec<ChatAttachment>,
}

/// Response from the AI API
#[derive(Debug, Serialize, Deserialize, Type)]
pub struct ChatApiResponse {
    pub ok: bool,
    pub reply: Option<ChatApiReply>,
    pub error: Option<String>,
}

/// Reply content from the AI
#[derive(Debug, Serialize, Deserialize, Type)]
pub struct ChatApiReply {
    pub text: Option<String>,
    pub r#type: Option<String>,
    pub images: Option<Vec<String>>, // base64 images
}
