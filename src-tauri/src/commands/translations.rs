use crate::domain::settings::translations;
use crate::errors::AppError;
use tauri::AppHandle;

#[tauri::command]
pub fn get_translations(app: AppHandle, lang: String) -> Result<serde_json::Value, AppError> {
    translations::get_translations(&app, &lang)
}
