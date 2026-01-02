use crate::errors::AppError;
use serde::{Deserialize, Serialize};
use std::str::FromStr;

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

#[derive(Debug)]
pub enum ModuleAction {
    Install,
    Uninstall,
    Start,
    Stop,
    Restart,
    Update,
}

impl FromStr for ModuleAction {
    type Err = AppError;
    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s.to_lowercase().as_str() {
            "install" => Ok(ModuleAction::Install),
            "uninstall" => Ok(ModuleAction::Uninstall),
            "start" => Ok(ModuleAction::Start),
            "stop" => Ok(ModuleAction::Stop),
            "restart" => Ok(ModuleAction::Restart),
            "update" => Ok(ModuleAction::Update),
            _ => Err(AppError::Validation(format!("Unknown action: {}", s))),
        }
    }
}
