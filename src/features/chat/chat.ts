// Chat Feature - Model Management, Voice Input, System Stats

declare function showToast(message: string, type: string, duration?: number, title?: string): void;
declare function t(key: string, fallback?: string): string;
declare function markUnsaved(fieldId: string): void;
declare function saveSetting(key: string, value: unknown, notify?: boolean, reload?: boolean, fieldId?: string): Promise<void>;
declare function agentLog(level: string, location: string, action: string, data?: Record<string, unknown>): void;
declare function loadSdModels(): void;
// globals declared in vite-env.d.ts

declare function flushLauncherLogs(): void;

interface ChatMessage {
    role: 'user' | 'assistant';
    content: string;
}

interface ChatAttachment {
    name: string;
    type: string;
    size: number;
    data_base64: string;
}

interface ChatImage {
    mime: string;
    data_base64: string;
}

document.addEventListener('keydown', (e: KeyboardEvent): void => {
    // Ctrl/Cmd + S to save current settings
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        const activeSection = document.querySelector('.settings-section.active');
        if (activeSection) {
            // LLM and SD settings moved to module-settings.html
            showToast(t('ui.launcher.web.settings_autosave_hint', 'Settings auto-save on blur'), 'success', 1500);
        }
    }
    // Ctrl/Cmd + K to focus search (if we add search later)
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        // Future: focus search
    }
});

// Bot token/channel functions removed - moved to module settings

// Paste models directory from clipboard
window.pasteModelsDir = async function (): Promise<void> {
    try {
        const text = await navigator.clipboard.readText();
        const modelsDirField = document.getElementById('field-models-dir') as HTMLInputElement | null;
        if (modelsDirField) {
            modelsDirField.value = text;
            markUnsaved('models-dir');
            showToast(t('ui.launcher.button.pasted', 'Путь вставлен'), 'success', 1500);
        }
    } catch (e) {
        showToast(t('ui.launcher.button.paste_failed', 'Не удалось вставить'), 'error');
    }
};

// Select models folder via Windows dialog
window.selectModelsFolder = async function (): Promise<void> {
    try {
        showToast(t('ui.launcher.button.opening_folder_dialog', 'Открывается диалог выбора папки...'), 'info', 1000);
        const res = await fetch('/api/select_folder', { method: 'POST' });
        const data = await res.json();
        if (data.ok && data.path) {
            const modelsDirField = document.getElementById('field-models-dir') as HTMLInputElement | null;
            if (modelsDirField) {
                modelsDirField.value = data.path;
                markUnsaved('models-dir');
                await saveSetting('MODELS_LLM_DIR', data.path, false, false, 'models-dir');
                showToast(t('ui.launcher.button.folder_selected', 'Папка выбрана'), 'success', 1500);
            }
        } else {
            if (data.error && !data.error.includes("не выбрана")) {
                showToast(data.error || t('ui.launcher.button.folder_select_failed', 'Не удалось выбрать папку'), 'error');
            }
        }
    } catch (e) {
        showToast(t('ui.launcher.button.folder_select_failed', 'Не удалось выбрать папку') + ': ' + (e as Error).message, 'error');
    }
};

// Paste SD models directory from clipboard
window.pasteSdModelsDir = async function (): Promise<void> {
    try {
        const text = await navigator.clipboard.readText();
        const modelsDirField = document.getElementById('field-sd-models-dir') as HTMLInputElement | null;
        if (modelsDirField) {
            modelsDirField.value = text;
            markUnsaved('sd-models-dir');
            showToast(t('ui.launcher.button.pasted', 'Путь вставлен'), 'success', 1500);
        }
    } catch (e) {
        showToast(t('ui.launcher.button.paste_failed', 'Не удалось вставить'), 'error');
    }
};

// Select SD models folder via Windows dialog
window.selectSdModelsFolder = async function (): Promise<void> {
    try {
        showToast(t('ui.launcher.button.opening_folder_dialog', 'Открывается диалог выбора папки...'), 'info', 1000);
        const res = await fetch('/api/select_folder', { method: 'POST' });
        const data = await res.json();
        if (data.ok && data.path) {
            const modelsDirField = document.getElementById('field-sd-models-dir') as HTMLInputElement | null;
            if (modelsDirField) {
                modelsDirField.value = data.path;
                markUnsaved('sd-models-dir');
                await saveSetting('MODELS_SD_DIR', data.path, false, false, 'sd-models-dir');
                showToast(t('ui.launcher.button.folder_selected', 'Папка выбрана'), 'success', 1500);
            }
        } else {
            if (data.error && !data.error.includes("не выбрана")) {
                showToast(data.error || t('ui.launcher.button.folder_select_failed', 'Не удалось выбрать папку'), 'error');
            }
        }
    } catch (e) {
        showToast(t('ui.launcher.button.folder_select_failed', 'Не удалось выбрать папку') + ': ' + (e as Error).message, 'error');
    }
};

// Model download
let downloadCanceled = false;
let downloadProgressInterval: ReturnType<typeof setInterval> | null = null;

window.downloadModel = async function (): Promise<void> {
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

    // Show notification
    showToast(t('ui.launcher.web.download_starting', 'Начало загрузки модели...'), 'success');

    // Show progress modal
    const modal = document.getElementById('model-download-modal');
    const modelNameEl = document.getElementById('download-model-name');
    const progressBarEl = document.getElementById('download-progress-bar');
    const progressTextEl = document.getElementById('download-progress-text');
    const speedTextEl = document.getElementById('download-speed-text');
    const downloadedEl = document.getElementById('download-downloaded');
    const totalEl = document.getElementById('download-total');
    const cancelBtn = document.getElementById('download-cancel-btn');

    if (modal) {
        modal.style.display = 'flex';
        modal.classList.add('show');

        // Extract model name from URL or use default
        const urlParts = url.split('/');
        const modelName = urlParts[urlParts.length - 1] || 'model.safetensors';
        modelNameEl.textContent = modelName;

        // Reset progress
        progressBarEl.style.width = '0%';
        progressTextEl.textContent = '0%';
        speedTextEl.textContent = '0 KB/s';
        downloadedEl.textContent = '0 MB';
        totalEl.textContent = '-- MB';
        downloadCanceled = false;

        // Start download
        try {
            const response = await fetch('/api/download_model', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: url })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            // Start polling for progress
            let lastDownloaded = 0;
            let lastTime = Date.now();
            downloadProgressInterval = setInterval(async () => {
                if (downloadCanceled) {
                    clearInterval(downloadProgressInterval);
                    return;
                }

                try {
                    const progressRes = await fetch('/api/download_progress');
                    if (progressRes.ok) {
                        const progress = await progressRes.json();
                        const percent = progress.percent || 0;
                        const downloaded = progress.downloaded || 0;
                        const total = progress.total || 0;
                        const speed = progress.speed || 0;

                        progressBarEl.style.width = percent + '%';
                        progressTextEl.textContent = percent.toFixed(1) + '%';

                        const downloadedMB = (downloaded / (1024 * 1024)).toFixed(1);
                        const totalMB = total > 0 ? (total / (1024 * 1024)).toFixed(1) : '--';
                        downloadedEl.textContent = downloadedMB + ' MB';
                        totalEl.textContent = totalMB + ' MB';

                        const speedKB = (speed / 1024).toFixed(1);
                        speedTextEl.textContent = speedKB + ' KB/s';

                        if (progress.completed) {
                            clearInterval(downloadProgressInterval);
                            setTimeout(() => {
                                hideModelDownloadModal();
                                showToast(t('ui.launcher.web.download_complete', 'Модель успешно загружена'), 'success');
                                loadSdModels();
                            }, 500);
                        } else if (progress.error) {
                            clearInterval(downloadProgressInterval);
                            hideModelDownloadModal();
                            showToast(t('ui.launcher.web.download_error', 'Ошибка загрузки') + ': ' + progress.error, 'error');
                        }
                    }
                } catch (e) {
                    console.error('Error fetching download progress:', e);
                }
            }, 500);
        } catch (e: any) {
            console.error('Download error:', e);
            clearInterval(downloadProgressInterval);
            hideModelDownloadModal();
            showToast(t('ui.launcher.web.download_error', 'Ошибка загрузки') + ': ' + e.message, 'error');
        }
    }
};

window.cancelModelDownload = function (): void {
    downloadCanceled = true;
    clearInterval(downloadProgressInterval);
    fetch('/api/cancel_download', { method: 'POST' }).catch(() => { });
    hideModelDownloadModal();
    showToast(t('ui.launcher.web.download_cancelled', 'Загрузка отменена'), 'warning');
};

window.hideModelDownloadModal = function (): void {
    const modal = document.getElementById('model-download-modal');
    if (modal) {
        modal.style.display = 'none';
        modal.classList.remove('show');
    }
    clearInterval(downloadProgressInterval);
};

