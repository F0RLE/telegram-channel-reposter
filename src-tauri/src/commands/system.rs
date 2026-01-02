use crate::domain::monitoring::models::SystemStats;
use crate::domain::monitoring::{self as system_monitor};

#[tauri::command]
pub fn get_system_stats() -> SystemStats {
    system_monitor::get_stats()
}

#[tauri::command]
pub fn get_gpu_info() -> String {
    // В будущем тут будет вызов сервиса с nvidia-smi логикой из Python
    "NVIDIA GeForce RTX 4090 (Simulated)".to_string()
}
