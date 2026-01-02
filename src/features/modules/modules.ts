let modulesLoading: boolean = false;
import { invoke } from '../../shared/api/tauri';
async function loadModulesTab(): Promise<void> {
    const grid = document.getElementById('modules-grid');
    if (!grid) return;

    // Prevent double loading
    if (modulesLoading) return;
    modulesLoading = true;

    // Show skeleton loaders (only once)
    const skeletons = grid.querySelectorAll('[id^="modules-grid-skeleton"]');
    skeletons.forEach(s => {
        const el = s as HTMLElement;
        el.style.display = 'block';
        el.style.animation = 'none';
        void el.offsetWidth; // Force reflow
        el.style.animation = '';
    });

    try {
        const items = await invoke<ModuleItem[]>('get_modules');



        // Hide skeleton loaders
        skeletons.forEach(s => (s as HTMLElement).style.display = 'none');

        // Render modules with animation
        renderModules(items);
        showActionFeedback('success');
    } catch (e: unknown) {
        skeletons.forEach(s => (s as HTMLElement).style.display = 'none');
        const error = e as Error;
        grid.innerHTML = `<div style="color: var(--danger); padding: 2rem; text-align: center;">Ошибка загрузки модулей: ${error.message}</div>`;
        showToast('Ошибка загрузки модулей', 'error', 3000, 'Ошибка');
    } finally {
        modulesLoading = false;
    }
}

interface ModuleItem {
    id: string;
    name?: string;
    version?: string;
    description?: string;
    type?: string;
    kind?: string;
    status?: string;
    installed?: boolean;
    icon?: string;
    removable?: boolean;
    recommended?: boolean;
    repo?: string;
    custom?: boolean;
}

interface ControlResponse {
    success: boolean;
    message: string;
    status?: string;
}

