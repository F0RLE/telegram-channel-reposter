use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct AppSettings {
    pub theme: String,
    pub language: String,
    pub use_gpu: bool,
    pub debug_mode: bool,
    #[serde(default = "default_api_base_url")]
    pub api_base_url: String,
}

fn default_api_base_url() -> String {
    "http://127.0.0.1:5000".to_string()
}

impl Default for AppSettings {
    fn default() -> Self {
        Self {
            theme: "dark".to_string(),
            language: "ru".to_string(),
            use_gpu: true,
            debug_mode: false,
            api_base_url: default_api_base_url(),
        }
    }
}
