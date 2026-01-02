import { removeQuotes } from '@core/utils/string';
import { invoke, listen } from '@core/api';

declare function showToast(message: string, type: string, duration?: number, title?: string): void;
declare function t(key: string, fallback?: string): string;
declare function loadSdModels(): void;

// Download state
let currentDownloadId: string | null = null;
let unlistenProgress: (() => void) | null = null;

interface DownloadProgress {
    id: string;
    current: number;
    total: number;
    speed: number;
    percent: number;
    completed: boolean;
    error: string | null;
}

/**
 * Start downloading a model from URL
 */
export async function downloadModel(): Promise<void> {
    const urlField = document.getElementById('field-sd-model-url') as HTMLInputElement | null;
    let url = urlField?.value?.trim();

    if (!url || url === '') {
        showToast(t('ui.launcher.web.no_model_url', 'Введите URL модели'), 'error');
        return;
    }

    // Clean the URL from quotes
    url = removeQuotes(url);

    if (!url || url === '' || url === '\\' || url === "'" || url === '"') {
        showToast(t('ui.launcher.web.no_model_url', 'Введите URL модели'), 'error');
        return;
    }

    // Update the field with cleaned URL
    if (urlField) urlField.value = url;

    if (!url.startsWith('http')) {
        showToast(t('ui.launcher.web.invalid_url', 'Некорректный URL'), 'error');
        return;
    }

    showToast(t('ui.launcher.web.download_starting', 'Начало загрузки модели...'), 'success');

    // Show progress modal
    const modal = document.getElementById('model-download-modal');
    const modelNameEl = document.getElementById('download-model-name');
    const progressBarEl = document.getElementById('download-progress-bar') as HTMLElement;
    const progressTextEl = document.getElementById('download-progress-text');
    const speedTextEl = document.getElementById('download-speed-text');
    const downloadedEl = document.getElementById('download-downloaded');
    const totalEl = document.getElementById('download-total');

    if (modal) {
        modal.style.display = 'flex';
        modal.classList.add('show');

        // Extract filename
        const urlParts = url.split('/');
        let modelName = urlParts[urlParts.length - 1] || 'model.safetensors';
        // Remove query params if any
        if (modelName.includes('?')) modelName = modelName.split('?')[0];

        if (modelNameEl) modelNameEl.textContent = modelName;

        // Reset progress
        if (progressBarEl) progressBarEl.style.width = '0%';
        if (progressTextEl) progressTextEl.textContent = '0%';
        if (speedTextEl) speedTextEl.textContent = '0 KB/s';
        if (downloadedEl) downloadedEl.textContent = '0 MB';
        if (totalEl) totalEl.textContent = '-- MB';

        try {
            // Unlisten previous if any
            if (unlistenProgress) {
                unlistenProgress();
                unlistenProgress = null;
            }

            // Listen for progress
            unlistenProgress = await listen<DownloadProgress>('download://progress', (event) => {
                const progress = event.payload;
                if (progress.id !== currentDownloadId) return;

                const percent = progress.percent || 0;
                const downloaded = progress.current || 0;
                const total = progress.total || 0;
                const speed = progress.speed || 0;

                if (progressBarEl) progressBarEl.style.width = percent + '%';
                if (progressTextEl) progressTextEl.textContent = percent.toFixed(1) + '%';

                const downloadedMB = (downloaded / (1024 * 1024)).toFixed(1);
                const totalMB = total > 0 ? (total / (1024 * 1024)).toFixed(1) : '--';
                if (downloadedEl) downloadedEl.textContent = downloadedMB + ' MB';
                if (totalEl) totalEl.textContent = totalMB + ' MB';

                const speedKB = (speed / 1024).toFixed(1);
                if (speedTextEl) speedTextEl.textContent = speedKB + ' KB/s';

                if (progress.completed) {
                    cleanup();
                    setTimeout(() => {
                        hideModelDownloadModal();
                        showToast(t('ui.launcher.web.download_complete', 'Модель успешно загружена'), 'success');
                        loadSdModels();
                    }, 500);
                } else if (progress.error) {
                    cleanup();
                    hideModelDownloadModal();
                    showToast(t('ui.launcher.web.download_error', 'Ошибка загрузки') + ': ' + progress.error, 'error');
                }
            });

            // Start download
            currentDownloadId = await invoke<string>('start_download', { url, filename: modelName });

        } catch (e: any) {
            console.error('Download error:', e);
            cleanup();
            hideModelDownloadModal();
            showToast(t('ui.launcher.web.download_error', 'Ошибка загрузки') + ': ' + e.message, 'error');
        }
    }
}

function cleanup() {
    if (unlistenProgress) {
        unlistenProgress();
        unlistenProgress = null;
    }
    currentDownloadId = null;
}

/**
 * Cancel ongoing model download
 */
export function cancelModelDownload(): void {
    if (currentDownloadId) {
        invoke('cancel_download', { id: currentDownloadId }).catch(console.error);
    }
    cleanup();
    hideModelDownloadModal();
    showToast(t('ui.launcher.web.download_cancelled', 'Загрузка отменена'), 'warning');
}

/**
 * Hide the download progress modal
 */
export function hideModelDownloadModal(): void {
    const modal = document.getElementById('model-download-modal');
    if (modal) {
        modal.style.display = 'none';
        modal.classList.remove('show');
    }
    cleanup();
}

// Register on window for backward compatibility
window.downloadModel = downloadModel;
window.cancelModelDownload = cancelModelDownload;
window.hideModelDownloadModal = hideModelDownloadModal;