function renderModules(items: ModuleItem[]): void {
    const grid = document.getElementById('modules-grid');
    if (!grid) return;
    if (!items || items.length === 0) {
        grid.innerHTML = '<div style="color: var(--text-muted); font-size: 0.85rem;">Модули пока не добавлены.</div>';
        return;
    }

    function serviceLabel(type: string): string {
        return '';
    }

    function statusHint(status: string, installed: boolean): string {
        if (status === 'recommended') return '';
        if (installed && status === 'installed') return 'Модуль установлен';
        if (status === 'running') return 'Сервис запущен';
        if (!installed && status === 'available') return 'Модуль можно скачать';
        return '';
    }

    // Категории модулей
    const textGenerationCards = [];
    const imageGenerationCards = [];
    const generalServicesCards = [];

    function getModuleCategory(type: string): string {
        const typeLower = (type || '').toLowerCase();
        if (typeLower === 'llm' || typeLower.includes('llm') || typeLower.includes('language') || typeLower.includes('text')) {
            return 'textGeneration';
        } else if (typeLower === 'sd' || typeLower === 'stable-diffusion' || typeLower.includes('image') || typeLower.includes('generator') || typeLower.includes('diffusion')) {
            return 'imageGeneration';
        } else {
            return 'generalServices';
        }
    }

    function pushCard(category: string, html: string): void {
        if (category === 'textGeneration') textGenerationCards.push(html);
        else if (category === 'imageGeneration') imageGenerationCards.push(html);
        else generalServicesCards.push(html);
    }

    items.forEach(mod => {
        const name = mod.name || mod.id || 'Module';
        const version = mod.version || '—';
        const desc = mod.description || '';
        const type = mod.type || mod.kind || 'module';
        const status = mod.status || 'available';
        const installed = mod.installed !== false;
        const icon = mod.icon || (type === 'bot' ? '#icon-bot' : type === 'llm' ? '#icon-llm' : type === 'sd' ? '#icon-sd' : '#icon-folder');
        const statusColor = status === 'running' ? 'var(--success)' :
            status === 'installed' ? 'var(--text_secondary)' :
                status === 'recommended' ? 'var(--primary)' :
                    status === 'available' ? 'var(--primary)' :
                        'var(--text-muted)';
        const statusLabel = status === 'recommended'
            ? 'РЕКОМЕНДУЕТСЯ'
            : status.toUpperCase();

        const canRemove = mod.removable !== false;
        const isRecommended = status === 'recommended' || mod.recommended === true;

        const repo = mod.repo || '';
        const hasRepo = !!repo;
        // Для модулей с репозиторием всегда даём возможность "Скачать/Обновить"
        const canInstall = hasRepo;
        const installLabel = installed
            ? t('ui.launcher.web.module_update', 'Обновить')
            : t('ui.launcher.web.module_install', 'Скачать');

        const moduleCategory = getModuleCategory(type);

        const showVersion = version && version !== 'core' && version !== '-' && version !== '—';
        const versionText = showVersion ? `v${version} · ` : '';
        const serviceText = serviceLabel(type);
        const hintText = statusHint(status, installed);

        const statusClass = status === 'running' ? 'status-running' :
            status === 'installed' ? 'status-stopped' :
                'status-stopped';
        const isRunning = status === 'running';

        const cardHtml = `
                    <div class="module-card ${statusClass}" data-module-id="${mod.id}" data-module-type="${type}">
                        <div class="module-card-header">
                            <div class="module-header">
                                <div class="module-header-center">
                                <div class="module-icon">
                                        <svg class="icon" style="width: 20px; height: 20px;"><use href="${icon}"></use></svg>
                                </div>
                                    <div class="module-title">${name}</div>
                                    ${mod.custom ? '<div class="module-user-badge">USER</div>' : ''}
                                </div>
                                ${installed ? `
                                    <div class="module-header-actions">
                                    <button class="module-action-btn module-action-btn-primary"
                                            onclick="event.stopPropagation(); window.openModuleSettings('${mod.id}')"
                                            title="${t('ui.launcher.web.module_settings', 'Настройки')}">
                                        <svg class="icon" style="width: 1rem; height: 1rem;"><use href="#icon-settings"></use></svg>
                                    </button>
                                        <button class="module-start-stop-btn ${isRunning ? 'running' : 'stopped'}"
                                                onclick="event.stopPropagation(); window.toggleModule('${mod.id}')"
                                                title="${isRunning ? 'Остановить' : 'Запустить'}">
                                        </button>
                                    </div>
                                ` : canInstall ? `
                                    <button class="module-install-btn" onclick="event.stopPropagation(); window.installModule('${mod.id}')">
                                        ${installLabel}
                                    </button>
                                ` : ''}
                            </div>
                        </div>
                        <div class="module-card-body">
                        </div>
                    </div>
                `;

        pushCard(moduleCategory, cardHtml);
    });

    const sections = [];

    // Генерация текста
    if (textGenerationCards.length > 0) {
        sections.push(`<div class="modules-category-section">
                <div class="modules-category-header">
                    <div class="modules-category-header-left">
                        <div class="modules-category-icon" style="background: linear-gradient(135deg, rgba(138, 43, 226, 0.2), rgba(75, 0, 130, 0.2));">
                            <svg class="icon" style="width: 24px; height: 24px; color: var(--primary);"><use href="#icon-llm"></use></svg>
                        </div>
                        <div>
                            <h2 class="modules-category-title">Генерация текста</h2>
                        </div>
                    </div>
                    <button class="modules-category-add-btn" onclick="window.addModule('textGeneration')" title="Добавить модуль">
                        <svg class="icon" style="width: 16px; height: 16px;"><use href="#icon-plus"></use></svg>
                        <span class="add-btn-text">Добавить</span>
                    </button>
                </div>
                    <div class="modules-category-grid">${textGenerationCards.join("")}</div>
            </div>`);
    }

    // Генерация изображений
    if (imageGenerationCards.length > 0) {
        sections.push(`<div class="modules-category-section">
                <div class="modules-category-header">
                    <div class="modules-category-header-left">
                        <div class="modules-category-icon" style="background: linear-gradient(135deg, rgba(255, 107, 107, 0.2), rgba(255, 159, 64, 0.2));">
                            <svg class="icon" style="width: 24px; height: 24px; color: #ff6b6b;"><use href="#icon-sd"></use></svg>
                        </div>
                        <div>
                            <h2 class="modules-category-title">Генерация изображений</h2>
                        </div>
                    </div>
                    <button class="modules-category-add-btn" onclick="window.addModule('imageGeneration')" title="Добавить модуль">
                        <svg class="icon" style="width: 16px; height: 16px;"><use href="#icon-plus"></use></svg>
                        <span class="add-btn-text">Добавить</span>
                    </button>
                </div>
                    <div class="modules-category-grid">${imageGenerationCards.join("")}</div>
            </div>`);
    }

    // Общие сервисы
    if (generalServicesCards.length > 0) {
        sections.push(`<div class="modules-category-section">
                <div class="modules-category-header">
                    <div class="modules-category-header-left">
                        <div class="modules-category-icon" style="background: linear-gradient(135deg, rgba(40, 167, 69, 0.2), rgba(25, 135, 84, 0.2));">
                            <svg class="icon" style="width: 24px; height: 24px; color: var(--success);"><use href="#icon-bot"></use></svg>
                        </div>
                        <div>
                            <h2 class="modules-category-title">Общие сервисы</h2>
                        </div>
                    </div>
                    <button class="modules-category-add-btn" onclick="window.addModule('generalServices')" title="Добавить модуль">
                        <svg class="icon" style="width: 16px; height: 16px;"><use href="#icon-plus"></use></svg>
                        <span class="add-btn-text">Добавить</span>
                    </button>
                </div>
                    <div class="modules-category-grid">${generalServicesCards.join("")}</div>
            </div>`);
    }

    // Show empty state if no modules
    if (sections.length === 0) {
        grid.innerHTML = '<div style="color: var(--text-muted); padding: 4rem 2rem; text-align: center; grid-column: 1 / -1;"><div style="font-size: 1.1rem; margin-bottom: 0.5rem;">Нет модулей</div><div style="font-size: 0.9rem; opacity: 0.7;">Начните с добавления модуля</div></div>';
    } else {
        grid.innerHTML = sections.join("");
    }
}

