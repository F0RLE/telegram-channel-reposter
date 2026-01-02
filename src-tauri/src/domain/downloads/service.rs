use reqwest::header::CONTENT_LENGTH;
use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::{Arc, Mutex};
use tauri::{AppHandle, Emitter, Manager};
use tokio::io::AsyncWriteExt;

#[derive(Clone, serde::Serialize)]
pub struct DownloadProgress {
    pub id: String,
    pub current: u64,
    pub total: u64,
    pub speed: u64, // bytes per second
    pub percent: f64,
    pub completed: bool,
    pub error: Option<String>,
}

pub struct DownloadManager {
    app: AppHandle,
    tasks: Arc<Mutex<HashMap<String, tauri::async_runtime::JoinHandle<()>>>>,
}

impl DownloadManager {
    pub fn new(app: AppHandle) -> Self {
        Self {
            app,
            tasks: Arc::new(Mutex::new(HashMap::new())),
        }
    }

    pub async fn download_file(&self, url: String, filename: String) -> Result<String, String> {
        let app_handle = self.app.clone();
        let download_id = uuid::Uuid::new_v4().to_string();
        let tasks = self.tasks.clone();
        let download_id_clone = download_id.clone();

        // Define paths
        let app_dir = app_handle.path().app_data_dir().unwrap();
        let models_dir = app_dir.join("models");
        if !models_dir.exists() {
            std::fs::create_dir_all(&models_dir).map_err(|e| e.to_string())?;
        }
        let file_path = models_dir.join(&filename);

        // Spawn async task
        let handle = tauri::async_runtime::spawn(async move {
            if let Err(e) =
                Self::download_task(app_handle, download_id_clone.clone(), url, file_path).await
            {
                // Emit error
                let _ = crate::services::logs::add_log(
                    &format!("Download failed: {}", e),
                    "Downloader",
                    "error",
                );
            }
            // Cleanup task
            // Note: In a real implementation we would remove from HashMap here, but we need a way to access the map inside the task or use a callbacks
        });

        // Store handle
        tasks.lock().unwrap().insert(download_id.clone(), handle);

        Ok(download_id)
    }

    async fn download_task(
        app: AppHandle,
        id: String,
        url: String,
        path: PathBuf,
    ) -> Result<(), String> {
        let client = reqwest::Client::new();
        let res = client.get(&url).send().await.map_err(|e| e.to_string())?;

        if !res.status().is_success() {
            return Err(format!("HTTP Error: {}", res.status()));
        }

        let total_size = res
            .headers()
            .get(CONTENT_LENGTH)
            .and_then(|ct_len| ct_len.to_str().ok())
            .and_then(|ct_len| ct_len.parse::<u64>().ok())
            .unwrap_or(0);

        let mut file = tokio::fs::File::create(&path)
            .await
            .map_err(|e| e.to_string())?;
        let mut stream = res.bytes_stream();

        let mut downloaded: u64 = 0;
        let start_time = std::time::Instant::now();
        let mut last_update = std::time::Instant::now();

        use futures_util::StreamExt;

        while let Some(item) = stream.next().await {
            let chunk = item.map_err(|e| e.to_string())?;
            file.write_all(&chunk).await.map_err(|e| e.to_string())?;
            downloaded += chunk.len() as u64;

            // Emit progress every 500ms
            if last_update.elapsed().as_millis() > 500 {
                let duration = start_time.elapsed().as_secs_f64();
                let speed = if duration > 0.0 {
                    (downloaded as f64 / duration) as u64
                } else {
                    0
                };
                let percent = if total_size > 0 {
                    (downloaded as f64 / total_size as f64) * 100.0
                } else {
                    0.0
                };

                let progress = DownloadProgress {
                    id: id.clone(),
                    current: downloaded,
                    total: total_size,
                    speed,
                    percent,
                    completed: false,
                    error: None,
                };

                let _ = app.emit("download://progress", &progress);
                last_update = std::time::Instant::now();
            }
        }

        // Final completion event
        let progress = DownloadProgress {
            id: id.clone(),
            current: downloaded,
            total: total_size,
            speed: 0,
            percent: 100.0,
            completed: true,
            error: None,
        };
        let _ = app.emit("download://progress", &progress);

        crate::services::logs::add_log(
            &format!("Download completed: {}", path.display()),
            "Downloader",
            "success",
        );

        Ok(())
    }

    pub fn cancel_download(&self, id: &str) {
        if let Some(task) = self.tasks.lock().unwrap().remove(id) {
            task.abort();
            // Ideally we should also delete the partial file
        }
    }
}
