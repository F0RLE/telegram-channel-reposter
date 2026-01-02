// Close modal on Escape key
document.addEventListener('keydown', (e: KeyboardEvent): void => {
    if (e.key === 'Escape') {
        const modal = document.getElementById('module-settings-modal');
        if (modal && modal.classList.contains('show')) {
            hideModuleSettingsModal();
        }
    }
});

declare function hideModuleSettingsModal(): void;
declare function loadModulesTab(): void;
declare function showToast(message: string, type: string, duration?: number, title?: string): void;
declare function initTaskbarToggles(): void;
declare function initMonitorToggles(): void;
declare function toggleNavItem(pageId: string, enabled: boolean): void;
declare function toggleMonitorItem(monitorId: string, enabled: boolean): void;

function generateModuleSettingsForm(settings: Record<string, any>): void {
    const container = document.getElementById('module-settings-fields');
    if (!container) return;
    container.innerHTML = '';

    if (Object.keys(settings).length === 0) {
        container.innerHTML = '<div style="text-align: center; padding: 2rem; color: var(--text-muted);">Нет доступных настроек.</div>';
        return;
    }

    Object.keys(settings).forEach(key => {
        const value = settings[key];
        const fieldType = typeof value;

        let fieldHtml = '';

        if (fieldType === 'boolean') {
            fieldHtml = `
                        <div class="form-group" style="margin-bottom: 1.5rem;">
                            <div class="switch-row">
                                <div style="flex: 1;">
                                    <div class="switch-label">${formatKey(key)}</div>
                                </div>
                                <label class="switch">
                                    <input type="checkbox" id="field-${key}" name="${key}" ${value ? 'checked' : ''}>
                                    <span class="slider"></span>
                                </label>
                            </div>
                        </div>
                    `;
        } else if (fieldType === 'number') {
            fieldHtml = `
                        <div class="form-group" style="margin-bottom: 1.5rem;">
                            <label class="form-label" for="field-${key}">${formatKey(key)}</label>
                            <input type="number" id="field-${key}" name="${key}" value="${value}" class="form-input" style="width: 100%; padding: 0.75rem; background: var(--bg-light); border: 1px solid var(--border-color); border-radius: 10px; color: var(--text-primary);">
                        </div>
                    `;
        } else if (Array.isArray(value)) {
            fieldHtml = `
                        <div class="form-group" style="margin-bottom: 1.5rem;">
                            <label class="form-label" for="field-${key}">${formatKey(key)}</label>
                            <textarea id="field-${key}" name="${key}" class="form-input" style="width: 100%; padding: 0.75rem; background: var(--bg-light); border: 1px solid var(--border-color); border-radius: 10px; color: var(--text-primary); min-height: 100px; font-family: 'Monocraft', 'Consolas', 'Monaco', monospace;">${(value as unknown[]).join('\n')}</textarea>
                            <div class="helper-text">Каждое значение на новой строке</div>
                        </div>
                    `;
        } else {
            const isLong = value && value.length > 100;
            fieldHtml = `
                        <div class="form-group" style="margin-bottom: 1.5rem;">
                            <label class="form-label" for="field-${key}">${formatKey(key)}</label>
                            ${isLong
                    ? `<textarea id="field-${key}" name="${key}" class="form-input" style="width: 100%; padding: 0.75rem; background: var(--bg-light); border: 1px solid var(--border-color); border-radius: 10px; color: var(--text-primary); min-height: 100px; font-family: 'Monocraft', 'Consolas', 'Monaco', monospace;">${escapeHtml((value as string) || '')}</textarea>`
                    : `<input type="text" id="field-${key}" name="${key}" value="${escapeHtml((value as string) || '')}" class="form-input" style="width: 100%; padding: 0.75rem; background: var(--bg-light); border: 1px solid var(--border-color); border-radius: 10px; color: var(--text-primary);">`
                }
                        </div>
                    `;
        }

        container.innerHTML += fieldHtml;
    });
}