window.addModule = function (category: string) {
    showAddModuleModal(category);
}

function toggleModuleContextMenu(moduleId: string, event: Event) {
    event.stopPropagation();
    const menus = document.querySelectorAll('.module-context-dropdown');
    menus.forEach(menu => {
        if (menu.id !== `context-menu-${moduleId}`) {
            menu.classList.remove('show');
        }
    });
    const menu = document.getElementById(`context-menu-${moduleId}`);
    if (menu) {
        menu.classList.toggle('show');
    }
}

function closeModuleContextMenu(moduleId: string) {
    const menu = document.getElementById(`context-menu-${moduleId}`);
    if (menu) {
        menu.classList.remove('show');
    }
}

document.addEventListener('click', function (e) {
    if (!(e.target as HTMLElement).closest('.module-context-menu')) {
        document.querySelectorAll('.module-context-dropdown').forEach(menu => {
            menu.classList.remove('show');
        });
    }
});

window.toggleModule = async function (moduleId: string) {
    const toggleBtn = (document.querySelector(`[onclick*="toggleModule('${moduleId}')"]`) ||
        document.querySelector(`.module-start-stop-btn[data-module-id="${moduleId}"]`)) as HTMLButtonElement | null;

    if (toggleBtn) {
        setButtonLoading(toggleBtn, true);
    }

    try {
        const res = await invoke<ControlResponse>('control_module', {
            request: { module_id: moduleId, action: 'start' } // 'toggle' in UI usually means start if stopped. But logic here was toggle.
            // Wait, Rust defined control_module taking ControlRequest { module_id, action }.
            // And ModuleAction enum has Install, Uninstall, Start, Stop, Restart, Update.
            // Does it have Toggle? No.
            // The UI 'toggleModule' previously called /api/modules/:id/toggle.
            // I should check if I need to implement 'toggle' logic in frontend or backend.
            // For now, let's assume 'start' or 'stop' based on current state.
            // But wait, the previous UI didn't check state before calling toggle API?
            // It did: `title="${isRunning ? 'Остановить' : 'Запустить'}"`.
            // But `toggleModule` function itself just called POST /toggle.
            // I should probably interpret the toggle logic here.
        });
        // Actually, let's just use 'start' or 'stop' based on button class for now.
        // But the button state is inside the button.
        // Better: let's fetch the current status or pass the desired action.
        // Simplified: The Rust `control` function can handle 'start' or 'stop'.
        // I will implement a `toggle` helper or just check the button state.
        const isRunning = toggleBtn?.classList.contains('running');
        const action = isRunning ? 'stop' : 'start';

         const data = await invoke<ControlResponse>('control_module', {
             request: { module_id: moduleId, action: action }
         });

        showActionFeedback('success');
        await loadModulesTab();
        showToast('Статус модуля обновлен', 'success', 2000, 'Успешно');
    } catch (e: any) {
        showActionFeedback('error');
        showToast('Ошибка: ' + e.message, 'error', 3000, 'Ошибка');
    } finally {
        if (toggleBtn) {
            setButtonLoading(toggleBtn, false);
        }
    }
};

window.viewModuleLogs = function (moduleId: string) {
    showPage('debug');
    const consoleTab = document.querySelector('.debug-tab[onclick*="console"]');
    if (consoleTab) {
        window.setDebugTab('console', consoleTab as HTMLElement);
    }
};