// System monitoring update
window.updateSystemStats = async function (): Promise<void> {
    try {
        const res = await fetch('/api/system_stats');
        // #region agent log
        agentLog('H1', 'index.html:updateSystemStats', 'fetch_system_stats', {
            status: res.status,
            ok: res.ok,
            serverPid: res.headers.get('X-Launcher-PID'),
            serverRun: res.headers.get('X-Launcher-Run')
        });
        // #endregion
        if (!res.ok) {
            console.warn('[SystemStats] Failed to fetch stats:', res.status);
            return;
        }
        const text = await res.text();
        if (!text) {
            console.warn('[SystemStats] Empty response');
            return;
        }
        const data = JSON.parse(text);

        // Helper: set value with secondary muted text (no HTML injection)
        const setValueWithSecondary = (el, primaryText, secondaryText) => {
            if (!el) return;
            el.innerHTML = '';
            const main = document.createElement('span');
            main.textContent = primaryText || '';
            el.appendChild(main);
            if (secondaryText) {
                const sub = document.createElement('span');
                sub.className = 'sysmon-value-sub';
                sub.textContent = secondaryText;
                el.appendChild(sub);
            }
        };

        // Helper: set progress bar color based on percentage
        const setProgressColor = (el, percent) => {
            if (!el) return;
            el.classList.remove('low', 'medium', 'high');
            if (percent >= 85) {
                el.classList.add('high');
            } else if (percent >= 70) {
                el.classList.add('medium');
            } else {
                el.classList.add('low');
            }
        };

        // Network stats
        const downloadRate = data.network?.download_rate || 0;
        const uploadRate = data.network?.upload_rate || 0;
        const networkUtil = data.network?.utilization || 0;

        // Format for network/disk: always MB/s (compact)
        const formatMB = (bytes) => {
            const mb = bytes / (1024 * 1024);
            if (mb < 0.1) return '0 MB/s';
            return mb.toFixed(1) + ' MB/s';
        };

        const networkStatusEl = document.getElementById('network-status');
        const networkProgressEl = document.getElementById('network-progress');

        const downloadMBps = downloadRate / (1024 * 1024);
        const uploadMBps = uploadRate / (1024 * 1024);
        const netPeak = Math.max(downloadMBps, uploadMBps);

        if (networkStatusEl) {
            setValueWithSecondary(networkStatusEl, `↓ ${formatMB(downloadRate)}`, ` • ↑ ${formatMB(uploadRate)}`);
        }
        if (networkProgressEl) {
            const netPercent = Math.min(100, (netPeak / 10) * 100); // 10 MB/s threshold
            networkProgressEl.style.width = Math.max(0, netPercent) + '%';

            if (netPeak >= 10) {
                networkProgressEl.classList.add('sysmon-fill-gold');
                setProgressColor(networkProgressEl, 100);
            } else {
                networkProgressEl.classList.remove('sysmon-fill-gold');
                setProgressColor(networkProgressEl, netPercent);
            }
        }

        // Disk stats (speed)
        const diskRead = data.disk?.read_rate || 0;
        const diskWrite = data.disk?.write_rate || 0;
        const diskUtil = data.disk?.utilization || 0;

        const diskUsageEl = document.getElementById('disk-usage');
        const diskProgressEl = document.getElementById('disk-progress');

        if (diskUsageEl) {
            // Show read/write in header (no duplicates) - always MB/s
            setValueWithSecondary(diskUsageEl, `R ${formatMB(diskRead)}`, ` • W ${formatMB(diskWrite)}`);
        }
        if (diskProgressEl) {
            diskProgressEl.style.width = Math.max(0, Math.min(100, diskUtil)) + '%';
            setProgressColor(diskProgressEl, diskUtil);
        }

        // CPU stats
        const cpuPercent = data.cpu?.percent || 0;
        const cpuPercentEl = document.getElementById('cpu-percent');
        const cpuProgressEl = document.getElementById('cpu-progress');

        if (cpuPercentEl) {
            cpuPercentEl.textContent = cpuPercent.toFixed(0) + '%';
        }
        if (cpuProgressEl) {
            cpuProgressEl.style.width = Math.max(0, Math.min(100, cpuPercent)) + '%';
            setProgressColor(cpuProgressEl, cpuPercent);
        }

        // RAM stats
        const ramPercent = data.ram?.percent || 0;
        const ramUsed = data.ram?.used_gb || 0;
        const ramTotal = data.ram?.total_gb || 0;

        const ramPercentEl = document.getElementById('ram-percent');
        const ramProgressEl = document.getElementById('ram-progress');

        if (ramPercentEl) {
            setValueWithSecondary(ramPercentEl, `${ramUsed.toFixed(1)} GB`, ` / ${ramTotal.toFixed(1)} GB`);
        }
        if (ramProgressEl) {
            ramProgressEl.style.width = Math.max(0, Math.min(100, ramPercent)) + '%';
            setProgressColor(ramProgressEl, ramPercent);
        }

        // GPU stats
        const gpuDetected = data.gpu?.detected || false;
        const gpuUtil = data.gpu?.utilization || 0;
        const gpuMemPercent = data.gpu?.memory_percent || 0;
        const gpuMemUsed = data.gpu?.memory_used_gb || 0;
        const gpuMemTotal = data.gpu?.memory_total_gb || 0;
        const gpuName = data.gpu?.name || 'N/A';

        const gpuUtilEl = document.getElementById('gpu-util');
        const gpuProgressEl = document.getElementById('gpu-progress');
        const vramProgressEl = document.getElementById('vram-progress');
        const gpuMemoryEl = document.getElementById('gpu-memory');

        if (gpuUtilEl) {
            if (gpuDetected) {
                gpuUtilEl.textContent = gpuUtil + '%';
            } else {
                gpuUtilEl.textContent = 'N/A';
            }
        }
        if (gpuProgressEl) {
            if (gpuDetected) {
                // Progress bar shows GPU core utilization (not VRAM)
                gpuProgressEl.style.width = Math.max(0, Math.min(100, gpuUtil)) + '%';
                setProgressColor(gpuProgressEl, gpuUtil);
            } else {
                gpuProgressEl.style.width = '0%';
                gpuProgressEl.classList.remove('low', 'medium', 'high');
            }
        }
        if (vramProgressEl) {
            if (gpuDetected && gpuMemTotal > 0) {
                vramProgressEl.style.width = Math.max(0, Math.min(100, gpuMemPercent)) + '%';
                setProgressColor(vramProgressEl, gpuMemPercent);
            } else {
                vramProgressEl.style.width = '0%';
                vramProgressEl.classList.remove('low', 'medium', 'high');
            }
        }
        if (gpuMemoryEl) {
            if (gpuDetected && gpuMemTotal > 0) {
                setValueWithSecondary(gpuMemoryEl, `${gpuMemUsed.toFixed(1)} GB`, ` / ${gpuMemTotal.toFixed(1)} GB`);
            } else {
                gpuMemoryEl.textContent = t('ui.launcher.web.gpu_not_detected', 'GPU не обнаружен');
            }
        }
    } catch (e) {
        console.error('[SystemStats] Error updating stats:', e);
    }
};

let chatHistory = []; // [{role:'user'|'assistant', content:string}]
let chatFiles = [];   // [File]

const chatQuestions = [
    'Над чем сосредоточен?',
    'Над чем ты работаешь?',
    'О чём ты думаешь?',
    'Что тебя интересует?',
    'Над какой задачей работаешь?',
    'Что у тебя на уме?',
    'Какая у тебя цель?',
    'Над чем размышляешь?',
    'Что тебя волнует?',
    'О чём мечтаешь?',
    'Какой проект в работе?',
    'Что планируешь?',
    'Над чем сейчас работаешь?',
    'Какая идея у тебя?',
    'Что хочешь обсудить?',
    'О чём хочешь поговорить?',
    'Над чем размышляешь сейчас?',
    'Что тебя вдохновляет?',
    'Какая задача стоит перед тобой?',
    'Что у тебя в планах?',
    'О чём задумался?',
    'Какой вопрос тебя интересует?',
    'Над чем фокусируешься?',
    'Что в приоритете?',
    'Какая мысль сейчас?',
    'О чём размышляешь?',
    'Что на повестке?',
    'Над чем концентрируешься?',
    'Что в голове?',
    'Какая тема актуальна?'
];

function getRandomChatQuestion(): string {
    return chatQuestions[Math.floor(Math.random() * chatQuestions.length)];
}

function chatFormatBytes(bytes: number): string {
    try {
        const b = Number(bytes || 0);
        if (b < 1024) return `${b} B`;
        const kb = b / 1024;
        if (kb < 1024) return `${kb.toFixed(1)} KB`;
        const mb = kb / 1024;
        if (mb < 1024) return `${mb.toFixed(1)} MB`;
        const gb = mb / 1024;
        return `${gb.toFixed(2)} GB`;
    } catch (e) {
        return '';
    }
}

interface AppendChatOptions {
    error?: boolean;
    images?: ChatImage[];
}

