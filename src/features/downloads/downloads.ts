
import { listen } from '@tauri-apps/api/event';

interface DownloadProgressPayload {
    id: string;
    current: number;
    total: number;
    speed: number;
    percent: number;
    completed: boolean;
    error: string | null;
}

interface DownloadProgress {
    id?: string;
    percent?: number;
    downloaded?: number;
    total?: number;
    speed?: number;
    completed?: boolean;
    error?: string;
    label?: string;
    active?: boolean;
}

// Store unlisten function
let unlisten: (() => void) | null = null;

function renderDownloadsProgress(progress: DownloadProgress = {}) {
    const percent = Number(progress.percent || 0);
    const downloaded = Number(progress.downloaded || 0);
    const total = Number(progress.total || 0);
    const speed = Number(progress.speed || 0);
    const completed = !!progress.completed;
    const error = progress.error;

    const bar = document.getElementById('downloads-progress-bar');
    const text = document.getElementById('downloads-progress-text');
    const speedEl = document.getElementById('downloads-speed');
    const downloadedEl = document.getElementById('downloads-downloaded');
    const totalEl = document.getElementById('downloads-total');
    const labelEl = document.getElementById('downloads-item-label');
    const statusEl = document.getElementById('downloads-status');
    const etaEl = document.getElementById('downloads-eta');
    const mainCard = document.getElementById('downloads-main-card') as HTMLElement | null;
    const emptyText = document.getElementById('downloads-empty-text');

    // Check if there's an active download (simplified logic)
    const hasActive = !!(
        progress.active ||  // Backend says it's active
        (
            (percent > 0 || downloaded > 0) &&
            !progress.completed &&
            !progress.error &&
            total > 0
        ) ||
        (completed && !error) // Keep showing completed state until dismissed or new one starts (logic to be decided)
    );

    // For now, if completed, show for a moment then maybe we should rely on user action?
    // Current logic: if completed, hasActive is true if label exists.
    // Adapting to event: event comes in, we render.

    // Show/hide main card and empty state - simplified for event stream
    const showCard = hasActive || (completed && !error);

    const downloadsBody = document.getElementById('downloads-body');
    const downloadsHeader = document.querySelector('.downloads-header') as HTMLElement | null;

    if (showCard) {
        if (mainCard) mainCard.style.display = 'block';
        if (downloadsBody) downloadsBody.classList.remove('empty-state');
        if (downloadsHeader) downloadsHeader.style.flex = '0';

        // Layout: Top alignment for active state
        const downloadsContainer = document.getElementById('downloads-container');
        if (downloadsContainer) downloadsContainer.style.justifyContent = 'flex-start';
    } else {
        if (mainCard) mainCard.style.display = 'none';
        if (downloadsBody) downloadsBody.classList.add('empty-state');
        if (downloadsHeader) downloadsHeader.style.flex = '1';

        // Layout: Center alignment for empty state
        const downloadsContainer = document.getElementById('downloads-container');
        if (downloadsContainer) downloadsContainer.style.justifyContent = 'center';
    }
    if (emptyText) {
        if (showCard) {
            emptyText.classList.add('hidden');
        } else {
            emptyText.classList.remove('hidden');
        }
    }

    // Update progress bar
    if (bar) {
        bar.style.width = `${Math.min(percent, 100)}%`;
    }
    if (text) {
        text.textContent = `${percent.toFixed(1)}%`;
    }

    // Format speed
    if (speedEl) {
        if (speed >= 1024 * 1024) {
            speedEl.textContent = `${(speed / (1024 * 1024)).toFixed(2)} MB/s`;
        } else if (speed >= 1024) {
            speedEl.textContent = `${(speed / 1024).toFixed(1)} KB/s`;
        } else {
            speedEl.textContent = `${speed.toFixed(0)} B/s`;
        }
    }

    // Format downloaded and total
    if (downloadedEl) {
        if (downloaded >= 1024 * 1024) {
            downloadedEl.textContent = `${(downloaded / (1024 * 1024)).toFixed(2)} MB`;
        } else if (downloaded >= 1024) {
            downloadedEl.textContent = `${(downloaded / 1024).toFixed(1)} KB`;
        } else {
            downloadedEl.textContent = `${downloaded.toFixed(0)} B`;
        }
    }
    if (totalEl) {
        if (total > 0) {
            if (total >= 1024 * 1024) {
                totalEl.textContent = `${(total / (1024 * 1024)).toFixed(2)} MB`;
            } else if (total >= 1024) {
                totalEl.textContent = `${(total / 1024).toFixed(1)} KB`;
            } else {
                totalEl.textContent = `${total.toFixed(0)} B`;
            }
        } else {
            totalEl.textContent = '--';
        }
    }

    // Update label
    if (labelEl) {
        // Label logic needs to come from somewhere. For now, use ID or generic.
        // In fully event based, we might want to pass label in event or look it up.
        // Downloads.rs event sends ID.
        const label = progress.label || progress.id || 'Downloading...'; // Fallback
        labelEl.textContent = label;
        labelEl.title = label;
    }

    // Update status
    if (statusEl) {
        statusEl.classList.remove('active', 'completed', 'error');
        if (completed) {
            statusEl.textContent = 'Завершено';
            statusEl.classList.add('completed');
        } else if (error) {
            statusEl.textContent = 'Ошибка';
            statusEl.classList.add('error');
        } else if (percent < 100) {
            statusEl.textContent = 'В процессе';
            statusEl.classList.add('active');
        } else {
            statusEl.textContent = 'Ожидание';
        }
    }

    // Update ETA
    if (etaEl) {
        if (completed) {
            etaEl.textContent = 'Готово';
        } else if (error) {
            etaEl.textContent = error;
        } else if (speed > 0 && total > 0) {
            const remainingBytes = Math.max(total - downloaded, 0);
            const seconds = remainingBytes / speed;
            if (seconds < 60) {
                etaEl.textContent = `${Math.floor(seconds)}с`;
            } else {
                const mins = Math.floor(seconds / 60);
                const secs = Math.floor(seconds % 60);
                etaEl.textContent = `${mins}м ${secs}с`;
            }
        } else {
            etaEl.textContent = '--';
        }
    }
}