function showAddModuleModal(category: string) {
    showToast('Функция добавления модулей будет доступна в будущем', 'info');
}

window.installModule = async function (id: string) {
    const installBtn = document.querySelector(`[onclick*="installModule('${id}')"]`) as HTMLButtonElement | null;
    if (installBtn) {
        setButtonLoading(installBtn, true);
    }

    try {
        const data = await invoke<ControlResponse>('control_module', {
            request: { module_id: id, action: 'install' }
        });
        if (data && (data.success || data.ok)) {
            showActionFeedback('success');
            showToast(t('ui.launcher.web.module_installed', 'Модуль установлен'), 'success', 2000, 'Успешно');
            loadModulesTab();
        } else {
            showActionFeedback('error');
            showToast(t('ui.launcher.web.module_install_failed', 'Не удалось установить модуль'), 'error', 3000, 'Ошибка');
        }
    } catch (e: any) {
        showActionFeedback('error');
        showToast(t('ui.launcher.web.module_install_failed', 'Не удалось установить модуль') + ': ' + e.message, 'error', 3000, 'Ошибка');
    } finally {
        if (installBtn) {
            setButtonLoading(installBtn, false);
        }
    }
};

window.uninstallModule = async function (id: string) {
    const uninstallBtn = document.querySelector(`[onclick*="uninstallModule('${id}')"]`) as HTMLButtonElement | null;
    if (uninstallBtn) {
        setButtonLoading(uninstallBtn, true);
    }

    try {
         const data = await invoke<ControlResponse>('control_module', {
            request: { module_id: id, action: 'uninstall' }
        });
        if (data && (data.success || data.ok)) {
            showActionFeedback('success');
            showToast(t('ui.launcher.web.module_removed', 'Модуль удалён'), 'success', 2000, 'Успешно');
            loadModulesTab();
        } else {
            showActionFeedback('error');
            showToast(t('ui.launcher.web.module_remove_failed', 'Не удалось удалить модуль'), 'error', 3000, 'Ошибка');
        }
    } catch (e: any) {
        showActionFeedback('error');
        showToast(t('ui.launcher.web.module_remove_failed', 'Не удалось удалить модуль') + ': ' + e.message, 'error', 3000, 'Ошибка');
    } finally {
        if (uninstallBtn) {
            setButtonLoading(uninstallBtn, false);
        }
    }
};

window.openModuleSettings = function (moduleId: string) {
    showModuleSettingsModal(moduleId);
};

currentModuleId = null;

async function showModuleSettingsModal(moduleId: string) {
    currentModuleId = moduleId;
    const modal = document.getElementById('module-settings-modal');
    const loading = document.getElementById('module-settings-loading');
    const formContainer = document.getElementById('module-settings-form-container');
    const errorDiv = document.getElementById('module-settings-error');
    const footer = document.getElementById('module-settings-footer');

    // Reset state
    loading.style.display = 'flex';
    formContainer.style.display = 'none';
    errorDiv.style.display = 'none';
    footer.style.display = 'none';
    errorDiv.textContent = '';

    // Show modal with animation
    modal.style.display = 'flex';
    setTimeout(() => {
        modal.classList.add('show');
    }, 10);

    try {
        // Load module info
        const modulesRes = await fetch('/api/modules');
        const modulesData = await modulesRes.json();
        const modules = modulesData.items || modulesData.available || [];
        const module = modules.find(m => m.id === moduleId);

        if (module) {
            document.getElementById('module-settings-title').textContent = module.name || moduleId;
            document.getElementById('module-settings-desc').textContent = module.description || 'Настройки модуля';

            // Update icon
            const icon = module.icon || (module.type === 'bot' ? '#icon-bot' : module.type === 'llm' ? '#icon-llm' : module.type === 'sd' ? '#icon-sd' : '#icon-folder');
            const iconEl = document.querySelector('#module-settings-icon svg use');
            if (iconEl) {
                iconEl.setAttribute('href', icon);
            }
        }

        // Load settings UI
        const uiRes = await fetch(`/api/modules/${moduleId}/settings_ui`);
        if (uiRes.ok) {
            const settingsHtml = await uiRes.text();
            const container = document.getElementById('module-settings-fields');
            container.innerHTML = settingsHtml;

            // Execute any scripts in the loaded HTML
            const scripts = container.querySelectorAll('script');
            scripts.forEach(oldScript => {
                const newScript = document.createElement('script');
                Array.from(oldScript.attributes).forEach(attr => {
                    newScript.setAttribute(attr.name, attr.value);
                });
                newScript.appendChild(document.createTextNode(oldScript.innerHTML));
                oldScript.parentNode.replaceChild(newScript, oldScript);
            });
        } else {
            // Fallback: generate form from settings data
            const res = await fetch(`/api/modules/${moduleId}/settings`);
            const data = await res.json();

            if (!data.success) {
                throw new Error(data.message || 'Не удалось загрузить настройки');
            }

            generateModuleSettingsForm(data.settings || {});
        }

        // Load settings values
        const res = await fetch(`/api/modules/${moduleId}/settings`);
        const data = await res.json();

        if (data.success && data.settings) {
            populateModuleSettingsForm(data.settings);
        }

        loading.style.display = 'none';
        formContainer.style.display = 'block';
        footer.style.display = 'flex';

        // Animate form appearance
        formContainer.style.opacity = '0';
        formContainer.style.transform = 'translateY(20px)';
        setTimeout(() => {
            formContainer.style.transition = 'opacity 0.4s cubic-bezier(0.4, 0, 0.2, 1), transform 0.4s cubic-bezier(0.4, 0, 0.2, 1)';
            formContainer.style.opacity = '1';
            formContainer.style.transform = 'translateY(0)';
        }, 100);

    } catch (e: any) {
        loading.style.display = 'none';
        errorDiv.style.display = 'block';
        errorDiv.textContent = 'Ошибка загрузки настроек: ' + e.message;
        console.error('Failed to load module settings:', e);
    }
}

