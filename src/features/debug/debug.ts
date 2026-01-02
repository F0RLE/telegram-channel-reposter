// Debug Page - Card Resizing and Debug Tools
// Note: startResize is defined in settings-ui.js



function handleResize(e: MouseEvent): void {
    if (!resizeState.isResizing || !resizeState.card) return;

    // Calculate movement relative to start position
    const diffX = e.clientX - resizeState.startX;
    const threshold = 20; // 20px threshold for switching

    // Only process if movement is significant enough
    if (Math.abs(diffX) < threshold) {
        return;
    }

    // Determine new width based on movement direction
    let newWidth;
    if (diffX < 0) {
        // Moved left - compact (half)
        newWidth = 'half';
    } else {
        // Moved right - full width
        newWidth = 'full';
    }

    const currentWidth = resizeState.card.getAttribute('data-card-width') || 'half';
    if (newWidth === currentWidth && resizeState.hasSwitched) {
        // Already in the target state, don't process again
        return;
    }

    // Mark as switched to prevent multiple switches
    if (newWidth !== currentWidth) {
        resizeState.hasSwitched = true;
    }

    // Find the grid container
    let container = null;

    // Method 1: Find parent with grid display
    let parent = resizeState.card.parentElement;
    while (parent && parent !== document.body) {
        const style = window.getComputedStyle(parent);
        if (style.display === 'grid' || parent.style.display === 'grid') {
            container = parent;
            break;
        }
        parent = parent.parentElement;
    }

    // Method 2: Find by style attribute
    if (!container) {
        container = resizeState.card.closest('div[style*="grid-template-columns"]');
    }

    // Method 3: Find by class settings-section
    if (!container) {
        const section = resizeState.card.closest('.settings-section');
        if (section) {
            const gridDiv = section.querySelector('div[style*="grid-template-columns"]');
            if (gridDiv) container = gridDiv;
        }
    }

    if (!container) {
        console.warn('Container not found for card resize');
        return;
    }

    // Remove animation class to restart it
    resizeState.card.classList.remove('animating');
    // Force reflow
    void resizeState.card.offsetWidth;

    // Update card width - only this card, not the grid
    resizeState.card.setAttribute('data-card-width', newWidth);

    // Add animation class for visual feedback
    resizeState.card.classList.add('animating');

    // Remove animation class after animation completes
    setTimeout(() => {
        if (resizeState.card) {
            resizeState.card.classList.remove('animating');
        }
    }, 500);

    resizeState.hasSwitched = true;

    // Don't change grid layout - keep it always as 1fr 1fr
    // CSS will handle the card width via grid-column property

    // Save to localStorage
    // Try to get card ID from data attribute first, fallback to title text
    const cardId = resizeState.card.getAttribute('data-card-id') ||
        resizeState.card.querySelector('.card-title')?.textContent?.trim() ||
        'unknown';
    localStorage.setItem(`cardWidth_${cardId}`, newWidth);

    console.log('Card resized:', cardId, 'from', currentWidth, 'to', newWidth, 'diffX:', diffX);
}

function stopResize(): void {
    if (resizeState.card) {
        // Remove resizing class after animation completes
        setTimeout(() => {
            if (resizeState.card) {
                resizeState.card.classList.remove('resizing');
            }
        }, 500);
    }
    resizeState.isResizing = false;
    resizeState.card = null;
    resizeState.hasSwitched = false;
    document.removeEventListener('mousemove', handleResize);
    document.removeEventListener('mouseup', stopResize);
    document.body.classList.remove('resizing');
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
}

