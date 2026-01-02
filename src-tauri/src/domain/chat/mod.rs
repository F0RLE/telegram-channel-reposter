//! Chat Domain
//!
//! Handles chat messages, history, and AI API communication.

pub mod handlers;
pub mod models;
pub mod service;

// Only export what's needed, avoid duplicate exports
pub use models::{ChatApiReply, ChatApiRequest, ChatApiResponse, ChatAttachment, ChatMessage};
pub use service::{ChatManager, ChatState};
