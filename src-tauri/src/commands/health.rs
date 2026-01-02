use crate::domain::monitoring::health;

#[tauri::command]
pub fn get_health() -> String {
    health::check()
}
