use crate::domain::settings::models::AppSettings;
use crate::domain::settings::{self};
use crate::errors::AppError;

#[tauri::command]
pub async fn get_settings() -> Result<AppSettings, AppError> {
    settings::get_settings()
}

#[tauri::command]
pub async fn save_settings(settings: AppSettings) -> Result<(), AppError> {
    settings::save_settings(settings)
}

#[tauri::command]
pub fn get_system_language() -> String {
    settings::get_language()
}