function populateModuleSettingsForm(settings: Record<string, any>): void {
    Object.keys(settings).forEach(key => {
        const field = document.getElementById(`field-${key}`) as HTMLInputElement | HTMLTextAreaElement | null;
        if (!field) return;

        const value = settings[key];

        if ((field as HTMLInputElement).type === 'checkbox') {
            (field as HTMLInputElement).checked = !!value;
        } else if (field.type === 'number') {
            field.value = value;
        } else if (field.tagName === 'TEXTAREA') {
            if (Array.isArray(value)) {
                field.value = value.join('\n');
            } else {
                field.value = value || '';
            }
        } else {
            field.value = value || '';
        }
    });
}

function formatKey(key: string): string {
    return key
        .replace(/_/g, ' ')
        .replace(/([A-Z])/g, ' $1')
        .replace(/^./, str => str.toUpperCase())
        .trim();
}

function escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Handle form submission
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('module-settings-form') as HTMLFormElement | null;
    if (form) {
        form.addEventListener('submit', async (e: Event): Promise<void> => {
            e.preventDefault();

            if (!currentModuleId) return;

            const formData = new FormData(form);
            const settings = {};

            // Collect form data
            for (const [key, value] of formData.entries()) {
                const field = document.getElementById(`field-${key}`) as HTMLInputElement | HTMLTextAreaElement | null;

                if (field instanceof HTMLInputElement && field.type === 'checkbox') {
                    settings[key] = (field as HTMLInputElement).checked;
                } else if (field instanceof HTMLInputElement && field.type === 'number') {
                    settings[key] = parseFloat(value as string) || 0;
                } else {
                    const strValue = value as string;
                    if (strValue.includes('\n')) {
                        settings[key] = strValue.split('\n').filter(v => v.trim());
                    } else {
                        settings[key] = strValue;
                    }
                }
            }

            // Save settings
            const saveBtn = document.getElementById('module-settings-save-btn') as HTMLButtonElement;
            const originalText = saveBtn.innerHTML;
            saveBtn.disabled = true;
            saveBtn.innerHTML = '<svg class="icon"><use href="#icon-save"></use></svg> <span>Сохранение...</span>';

            try {
                const res = await fetch(`/api/modules/${currentModuleId}/settings`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(settings)
                });

                const data = await res.json();

                if (data.success) {
                    showToast('Настройки сохранены', 'success');
                    setTimeout(() => {
                        hideModuleSettingsModal();
                        // Reload modules tab to reflect changes
                        if (typeof loadModulesTab === 'function') {
                            loadModulesTab();
                        }
                    }, 1000);
                } else {
                    showToast(data.message || 'Ошибка сохранения', 'error');
                    saveBtn.disabled = false;
                    saveBtn.innerHTML = originalText;
                }
            } catch (e) {
                showToast('Ошибка: ' + (e as Error).message, 'error');
                saveBtn.disabled = false;
                saveBtn.innerHTML = originalText;
            }
        });
    }
});


window.showSettingsSection = function (sectId: string, btn: HTMLElement | null): void {
    // Get current active section
    const currentSection = document.querySelector('.settings-section.active') as HTMLElement;
    const targetSection = document.getElementById('sect-' + sectId);

    if (!targetSection) {
        console.error('Settings section not found:', 'sect-' + sectId);
        return;
    }

    // If switching to a different section, animate out current section
    if (currentSection && currentSection !== targetSection) {
        currentSection.style.transition = 'opacity 0.3s cubic-bezier(0.4, 0, 0.2, 1), transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
        currentSection.style.opacity = '0';
        currentSection.style.transform = 'translateY(-20px)';

        // Remove active class after animation
        setTimeout(() => {
            currentSection.classList.remove('active');
            currentSection.style.display = 'none';
        }, 300);
    }

    // Show and animate in new section
    targetSection.style.display = 'block';
    targetSection.style.opacity = '0';
    targetSection.style.transform = 'translateY(20px)';

    // Force reflow
    targetSection.offsetHeight;

    // Animate in
    setTimeout(() => {
        targetSection.classList.add('active');
        targetSection.style.transition = 'opacity 0.4s cubic-bezier(0.4, 0, 0.2, 1), transform 0.4s cubic-bezier(0.4, 0, 0.2, 1)';
        targetSection.style.opacity = '1';
        targetSection.style.transform = 'translateY(0)';
    }, currentSection && currentSection !== targetSection ? 50 : 0);

    // Update navigation buttons
    document.querySelectorAll('.settings-nav .nav-btn').forEach(b => b.classList.remove('active'));
    if (btn) {
        btn.classList.add('active');
    }

    // Initialize taskbar toggles when opening general section
    if (sectId === 'general') {
        setTimeout(() => {
            if (typeof initTaskbarToggles === 'function') {
                initTaskbarToggles();
            }
            if (typeof initMonitorToggles === 'function') {
                initMonitorToggles();
            }
            if (typeof window.loadCardWidths === 'function') {
                window.loadCardWidths();
            }
        }, 100);
    }
};
window.setTab = function (tab: string, btn: HTMLElement | null): void {
    // Tabs removed - no filtering
};