// Debug Page Initialization
function initDebugPage(): void {
    // Slider 1
    const slider1 = document.querySelector('.debug-slider-1') as HTMLInputElement | null;
    const slider1Value = document.querySelector('.debug-slider-1-value');
    if (slider1 && slider1Value) {
        slider1.addEventListener('input', function (e: Event): void {
            const target = e.target as HTMLInputElement;
            slider1Value.textContent = target.value + '%';
        });
    }

    // Slider 2 (animated)
    const animatedSlider = document.querySelector('.debug-slider-animated') as HTMLInputElement | null;
    const sliderValue = document.querySelector('.debug-slider-value');
    if (animatedSlider && sliderValue) {
        animatedSlider.addEventListener('input', function (e: Event): void {
            const target = e.target as HTMLInputElement;
            sliderValue.textContent = target.value + '%';
        });
    }

    // Slider 3 (gradient)
    const slider3 = document.querySelector('.debug-slider-3') as HTMLInputElement | null;
    const slider3Value = document.querySelector('.debug-slider-3-value');
    if (slider3 && slider3Value) {
        slider3.addEventListener('input', function (e: Event): void {
            const target = e.target as HTMLInputElement;
            slider3Value.textContent = target.value + '%';
        });
    }

    // Draggable elements - improved
    const draggable = document.querySelector('.debug-draggable') as HTMLElement | null;
    if (draggable) {
        let isDragging = false;
        let startX, startY, initialX, initialY;

        draggable.addEventListener('mousedown', function (e: MouseEvent) {
            isDragging = true;
            startX = e.clientX;
            startY = e.clientY;
            const rect = draggable.getBoundingClientRect();
            initialX = rect.left;
            initialY = rect.top;
            (draggable as HTMLElement).style.position = 'fixed';
            (draggable as HTMLElement).style.zIndex = '10000';
            (draggable as HTMLElement).style.cursor = 'grabbing';
            e.preventDefault();
            e.stopPropagation();
        });

        const handleMouseMove = function (e: MouseEvent) {
            if (!isDragging) return;
            e.preventDefault();
            const dx = e.clientX - startX;
            const dy = e.clientY - startY;
            (draggable as HTMLElement).style.left = (initialX + dx) + 'px';
            (draggable as HTMLElement).style.top = (initialY + dy) + 'px';
        };

        const handleMouseUp = function (e) {
            if (!isDragging) return;
            isDragging = false;
            (draggable as HTMLElement).style.cursor = 'move';
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
        };

        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('mouseup', handleMouseUp);
    }

    // Drop zone
    const dropzone = document.querySelector('.debug-dropzone') as HTMLElement | null;
    if (dropzone) {
        dropzone.addEventListener('dragover', function (e) {
            e.preventDefault();
            dropzone.classList.add('drag-over');
        });

        dropzone.addEventListener('dragleave', function () {
            dropzone.classList.remove('drag-over');
        });

        dropzone.addEventListener('drop', function (e) {
            e.preventDefault();
            dropzone.classList.remove('drag-over');
            dropzone.textContent = 'Элемент перетащен!';
            setTimeout(() => {
                dropzone.textContent = 'Перетащите сюда';
            }, 2000);
        });
    }
}

window.setDebugTab = function (tabId: string, btn: HTMLElement | null): void {
    document.querySelectorAll('.debug-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.debug-tab-content').forEach(p => p.classList.remove('active'));
    if (btn) btn.classList.add('active');
    const tabContent = document.getElementById('debug-' + tabId + '-tab');
    if (tabContent) {
        tabContent.classList.add('active');
    }
};

// Load saved card widths
window.loadCardWidths = function (): void {
    document.querySelectorAll('.resizable-card').forEach(card => {
        // Try to get card ID from data attribute first, fallback to title text
        const cardId = card.getAttribute('data-card-id') ||
            card.querySelector('.card-title')?.textContent?.trim() ||
            'unknown';
        const savedWidth = localStorage.getItem(`cardWidth_${cardId}`);
        if (savedWidth && (savedWidth === 'full' || savedWidth === 'half')) {
            card.setAttribute('data-card-width', savedWidth);
        }
    });

    // Don't change grid layout - keep it always as 1fr 1fr
    // CSS will handle individual card widths via grid-column property
};

// Initialize on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        setTimeout(() => {
            initTaskbarToggles();
            initMonitorToggles();
            window.loadCardWidths();
        }, 500);
    });
} else {
    setTimeout(() => {
        initTaskbarToggles();
        initMonitorToggles();
        window.loadCardWidths();
    }, 500);
}

interface LogEntry {
    level: string;
    source: string;
    timestamp: number;
    message: string;
}

let lastTimestamp: number = 0, allLogs: LogEntry[] = [];
let currentLogView: string = 'general'; // general | bot | llm | sd
const LOG_PREFIX_MAP: Record<string, string> = { "BOT": "🤖", "LLM": "🧠", "SD": "🎨", "SYSTEM": "⚙️" };

function normSource(source: string | undefined): string {
    const raw = String(source || '').trim();
    return raw.replace(/[^a-z0-9_]/gi, '').toUpperCase();
}

function getLogPrefix(sourceNorm: string): string {
    return LOG_PREFIX_MAP[sourceNorm] || "📝";
}

function logMatchesView(log: LogEntry | undefined, view: string): boolean {
    const s = normSource(log && log.source);
    if (!s) return false;
    if (view === 'bot') return s === 'BOT';
    if (view === 'llm') return s === 'LLM';
    if (view === 'sd') return s === 'SD';
    // general: everything else (SYSTEM, DebugServer, etc.)
    return s !== 'BOT' && s !== 'LLM' && s !== 'SD';
}

function getActiveLogsPane(): HTMLElement | null {
    const id = `logs-${currentLogView}`;
    return document.getElementById(id) || document.getElementById('logs-general');
}

window.setLogView = function (view: string, btn: HTMLElement | null): void {
    currentLogView = view || 'general';
    document.querySelectorAll('.terminal-tab').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    document.querySelectorAll('.logs-pane').forEach(p => p.classList.remove('active'));
    const pane = getActiveLogsPane();
    if (pane) pane.classList.add('active');
    renderLogs(true);
};

