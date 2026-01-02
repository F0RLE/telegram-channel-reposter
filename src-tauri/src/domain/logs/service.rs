//! Centralized Logging Service for Flux Platform
//!
//! Provides in-memory log storage with optional file persistence.
//! Logs are rotated when they exceed the maximum size.

use once_cell::sync::Lazy;
use serde::Serialize;
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::PathBuf;
use std::sync::Mutex;
use std::time::{SystemTime, UNIX_EPOCH};

use crate::utils::paths::LOG_DIR;

/// Log entry structure
#[derive(Debug, Serialize, Clone)]
pub struct LogEntry {
    pub timestamp: f64,
    pub source: String,
    pub level: String,
    pub message: String,
}

/// Log levels for filtering
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum LogLevel {
    Debug = 0,
    Info = 1,
    Warn = 2,
    Error = 3,
}

impl LogLevel {
    pub fn from_str(s: &str) -> Self {
        match s.to_lowercase().as_str() {
            "debug" => LogLevel::Debug,
            "info" | "success" => LogLevel::Info,
            "warn" | "warning" => LogLevel::Warn,
            "error" => LogLevel::Error,
            _ => LogLevel::Info,
        }
    }

    pub fn as_str(&self) -> &'static str {
        match self {
            LogLevel::Debug => "debug",
            LogLevel::Info => "info",
            LogLevel::Warn => "warn",
            LogLevel::Error => "error",
        }
    }
}

/// Configuration for the log store
struct LogConfig {
    max_entries: usize,
    persist_to_file: bool,
    min_level: LogLevel,
}

impl Default for LogConfig {
    fn default() -> Self {
        Self {
            max_entries: 1000,
            persist_to_file: true,
            min_level: LogLevel::Info,
        }
    }
}

/// In-memory log storage with optional file persistence
struct LogStore {
    entries: Vec<LogEntry>,
    config: LogConfig,
}

static LOG_STORE: Lazy<Mutex<LogStore>> = Lazy::new(|| {
    Mutex::new(LogStore {
        entries: Vec::with_capacity(1000),
        config: LogConfig::default(),
    })
});

/// Get the current log file path
fn get_log_file_path() -> PathBuf {
    let now = chrono::Local::now();
    LOG_DIR.join(format!("flux_{}.log", now.format("%Y-%m-%d")))
}

/// Rotate log file if it exceeds 10MB
fn rotate_log_file_if_needed(path: &PathBuf) {
    const MAX_SIZE: u64 = 10 * 1024 * 1024; // 10MB

    if let Ok(metadata) = fs::metadata(path) {
        if metadata.len() > MAX_SIZE {
            // Rename to .old and start fresh
            let old_path = path.with_extension("old.log");
            let _ = fs::rename(path, old_path);
        }
    }
}

/// Add a log entry
pub fn add_log(message: &str, source: &str, level: &str) {
    let mut store = LOG_STORE.lock().unwrap();

    let log_level = LogLevel::from_str(level);

    // Skip if below minimum level
    if log_level < store.config.min_level {
        return;
    }

    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs_f64();

    let entry = LogEntry {
        timestamp: now,
        source: source.to_string(),
        level: level.to_string(),
        message: message.to_string(),
    };

    // Add to memory store
    store.entries.push(entry.clone());

    // Trim if over capacity
    if store.entries.len() > store.config.max_entries {
        store.entries.drain(0..100); // Remove oldest 100
    }

    // Persist to file
    if store.config.persist_to_file {
        drop(store); // Release lock before file I/O
        persist_log_entry(&entry);
    }
}

/// Persist a log entry to file
fn persist_log_entry(entry: &LogEntry) {
    let path = get_log_file_path();

    // Ensure log directory exists
    if let Some(parent) = path.parent() {
        let _ = fs::create_dir_all(parent);
    }

    rotate_log_file_if_needed(&path);

    if let Ok(mut file) = OpenOptions::new().create(true).append(true).open(&path) {
        let timestamp = chrono::Local::now().format("%Y-%m-%d %H:%M:%S%.3f");
        let line = format!(
            "[{}] [{}] [{}] {}\n",
            timestamp,
            entry.level.to_uppercase(),
            entry.source,
            entry.message
        );
        let _ = file.write_all(line.as_bytes());
    }
}

/// Get logs since a given timestamp
pub fn get_logs_since(since: f64) -> Vec<LogEntry> {
    let store = LOG_STORE.lock().unwrap();
    store
        .entries
        .iter()
        .filter(|e| e.timestamp > since)
        .cloned()
        .collect()
}

/// Get recent logs with limit
pub fn get_recent_logs(limit: usize) -> Vec<LogEntry> {
    let store = LOG_STORE.lock().unwrap();
    store
        .entries
        .iter()
        .rev()
        .take(limit)
        .cloned()
        .collect::<Vec<_>>()
        .into_iter()
        .rev()
        .collect()
}

/// Get logs filtered by level
pub fn get_logs_by_level(level: &str, limit: usize) -> Vec<LogEntry> {
    let store = LOG_STORE.lock().unwrap();
    store
        .entries
        .iter()
        .filter(|e| e.level.to_lowercase() == level.to_lowercase())
        .rev()
        .take(limit)
        .cloned()
        .collect::<Vec<_>>()
        .into_iter()
        .rev()
        .collect()
}

/// Clear all in-memory logs
pub fn clear_logs() {
    let mut store = LOG_STORE.lock().unwrap();
    store.entries.clear();
}

/// Set minimum log level
pub fn set_min_level(level: &str) {
    let mut store = LOG_STORE.lock().unwrap();
    store.config.min_level = LogLevel::from_str(level);
}

/// Enable or disable file persistence
pub fn set_persist_to_file(enabled: bool) {
    let mut store = LOG_STORE.lock().unwrap();
    store.config.persist_to_file = enabled;
}

// Convenience functions for different log levels
pub fn log_debug(source: &str, message: &str) {
    add_log(message, source, "debug");
}

pub fn log_info(source: &str, message: &str) {
    add_log(message, source, "info");
}

pub fn log_warn(source: &str, message: &str) {
    add_log(message, source, "warn");
}

pub fn log_error(source: &str, message: &str) {
    add_log(message, source, "error");
}
