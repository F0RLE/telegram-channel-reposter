use crate::domain::chat::models::{ChatApiRequest, ChatApiResponse, ChatAttachment, ChatMessage};
use crate::domain::ports::ai::AiService;
use reqwest::Client;

pub struct PythonAiClient {
    base_url: String,
    client: Client,
}

impl PythonAiClient {
    pub fn new(base_url: String) -> Self {
        Self {
            base_url,
            client: Client::new(),
        }
    }
}

#[async_trait::async_trait]
impl AiService for PythonAiClient {
    async fn send_message(
        &self,
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

        let api_url = format!("{}/api/chat/send", self.base_url);

        let res = self
            .client
            .post(&api_url)
            .json(&payload)
            .send()
            .await
            .map_err(|e| format!("Failed to connect to API: {}", e))?;

        res.json()
            .await
            .map_err(|e| format!("Failed to parse API response: {}", e))
    }
}