async function clearBackendLogs(): Promise<void> {
    try {
        // Best-effort; even if it fails we still clear UI
        await fetch('/api/logs/clear', { method: 'POST' });
    } catch (e) {
        // silent
    }
}

window.clearLogs = async function (showMessage: boolean = true): Promise<void> {
    ['logs-general', 'logs-bot', 'logs-llm', 'logs-sd'].forEach(id => {
        const pane = document.getElementById(id);
        if (pane) pane.innerHTML = '';
    });
    allLogs = [];
    lastTimestamp = 0;
    await clearBackendLogs();
    if (showMessage) {
        showToast(t('ui.launcher.web.logs_cleared', 'Логи очищены'), 'success', 1500);
    }
};

function createLogEl(log: LogEntry): HTMLElement {
    const div = document.createElement('div');
    div.className = `log-entry level-${log.level}`;
    const sNorm = normSource(log.source);
    const prefix = getLogPrefix(sNorm);
    const time = new Date(log.timestamp * 1000).toLocaleTimeString();
    const msg = log.message.replace(/</g, '&lt;').replace(/>/g, '&gt;');
    div.innerHTML = `<span class="log-time">${time}</span><span class="log-src src-${sNorm}">${prefix} ${sNorm || log.source}</span><span class="log-msg">${msg}</span>`;
    return div;
}

function renderLogs(clear: boolean = false): void {
    const container = getActiveLogsPane();
    if (!container) return;
    if (clear) container.innerHTML = '';

    const logsToShow = allLogs
        .filter(l => logMatchesView(l, currentLogView))
        .sort((a, b) => a.timestamp - b.timestamp);

    const fragment = document.createDocumentFragment();
    logsToShow.forEach(log => fragment.appendChild(createLogEl(log)));
    container.appendChild(fragment);
    container.scrollTop = container.scrollHeight;
}

// Safe JSON parse helper (define early for use in pollLogs)
if (!window.safeJsonParse) {
    window.safeJsonParse = function (text, defaultValue = {}) {
        try {
            return text ? JSON.parse(text) : defaultValue;
        } catch (e) {
            console.warn('JSON parse error:', e, 'Text:', text?.substring(0, 100));
            return defaultValue;
        }
    };
}

async function pollLogs(): Promise<void> {
    try {
        const res = await fetch(`/api/logs?since=${lastTimestamp}`);
        const text = await res.text();
        const newLogs = window.safeJsonParse(text, []);
        if (newLogs.length > 0) {
            allLogs.push(...newLogs);
            lastTimestamp = newLogs[newLogs.length - 1].timestamp;
            const pane = getActiveLogsPane();
            const shouldScroll = pane ? (pane.scrollHeight - pane.scrollTop - pane.clientHeight < 100) : true;
            const prevScrollTop = pane ? pane.scrollTop : 0;
            renderLogs(true);
            if (pane) {
                pane.scrollTop = shouldScroll ? pane.scrollHeight : prevScrollTop;
            }
            if (allLogs.length > 2000) {
                // Keep only last N logs to avoid memory issues
                allLogs = allLogs.slice(-1000);
                renderLogs(true);
            }
        }
    } catch (e) {
        console.error("Failed to poll logs:", e);
    }
    setTimeout(pollLogs, 1000);
}

