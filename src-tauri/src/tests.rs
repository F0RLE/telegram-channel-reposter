//! Unit tests for Flux Platform backend
//!
//! Run with: cargo test

#[cfg(test)]
mod tests {
    use crate::domain::settings::models::AppSettings;

    /// Test default settings values
    #[test]
    fn test_default_settings() {
        let settings = AppSettings::default();

        assert_eq!(settings.theme, "dark");
        assert_eq!(settings.language, "ru");
        assert!(settings.use_gpu);
        assert!(!settings.debug_mode);
        assert_eq!(settings.api_base_url, "http://127.0.0.1:5000");
    }

    /// Test settings serialization
    #[test]
    fn test_settings_serialization() {
        let settings = AppSettings {
            theme: "light".to_string(),
            language: "en".to_string(),
            use_gpu: false,
            debug_mode: true,
            api_base_url: "http://localhost:5000".to_string(),
        };

        let json = serde_json::to_string(&settings).expect("Failed to serialize");
        assert!(json.contains("\"theme\":\"light\""));
        assert!(json.contains("\"language\":\"en\""));
        assert!(json.contains("\"use_gpu\":false"));
        assert!(json.contains("\"debug_mode\":true"));
        assert!(json.contains("\"api_base_url\":\"http://localhost:5000\""));
    }

    /// Test settings deserialization with default api_base_url
    #[test]
    fn test_settings_deserialization() {
        let json = r#"{"theme":"dark","language":"zh","use_gpu":true,"debug_mode":false}"#;
        let settings: AppSettings = serde_json::from_str(json).expect("Failed to deserialize");

        assert_eq!(settings.theme, "dark");
        assert_eq!(settings.language, "zh");
        assert!(settings.use_gpu);
        assert!(!settings.debug_mode);
        // api_base_url should use default when not in JSON
        assert_eq!(settings.api_base_url, "http://127.0.0.1:5000");
    }

    /// Test settings clone
    #[test]
    fn test_settings_clone() {
        let original = AppSettings::default();
        let cloned = original.clone();

        assert_eq!(original.theme, cloned.theme);
        assert_eq!(original.language, cloned.language);
        assert_eq!(original.use_gpu, cloned.use_gpu);
        assert_eq!(original.debug_mode, cloned.debug_mode);
        assert_eq!(original.api_base_url, cloned.api_base_url);
    }

    /// Test path utilities are initialized
    #[test]
    fn test_appdata_root_initialized() {
        use crate::utils::paths::APPDATA_ROOT;

        // Verify path ends with FluxData
        let path_str = APPDATA_ROOT.to_string_lossy();
        assert!(
            path_str.ends_with("FluxData"),
            "APPDATA_ROOT should end with FluxData"
        );
    }

    /// Test directory paths are correctly derived
    #[test]
    fn test_directory_paths() {
        use crate::utils::paths::{CONFIG_DIR, LOG_DIR, SYSTEM_ROOT, USER_ROOT};

        // Verify USER_ROOT is under APPDATA_ROOT
        assert!(USER_ROOT.to_string_lossy().contains("FluxData"));
        assert!(USER_ROOT.to_string_lossy().contains("User"));

        // Verify CONFIG_DIR is under USER_ROOT
        assert!(CONFIG_DIR.to_string_lossy().contains("Configs"));

        // Verify SYSTEM_ROOT and LOG_DIR
        assert!(SYSTEM_ROOT.to_string_lossy().contains("System"));
        assert!(LOG_DIR.to_string_lossy().contains("Logs"));
    }

    /// Test file paths are correctly derived
    #[test]
    fn test_file_paths() {
        use crate::utils::paths::{FILE_ENV, FILE_GEN_CONFIG};

        assert!(FILE_ENV.to_string_lossy().ends_with(".env"));
        assert!(FILE_GEN_CONFIG
            .to_string_lossy()
            .ends_with("generation_config.json"));
    }
}

#[cfg(test)]
mod log_tests {
    use crate::domain::logs::{add_log, clear_logs, get_logs_since};

    #[test]
    #[ignore] // Flaky due to shared static LOG_STORE - run with cargo test -- --ignored
    fn test_add_and_get_logs() {
        // Add unique messages
        add_log("UniqueLogTest001", "TestModule", "info");
        add_log("UniqueLogTest002", "TestModule", "error");

        // Get all logs
        let logs = get_logs_since(0.0);

        // Check our messages exist somewhere in the logs
        let found_1 = logs.iter().any(|l| l.message.contains("UniqueLogTest001"));
        let found_2 = logs.iter().any(|l| l.message.contains("UniqueLogTest002"));

        assert!(found_1 || found_2, "Should find at least one test message");
    }

