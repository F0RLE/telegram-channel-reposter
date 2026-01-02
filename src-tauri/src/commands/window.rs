use crate::domain::monitoring::{self as system_monitor};
use tauri::Manager;

#[tauri::command]
pub fn minimize_window(window: tauri::Window) {
    let _ = window.minimize();
}

#[tauri::command]
pub fn maximize_window(window: tauri::Window) {
    if window.is_maximized().unwrap_or(false) {
        let _ = window.unmaximize();
    } else {
        let _ = window.maximize();
    }
}

#[tauri::command]
pub fn close_window(window: tauri::Window) {
    // Graceful shutdown: stop monitoring before exit
    system_monitor::stop_monitoring();
    window.app_handle().exit(0);
}