function hideModuleSettingsModal() {
    const modal = document.getElementById('module-settings-modal');
    if (!modal) return;

    setTimeout(() => {
        modal.style.display = 'none';
        currentModuleId = null;
    }, 400);
}

// Subscribe to download events
if (window.listenToEvent) {
    window.listenToEvent('download://progress', (event: any) => {
        const payload = event.payload;
        // Payload ID is "module_id.zip", so we strip extension to get module ID
        const moduleId = payload.id.replace('.zip', '');
        updateDownloadUI(moduleId, payload);
    });
}

function updateDownloadUI(moduleId: string, progress: any) {
    const card = document.querySelector(`.module-card[data-module-id="${moduleId}"]`);
    if (!card) return;

    const body = card.querySelector('.module-card-body');
    const headerActions = card.querySelector('.module-header-actions') || card.querySelector('.module-header');

    // Remove old install button if present
    const installBtn = card.querySelector('.module-install-btn') as HTMLElement;
    if (installBtn) installBtn.style.display = 'none';

    // Create or update progress bar container
    let progressContainer = card.querySelector('.download-progress-container') as HTMLElement;
    if (!progressContainer) {
        progressContainer = document.createElement('div');
        progressContainer.className = 'download-progress-container';
        progressContainer.style.cssText = 'padding: 10px; background: rgba(0,0,0,0.2); border-radius: 8px; margin-top: 10px;';
        // Insert into body or append to header if body is empty/hidden
        if (body) body.appendChild(progressContainer);
        else card.appendChild(progressContainer);
    }

    // Update content
    const percent = progress.progress_percent.toFixed(1);
    const speed = (progress.speed_bytes_per_sec / 1024 / 1024).toFixed(2); // MB/s

    if (progress.status === 'Downloading') {
        progressContainer.innerHTML = `
            <div style="display: flex; justify-content: space-between; margin-bottom: 5px; font-size: 0.8rem; color: var(--text-muted);">
                <span>Downloading...</span>
                <span>${percent}% (${speed} MB/s)</span>
            </div>
            <div style="width: 100%; height: 6px; background: rgba(255,255,255,0.1); border-radius: 3px; overflow: hidden;">
                <div style="width: ${percent}%; height: 100%; background: var(--primary); transition: width 0.2s;"></div>
            </div>
        `;
    } else if (progress.status === 'Completed') {
        progressContainer.innerHTML = `
            <div style="color: var(--success); font-size: 0.9rem; text-align: center; padding: 5px;">
                ✓ Installed
            </div>
        `;
        // Refresh modules to show "Open/Start" buttons after short delay
        setTimeout(() => {
            progressContainer.remove();
            if (window.loadModulesTab) window.loadModulesTab();
        }, 1500);
    } else if (progress.status === 'Failed') {
        progressContainer.innerHTML = `
            <div style="color: var(--danger); font-size: 0.9rem; text-align: center; padding: 5px;">
                ⚠ Download Failed
            </div>
        `;
        if (installBtn) installBtn.style.display = 'block';
    }
}
