use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize)]
pub struct ControlRequest {
    pub module_id: Option<String>,
    pub action: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ControlResponse {
    pub success: bool,
    pub message: String,
    pub status: Option<String>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ModuleItem {
    pub id: String,
    pub name: Option<String>,
    pub version: Option<String>,
    pub description: Option<String>,
    pub r#type: Option<String>,
    pub kind: Option<String>,
    pub status: Option<String>,
    pub installed: Option<bool>,
    pub icon: Option<String>,
    pub removable: Option<bool>,
    pub recommended: Option<bool>,
    pub repo: Option<String>,
    pub custom: Option<bool>,
}
