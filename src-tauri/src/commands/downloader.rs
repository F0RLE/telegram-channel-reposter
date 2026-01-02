use crate::services::downloader::DownloadManager;
use tauri::State;

#[tauri::command]
pub async fn start_download(
    manager: State<'_, DownloadManager>,
    url: String,
    filename: String,
) -> Result<String, String> {
    manager.download_file(url, filename).await
}

#[tauri::command]
pub async fn cancel_download(
    manager: State<'_, DownloadManager>,
    id: String,
) -> Result<(), String> {
    manager.cancel_download(&id);
    Ok(())
}
