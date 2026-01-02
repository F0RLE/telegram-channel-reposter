pub mod chat;
pub mod license;
pub mod logs;
pub mod module_controller;
pub mod module_lifecycle;
pub mod settings;
pub mod system_monitor;
pub mod theme;
pub mod translations;
pub mod window_settings;

pub mod health {
    pub fn check() -> String {
        "Healthy".to_string()
    }
}

pub mod downloader;
