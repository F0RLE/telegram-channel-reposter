use crate::domain::chat::models::{ChatApiResponse, ChatAttachment, ChatMessage};

#[async_trait::async_trait]
pub trait AiService: Send + Sync {
    async fn send_message(
        &self,
        text: &str,
        mode: &str,
        attachments: Vec<ChatAttachment>,
        history: Vec<ChatMessage>,
    ) -> Result<ChatApiResponse, String>;
}