window.updateState = async function (): Promise<void> {
    try {
        const res = await fetch('/api/state');
        const text = await res.text();
        const data = window.safeJsonParse(text, {}) as any;
        const serviceMap = {
            bot: t('ui.launcher.service.telegram_bot', 'Telegram Bot'),
            llm: t('ui.launcher.service.llm_server', 'Ollama'),
            sd: t('ui.launcher.service.stable_diffusion', 'Stable Diffusion')
        };
        const list = document.getElementById('services-list');
        if (!list) return; // Exit if list doesn't exist

        // IMPORTANT: Do not rebuild the whole list each poll.
        // Rebuilding causes DOM nodes to be replaced every 2s, which breaks clicks and UX.
        let allRunning = true;
        let anyRunning = false;
        Object.entries(serviceMap).forEach(([key, name]) => {
            const status = data.services[key] || 'stopped';
            const isRun = status === 'running';
            if (isRun) anyRunning = true;
            if (status !== 'running') allRunning = false;
            const buttonTitle = isRun ? t('ui.launcher.button.stop', 'Остановить') + ' ' + name :
                t('ui.launcher.button.start', 'Запустить') + ' ' + name;

            let row = list.querySelector(`.service-row[data-service="${key}"]`);
            if (!row) {
                row = document.createElement('div');
                row.className = 'service-row';
                row.setAttribute('data-service', key);
                row.innerHTML = `
                            <div class="service-info">
                                <div class="status-dot"></div>
                                <div class="service-name"></div>
                            </div>
                            <div class="service-actions" style="display: flex; gap: 0.25rem;"></div>
                        `;
                list.appendChild(row);
            }

            // Status + name
            row.setAttribute('data-status', status);
            const nameEl = row.querySelector('.service-name');
            if (nameEl) nameEl.textContent = name;
            const dotEl = row.querySelector('.status-dot');
            if (dotEl) dotEl.className = `status-dot ${status}`;

            // Actions
            const actions = row.querySelector('.service-actions');
            if (actions) {
                // Restart button (only when running)
                let restartBtn = actions.querySelector('.btn-toggle-service.restart') as HTMLButtonElement | null;
                if (isRun) {
                    if (!restartBtn) {
                        restartBtn = document.createElement('button');
                        restartBtn.className = 'btn-toggle-service restart';
                        restartBtn.style.background = 'var(--warning)';
                        restartBtn.style.opacity = '0.7';
                        restartBtn.innerHTML = `<svg class="icon" style="transform: rotate(180deg);"><use href="#icon-start"></use></svg>`;
                        restartBtn.addEventListener('click', () => control('restart', key));
                        actions.appendChild(restartBtn);
                    }
                    restartBtn.title = `${t('ui.launcher.button.restart', 'Перезапустить')} ${name}`;
                } else if (restartBtn) {
                    restartBtn.remove();
                }

                // Main toggle button
                let toggleBtn = actions.querySelector('.btn-toggle-service.main') as HTMLButtonElement | null;
                if (!toggleBtn) {
                    toggleBtn = document.createElement('button');
                    toggleBtn.className = 'btn-toggle-service main';
                    toggleBtn.innerHTML = `<svg class="icon"><use href="#icon-start"></use></svg>`;
                    actions.appendChild(toggleBtn);
                }
                toggleBtn.classList.toggle('stop', isRun);
                toggleBtn.title = buttonTitle;
                toggleBtn.onclick = () => {
                    // If SD is not installed, show install prompt instead of failing start.
                    if (!isRun && key === 'sd') {
                        startSdWithInstallCheck();
                        return;
                    }
                    control(isRun ? 'stop' : 'start', key);
                };
                const useEl = toggleBtn.querySelector('use');
                if (useEl) useEl.setAttribute('href', `#icon-${isRun ? 'stop' : 'start'}`);
            }
        });

        // Update status indicator (prefer: Error > Online > Offline)
        const statusIndicator = document.getElementById('status-indicator');
        const statusDot = document.querySelector('.status-indicator');
        if (statusIndicator && data.services) {
            // Only update if we have valid service data
            const hasValidData = Object.keys(data.services).length > 0;
            if (hasValidData) {
                const statuses = Object.values(data.services || {});
                const anyError = statuses.includes('error');
                const anyRun2 = statuses.includes('running');
                if (anyError) {
                    statusIndicator.style.color = 'var(--danger)';
                    statusIndicator.textContent = t('ui.launcher.status.error', 'Ошибка');
                } else if (anyRun2) {
                    statusIndicator.style.color = 'var(--success)';
                    statusIndicator.textContent = t('ui.launcher.web.status_online', 'Online');
                } else {
                    statusIndicator.style.color = 'var(--text-muted)';
                    statusIndicator.textContent = t('ui.launcher.web.status_offline', 'Offline');
                }
            }
        }
        if (statusDot && data.services && Object.keys(data.services).length > 0) {
            const statuses = Object.values(data.services || {});
            const anyError = statuses.includes('error');
            const anyRun2 = statuses.includes('running');
            (statusDot as HTMLElement).style.background = anyError ? 'var(--danger)' : (anyRun2 ? 'var(--success)' : 'var(--text-muted)');
        }
    } catch (e) {
        const statusIndicator = document.getElementById('status-indicator');
        if (statusIndicator) {
            statusIndicator.style.color = 'var(--danger)';
        }
    }
}

async function startSdWithInstallCheck(): Promise<void> {
    try {
        const res = await fetch('/api/check_sd_installed');
        if (res.ok) {
            const data = await res.json();
            if (data && data.installed === false) {
                // Explicit user action: show modal even if previously dismissed.
                window.showInstallModal();
                return;
            }
        }
    } catch (e) {
        // ignore and fall back to start attempt
    }
    control('start', 'sd');
}

window.toggleLangDropdown = function (page: string = 'console'): void {
    const menuId = `lang-dropdown-menu-${page}`;
    const menu = document.getElementById(menuId);
    if (menu) {
        // Close all other dropdowns
        document.querySelectorAll('.lang-dropdown-menu').forEach(m => {
            if (m.id !== menuId) m.classList.remove('show');
        });
        menu.classList.toggle('show');
    }
};