function appendChatMessage(role: string, content: string, opts: AppendChatOptions = {}): void {
    const wrap = document.getElementById('chat-messages');
    const container = document.getElementById('chat-container');
    if (!wrap || !container) return;

    // Add has-messages class to show background on first message and expand layout
    if (!wrap.classList.contains('has-messages')) {
        wrap.classList.add('has-messages');
        container.classList.add('has-messages');
    }

    const row = document.createElement('div');
    row.className = 'chat-row ' + (role === 'user' ? 'user' : 'bot');

    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble' + (opts.error ? ' chat-error' : '');
    bubble.textContent = content || '';

    if (opts.images && Array.isArray(opts.images)) {
        opts.images.forEach(img => {
            try {
                const mime = img.mime || 'image/png';
                const b64 = img.data_base64 || '';
                if (!b64) return;
                const el = document.createElement('img');
                el.className = 'chat-img';
                el.src = `data:${mime};base64,${b64}`;
                bubble.appendChild(el);
            } catch (e) { }
        });
    }

    const meta = document.createElement('div');
    meta.className = 'chat-meta';
    meta.textContent = new Date().toLocaleTimeString();
    bubble.appendChild(meta);

    row.appendChild(bubble);
    wrap.appendChild(row);
    wrap.scrollTop = wrap.scrollHeight;
}

function updateChatAttachmentsUI(): void {
    const wrap = document.getElementById('chat-attachments');
    if (!wrap) return;
    wrap.innerHTML = '';
    if (!chatFiles.length) {
        wrap.style.display = 'none';
        return;
    }
    wrap.style.display = 'flex';
    chatFiles.forEach((f, idx) => {
        const chip = document.createElement('div');
        chip.className = 'chat-attach-chip';
        chip.innerHTML = `<span>${(f.name || 'file')} (${chatFormatBytes(f.size)})</span>`;
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.title = 'Remove';
        btn.textContent = '×';
        btn.onclick = () => {
            chatFiles.splice(idx, 1);
            updateChatAttachmentsUI();
        };
        chip.appendChild(btn);
        wrap.appendChild(chip);
    });
}

function readFileAsBase64(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => {
            try {
                const res = String(reader.result || '');
                const b64 = res.includes(',') ? res.split(',')[1] : res;
                resolve(b64);
            } catch (e) {
                resolve('');
            }
        };
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}

window.pickChatFiles = function (): void {
    const input = document.getElementById('chat-file');
    if (input) input.click();
};

window.clearChat = function (): void {
    chatHistory = [];
    chatFiles = [];
    const wrap = document.getElementById('chat-messages');
    const container = document.getElementById('chat-container');
    if (wrap) {
        wrap.innerHTML = '';
        wrap.classList.remove('has-messages');
    }
    if (container) {
        container.classList.remove('has-messages');
    }
    updateChatAttachmentsUI();
    showToast(t('ui.launcher.web.chat_cleared', 'Chat cleared'), 'success', 1500);
};

// Voice Input using Backend Transcription (Chunked)
let isRecording = false;
let audioContext = null;
let mediaStream = null;
let audioProcessor = null;
let audioInput = null;
let audioChunks = [];
let chunkInterval = null;
let initialInputText = '';

window.toggleVoiceInput = async function (): Promise<void> {
    const voiceBtn = document.getElementById('chat-voice-btn') as HTMLElement | null;
    const chatInput = document.getElementById('chat-input') as HTMLInputElement | null;

    if (isRecording) {
        stopVoiceRecording();
        return;
    }

    // Start Recording
    try {
        if (chatInput) {
            initialInputText = chatInput.value || '';
        }

        mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });

        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        audioInput = audioContext.createMediaStreamSource(mediaStream);

        // Record mono, 16kHz
        const bufferSize = 4096;
        audioProcessor = audioContext.createScriptProcessor(bufferSize, 1, 1);

        audioChunks = [];

        audioProcessor.onaudioprocess = (e) => {
            if (!isRecording) return;
            const channelData = e.inputBuffer.getChannelData(0);
            audioChunks.push(new Float32Array(channelData));
        };

        audioInput.connect(audioProcessor);
        audioProcessor.connect(audioContext.destination);

        isRecording = true;

        if (window.soundFX) window.soundFX.playToggle(true);

        if (voiceBtn) {
            voiceBtn.style.color = 'var(--danger)';
            voiceBtn.style.animation = 'pulse 1s infinite';
        }
        if (chatInput) {
            chatInput.placeholder = t('ui.launcher.web.voice_listening', 'Слушаю...');
        }

        // Start Chunk Loop (every 2s for stability)
        chunkInterval = setInterval(processAudioChunk, 2000);

    } catch (e: any) {
        console.error('Voice input error:', e);
        showToast(t('ui.launcher.web.voice_error', 'Ошибка доступа к микрофону') + ': ' + e.message, 'error', 3000);
        stopVoiceRecording();
    }
};

async function processAudioChunk(isFinal: boolean = false): Promise<void> {
    if (audioChunks.length === 0) return;
    if (!audioContext) return;

    // Don't process tiny chunks unless final
    if (!isFinal && audioChunks.length < 10) return;

    // Snapshot chunks and clear buffer for next segment
    const currentChunks = [...audioChunks];
    audioChunks = []; // Reset for next phrase

    const chatInput = document.getElementById('chat-input');

    try {
        const wavBlob = exportWAV(currentChunks, audioContext.sampleRate);

        // Upload
        const lang = (typeof currentLang !== 'undefined' ? currentLang : (window.currentLang || 'en'));
        // User asked for "no forced language", but API needs one.
        // We'll stick to UI language for now as a reasonable default.
        const langParam = lang === 'ru' ? 'ru-RU' : 'en-US';

        const response = await fetch(`/api/transcribe?lang=${langParam}`, {
            method: 'POST',
            body: wavBlob
        });

        const data = await response.json();

        if (data.text && data.text.trim()) {
            if (chatInput) {
                // If this is not the first chunk, append with space
                const currentText = (chatInput as HTMLInputElement).value;
                const prefix = currentText ? (currentText + (currentText.endsWith(' ') ? '' : ' ')) : '';
                (chatInput as HTMLInputElement).value = prefix + data.text;
                (chatInput as HTMLInputElement).scrollTop = chatInput.scrollHeight;

                // Update initialInputText so if we stop/start we don't dup?
                // Actually initialInputText is basically ignored after first chunk append
            }
        }
    } catch (e) {
        console.error('Chunk upload error:', e);
        // Don't show toast for every chunk error to avoid span
    }
}

async function stopVoiceRecording(): Promise<void> {
    const voiceBtn = document.getElementById('chat-voice-btn');
    const chatInput = document.getElementById('chat-input');

    if (!isRecording) return;

    isRecording = false;
    clearInterval(chunkInterval);
    if (window.soundFX) window.soundFX.playToggle(false);

    // Stop tracks
    if (mediaStream) {
        mediaStream.getTracks().forEach(track => track.stop());
    }
    // Disconnect nodes
    if (audioInput) audioInput.disconnect();
    if (audioProcessor) audioProcessor.disconnect();

    // Process final chunk
    await processAudioChunk(true);

    // UI Cleanup
    if (voiceBtn) {
        voiceBtn.style.color = 'var(--text-secondary)'; // Restore correct color
        voiceBtn.style.animation = '';
    }
    if (chatInput) {
        (chatInput as HTMLInputElement).placeholder = t('ui.launcher.web.chat_placeholder_ask', 'Спросите что-нибудь...');
        chatInput.focus();
    }

    // cleanup context
    if (audioContext) audioContext.close();
    audioContext = null;
}

// WAV Encoder Helpers
function exportWAV(chunks: Float32Array[], sampleRate: number): Blob {
    // Merge chunks
    let length = 0;
    for (let chunk of chunks) length += chunk.length;
    let buffer = new Float32Array(length);
    let offset = 0;
    for (let chunk of chunks) {
        buffer.set(chunk, offset);
        offset += chunk.length;
    }

    // Downsample to 16kHz (optional, improves speed/compatibility) - skipping for simplicity, sending full rate
    // Actually, simple WAV header writing:

    const buffer16 = new Int16Array(length);
    for (let i = 0; i < length; i++) {
        let s = Math.max(-1, Math.min(1, buffer[i]));
        buffer16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }

    // Create WAV Header
    const wavHead = new ArrayBuffer(44);
    const view = new DataView(wavHead);

    /* RIFF identifier */
    writeString(view, 0, 'RIFF');
    /* file length */
    view.setUint32(4, 36 + length * 2, true);
    /* RIFF type */
    writeString(view, 8, 'WAVE');
    /* format chunk identifier */
    writeString(view, 12, 'fmt ');
    /* format chunk length */
    view.setUint32(16, 16, true);
    /* sample format (raw) */
    view.setUint16(20, 1, true);
    /* channel count */
    view.setUint16(22, 1, true); /* MONO */
    /* sample rate */
    view.setUint32(24, sampleRate, true);
    /* byte rate (sample rate * block align) */
    view.setUint32(28, sampleRate * 2, true);
    /* block align (channel count * bytes per sample) */
    view.setUint16(32, 2, true);
    /* bits per sample */
    view.setUint16(34, 16, true);
    /* data chunk identifier */
    writeString(view, 36, 'data');
    /* data chunk length */
    view.setUint32(40, length * 2, true);

    return new Blob([view, buffer16], { type: 'audio/wav' });
}

function writeString(view: DataView, offset: number, string: string): void {
    for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i));
    }
}