// Card width management
window.setCardWidth = function (btn: HTMLElement, width: string): void {
    const card = btn.closest('.hardware-card') as HTMLElement;
    if (!card) return;

    card.setAttribute('data-card-width', width);

    // Update button states
    const buttons = card.querySelectorAll('.btn');
    buttons.forEach(b => {
        if (b === btn) {
            (b as HTMLElement).style.background = 'var(--primary)';
            (b as HTMLElement).style.color = 'white';
        } else {
            (b as HTMLElement).style.background = 'var(--bg-light)';
            (b as HTMLElement).style.color = 'var(--text-secondary)';
        }
    });

    // Update grid layout
    const container = card.closest('[style*="grid-template-columns"]') as HTMLElement;
    if (container) {
        if (width === 'full') {
            container.style.gridTemplateColumns = '1fr';
        } else {
            container.style.gridTemplateColumns = '1fr 1fr';
        }
    }
};

// Taskbar visibility management
window.toggleNavItem = function (pageId: string, enabled: boolean): void {
    const navBtn = document.querySelector(`#sidebar .nav-btn[data-page="${pageId}"]`);
    if (!navBtn) return;

    // Save to localStorage
    let hiddenItems = [];
    try {
        const stored = localStorage.getItem('hiddenNavItems');
        hiddenItems = stored ? JSON.parse(stored) : [];
    } catch (e) {
        hiddenItems = [];
        localStorage.setItem('hiddenNavItems', '[]');
    }

    if (enabled) {
        // Show
        const index = hiddenItems.indexOf(pageId);
        if (index > -1) {
            hiddenItems.splice(index, 1);

            // Prepare for animation: make visible but hidden state
            navBtn.classList.add('nav-item-hiding');
            navBtn.classList.remove('hidden');

            // Force reflow
            void (navBtn as HTMLElement).offsetHeight;

            // Animate in
            navBtn.classList.remove('nav-item-hiding');
        }
    } else {
        // Hide
        if (!hiddenItems.includes(pageId)) {
            hiddenItems.push(pageId);

            // Animate out
            navBtn.classList.add('nav-item-hiding');

            // Wait for animation then hide completely
            setTimeout(() => {
                // Ensure it's still supposed to be hidden (user didn't toggle back quickly)
                if (navBtn.classList.contains('nav-item-hiding')) {
                    navBtn.classList.add('hidden');
                    navBtn.classList.remove('nav-item-hiding');
                }
            }, 500);
        }
    }
    localStorage.setItem('hiddenNavItems', JSON.stringify(hiddenItems));
};

