use crate::errors::AppError;
use tauri::AppHandle;

pub fn get_translations(_app: &AppHandle, lang: &str) -> Result<serde_json::Value, AppError> {
    let json_content = match lang {
        "en" => Some(include_str!("../../../resources/locales/en.json")),
        "ru" => Some(include_str!("../../../resources/locales/ru.json")),
        "zh" => Some(include_str!("../../../resources/locales/zh.json")),
        _ => None,
    };

    let content =
        json_content.ok_or_else(|| AppError::NotFound(format!("Locale '{}' not found", lang)))?;

    serde_json::from_str(content).map_err(|e| AppError::Serialization(e))
}