// Auto-detect mode based on text content
function detectChatMode(text: string): string {
    if (!text) return 'llm';
    const lowerText = text.toLowerCase();
    const generationKeywords = [
        'сгенерируй', 'сгенерировать', 'генерация', 'generate', 'generation',
        'создай изображение', 'создать изображение', 'create image', 'draw image',
        'нарисуй', 'нарисовать', 'draw', 'paint', 'render',
        'сделай картинку', 'создай картинку', 'make image', 'create picture',
        'изобрази', 'изобразить', 'depict', 'illustrate',
        'покажи', 'показать', 'show', 'visualize'
    ];
    return generationKeywords.some(keyword => lowerText.includes(keyword)) ? 'sd' : 'llm';
}

window.sendChat = async function (): Promise<void> {
    const chatInput = document.getElementById('chat-input') as HTMLInputElement | null;
    const btn = document.getElementById('chat-send') as HTMLButtonElement | null;

    const text = (chatInput ? chatInput.value : '').trim();
    if (!text && !chatFiles.length) {
        showToast(t('ui.launcher.web.chat_empty', 'Enter a message or attach a file'), 'error', 2000);
        return;
    }

    // Auto-detect mode
    const mode = detectChatMode(text);

    const fileNote = chatFiles.length ? `\n(${t('ui.launcher.web.chat_attached', 'Attached')}: ${chatFiles.map(f => f.name).join(', ')})` : '';
    appendChatMessage('user', (text || '') + fileNote);

    // Clear input immediately after showing user message
    if (chatInput) chatInput.value = '';

    const attachments = [];
    const maxTotalBytes = 15 * 1024 * 1024; // 15 MB total
    const maxFileBytes = 10 * 1024 * 1024;  // 10 MB per file
    let totalBytes = 0;

    // Add typing indicator
    const typingId = 'typing-indicator-' + Date.now();
    appendTypingIndicator(typingId);

    try {
        if (btn) btn.disabled = true;
        // Keep button as icon only - no text change

        // Check if LLM is running (only for LLM mode)
        if (mode === 'llm') {
            let llmRunning = false;
            try {
                const stateRes = await fetch('/api/state');
                const stateData = await stateRes.json();
                llmRunning = stateData.services && stateData.services.llm && stateData.services.llm.status === 'running';
            } catch (e) {
                llmRunning = false;
            }

            // If state says not running, try direct ping to Ollama (covers external server already running)
            if (!llmRunning) {
                try {
                    const ping = await fetch('http://127.0.0.1:11434/api/tags', { method: 'GET', signal: AbortSignal.timeout(1500) });
                    if (ping.ok) {
                        llmRunning = true;
                    }
                } catch (e) {
                    llmRunning = false;
                }
            }

            // Auto-start LLM without prompting user
            if (!llmRunning) {
                await fetch('/api/control', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action: 'start', service: 'llm' })
                });
                // Wait for LLM to start silently
                let attempts = 0;
                const maxAttempts = 30;
                let llmReady = false;
                while (attempts < maxAttempts) {
                    await new Promise(resolve => setTimeout(resolve, 1000));
                    try {
                        const pingRes = await fetch('http://127.0.0.1:11434/api/tags', { method: 'GET', signal: AbortSignal.timeout(2000) });
                        if (pingRes.ok) {
                            llmReady = true;
                            break;
                        }
                    } catch (e) {
                        // Ollama not ready yet
                    }
                    attempts++;
                }
                if (!llmReady) {
                    throw new Error(t('ui.launcher.web.chat_llm_timeout', 'LLM сервер не запустился. Попробуйте запустить вручную.'));
                }
            }
        }

        for (const f of chatFiles) {
            if (!f) continue;
            if (f.size > maxFileBytes) {
                throw new Error(t('ui.launcher.web.chat_file_too_large', 'File too large') + `: ${f.name}`);
            }
            totalBytes += f.size;
            if (totalBytes > maxTotalBytes) {
                throw new Error(t('ui.launcher.web.chat_total_too_large', 'Total attachments too large'));
            }
            const b64 = await readFileAsBase64(f);
            attachments.push({ name: f.name, type: f.type || 'application/octet-stream', size: f.size, data_base64: b64 });
        }

        const history = chatHistory.slice(-40);
        const payload = { mode, text, history, attachments };

        const res = await fetch('/api/chat/send', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        // Robust JSON parsing with error handling
        let data = null;
        try {
            const text = await res.text();
            if (!text || text.trim() === '') {
                throw new Error('Empty response from server');
            }
            data = JSON.parse(text);
        } catch (parseError: any) {
            console.error('[Chat] JSON parse error:', parseError, 'Response text:', text?.substring(0, 200));
            data = { ok: false, error: `Ошибка сервера: ${parseError.message || 'Неверный формат ответа'}` };
        }

        // Keep local history (text only)
        if (text) chatHistory.push({ role: 'user', content: text });

        // Remove typing indicator
        removeTypingIndicator(typingId);

        if (data && data.ok) {
            const reply = data.reply || {};
            if (reply.type === 'image' && reply.images) {
                appendChatMessage('assistant', reply.text || t('ui.launcher.web.chat_image_ready', 'Image generated'), { images: reply.images });
                chatHistory.push({ role: 'assistant', content: reply.text || '[image]' });
            } else {
                appendChatMessage('assistant', reply.text || '');
                chatHistory.push({ role: 'assistant', content: reply.text || '' });
            }
        } else {
            appendChatMessage('assistant', (data && data.error) ? String(data.error) : t('ui.launcher.web.chat_error', 'Error'), { error: true });
        }
    } catch (e: any) {
        // Remove typing indicator on error too
        removeTypingIndicator(typingId);
        appendChatMessage('assistant', String(e && e.message ? e.message : e), { error: true });
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.textContent = t('ui.launcher.web.chat_send', 'Отправить');
        }
        // Input already cleared above, just clear attachments
        chatFiles = [];
        updateChatAttachmentsUI();
    }
};

// Typing indicator functions
function appendTypingIndicator(id: string): void {
    const container = document.getElementById('chat-messages');
    if (!container) return;

    const typingDiv = document.createElement('div');
    typingDiv.id = id;
    typingDiv.className = 'chat-message assistant typing';
    typingDiv.innerHTML = `
                <div class="typing-dots">
                    <span></span><span></span><span></span>
                </div>
            `;
    container.appendChild(typingDiv);
    container.scrollTop = container.scrollHeight;
}

function removeTypingIndicator(id: string): void {
    const indicator = document.getElementById(id);
    if (indicator) indicator.remove();
}

// Update range progress for all sliders
function updateRangeProgress(): void {
    document.querySelectorAll('input[type="range"]').forEach(r => {
        const range = r as HTMLInputElement;
        const wrap = range.closest('.range-wrap') as HTMLElement;
        if (wrap) {
            const min = parseFloat(range.min) || 0;
            const max = parseFloat(range.max) || 100;
            const value = parseFloat(range.value) || min;
            const percent = ((value - min) / (max - min)) * 100;
            wrap.style.setProperty('--range-progress', percent + '%');
        }
    });
}

// Update range progress on input
document.addEventListener('input', (e: Event) => {
    const target = e.target as HTMLInputElement;
    if (target && target.type === 'range') {
        updateRangeProgress();
    }
});

setTimeout(() => {
    if (launcherLogBuffer.length > 0) {
        flushLauncherLogs();
    }
}, 100);

// Debug Tab Functions
window.setDebugTab = function (tabId: string, btn: HTMLElement | null): void {
    // Update buttons
    document.querySelectorAll('.debug-tabs .debug-tab').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');

    // Update content visibility
    document.querySelectorAll('.debug-tab-content').forEach(c => c.classList.remove('active'));
    const content = document.getElementById(`debug-${tabId}-tab`);
    if (content) {
        content.classList.add('active');
    }
};

window.debugSwitchTab = function (tabId: string, btn: HTMLElement): void {
    // Update buttons
    const tabsContainer = btn.closest('.tabs');
    if (tabsContainer) {
        tabsContainer.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
    }
    if (btn) btn.classList.add('active');

    // Hide all panes
    const container = document.getElementById('debug-tab-content');
    if (container) {
        container.querySelectorAll('.debug-tab-pane').forEach(p => {
            (p as HTMLElement).style.display = 'none';
            p.classList.remove('active');
        });
    }

    // Show target pane
    const pane = document.getElementById(`debug-${tabId}`);
    if (pane) {
        pane.style.display = 'block';
        pane.classList.add('active');
    }
};

// Module Loading & Caching
let modulesCache = null;
let modulesFetchPromise = null;

window.fetchModulesCached = async function (force: boolean = false): Promise<unknown> {
    if (force || !modulesCache) {
        if (!modulesFetchPromise || force) {
            modulesFetchPromise = fetch('/api/modules')
                .then(res => res.json())
                .then(data => {
                    modulesCache = data;
                    return data;
                })
                .catch(err => {
                    console.error("Failed to fetch modules:", err);
                    throw err;
                })
                .finally(() => {
                    modulesFetchPromise = null;
                });
        }
        return modulesFetchPromise;
    }
    return modulesCache;
};

