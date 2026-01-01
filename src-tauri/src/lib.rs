pub mod commands;
pub mod errors;
pub mod models;
pub mod services;
pub mod utils;

use commands::*;
use tauri::{
    menu::{Menu, MenuItem},
    tray::TrayIconBuilder,
    Manager,
};

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    // Initialize logging
    env_logger::init();
    log::info!("🚀 Starting Flux Platform");

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![
            health::get_health,
            settings::get_settings,
            settings::save_settings,
            settings::get_system_language,
            logs::get_logs,
            logs::clear_logs,
            logs::add_log,
            downloader::start_download,
            system::get_system_stats,
            system::get_gpu_info,
            modules::get_modules,
            modules::control_module,
            window::minimize_window,
            window::maximize_window,
            window::close_window,
            translations::get_translations,
            // License commands
            license::get_license_status,
            license::activate_license,
            license::deactivate_license,
            license::check_feature,
            theme::get_theme_colors,
            // Window settings commands
            window_settings::get_window_settings,
            window_settings::save_window_size,
            window_settings::save_window_position,
            window_settings::save_maximized_state,
            window_settings::save_zoom_level,
        ])
        .setup(|app| {
            // Initialize directories
            crate::utils::paths::init_filesystem().ok();

            // Initialize process group (Windows Job Objects)
            crate::utils::process::init_process_group();

            // Start system monitoring with events
            services::system_monitor::start_monitoring(app.handle().clone(), 1000);

            // Setup System Tray
            setup_system_tray(app)?;

            log::info!("✅ Setup complete");
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

/// Setup system tray icon with menu
fn setup_system_tray(app: &tauri::App) -> Result<(), Box<dyn std::error::Error>> {
    // Create menu items
    let show_item = MenuItem::with_id(app, "show", "Показать", true, None::<&str>)?;
    let separator = MenuItem::with_id(app, "sep", "─────────", false, None::<&str>)?;
    let quit_item = MenuItem::with_id(app, "quit", "Выход", true, None::<&str>)?;

    // Create menu
    let menu = Menu::with_items(app, &[&show_item, &separator, &quit_item])?;

    // Build tray icon
    let _tray = TrayIconBuilder::new()
        .icon(app.default_window_icon().unwrap().clone())
        .tooltip("Flux Platform")
        .menu(&menu)
        .show_menu_on_left_click(false)
        .on_menu_event(|app, event| match event.id.as_ref() {
            "show" => {
                if let Some(window) = app.get_webview_window("main") {
                    let _ = window.unminimize();
                    let _ = window.show();
                    let _ = window.set_focus();
                }
            }
            "quit" => {
                // Graceful shutdown
                services::system_monitor::stop_monitoring();
                app.exit(0);
            }
            _ => {}
        })
        .on_tray_icon_event(|tray, event| {
            if let tauri::tray::TrayIconEvent::DoubleClick { .. } = event {
                let app = tray.app_handle();
                if let Some(window) = app.get_webview_window("main") {
                    let _ = window.unminimize();
                    let _ = window.show();
                    let _ = window.set_focus();
                }
            }
        })
        .build(app)?;

    log::info!("🔔 System tray initialized");
    Ok(())
}