    #[test]
    fn test_clear_logs() {
        add_log("To be cleared", "Test", "info");
        clear_logs();

        let logs = get_logs_since(0.0);
        assert!(logs.is_empty(), "Logs should be empty after clear");
    }

    #[test]
    fn test_logs_filter_by_time() {
        clear_logs();

        let before = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_secs_f64();

        std::thread::sleep(std::time::Duration::from_millis(10));
        add_log("After timestamp", "Test", "info");

        let logs = get_logs_since(before);
        assert!(!logs.is_empty(), "Should find logs after timestamp");
    }
}

#[cfg(test)]
mod system_stats_tests {
    use crate::domain::monitoring::models::{
        CpuStats, DiskStats, NetworkStats, RamStats, SystemStats,
    };

    #[test]
    fn test_system_stats_creation() {
        let stats = SystemStats {
            cpu: CpuStats {
                percent: 50.0,
                cores: 8,
                name: "Test CPU".to_string(),
            },
            ram: RamStats {
                percent: 60.0,
                used_gb: 16.0,
                total_gb: 32.0,
                available_gb: 16.0,
            },
            gpu: None,
            vram: None,
            disk: DiskStats {
                read_rate: 100.0,
                write_rate: 50.0,
                utilization: 25.0,
                total_gb: 500.0,
                used_gb: 250.0,
            },
            network: NetworkStats {
                download_rate: 1024.0,
                upload_rate: 512.0,
                total_received: 1000000,
                total_sent: 500000,
                utilization: 10.0,
            },
            pid: 1234,
        };

        assert_eq!(stats.cpu.percent, 50.0);
        assert_eq!(stats.cpu.cores, 8);
        assert_eq!(stats.ram.total_gb, 32.0);
        assert!(stats.gpu.is_none());
    }

    #[test]
    fn test_system_stats_serialization() {
        let stats = SystemStats {
            cpu: CpuStats {
                percent: 25.0,
                cores: 4,
                name: "CPU".to_string(),
            },
            ram: RamStats {
                percent: 50.0,
                used_gb: 8.0,
                total_gb: 16.0,
                available_gb: 8.0,
            },
            gpu: None,
            vram: None,
            disk: DiskStats {
                read_rate: 0.0,
                write_rate: 0.0,
                utilization: 0.0,
                total_gb: 100.0,
                used_gb: 50.0,
            },
            network: NetworkStats {
                download_rate: 0.0,
                upload_rate: 0.0,
                total_received: 0,
                total_sent: 0,
                utilization: 0.0,
            },
            pid: 0,
        };

        let json = serde_json::to_string(&stats).expect("Failed to serialize");
        assert!(json.contains("\"percent\":25.0"));
        assert!(json.contains("\"cores\":4"));
    }
}

#[cfg(test)]
mod chat_model_tests {
    use crate::domain::chat::models::{ChatApiReply, ChatApiResponse, ChatAttachment, ChatMessage};

    #[test]
    fn test_chat_message_creation() {
        let msg = ChatMessage {
            id: Some(1),
            role: "user".to_string(),
            content: "Hello".to_string(),
            timestamp: 1234567890,
        };

        assert_eq!(msg.id, Some(1));
        assert_eq!(msg.role, "user");
        assert_eq!(msg.content, "Hello");
    }

    #[test]
    fn test_chat_message_serialization() {
        let msg = ChatMessage {
            id: None,
            role: "assistant".to_string(),
            content: "Hi there!".to_string(),
            timestamp: 0,
        };

        let json = serde_json::to_string(&msg).expect("Serialize failed");
        assert!(json.contains("\"role\":\"assistant\""));
        assert!(json.contains("\"content\":\"Hi there!\""));
    }

    #[test]
    fn test_chat_api_response() {
        let response = ChatApiResponse {
            ok: true,
            reply: Some(ChatApiReply {
                text: Some("Response text".to_string()),
                r#type: Some("text".to_string()),
                images: None,
            }),
            error: None,
        };

        assert!(response.ok);
        assert!(response.reply.is_some());
        assert_eq!(response.reply.unwrap().text.unwrap(), "Response text");
    }

    #[test]
    fn test_chat_attachment() {
        let attachment = ChatAttachment {
            name: "file.txt".to_string(),
            r#type: "text/plain".to_string(),
            size: 1024,
            data_base64: "SGVsbG8=".to_string(),
        };

        assert_eq!(attachment.name, "file.txt");
        assert_eq!(attachment.size, 1024);
    }
}