// Module Categories Helper
function getModuleCategory(mod) {
    const id = (mod.id || '').toLowerCase();
    const name = (mod.name || '').toLowerCase();
    const desc = (mod.description || '').toLowerCase();

    // LLM detection
    if (id.includes('llm') || id.includes('ollama') || id.includes('text') ||
        desc.includes('language model') || desc.includes('llm') || desc.includes('chat')) {
        return 'llm';
    }
    // Image Gen detection
    if (id.includes('sd') || id.includes('stable') || id.includes('diffusion') || id.includes('image') ||
        desc.includes('image generation') || desc.includes('draw')) {
        return 'image';
    }
    // Tools/System
    return 'tools';
}


window.loadModulesTab = async function () {
    // Disabled - Modules page uses static HTML empty state
    return;
    if (modulesTab.dataset.loading === 'true') return;
    modulesTab.dataset.loading = 'true';

    // --- Inject CSS for Layout 3.0 (Slots & Library) ---
    if (!document.getElementById('modules-layout-3-styles')) {
        const style = document.createElement('style');
        style.id = 'modules-layout-3-styles';
        style.textContent = `
                    .modules-workbench-container {
                        display: flex;
                        height: calc(100vh - 8rem);
                        gap: 2rem;
                        position: relative;
                        overflow: hidden;
                        animation: fadeIn 0.4s ease;
                    }

                    /* CENTER ZONE: Function Slots */
                    .workbench-center {
                        flex: 1;
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        padding: 6rem 2rem 6rem; /* Increased padding further to clear global header if needed, or visual consistency */
                        gap: 1.5rem;
                        overflow-y: auto;
                    }

                    /* SIDEBAR BLUR HEADER (Backdrop for Top Controls) */
                    .sidebar-visual-header {
                        position: fixed;
                        top: 0;
                        right: 0;
                        width: 340px; /* Matches sidebar width */
                        height: 90px;
                        background: rgba(15, 15, 20, 0.7);
                        backdrop-filter: blur(20px);
                        -webkit-backdrop-filter: blur(20px);
                        z-index: 10000; /* Below .top-controls (10001) */
                        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
                        display: flex;
                        align-items: center;
                        padding-left: 1.5rem;
                        pointer-events: none; /* Let clicks pass through, just visual */
                        animation: fadeIn 0.5s ease;
                    }

                    .slot-card {
                        width: 100%;
                        max-width: 650px;
                        min-height: 160px;
                        background: rgba(20, 20, 25, 0.4);
                        backdrop-filter: blur(12px);
                         -webkit-backdrop-filter: blur(12px);
                        border: 1px dashed rgba(255, 255, 255, 0.15);
                        border-radius: 20px;
                        padding: 1.5rem;
                        display: flex;
                        align-items: center;
                        gap: 1.5rem;
                        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
                        position: relative;
                    }
                    /* Filled State */
                    .slot-card.filled {
                        background: rgba(35, 35, 45, 0.7);
                        border: 1px solid rgba(255, 255, 255, 0.1);
                        border-left: 4px solid var(--accent-primary);
                    }
                    /* Priority Slot (Bot) - Removed Yellow Border */
                    .slot-card.priority {
                        /* border-color removed per user request */
                    }
                    .slot-card.priority.filled {
                        background: linear-gradient(135deg, rgba(40,35,20,0.6), rgba(30,30,40,0.8));
                        /* border-left-color: #FFD700; */
                    }

                    /* Drag Over State */
                    .slot-card.drag-over {
                        background: rgba(0, 255, 136, 0.08);
                        border-color: #00ff88;
                        transform: scale(1.02);
                        box-shadow: 0 0 30px rgba(0, 255, 136, 0.1);
                    }

                    /* Slot Content */
                    .slot-icon-area {
                        width: 64px;
                        height: 64px;
                        border-radius: 16px;
                        background: rgba(255,255,255,0.05);
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        font-size: 2rem;
                        flex-shrink: 0;
                        color: rgba(255,255,255,0.5);
                        transition: all 0.3s;
                    }
                    .slot-card.filled .slot-icon-area {
                        background: var(--accent-primary);
                        color: white;
                    }
                    .slot-card.priority.filled .slot-icon-area {
                        background: #FFD700;
                        color: #000;
                    }

                    .slot-info { flex: 1; }
                    .slot-title { font-size: 1.2rem; font-weight: 700; color: var(--text-primary); margin-bottom: 0.3rem; }
                    .slot-desc { font-size: 0.9rem; color: var(--text-secondary); }

                    .active-module-chip {
                        display: inline-flex;
                        align-items: center;
                        gap: 0.5rem;
                        padding: 0.4rem 0.8rem;
                        background: rgba(255,255,255,0.1);
                        border-radius: 8px;
                        font-size: 0.85rem;
                        margin-top: 0.8rem;
                        color: #fff;
                    }

                    /* RIGHT SIDEBAR: Module Repository */
                    .workbench-sidebar {
                        width: 340px;
                        background: rgba(15, 15, 20, 0.8);
                        border-left: 1px solid rgba(255, 255, 255, 0.08);
                        display: flex;
                        flex-direction: column;
                        padding: 3.5rem 1.5rem 1.5rem; /* Increased top padding for window controls */
                        flex-shrink: 0;
                        backdrop-filter: blur(20px);
                    }
                    .sidebar-section-title {
                        font-size: 0.85rem;
                        text-transform: uppercase;
                        letter-spacing: 1px;
                        color: var(--text-muted);
                        margin: 1.5rem 0 0.8rem 0;
                        font-weight: 700;
                    }
                    .module-draggable {
                        background: rgba(255, 255, 255, 0.03);
                        border: 1px solid rgba(255, 255, 255, 0.05);
                        border-radius: 12px;
                        padding: 1rem;
                        margin-bottom: 0.8rem;
                        cursor: grab;
                        display: flex;
                        align-items: center;
                        gap: 1rem;
                        transition: all 0.2s;
                    }
                    .module-draggable:hover {
                        background: rgba(255, 255, 255, 0.08);
                        border-color: rgba(255, 255, 255, 0.15);
                        transform: translateX(-4px);
                    }
                    .module-draggable:active { cursor: grabbing; }

                    .drag-mini-icon { width: 32px; height: 32px; border-radius: 8px; background: rgba(255,255,255,0.1); display:flex; align-items:center; justify-content:center; }

                    /* Empty State Hints */
                    .empty-hint {
                        font-size: 0.9rem;
                        color: var(--text-muted);
                        font-style: italic;
                        margin-top: 0.5rem;
                        display: flex;
                        align-items: center;
                        gap: 0.5rem;
                    }

                    /* FAB */
                    .fab-add-container { position: fixed; bottom: 2rem; right: 2rem; z-index: 100; }
                    .fab-add-btn {
                        width: 56px; height: 56px; border-radius: 28px;
                        background: linear-gradient(135deg, #8A2BE2, #4B0082);
                        display: flex; align-items: center; justify-content: center;
                        box-shadow: 0 4px 15px rgba(138, 43, 226, 0.4);
                        cursor: pointer; transition: transform 0.2s;
                    }
                    .fab-add-btn:hover { transform: scale(1.1); }
                    .fab-icon { font-size: 2rem; color: white; display:flex; justify-content:center; align-items:center; width:100%; height:100%; padding-bottom:4px;}

                    @keyframes fadeIn { from { opacity:0; transform:translateY(10px); } to { opacity:1; transform:translateY(0); } }
                    `;
        document.head.appendChild(style);
    }

    modulesTab.innerHTML = '<div style="display:flex;justify-content:center;align-items:center;height:100%;"><div class="spinner"></div></div>';

    try {
        // 1. Data Fetching
        const modulesRes = await fetch('/api/modules').then(r => r.json());
        // Support both structure variations
        const installedItems = modulesRes.items || modulesRes.modules || [];

        // 2. State Management (LocalStorage for Active Slots)
        // We store: { "text_slot": "module_id_1", "image_slot": null, "bot_slot": "module_id_3" }
        let activeSlots = JSON.parse(localStorage.getItem('flux_active_slots') || '{}');

        // 3. Define the Function Slots (The "Machine")
        const functionSlots = [
            {
                id: 'text_slot',
                title: 'Text Generation',
                desc: 'LLM capabilities for chat and reasoning.',
                accepts: ['llm', 'text'], // Module types accepted
                icon: '📝',
                isPriority: false
            },
            {
                id: 'image_slot',
                title: 'Image Generation',
                desc: 'Visual synthesis and diffusion models.',
                accepts: ['sd', 'image', 'diffusion'],
                icon: '🎨',
                isPriority: false
            },
            {
                id: 'bot_slot',
                title: 'Telegram Bot',
                desc: 'Core interface for Telegram integration.',
                accepts: ['bot', 'telegram'],
                icon: '🤖',
                isPriority: true // Golden Slot
            }
        ];

        // 4. Render Workbench
        modulesTab.innerHTML = '';

        // Inject Visual Header for Sidebar (Backdrop for Top Controls)
        const visualHeader = document.createElement('div');
        visualHeader.className = 'sidebar-visual-header';
        modulesTab.appendChild(visualHeader);

        const container = document.createElement('div');
        container.className = 'modules-workbench-container';

        // --- CENTER ZONE: SLOTS ---
        const centerZone = document.createElement('div');
        centerZone.className = 'workbench-center';

        const centerHeader = document.createElement('div');
        centerHeader.innerHTML = `
                        <h2 style="margin:0; font-size:1.8rem;">Function Slots</h2>
                        <p style="color:var(--text-secondary); margin:0.5rem 0 0 0;">Drag modules from the right to activate these functions.</p>
                    `;
        centerHeader.style.textAlign = 'center';
        centerHeader.style.marginBottom = '1rem';
        centerZone.appendChild(centerHeader);

        function renderSlots() {
            // Clear existing slots (except header)
            while (centerZone.children.length > 1) {
                centerZone.removeChild(centerZone.lastChild);
            }

            functionSlots.forEach(slot => {
                const activeModuleId = activeSlots[slot.id];
                const activeModule = activeModuleId ? installedItems.find(m => m.id === activeModuleId) : null;
                const isFilled = !!activeModule;

                const card = document.createElement('div');
                card.className = `slot-card ${isFilled ? 'filled' : ''} ${slot.isPriority ? 'priority' : ''}`;

                // Slot Content
                let iconContent = slot.icon;
                let titleContent = slot.title;
                let descContent = isFilled ? activeModule.description || activeModule.desc : slot.desc;

                // If filled, show module info
                let activeChipHtml = '';
                if (isFilled) {
                    descContent = activeModule.desc || "Module Active";
                    activeChipHtml = `
                                    <div class="active-module-chip">
                                        <svg style="width:14px;height:14px;" fill="currentColor" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>
                                        Active: <strong>${activeModule.name || activeModule.title}</strong>
                                    </div>
                                `;
                } else {
                    activeChipHtml = `<div class="empty-hint">Empty Slot &mdash; Drop Module Here</div>`;
                }

                card.innerHTML = `
                                <div class="slot-icon-area">${iconContent}</div>
                                <div class="slot-info">
                                    <div class="slot-title">${titleContent}</div>
                                    <div class="slot-desc">${descContent}</div>
                                    ${activeChipHtml}
                                </div>
                                ${isFilled ? `
                                <div style="display:flex; gap:6px; align-items:center;">
                                    <button class="action-btn-subtle btn-settings" onclick="event.stopPropagation(); window.openModuleSettings('${activeModule.id}')" title="Settings" style="background:rgba(255,255,255,0.1);border-radius:50%;width:32px;height:32px;border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:background 0.2s;">
                                        <svg style="width:16px;height:16px;pointer-events:none;" fill="currentColor"><use href="#icon-settings"></use></svg>
                                    </button>
                                    <button class="action-btn-subtle btn-eject" title="Eject" style="background:rgba(255,255,255,0.1);border-radius:50%;width:32px;height:32px;border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:background 0.2s;">✕</button>
                                </div>` : ''}
                            `;

                // Eject Button Logic
                if (isFilled) {
                    const btn = card.querySelector('.btn-eject') as HTMLElement;
                    if (btn) {
                        btn.onclick = (e) => {
                            e.stopPropagation();
                            activeSlots[slot.id] = null;
                            localStorage.setItem('flux_active_slots', JSON.stringify(activeSlots));
                            renderSlots(); // Re-render
                            showToast(`${slot.title} cleared`, 'info');
                        };
                    }
                }

                // Drop Handling
                card.addEventListener('dragover', (e) => {
                    e.preventDefault();
                    card.classList.add('drag-over');
                });
                card.addEventListener('dragleave', () => card.classList.remove('drag-over'));
                card.addEventListener('drop', (e) => {
                    e.preventDefault();
                    card.classList.remove('drag-over');
                    const dataStr = e.dataTransfer.getData('application/json');
                    if (!dataStr) return;

                    try {
                        const module = JSON.parse(dataStr);
                        // Compatibility Check
                        // A module type 'llm' fits in a slot expecting 'llm'
                        const isCompatible = slot.accepts.some(type =>
                            (module.type || '').toLowerCase().includes(type) ||
                            (module.tags || []).some(t => t.toLowerCase().includes(type))
                        );

                        // Special override: Bot slot is strict
                        // In a real app we'd have robust type checking

                        if (slot.isPriority && module.type !== 'bot') {
                            showToast(`Only Bot modules work in this slot.`, 'error');
                            return;
                        }

                        activeSlots[slot.id] = module.id;
                        localStorage.setItem('flux_active_slots', JSON.stringify(activeSlots));
                        renderSlots();
                        showToast(`${module.name} activated for ${slot.title}`, 'success');

                    } catch (err) { console.error('Drop error', err); }
                });

                centerZone.appendChild(card);
            });
        }
        renderSlots();
        container.appendChild(centerZone);


        // --- RIGHT SIDEBAR: MODULES REPOSITORY ---
        const sidebar = document.createElement('div');
        sidebar.className = 'workbench-sidebar';

        sidebar.innerHTML = `
                        <div style="font-size:1.2rem; font-weight:700; margin-bottom:1rem; display:flex; align-items:center; gap:0.5rem;">
                            <span style="opacity:0.6;">📦</span> Module Library
                        </div>
                    `;

        // Group Modules by Type for the sidebar
        const grouped = {};
        installedItems.forEach(m => {
            const type = m.type || 'other';
            if (!grouped[type]) grouped[type] = [];
            grouped[type].push(m);
        });

        // Mock data if empty (for demo purposes if API returns nothing useful yet)
        if (installedItems.length === 0) {
            grouped['llm'] = [
                { id: 'llama3', name: 'Llama 3.1 [8b]', type: 'llm', desc: 'Meta Llama 3 model' },
                { id: 'gemma2', name: 'Gemma 2 [9b]', type: 'llm', desc: 'Google Gemma model' }
            ];
            grouped['sd'] = [
                { id: 'flux1', name: 'Flux.1 [schnell]', type: 'sd', desc: 'Fastest image gen' },
                { id: 'sdxl', name: 'SDXL Turbo', type: 'sd', desc: 'High quality SDXL' }
            ];
            grouped['bot'] = [
                { id: 'bot_core', name: 'Telegram Bot Core', type: 'bot', desc: 'Main bot engine' }
            ];
        }

        Object.keys(grouped).forEach(type => {
            const sectionTitle = document.createElement('div');
            sectionTitle.className = 'sidebar-section-title';
            sectionTitle.innerText = type.toUpperCase();
            sidebar.appendChild(sectionTitle);

            grouped[type].forEach(mod => {
                const draggable = document.createElement('div');
                draggable.className = 'module-draggable';
                draggable.draggable = true;
                draggable.innerHTML = `
                                <div class="drag-mini-icon">${mod.type === 'bot' ? '🤖' : (mod.type === 'llm' ? '📝' : '🎨')}</div>
                                <div style="flex:1;">
                                    <div style="font-weight:600; font-size:0.95rem;">${mod.name || mod.title}</div>
                                    <div style="font-size:0.75rem; color:rgba(255,255,255,0.5);">${mod.type}</div>
                                </div>
                                <button class="action-btn-subtle" onclick="event.preventDefault(); event.stopPropagation(); window.openModuleSettings('${mod.id}')" title="Settings" style="background:transparent; border:none; cursor:pointer; opacity:0.6; padding:4px; border-radius:4px; display:flex; align-items:center;">
                                    <svg style="width:16px;height:16px;" fill="currentColor"><use href="#icon-settings"></use></svg>
                                </button>
                            `;

                draggable.addEventListener('dragstart', (e) => {
                    e.dataTransfer.setData('application/json', JSON.stringify(mod));
                });

                sidebar.appendChild(draggable);
            });
        });

        container.appendChild(sidebar);
        modulesTab.appendChild(container);

        // Add FAB
        const fabContainer = document.createElement('div');
        fabContainer.className = 'fab-add-container';
        fabContainer.innerHTML = `
                        <div class="fab-add-btn" onclick="showInstallModal()" title="Install New Module">
                            <div class="fab-icon">+</div>
                        </div>
                    `;
        modulesTab.appendChild(fabContainer);

    } catch (err: any) {
        console.error("Modules Tab Error:", err);
        modulesTab.innerHTML = `<div style="text-align:center;padding:2rem;color:#ff6b6b;">Failed to load modules: ${err.message}</div>`;
    } finally {
        modulesTab.dataset.loading = 'false';
    }
};