// Initialize taskbar toggles - NEW SELECTABLE CARD DESIGN
window.initTaskbarToggles = function (): void {
    const container = document.getElementById('taskbar-toggles');
    if (!container) return;

    // Prevent double initialization
    if (container.dataset.initialized === 'true') return;
    container.dataset.initialized = 'true';

    // Updated per user request: Removed 'settings' and 'console', renamed 'debug'
    const navItems = [
        { id: 'home', label: 'Главное меню', icon: '#icon-home' },
        { id: 'chat', label: 'Чат', icon: '#icon-chat' },
        { id: 'modules', label: 'Модули', icon: '#icon-folder' },
        { id: 'downloads', label: 'Загрузки', icon: '#icon-download' },
        { id: 'debug', label: 'Консоль', icon: '#icon-console' }
    ];

    let hiddenItems = [];
    try {
        const stored = localStorage.getItem('hiddenNavItems');
        hiddenItems = stored ? JSON.parse(stored) : [];
    } catch (e) {
        hiddenItems = [];
        localStorage.setItem('hiddenNavItems', '[]');
    }

    // Pre-fetch all nav buttons to check their current hidden state
    const navBtnMap = {};
    navItems.forEach(item => {
        navBtnMap[item.id] = document.querySelector(`#sidebar .nav-btn[data-page="${item.id}"]`);
    });

    const html = navItems.map(item => {
        const isHidden = navBtnMap[item.id] && navBtnMap[item.id].classList.contains('hidden');
        const isActive = !isHidden;
        const labelKey = `ui.launcher.settings.toggle_${item.id}`;
        return `
            <div class="taskbar-toggle-item ${isActive ? 'active' : ''}"
                 data-page-id="${item.id}"
                 onclick="toggleTaskbarItem('${item.id}')"
                 title="${item.label}">
                <svg class="toggle-icon">
                    <use href="${item.icon}"></use>
                </svg>
                <span class="toggle-label" data-i18n="${labelKey}">${item.label}</span>
            </div>
        `;
    }).join('');

    container.innerHTML = html;

    // Apply hidden state on load
    hiddenItems.forEach(pageId => {
        const navBtn = document.querySelector(`#sidebar .nav-btn[data-page="${pageId}"]`);
        if (navBtn) {
            navBtn.classList.add('hidden');
        }
    });
};

// Toggle taskbar item handler
window.toggleTaskbarItem = function (pageId: string): void {
    const item = document.querySelector(`.taskbar-toggle-item[data-page-id="${pageId}"]`);
    if (!item) return;

    const isCurrentlyActive = item.classList.contains('active');
    const newState = !isCurrentlyActive;

    // Toggle visual state
    item.classList.toggle('active');

    // Call existing toggle logic
    toggleNavItem(pageId, newState);
};

// Monitor visibility management
window.toggleMonitorItem = function (monitorId: string, enabled: boolean): void {
    const monitorStat = document.querySelector(`#system-monitor .sysmon-stat[data-monitor-id="${monitorId}"]`);
    if (!monitorStat) return;

    // Save to localStorage
    let hiddenMonitors = [];
    try {
        const stored = localStorage.getItem('hiddenMonitors');
        hiddenMonitors = stored ? JSON.parse(stored) : [];
    } catch (e) {
        hiddenMonitors = [];
        localStorage.setItem('hiddenMonitors', '[]');
    }

    if (enabled) {
        // Show - remove from hidden list
        const index = hiddenMonitors.indexOf(monitorId);
        if (index > -1) {
            hiddenMonitors.splice(index, 1);
        }
        // Ensure hiding class is set first (so it starts invisible)
        monitorStat.classList.add('hiding');
        // Remove hidden to put element back in layout
        monitorStat.classList.remove('hidden');
        // Force reflow
        void (monitorStat as HTMLElement).offsetHeight;
        // Remove hiding to trigger fade-in animation
        monitorStat.classList.remove('hiding');
    } else {
        // Hide - add to hidden list
        if (!hiddenMonitors.includes(monitorId)) {
            hiddenMonitors.push(monitorId);
        }
        // First add hiding class for animation
        monitorStat.classList.add('hiding');
        // After animation completes, add hidden to remove from layout
        setTimeout(() => {
            monitorStat.classList.add('hidden');
            window.updateMonitorPanelVisibility();
        }, 250);
    }

    localStorage.setItem('hiddenMonitors', JSON.stringify(hiddenMonitors));

    // Update divider and panel visibility
    updateMonitorDivider();
    if (enabled) {
        window.updateMonitorPanelVisibility();
    }
};

window.updateMonitorPanelVisibility = function (): void {
    const monitorPanel = document.getElementById('system-monitor');
    if (!monitorPanel) return;

    let hiddenMonitors = [];
    try {
        hiddenMonitors = JSON.parse(localStorage.getItem('hiddenMonitors') || '[]');
    } catch (e) { }

    const totalMonitors = ['cpu', 'gpu', 'ram', 'vram', 'disk', 'network'];
    const allHidden = totalMonitors.every(id => hiddenMonitors.includes(id));

    if (allHidden) {
        monitorPanel.style.opacity = '0';
        monitorPanel.style.maxHeight = '0';
        monitorPanel.style.overflow = 'hidden';
        monitorPanel.style.pointerEvents = 'none';
        monitorPanel.style.padding = '0';
        monitorPanel.style.margin = '0';
        monitorPanel.style.border = 'none';
    } else {
        monitorPanel.style.opacity = '';
        monitorPanel.style.maxHeight = '';
        monitorPanel.style.overflow = '';
        monitorPanel.style.pointerEvents = '';
        monitorPanel.style.padding = '';
        monitorPanel.style.margin = '';
        monitorPanel.style.border = '';
    }
};