async function startDownloadsListener() {
    if (unlisten) {
        unlisten();
        unlisten = null;
    }

    // Initialize with empty state
    const downloadsBody = document.getElementById('downloads-body');
    const mainCard = document.getElementById('downloads-main-card');
    const emptyText = document.getElementById('downloads-empty-text');
    // Don't hide everything by default, allows persistent last state if we wanted,
    // but for now let's reset to clean state on load.
    if (mainCard) mainCard.style.display = 'none';
    if (downloadsBody) downloadsBody.classList.add('empty-state');
    if (emptyText) emptyText.classList.remove('hidden');

    unlisten = await listen<DownloadProgressPayload>('download://progress', (event) => {
        const payload = event.payload;
        // Map Rust payload to UI interface
        const uiProgress: DownloadProgress = {
            percent: payload.percent,
            downloaded: payload.current,
            total: payload.total,
            speed: payload.speed,
            completed: payload.completed,
            error: payload.error || undefined,
            label: payload.id, // Using ID as label for now
            active: !payload.completed && !payload.error
        };
        renderDownloadsProgress(uiProgress);
    });

    console.log('[Downloads] Event listener started');
}


// Start listening when module loads (or you can call it from main)
startDownloadsListener();



// Download Settings Modal
let downloadSettings = {
    limitEnabled: false,
    maxSpeed: 50  // MB/s
};

// Load settings from localStorage
function loadDownloadSettings() {
    try {
        const saved = localStorage.getItem('downloadSettings');
        if (saved) {
            downloadSettings = JSON.parse(saved);
        }
    } catch (e) {
        console.warn('Failed to load download settings:', e);
    }
}

// Save settings to localStorage
window.saveDownloadSettings = function (): void {
    const toggle = document.getElementById('download-speed-limit-toggle') as HTMLInputElement | null;
    const slider = document.getElementById('download-speed-slider') as HTMLInputElement | null;
    const controls = document.getElementById('speed-limit-controls');

    if (toggle && slider) {
        downloadSettings.limitEnabled = toggle.checked;
        downloadSettings.maxSpeed = parseInt(slider.value);

        // Update controls visibility
        if (controls) {
            controls.style.opacity = toggle.checked ? '1' : '0.5';
            controls.style.pointerEvents = toggle.checked ? 'auto' : 'none';
        }

        // Update toggle visual
        toggle.style.background = toggle.checked ? 'var(--primary)' : 'var(--bg-light)';

        try {
            localStorage.setItem('downloadSettings', JSON.stringify(downloadSettings));
        } catch (e) {
            console.warn('Failed to save download settings:', e);
        }
    }
};

window.updateSpeedDisplay = function (value: number | string): void {
    const display = document.getElementById('speed-limit-value');
    const slider = document.getElementById('download-speed-slider') as HTMLInputElement | null;
    if (display) display.textContent = String(value);

    // Update slider background gradient
    if (slider) {
        const numValue = typeof value === 'string' ? parseInt(value) : value;
        const percent = ((numValue - 1) / (200 - 1)) * 100;
        slider.style.background = `linear-gradient(to right, var(--primary) ${percent}%, var(--bg-light) ${percent}%)`;
    }
};

window.openDownloadSettings = function (): void {
    loadDownloadSettings();

    const overlay = document.getElementById('download-settings-overlay');
    const toggle = document.getElementById('download-speed-limit-toggle') as HTMLInputElement | null;
    const slider = document.getElementById('download-speed-slider') as HTMLInputElement | null;
    const controls = document.getElementById('speed-limit-controls');

    if (toggle) {
        toggle.checked = downloadSettings.limitEnabled;
        toggle.style.background = toggle.checked ? 'var(--primary)' : 'var(--bg-light)';
    }
    if (slider) {
        slider.value = String(downloadSettings.maxSpeed);
        window.updateSpeedDisplay(String(downloadSettings.maxSpeed));
    }
    if (controls) {
        controls.style.opacity = downloadSettings.limitEnabled ? '1' : '0.5';
        controls.style.pointerEvents = downloadSettings.limitEnabled ? 'auto' : 'none';
    }

    if (overlay) {
        if (overlay.style.display === 'none') overlay.style.display = '';
        overlay.classList.add('show');
    }
};

window.closeDownloadSettings = function () {
    const overlay = document.getElementById('download-settings-overlay');
    if (overlay) {
        overlay.classList.remove('show');
    }
};

window.closeDownloadSettingsOnOverlay = function (event: Event): void {
    // Close only if clicked on overlay itself, not on modal content
    const target = event.target as HTMLElement;
    if (target.id === 'download-settings-overlay') {
        window.closeDownloadSettings();
    }
};

// Initialize settings on load
loadDownloadSettings();