// Helper to remove active module
window.removeActiveModule = async function (slot: string): Promise<void> {
    try {
        const res = await fetch('/api/modules/active', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ slot: slot, module_id: null })
        });
        const data = await res.json();
        if (data.success) {
            window.loadModulesTab();
        }
    } catch (err) {
        showToast('Error removing module', 'error');
    }
};

window.installModule = async function (moduleId: string, repoUrl: string): Promise<void> {
    const btn = event?.target as HTMLButtonElement;
    if (!btn) return;
    const originalText = btn.textContent;
    btn.textContent = 'Installing...';
    btn.disabled = true;

    try {
        const res = await fetch('/api/modules/install', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ module_id: moduleId, repo_url: repoUrl })
        });

        const data = await res.json();
        if (data.success) {
            showToast(`Module ${moduleId} installed successfully`, 'success');
            window.loadModulesTab();
        } else {
            showToast('Installation failed: ' + data.message, 'error');
            btn.textContent = originalText;
            btn.disabled = false;
        }
    } catch (e: any) {
        showToast('Installation error: ' + (e.message || e), 'error');
        btn.textContent = originalText;
        btn.disabled = false;
    }
};

window.removeModule = async function (moduleId: string): Promise<void> {
    if (!confirm(`Are you sure you want to remove ${moduleId}?`)) return;

    try {
        const res = await fetch(`/api/modules/${moduleId}`, {
            method: 'DELETE'
        });
        const data = await res.json();
        if (data.success) {
            showToast(`Module ${moduleId} removed`, 'success');
            window.loadModulesTab();
        } else {
            showToast('Removal failed: ' + data.message, 'error');
        }
    } catch (e: any) {
        showToast('Removal error: ' + (e.message || e), 'error');
    }
};