function updateMonitorDivider(): void {
    const divider = document.querySelector('.sysmon-divider');
    if (!divider) return;

    // The divider separates CPU/GPU/RAM/VRAM from Disk/Network
    // Hide it if all items above OR all items below are hidden
    let hiddenMonitors = [];
    try {
        hiddenMonitors = JSON.parse(localStorage.getItem('hiddenMonitors') || '[]');
    } catch (e) { }

    const aboveItems = ['cpu', 'gpu', 'ram', 'vram'];
    const belowItems = ['disk', 'network'];

    const allAboveHidden = aboveItems.every(id => hiddenMonitors.includes(id));
    const allBelowHidden = belowItems.every(id => hiddenMonitors.includes(id));

    // Hide divider if either all above OR all below are hidden
    if (allAboveHidden || allBelowHidden) {
        (divider as HTMLElement).style.display = 'none';
    } else {
        (divider as HTMLElement).style.display = '';
    }
}

// Initialize monitor toggles - NEW GRID BUTTON DESIGN
window.initMonitorToggles = function (): void {
    const container = document.getElementById('monitor-toggles');
    if (!container) return;

    // Prevent double initialization
    if (container.dataset.initialized === 'true') return;
    container.dataset.initialized = 'true';

    const monitorItems = [
        { id: 'cpu', label: 'CPU', icon: '#icon-cpu' },
        { id: 'gpu', label: 'GPU', icon: '#icon-gpu' },
        { id: 'ram', label: 'RAM', icon: '#icon-ram' },
        { id: 'vram', label: 'VRAM', icon: '#icon-vram' },
        { id: 'disk', label: 'Диск', icon: '#icon-disk' },
        { id: 'network', label: 'Сеть', icon: '#icon-network' }
    ];

    let hiddenMonitors = [];
    try {
        const stored = localStorage.getItem('hiddenMonitors');
        hiddenMonitors = stored ? JSON.parse(stored) : [];
    } catch (e) {
        hiddenMonitors = [];
        localStorage.setItem('hiddenMonitors', '[]');
    }

    container.innerHTML = monitorItems.map(item => {
        const isActive = !hiddenMonitors.includes(item.id);
        const labelKey = `ui.launcher.settings.monitor_${item.id}`;
        return `
            <button class="monitor-toggle-btn ${isActive ? 'active' : ''}"
                    data-monitor-id="${item.id}"
                    onclick="toggleMonitorBtn('${item.id}')"
                    title="${item.label}">
                <svg class="toggle-icon">
                    <use href="${item.icon}"></use>
                </svg>
                <span class="toggle-label" data-i18n="${labelKey}">${item.label}</span>
            </button>
        `;
    }).join('');

    // Apply hidden state on load
    hiddenMonitors.forEach(monitorId => {
        const monitorStat = document.querySelector(`#system-monitor .sysmon-stat[data-monitor-id="${monitorId}"]`);
        if (monitorStat) {
            (monitorStat as HTMLElement).classList.add('hidden');
        }
    });

    // Update divider visibility on init
    updateMonitorDivider();
};

// Toggle monitor button handler
window.toggleMonitorBtn = function (monitorId: string): void {
    const btn = document.querySelector(`.monitor-toggle-btn[data-monitor-id="${monitorId}"]`);
    if (!btn) return;

    const isCurrentlyActive = btn.classList.contains('active');
    const newState = !isCurrentlyActive;

    // Toggle visual state
    btn.classList.toggle('active');

    // Call existing toggle logic
    toggleMonitorItem(monitorId, newState);
};

// Card resize management
interface ResizeState {
    isResizing: boolean;
    card: HTMLElement | null;
    startX: number;
    startWidth: string;
    hasSwitched: boolean;
}

window.resizeState = {
    isResizing: false,
    card: null,
    startX: 0,
    startWidth: 'full',
    hasSwitched: false
};

