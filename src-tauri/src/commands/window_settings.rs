// Window settings commands for frontend

use crate::errors::AppError;
use crate::services::window_settings::{self, WindowSettings};

#[tauri::command]
pub fn get_window_settings() -> WindowSettings {
    window_settings::load_window_settings()
}

#[tauri::command]
pub fn save_window_size(width: u32, height: u32) -> Result<(), AppError> {
    window_settings::update_window_size(width, height)
}

#[tauri::command]
pub fn save_window_position(x: i32, y: i32) -> Result<(), AppError> {
    window_settings::update_window_position(x, y)
}

#[tauri::command]
pub fn save_maximized_state(maximized: bool) -> Result<(), AppError> {
    window_settings::update_maximized_state(maximized)
}

#[tauri::command]
pub fn save_zoom_level(zoom: f64) -> Result<(), AppError> {
    window_settings::update_zoom_level(zoom)
}