// Install Modal Functions
window.showInstallModal = function (): void {
    // Remove existing modal if any
    const existing = document.getElementById('install-modal-overlay');
    if (existing) existing.remove();

    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay show';
    overlay.id = 'install-modal-overlay';
    overlay.style.zIndex = '10005';

    overlay.innerHTML = `
                <div class="modal" style="width: 500px; max-width: 90%;">
                    <div class="modal-title">${t('ui.launcher.modules.install_title', 'Install Module')}</div>
                    <div class="modal-message">
                        ${t('ui.launcher.modules.install_msg', 'Enter the GitHub repository URL of the module you want to install.')}
                        <div style="margin-top: 1rem;">
                            <input type="text" id="install-url-input" class="form-input" placeholder="https://github.com/username/repo" autocomplete="off" style="width: 100%; padding: 0.8rem; border-radius: 8px; border: 1px solid var(--border-color); background: var(--bg-light); color: var(--text-primary);">
                        </div>
                        <div id="install-error-msg" style="color: var(--danger); font-size: 0.85rem; margin-top: 0.5rem; display: none;"></div>
                    </div>
                    <div class="modal-actions">
                        <button class="modal-btn modal-btn-cancel" onclick="document.getElementById('install-modal-overlay').remove()">${t('ui.launcher.button.cancel', 'Cancel')}</button>
                        <button class="modal-btn modal-btn-primary" id="confirm-install-btn">${t('ui.launcher.button.install', 'Install')}</button>
                    </div>
                </div>
            `;

    document.body.appendChild(overlay);

    const input = overlay.querySelector('#install-url-input') as HTMLInputElement;
    const installBtn = overlay.querySelector('#confirm-install-btn') as HTMLButtonElement;
    const errorMsg = overlay.querySelector('#install-error-msg') as HTMLElement;

    // Focus input
    setTimeout(() => input.focus(), 50);

    const handleInstall = async () => {
        const url = input.value.trim();
        if (!url) {
            errorMsg.textContent = "Please enter a URL";
            errorMsg.style.display = 'block';
            return;
        }

        installBtn.disabled = true;
        const originalText = installBtn.textContent;
        installBtn.textContent = 'Installing...';
        installBtn.style.opacity = '0.7';
        errorMsg.style.display = 'none';

        showToast("Starting installation...", "info");

        try {
            const res = await fetch('/api/modules/install', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ repo_url: url })
            });

            const data = await window.safeJsonParse(await res.text(), {}) as any;

            if (data.success) {
                showToast(`Module installed successfully`, 'success');
                overlay.remove();
                if (typeof window.loadModulesTab === 'function') {
                    window.loadModulesTab();
                }
            } else {
                throw new Error(data.error || 'Installation failed');
            }
        } catch (e: any) {
            console.error("Install error:", e);
            errorMsg.textContent = e.message || "Connection failed";
            errorMsg.style.display = 'block';
            installBtn.disabled = false;
            installBtn.textContent = originalText;
            installBtn.style.opacity = '1';
        }
    };

    installBtn.onclick = handleInstall;
    input.onkeydown = (e: KeyboardEvent) => {
        if (e.key === 'Enter') handleInstall();
    };

    overlay.onclick = (e: MouseEvent) => {
        if (e.target === overlay) overlay.remove();
    };
};