window.startResize = function (e: MouseEvent, handle: HTMLElement): void {
    e.preventDefault();
    resizeState.isResizing = true;
    resizeState.card = handle.closest('.resizable-card') as HTMLElement;
    resizeState.startX = e.clientX;
    resizeState.startWidth = resizeState.card.dataset.cardWidth || 'full';
    resizeState.hasSwitched = false;

    document.body.style.cursor = 'ew-resize';
    document.body.classList.add('no-select');

    // Add overlay to prevent iframe interference
    const overlay = document.createElement('div');
    overlay.id = 'resize-overlay';
    overlay.style.position = 'fixed';
    overlay.style.top = '0';
    overlay.style.left = '0';
    overlay.style.width = '100%';
    overlay.style.height = '100%';
    overlay.style.zIndex = '9999';
    overlay.style.cursor = 'ew-resize';
    document.body.appendChild(overlay);
};

// --- Responsive Helper ---
function observeToggleGrid(containerId: string): void {
    const container = document.getElementById(containerId);
    if (!container) return;

    // Disconnect existing if any (stored on element)
    if ((container as any)._resizeObserver) {
        (container as any)._resizeObserver.disconnect();
    }

    const observer = new ResizeObserver(entries => {
        for (const entry of entries) {
            const width = entry.contentRect.width;

            // Compact mode: < 450px (hides text)
            if (width < 450) {
                container.classList.add('compact');
            } else {
                container.classList.remove('compact');
            }

            // Super compact: < 300px (smaller icons)
            if (width < 300) {
                container.classList.add('super-compact');
            } else {
                container.classList.remove('super-compact');
            }
        }
    });

    observer.observe(container);
    (container as any)._resizeObserver = observer;
}

// Hook into initializations
const originalInitTaskbar = window.initTaskbarToggles;
window.initTaskbarToggles = function (): void {
    if (originalInitTaskbar) originalInitTaskbar();
    observeToggleGrid('taskbar-toggles');
};

const originalInitMonitor = window.initMonitorToggles;
window.initMonitorToggles = function (): void {
    if (originalInitMonitor) originalInitMonitor();
    observeToggleGrid('monitor-toggles');
};

document.addEventListener('mousemove', (e) => {
    if (!resizeState.isResizing || !resizeState.card) return;

    const delta = e.clientX - resizeState.startX;
    const threshold = 100; // px to switch

    // Visual feedback could be added here
    // For now we just switch if threshold is crossed
    if (!resizeState.hasSwitched) {
        if (resizeState.startWidth === 'full' && delta < -threshold) {
            // Shrink to half
            resizeState.card.dataset.cardWidth = 'half';
            resizeState.hasSwitched = true;
            saveCardWidths();
        } else if (resizeState.startWidth === 'half' && delta > threshold) {
            // Grow to full
            resizeState.card.dataset.cardWidth = 'full';
            resizeState.hasSwitched = true;
            saveCardWidths();
        }
    } else {
        // If we already switched, check if we need to revert
        // This logic can be complex, simplifying for now:
        // user has to release and drag again to revert, to avoid flickering
    }
});

document.addEventListener('mouseup', () => {
    if (resizeState.isResizing) {
        resizeState.isResizing = false;
        resizeState.card = null;
        document.body.style.cursor = '';
        document.body.classList.remove('no-select');

        const overlay = document.getElementById('resize-overlay');
        if (overlay) overlay.remove();
    }
});

function saveCardWidths(): void {
    const widths = {};
    document.querySelectorAll('.resizable-card').forEach(card => {
        const id = (card as HTMLElement).dataset.cardId;
        if (id) {
            widths[id] = (card as HTMLElement).dataset.cardWidth;
        }
    });
    localStorage.setItem('settings_card_widths', JSON.stringify(widths));
}

window.loadCardWidths = function (): void {
    try {
        const widths = JSON.parse(localStorage.getItem('settings_card_widths') || '{}');
        Object.keys(widths).forEach(id => {
            const card = document.querySelector(`.resizable-card[data-card-id="${id}"]`) as HTMLElement;
            if (card) {
                card.dataset.cardWidth = widths[id];
            }
        });
    } catch (e) { console.error('Failed to load card widths', e); }
};