document.addEventListener('DOMContentLoaded', async () => {
    flushLauncherLogs();

    const initSteps = [];

    // Step 1-3: DOM setup (sequential, but fast)
    launcherLog('INFO', 'Step 1-3: Setting up DOM elements and buttons...');
    const sidebar = document.getElementById('sidebar');
    const mainArea = document.getElementById('main-area');
    const body = document.body;
    launcherLog('INFO', `Sidebar: ${!!sidebar}, Main area: ${!!mainArea}, Body: ${!!body}`);

    const navButtons = document.querySelectorAll('#sidebar .nav-btn[data-page]');
    navButtons.forEach((b) => {
        const btn = b as HTMLElement;
        const pageId = btn.getAttribute('data-page');
        btn.onclick = null;
        btn.removeAttribute('onclick');
        btn.addEventListener('click', function (this: HTMLElement, e: Event) {
            e.preventDefault();
            e.stopPropagation();
            const pageId = this.getAttribute('data-page');
            const moduleSettingsModal = document.getElementById('module-settings-modal');
            if (moduleSettingsModal && moduleSettingsModal.classList.contains('show')) {
                if (typeof hideModuleSettingsModal === 'function') {
                    hideModuleSettingsModal();
                }
            }
            if (pageId && typeof window.showPage === 'function') {
                window.showPage(pageId, this);
            }
            return false;
        });
    });

    const closeBtn = document.getElementById('close-btn');
    if (closeBtn) {
        closeBtn.onclick = null;
        closeBtn.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            if (typeof window.showCloseConfirmModal === 'function') {
                window.showCloseConfirmModal();
            }
            return false;
        });
    }

    // --- Splash Screen Logic ---
    setTimeout(() => {
        const splash = document.getElementById('splash-screen');
        if (splash) {
            splash.classList.add('hidden');
            // Ensure content is visible
            document.body.style.opacity = '1';
        }
    }, 2200);

    initSteps.push(() => {
        try {
            if (typeof initEmojiFlags === 'function') {
                initEmojiFlags();
            }
        } catch (err) { }
    });

    initSteps.push(async () => {
        try {
            if (typeof checkFirstLaunch === 'function') {
                await checkFirstLaunch();
            }
        } catch (err) { }
    });

    initSteps.push(() => {
        try {
            if (typeof loadGpuInfo === 'function') {
                loadGpuInfo();
            }
        } catch (err) { }
    });

    initSteps.push(async () => {
        try {
            if (typeof loadTranslations === 'function') {
                await loadTranslations();
            }
        } catch (err) { }
    });

    await Promise.all(initSteps.map(step => {
        const result = step();
        return result instanceof Promise ? result : Promise.resolve();
    }));

    try {
        if (typeof initEmojiFlags === 'function') {
            initEmojiFlags();
        }
        if (typeof updateLangButtons === 'function') {
            updateLangButtons();
        }
    } catch (err) { }

    setTimeout(() => {
        const urlParams = new URLSearchParams(window.location.search);
        const pageParam = urlParams.get('page');

        if (pageParam) {
            let pageBtn = document.querySelector(`#sidebar .nav-btn[data-page="${pageParam}"]`);
            if (!pageBtn) {
                const allNavBtns = document.querySelectorAll('#sidebar .nav-btn');
                for (const btn of allNavBtns) {
                    const onclick = btn.getAttribute('onclick');
                    if (onclick && onclick.includes(`'${pageParam}'`)) {
                        pageBtn = btn;
                        break;
                    }
                }
            }
            if (pageBtn && typeof window.showPage === 'function') {
                window.showPage(pageParam, pageBtn as HTMLElement);
            } else if (typeof window.showPage === 'function') {
                const homeBtn = document.querySelector('#sidebar .nav-btn[data-page="home"]');
                if (homeBtn) {
                    window.showPage('home', homeBtn as HTMLElement);
                }
            }
        } else {
            const homeBtn = document.querySelector('#sidebar .nav-btn[data-page="home"]');
            if (homeBtn && typeof window.showPage === 'function') {
                window.showPage('home', homeBtn as HTMLElement);
            } else if (typeof window.showPage === 'function') {
                window.showPage('home');
            }
        }
    }, 0);

    // Chat wiring
    const chatFileEl = document.getElementById('chat-file');
    if (chatFileEl) {
        chatFileEl.addEventListener('change', () => {
            try {
                const files = Array.from((chatFileEl as HTMLInputElement).files || []);
                if (files.length) {
                    chatFiles.push(...files);
                    updateChatAttachmentsUI();
                }
                (chatFileEl as HTMLInputElement).value = '';
            } catch (e) { }
        });
    }
    const chatInputEl = document.getElementById('chat-input');
    if (chatInputEl) {
        chatInputEl.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                window.sendChat();
            }
        });
    }

    // Steps 10-14: Parallel initialization of independent operations
    const parallelSteps = [];

    parallelSteps.push(async () => {
        try {
            if (typeof updateState === 'function') {
                await updateState();
                if (typeof initEmojiFlags === 'function') initEmojiFlags();
                if (typeof updateLangButtons === 'function') updateLangButtons();
                if (typeof updateRangeProgress === 'function') updateRangeProgress();
            }
        } catch (err) { }
    });

    parallelSteps.push(() => {
        try {
            if (typeof renderLogs === 'function') {
                renderLogs(true);
            }
        } catch (err) { }
    });

    parallelSteps.push(() => {
        try {
            if (typeof checkSdInstalled === 'function') {
                checkSdInstalled();
            }
        } catch (err) { }
    });

    parallelSteps.push(() => {
        try {
            if (typeof pollLogs === 'function') {
                pollLogs();
            }
        } catch (err) { }
    });

    parallelSteps.push(() => {
        try {
            if (typeof updateSystemStats === 'function') {
                window.updateSystemStats();
                setInterval(window.updateSystemStats, 2000);
            }
        } catch (err) { }
    });

    await Promise.all(parallelSteps.map(step => {
        const result = step();
        return result instanceof Promise ? result : Promise.resolve();
    }));

    (function () {
        const sidebar = document.getElementById('sidebar');
        const dragHandle = document.getElementById('sidebar-drag-handle');
        if (!sidebar || !dragHandle) return;

        let isDragging = false;
        let startX = 0;
        let startWidth = 0;

        // --- Load Saved State ---
        function loadSidebarState() {
            const savedState = localStorage.getItem('sidebarState');
            const savedWidth = localStorage.getItem('sidebarWidth');

            if (savedState === 'collapsed') {
                sidebar.classList.add('collapsed');
                document.documentElement.style.setProperty('--sidebar-width', '80px');
            } else if (savedWidth) {
                sidebar.classList.remove('collapsed');
                document.documentElement.style.setProperty('--sidebar-width', savedWidth + 'px');
            }
        }
        loadSidebarState(); // Init on load

        dragHandle.addEventListener('mousedown', (e) => {
            isDragging = true;
            startX = e.clientX;
            // Calculate start width from current variable state
            const currentVar = getComputedStyle(document.documentElement).getPropertyValue('--sidebar-width');
            startWidth = parseInt(currentVar) || sidebar.offsetWidth;

            sidebar.classList.add('dragging');
            dragHandle.classList.add('dragging');
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';
            e.preventDefault();
            e.stopPropagation();
        });

        document.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            const diff = e.clientX - startX;
            let newWidth = Math.max(80, Math.min(400, startWidth + diff));

            // Visual feedback: toggle class but DON'T snap width yet (smooth drag)
            if (newWidth < 160) {
                sidebar.classList.add('collapsed');
            } else {
                sidebar.classList.remove('collapsed');
            }

            // Update width normally during drag
            document.documentElement.style.setProperty('--sidebar-width', newWidth + 'px');
            // Remove direct style to rely on variable
            if (sidebar.style.width) sidebar.style.width = '';
        });

        document.addEventListener('mouseup', () => {
            if (isDragging) {
                isDragging = false;
                sidebar.classList.remove('dragging');
                dragHandle.classList.remove('dragging');
                document.body.style.cursor = '';
                document.body.style.userSelect = '';

                // --- Snap Logic on Drop ---
                // Check current width (variable)
                const currentWidth = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--sidebar-width')) || 80;

                if (currentWidth < 160) {
                    // Snap to collapsed (Magnet Effect)
                    document.body.classList.add('snapping');
                    document.documentElement.style.setProperty('--sidebar-width', '80px');
                    sidebar.classList.add('collapsed'); // Ensure class is present

                    localStorage.setItem('sidebarState', 'collapsed');

                    // Cleanup animation class
                    setTimeout(() => document.body.classList.remove('snapping'), 300);
                } else {
                    // Expanded state
                    sidebar.classList.remove('collapsed');
                    localStorage.setItem('sidebarState', 'expanded');
                    localStorage.setItem('sidebarWidth', String(currentWidth));
                }
            }
        });
    })();

    // Update launcher status badge
    function updateLauncherStatus() {
        const badge = document.getElementById('launcher-status-badge');
        if (badge) {
            // Check if launcher is responding
            fetch('/api/state')
                .then(res => {
                    if (res.ok) {
                        badge.classList.remove('offline');
                        const dot = badge.querySelector('.status-dot') as HTMLElement;
                        if (dot) {
                            dot.style.background = 'var(--success)';
                            dot.style.boxShadow = '0 0 8px var(--success)';
                        }
                        const pidEl = document.getElementById('launcher-pid');
                        if (pidEl) {
                            const pid = res.headers.get('X-Launcher-PID');
                            pidEl.textContent = pid ? `PID: ${pid}` : 'PID: --';
                        }
                    } else {
                        badge.classList.add('offline');
                        const pidEl = document.getElementById('launcher-pid');
                        if (pidEl) pidEl.textContent = 'PID: --';
                    }
                })
                .catch(() => {
                    badge.classList.add('offline');
                    const pidEl = document.getElementById('launcher-pid');
                    if (pidEl) pidEl.textContent = 'PID: --';
                });
        }
    }
    updateLauncherStatus();
    setInterval(updateLauncherStatus, 5000);

    setInterval(() => {
        updateState().then(() => {
            initEmojiFlags();
            updateLangButtons();
            updateRangeProgress();
        });
    }, 2000);

    window.safeJsonParse = function (text: string, defaultValue = {}) {
        try {
            return text ? JSON.parse(text) : defaultValue;
        } catch (e) {
            console.warn('JSON parse error:', e, 'Text:', text?.substring(0, 100));
            return defaultValue;
        }
    };

    // Safe fetch JSON helper
    window.safeFetchJson = async function <T>(url: string, defaultValue: T, options?: RequestInit): Promise<T> {
        try {
            const res = await fetch(url, options);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const text = await res.text();
            return window.safeJsonParse(text, defaultValue);
        } catch (e) {
            console.warn('Fetch JSON error:', e, 'URL:', url);
            return defaultValue;
        }
    };

    document.body.style.opacity = '1';

    flushLauncherLogs();

    try {
    // Electron IPC removed
    try {
        console.log('Launcher ready');
    } catch (e) { }
    } catch (e) { }

    setTimeout(() => {
        flushLauncherLogs();
        setTimeout(() => {
            flushLauncherLogs();
            setTimeout(() => {
                deleteLauncherLog();
            }, 500);
        }, 1000);
    }, 500);
});

// --- Keyboard shortcuts handler ---
// Block Ctrl+R to prevent page reload which would crash the launcher
document.addEventListener('keydown', (e) => {
    // Handle Ctrl+R - block completely and do soft refresh
    if (e.ctrlKey && (e.key === 'r' || e.key === 'R' || e.key === 'к' || e.key === 'К')) {
        e.preventDefault();
        e.stopPropagation();
        // Soft refresh: reload translations and update UI
        console.log('Ctrl+R pressed - performing soft UI refresh');
        if (typeof loadTranslations === 'function') {
            loadTranslations().then(() => {
                if (typeof applyTranslations === 'function') applyTranslations();
                if (typeof loadSettings === 'function') loadSettings();
                if (typeof loadSettings === 'function') loadSettings();
                if (typeof window.loadModulesTab === 'function') window.loadModulesTab();
                console.log('Soft refresh completed');
            }).catch(err => console.error('Soft refresh error:', err));
        }
        return false;
    }
});

// --- Shutdown on unload ---
// Only shutdown when explicitly closing via close button (not on refresh)
let isClosingApp = false;

// Override showCloseConfirmModal to set the flag
const originalShowCloseConfirmModal = window.showCloseConfirmModal;
window.showCloseConfirmModal = function () {
    if (typeof originalShowCloseConfirmModal === 'function') {
        originalShowCloseConfirmModal();
    }
};

// Hook into confirmClose to set the flag before actually closing
const originalConfirmClose = window.confirmClose;
window.confirmClose = function () {
    isClosingApp = true;
    if (typeof originalConfirmClose === 'function') {
        originalConfirmClose();
    }
};

window.addEventListener('beforeunload', (e) => {
    // Only send shutdown if we're actually closing the app (not refreshing)
    if (!isClosingApp) {
        return; // Don't shutdown on refresh
    }

    const stopData = JSON.stringify({ action: 'stop', service: 'all' });

    // Use sendBeacon for reliable transmission during unload
    if (navigator && typeof navigator.sendBeacon === 'function') {
        try {
            navigator.sendBeacon('/api/control', stopData);
            navigator.sendBeacon('/api/shutdown', '');
            navigator.sendBeacon('/api/logs/clear', '');
        } catch (e) { console.error("Shutdown beacon failed", e); }
    } else {
        // Fallback for older browsers
        fetch('/api/control', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: stopData,
            keepalive: true
        }).catch(() => { });
        fetch('/api/shutdown', { method: 'POST', keepalive: true }).catch(() => { });
        fetch('/api/logs/clear', { method: 'POST', keepalive: true }).catch(() => { });
    }
});

document.addEventListener('visibilitychange', () => { });
