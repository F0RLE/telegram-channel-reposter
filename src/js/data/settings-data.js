// Settings Data JS

// Close dropdown when clicking outside
document.addEventListener('click', (e) => {
    document.querySelectorAll('.lang-dropdown-menu').forEach(dropdown => {
        const page = dropdown.id.replace('lang-dropdown-menu-', '');
        const btn = document.getElementById(`lang-dropdown-btn-${page}`);
        if (dropdown && btn && !dropdown.contains(e.target) && !btn.contains(e.target)) {
            dropdown.classList.remove('show');
        }
    });
});

window.control = async function (action, service) {
    try {
        const serviceName = service === 'all' ? t('ui.launcher.web.all_services', 'все сервисы') :
            service === 'bot' ? t('ui.launcher.service.telegram_bot', 'Telegram Bot') :
                service === 'llm' ? t('ui.launcher.service.llm_server', 'Ollama') :
                    service === 'sd' ? t('ui.launcher.service.stable_diffusion', 'Stable Diffusion') : service;

        // Handle restart action (stop then start)
        if (action === 'restart') {
            const actionText = t('ui.launcher.button.restart', 'Перезапуск');
            showToast(`${actionText} ${serviceName}...`, 'success', 2000);

            // First stop
            const stopRes = await fetch('/api/control', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'stop', service })
            });

            if (stopRes.ok) {
                // Wait a bit, then start
                setTimeout(async () => {
                    const startRes = await fetch('/api/control', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ action: 'start', service })
                    });

                    if (startRes.ok) {
                        setTimeout(updateState, 300);
                        setTimeout(updateState, 1000);
                        setTimeout(updateState, 2000);
                        showToast(`${serviceName} ${t('ui.launcher.web.restarted', 'перезапущен')}`, 'success', 2000);
                    } else {
                        showToast(`${t('ui.launcher.web.failed', 'Ошибка')}: ${actionText} ${serviceName}`, 'error');
                    }
                }, 1500);
            } else {
                showToast(`${t('ui.launcher.web.failed', 'Ошибка')}: ${actionText} ${serviceName}`, 'error');
            }
            return;
        }

        const actionText = action === 'start' ? t('ui.launcher.button.start', 'Запуск') :
            action === 'stop' ? t('ui.launcher.button.stop', 'Остановка') : action;

        showToast(`${actionText} ${serviceName}...`, 'success', 1500);

        const res = await fetch('/api/control', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action, service })
        });
        // #region agent log
        agentLog('H1', 'index.html:control', 'fetch_control', {
            action,
            service,
            status: res.status,
            ok: res.ok,
            serverPid: res.headers.get('X-Launcher-PID'),
            serverRun: res.headers.get('X-Launcher-Run')
        });
        // #endregion

        if (res.ok) {
            // Update state multiple times to catch status changes
            setTimeout(updateState, 300);
            setTimeout(updateState, 1000);
            setTimeout(updateState, 2000);
        } else {
            const errorText = await res.text();
            console.error("Control failed:", errorText);
            showToast(`${t('ui.launcher.web.failed', 'Ошибка')}: ${actionText} ${serviceName}`, 'error');
        }
    } catch (e) {
        console.error("Control failed:", e);
        showToast(`${t('ui.launcher.web.error', 'Ошибка')}: ${e.message}`, 'error');
    }
};

// Helper function to remove quotes from strings
function removeQuotes(str) {
    if (typeof str !== 'string') return str || '';
    let result = str;
    // Replace escaped quotes in the middle
    result = result.replace(/\\'/g, "'");
    result = result.replace(/\\"/g, '"');
    // Remove quotes from start/end (multiple passes for nested quotes)
    while (result.match(/^\\?['"]|\\?['"]$/)) {
        result = result.replace(/^\\?['"]+|\\?['"]+$/g, '');
    }
    return result;
}

async function loadSettings() {
    try {
        const res = await fetch('/api/settings');
        const data = await res.json();

        // Check modules installation state to enable/disable settings sections
        try {
            const modsPayload = await window.fetchModulesCached();
            if (modsPayload) {
                const items = modsPayload.items || modsPayload.modules || [];
                const llmMod = items.find(m => m.id === 'llm');
                const sdMod = items.find(m => m.id === 'sd');
                const llmInstalled = !llmMod || llmMod.installed !== false;
                const sdInstalled = !sdMod || sdMod.installed !== false;

                const llmOverlay = document.getElementById('llm-settings-disabled-overlay');
                const sdOverlay = document.getElementById('sd-settings-disabled-overlay');
                if (llmOverlay) llmOverlay.style.display = llmInstalled ? 'none' : 'flex';
                if (sdOverlay) sdOverlay.style.display = sdInstalled ? 'none' : 'flex';
            }
        } catch (e) {
            console.warn('[Settings] modules fetch failed', e);
        }

        // Helper to safely call optional functions
        const safeCall = (fnName) => {
            console.log('[Settings] safeCall:', fnName, typeof window[fnName]);
            if (typeof window[fnName] === 'function') window[fnName]();
        };

        // Initialize UI components
        safeCall('loadGpuInfo');
        safeCall('initTaskbarToggles');
        safeCall('initMonitorToggles');
        safeCall('loadCardWidths'); // Ensure correct card sizing

        // General

        // General
        document.getElementById('field-gpu').checked = data.USE_GPU !== 'false';
        // Default DEBUG_MODE to true if not set (if element exists)
        const debugField = document.getElementById('field-debug');
        if (debugField) {
            debugField.checked = data.DEBUG_MODE === 'true' || data.DEBUG_MODE === undefined || data.DEBUG_MODE === '';
        }

        // LLM - with default prompts if not set
        const defaultSysPrompt = "Ты — талантливый редактор Telegram-канала. Твоя задача — переписать текст, сделав его живым, конкретным и цепляющим. Избегай воды и вводных слов.\nФОРМАТ ОТВЕТА СТРОГО:\nКликбейтный Заголовок ||| Основной текст поста";
        const defaultUserPrompt = "Перепиши этот текст:\n\n{text}";
        const defaultCliches = "а вы знали, не может быть, ого, да ну, и такие виды";
        const defaultSdPositive = "score_9, score_8_up, score_7_up, ";
        const defaultSdNegative = "score_6, score_5, score_4, (worst quality:1.2), (low quality:1.2), (normal quality:1.2), lowres, bad anatomy, bad hands, signature, watermarks, ugly, imperfect eyes, skewed eyes, unnatural face, unnatural body, error, extra limb, missing limbs, text, username, artist name";

        // LLM fields - may not exist if not on module settings modal
        const llmSys = document.getElementById('field-llm-sys');
        const llmUser = document.getElementById('field-llm-user');
        const llmPositive = document.getElementById('field-llm-positive');
        const llmNegative = document.getElementById('field-llm-negative');
        const llmCliches = document.getElementById('field-llm-cliches');
        const llmTemp = document.getElementById('field-llm-temp');
        const valLlmTemp = document.getElementById('val-llm-temp');
        const llmCtx = document.getElementById('field-llm-ctx');
        const valLlmCtx = document.getElementById('val-llm-ctx');

        if (llmSys) llmSys.value = removeQuotes(data.llm_rewrite_system_prompt) || defaultSysPrompt;
        if (llmUser) llmUser.value = removeQuotes(data.llm_rewrite_user_prompt) || defaultUserPrompt;
        if (llmPositive) llmPositive.value = removeQuotes(data.llm_positive_prompt) || defaultSdPositive;
        if (llmNegative) llmNegative.value = removeQuotes(data.llm_negative_prompt) || defaultSdNegative;
        if (llmCliches) llmCliches.value = removeQuotes(data.llm_rewrite_cliches) || defaultCliches;
        if (llmTemp) llmTemp.value = data.llm_temp || 0.7;
        if (valLlmTemp) valLlmTemp.innerText = parseFloat(data.llm_temp || 0.7).toFixed(1);
        const ctxValue = data.llm_ctx || 4096;
        if (llmCtx) llmCtx.value = ctxValue;
        if (valLlmCtx) valLlmCtx.innerText = ctxValue.toString().replace(/'/g, '');
        if (typeof updateTokenCount === 'function') updateTokenCount();
        if (typeof updateRangeProgress === 'function' && llmTemp) updateRangeProgress('field-llm-temp');
        if (typeof updateRangeProgress === 'function' && llmCtx) updateRangeProgress('field-llm-ctx');
        if (data.MODELS_LLM_DIR) {
            document.getElementById('field-models-dir').value = removeQuotes(data.MODELS_LLM_DIR);
        } else {
            // Try to get from config
            try {
                const configRes = await fetch('/api/config');
                const config = await configRes.json();
                if (config.MODELS_LLM_DIR) {
                    document.getElementById('field-models-dir').value = removeQuotes(config.MODELS_LLM_DIR);
                }
            } catch (e) { }
        }

        // SD
        document.getElementById('field-sd-args').value = removeQuotes(data.SD_ARGS);
        document.getElementById('field-sd-model-url').value = removeQuotes(data.SD_MODEL_URL);
        if (data.MODELS_SD_DIR) {
            const sdModelsDirField = document.getElementById('field-sd-models-dir');
            if (sdModelsDirField) {
                sdModelsDirField.value = removeQuotes(data.MODELS_SD_DIR);
            }
        } else {
            // Try to get from config or use default
            try {
                const configRes = await fetch('/api/config');
                const config = await configRes.json();
                const sdModelsDirField = document.getElementById('field-sd-models-dir');
                if (sdModelsDirField) {
                    if (config.MODELS_SD_DIR) {
                        sdModelsDirField.value = removeQuotes(config.MODELS_SD_DIR);
                    } else {
                        // Set default path: SD_DIR/models/Stable-diffusion
                        // This is the standard location for SD models
                        const defaultPath = config.SD_DIR ?
                            config.SD_DIR.replace(/\\/g, '/') + '/models/Stable-diffusion' :
                            '';
                        if (defaultPath) {
                            sdModelsDirField.value = defaultPath;
                        }
                    }
                }
            } catch (e) { }
        }
        if (data.sd_steps) {
            document.getElementById('field-sd-steps').value = data.sd_steps;
            document.getElementById('val-sd-steps').innerText = data.sd_steps;
            updateRangeProgress('field-sd-steps');
        }
        if (data.sd_cfg) {
            document.getElementById('field-sd-cfg').value = data.sd_cfg;
            document.getElementById('val-sd-cfg').innerText = parseFloat(data.sd_cfg).toFixed(1);
            updateRangeProgress('field-sd-cfg');
        }
        if (data.sd_width) document.getElementById('field-sd-w').value = data.sd_width;
        if (data.sd_height) document.getElementById('field-sd-h').value = data.sd_height;
        if (data.sd_sampler) document.getElementById('field-sd-sampler').value = data.sd_sampler;
        if (data.sd_seed) document.getElementById('field-sd-seed').value = data.sd_seed;
        document.getElementById('field-sd-positive').value = removeQuotes(data.sd_positive_prefix);
        document.getElementById('field-sd-negative').value = removeQuotes(data.sd_negative_prompt);

        // ADetailer
        document.getElementById('field-ad-enabled').checked = data.ad_enabled;
        if (data.ad_steps) {
            document.getElementById('field-ad-steps').value = data.ad_steps;
            document.getElementById('val-ad-steps').innerText = data.ad_steps;
        }
        document.getElementById('field-ad-face').checked = data.ad_face;
        document.getElementById('field-ad-hand').checked = data.ad_hand;
        document.getElementById('field-ad-person').checked = data.ad_person;
        document.getElementById('field-ad-clothing').checked = data.ad_clothing;
        if (data.ad_face_conf) {
            document.getElementById('field-ad-face-conf').value = data.ad_face_conf;
            document.getElementById('val-ad-face-conf').innerText = parseFloat(data.ad_face_conf).toFixed(2);
        }
        if (data.ad_hand_conf) {
            document.getElementById('field-ad-hand-conf').value = data.ad_hand_conf;
            document.getElementById('val-ad-hand-conf').innerText = parseFloat(data.ad_hand_conf).toFixed(2);
        }
        if (data.ad_person_conf) {
            document.getElementById('field-ad-person-conf').value = data.ad_person_conf;
            document.getElementById('val-ad-person-conf').innerText = parseFloat(data.ad_person_conf).toFixed(2);
        }
        if (data.ad_clothing_conf) {
            document.getElementById('field-ad-clothing-conf').value = data.ad_clothing_conf;
            document.getElementById('val-ad-clothing-conf').innerText = parseFloat(data.ad_clothing_conf).toFixed(2);
        }
        toggleAdZones();
        // Update range progress for all ADetailer sliders after loading
        setTimeout(() => updateRangeProgress(), 100);
    } catch (e) { console.error(e); }
}

async function loadSdModels() {
    try {
        const res = await fetch('/api/sd_models');
        const models = await res.json();
        const container = document.getElementById('sd-models-list');
        if (!container) return;

        const settingsRes = await fetch('/api/settings');
        const settings = await settingsRes.json();
        const selectedModel = (settings?.SD_CHECKPOINT || '').trim();

        if (models.length === 0) {
            container.innerHTML = `<div style="color: var(--text-muted); font-size: 0.85rem; padding: 1rem; text-align: center;">${t('ui.launcher.web.no_sd_models', 'No SD models found. Download models to use them.')}</div>`;
        } else {
            container.innerHTML = '<div style="display: grid; gap: 0.5rem;">';
            models.forEach(model => {
                const isSelected = selectedModel && selectedModel === model;
                container.innerHTML += `
                            <div style="background: var(--bg-light); padding: 0.75rem; border-radius: 6px; display: flex; justify-content: space-between; align-items: center; gap: 0.5rem;">
                                <div style="flex: 1;">
                                    <div style="font-weight: 500;">${model}</div>
                                </div>
                                <div style="display: flex; gap: 0.5rem; align-items: center;">
                                    ${isSelected
                        ? `<span style="color: var(--success); font-weight: 600; font-size: 0.85rem; display: inline-flex; align-items: center; gap: 0.3rem; padding: 0.4rem 0.8rem; background: rgba(40, 167, 69, 0.15); border-radius: 6px;">✔ ${t('ui.launcher.web.selected', 'Выбрана')}</span>`
                        : `<button class="btn" style="background: var(--primary); color: white; padding: 0.5rem 1rem; font-size: 0.85rem;" onclick="selectSdModel('${model}')">${t('ui.launcher.button.select', 'Выбрать')}</button>`
                    }
                                    <button class="btn" style="background: var(--danger, #dc3545); color: white; padding: 0.5rem 0.75rem; font-size: 0.85rem; min-width: auto;" onclick="deleteSdModel('${model}')" title="${t('ui.launcher.button.delete_model', 'Удалить модель')}">🗑️</button>
                                </div>
                            </div>
                        `;
            });
            container.innerHTML += '</div>';
        }
    } catch (e) {
        console.error("Failed to load SD models", e);
        const container = document.getElementById('sd-models-list');
        if (container) {
            container.innerHTML = `<div style="color: var(--text-muted); font-size: 0.85rem; padding: 1rem; text-align: center;">${t('ui.launcher.web.sd_models_error', 'Ошибка загрузки моделей')}</div>`;
        }
    }
}

window.selectSdModel = async function (name) {
    try {
        await saveSetting('SD_CHECKPOINT', name, false, false);
        showToast(t('ui.launcher.settings.model_selected', 'Модель выбрана'), 'success');
        loadSdModels();
    } catch (e) {
        console.error("Failed to select model:", e);
        showToast(t('ui.launcher.settings.model_select_failed', 'Ошибка выбора модели'), 'error');
    }
}

window.deleteSdModel = async function (name) {
    const confirmMsg = t('ui.launcher.web.delete_model_confirm', `Вы уверены, что хотите удалить модель "${name}"?`).replace('{model}', name);
    if (!confirm(confirmMsg)) {
        return;
    }
    try {
        const res = await fetch('/api/delete_sd_model', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model: name })
        });
        const data = await res.json();
        if (data.error) {
            showToast(t('ui.launcher.web.delete_model_error', 'Ошибка удаления модели') + ': ' + data.error, 'error');
        } else {
            showToast(t('ui.launcher.web.delete_model_success', 'Модель удалена'), 'success');
            // If deleted model was selected, reset to "auto detect"
            const settingsRes = await fetch('/api/settings');
            const settings = await settingsRes.json();
            if (settings.SD_CHECKPOINT === name) {
                await saveSetting('SD_CHECKPOINT', 'auto detect', false, false);
            }
            loadSdModels();
        }
    } catch (e) {
        console.error("Failed to delete model:", e);
        showToast(t('ui.launcher.web.delete_model_error', 'Ошибка удаления модели'), 'error');
    }
}

async function loadLlmModels() {
    try {
        // Get current selected model from settings
        const settingsRes = await fetch('/api/settings');
        const settingsData = await settingsRes.json();
        const selectedModel = (settingsData?.LLM_MODEL || '').trim();

        const res = await fetch('/api/llm_models');
        const models = await res.json();
        const container = document.getElementById('llm-models-list');
        if (models.length === 0) {
            container.innerHTML = `<div style="color: var(--text-muted); font-size: 0.85rem; padding: 1rem; text-align: center;">${t('ui.launcher.web.no_llm_models', 'No LLM models found. Install models through Ollama.')}</div>`;
        } else {
            container.innerHTML = '<div style="display: grid; gap: 0.5rem;">';
            models.forEach(model => {
                const isSelected = selectedModel && selectedModel === model.name;
                container.innerHTML += `
                            <div style="background: var(--bg-light); padding: 0.75rem; border-radius: 6px; display: flex; justify-content: space-between; align-items: center;">
                                <div style="flex: 1;">
                                    <div style="font-weight: 500;">${model.name}</div>
                                    <div style="font-size: 0.75rem; color: var(--text-muted);">${model.type}</div>
                                </div>
                                ${isSelected
                        ? `<span style="color: var(--success); font-weight: 600; font-size: 0.85rem; display: inline-flex; align-items: center; gap: 0.3rem; padding: 0.4rem 0.8rem; background: rgba(40, 167, 69, 0.15); border-radius: 6px;">✔ ${t('ui.launcher.web.selected', 'Выбрана')}</span>`
                        : `<button class="btn" style="background: var(--primary); color: white; padding: 0.5rem 1rem; font-size: 0.85rem;" onclick="selectLlmModel('${model.name}', '${model.type}')">${t('ui.launcher.button.select', 'Выбрать')}</button>`
                    }
                            </div>
                        `;
            });
            container.innerHTML += '</div>';
        }
    } catch (e) {
        console.error("Failed to load LLM models", e);
        document.getElementById('llm-models-list').innerHTML = `<div style="color: var(--danger); font-size: 0.85rem; padding: 1rem;">${t('ui.launcher.web.failed_load_llm_models', 'Failed to load LLM models')}</div>`;
    }
}

window.selectLlmModel = async function (name, type) {
    try {
        // Launcher uses LLM_MODEL, Bot uses SELECTED_LLM_MODEL (format: type:name)
        await saveSetting('LLM_MODEL', name, false, false);
        const tpe = (type || 'ollama').toString().trim() || 'ollama';
        await saveSetting('SELECTED_LLM_MODEL', `${tpe}:${name}`, false, false);
        showToast(t('ui.launcher.settings.model_selected', 'Модель выбрана') + `: ${name}`, 'success', 2000);
        // Reload models to update UI
        loadLlmModels();
    } catch (e) {
        console.error("Failed to select model:", e);
        showToast(t('ui.launcher.settings.model_select_failed', 'Ошибка выбора модели'), 'error');
    }
}

window.saveLlmPrompts = async function (showNotification = true) {
    try {
        const prompts = {
            llm_rewrite_system_prompt: { value: document.getElementById('field-llm-sys')?.value || '', fieldId: 'llm-sys' },
            llm_rewrite_user_prompt: { value: document.getElementById('field-llm-user')?.value || '', fieldId: 'llm-user' },
            llm_positive_prompt: { value: document.getElementById('field-llm-positive')?.value || '', fieldId: 'llm-positive' },
            llm_negative_prompt: { value: document.getElementById('field-llm-negative')?.value || '', fieldId: 'llm-negative' },
            llm_rewrite_cliches: { value: document.getElementById('field-llm-cliches')?.value || '', fieldId: 'llm-cliches' }
        };

        for (const [key, config] of Object.entries(prompts)) {
            await saveSetting(key, config.value, true, false, config.fieldId);
        }

        if (showNotification) {
            showToast(t('ui.launcher.settings.llm_prompts_saved', 'Промпты LLM сохранены'), 'success');
        }
    } catch (e) {
        console.error("Failed to save LLM prompts:", e);
        if (showNotification) {
            showToast(t('ui.launcher.settings.save_failed', 'Ошибка сохранения') + ': ' + e.message, 'error');
        }
    }
}

window.saveSdPrompts = async function (showNotification = true) {
    try {
        const prompts = {
            sd_positive_prefix: { value: document.getElementById('field-sd-positive')?.value || '', fieldId: 'sd-positive' },
            sd_negative_prompt: { value: document.getElementById('field-sd-negative')?.value || '', fieldId: 'sd-negative' }
        };

        for (const [key, config] of Object.entries(prompts)) {
            await saveSetting(key, config.value, true, false, config.fieldId);
        }

        if (showNotification) {
            showToast(t('ui.launcher.settings.sd_prompts_saved', 'Промпты SD сохранены'), 'success');
        }
    } catch (e) {
        console.error("Failed to save SD prompts:", e);
        if (showNotification) {
            showToast(t('ui.launcher.settings.save_failed', 'Ошибка сохранения'), 'error');
        }
    }
}

// Track unsaved changes and auto-save
let unsavedChanges = {};
let saveTimeout = null;
let autoSaveTimeout = null;

// Save indicator element
let saveIndicator = null;
function getSaveIndicator() {
    if (!saveIndicator) {
        saveIndicator = document.createElement('div');
        saveIndicator.id = 'save-indicator';
        saveIndicator.innerHTML = '💾';
        document.body.appendChild(saveIndicator);
    }
    return saveIndicator;
}

function showSaveIndicator() {
    const indicator = getSaveIndicator();
    indicator.classList.add('saving');
    setTimeout(() => {
        indicator.classList.remove('saving');
    }, 2000);
}

function markUnsaved(fieldId) {
    unsavedChanges[fieldId] = true;

    // Auto-save after 500ms delay (debounce)
    if (autoSaveTimeout) clearTimeout(autoSaveTimeout);
    autoSaveTimeout = setTimeout(() => {
        autoSaveField(fieldId);
    }, 500);
}

async function autoSaveField(fieldId) {
    const allFields = {
        'lang': { key: 'LANGUAGE', isJson: false },
        'gpu': { key: 'USE_GPU', isJson: false, isBool: true },
        'bot-lang': { key: 'BOT_LANGUAGE', isJson: false },
        'debug': { key: 'DEBUG_MODE', isJson: false, isBool: true },
        'models-dir': { key: 'MODELS_LLM_DIR', isJson: false },
        'sd-models-dir': { key: 'MODELS_SD_DIR', isJson: false },
        'sd-model-url': { key: 'SD_MODEL_URL', isJson: false },
        'sd-args': { key: 'SD_ARGS', isJson: false }
    };

    const config = allFields[fieldId];
    if (!config) return;

    const el = document.getElementById('field-' + fieldId);
    if (!el) return;

    try {
        let value = config.isBool ? (el.checked ? 'true' : 'false') : el.value;
        await saveSetting(config.key, value, config.isJson, false, fieldId);
        delete unsavedChanges[fieldId];
        showSaveIndicator();
    } catch (e) {
        console.error('Auto-save failed:', e);
    }
}

// Also auto-save prompts when they change
const originalSaveLlmPrompts = window.saveLlmPrompts;
window.saveLlmPrompts = async function (showNotification = false) {
    await originalSaveLlmPrompts(showNotification);
    showSaveIndicator();
};

const originalSaveSdPrompts = window.saveSdPrompts;
window.saveSdPrompts = async function (showNotification = false) {
    await originalSaveSdPrompts(showNotification);
    showSaveIndicator();
};

function clearUnsaved(fieldId) {
    if (fieldId) {
        delete unsavedChanges[fieldId];
    } else {
        unsavedChanges = {};
    }
}

window.saveAllChanges = async function () {
    // Save all prompts
    await saveLlmPrompts(false);
    await saveSdPrompts(false);

    // Save all other settings with unsaved changes
    const allFields = {
        // Bot settings (token, channel) moved to module settings
        'lang': { key: 'LANGUAGE', isJson: false },
        'gpu': { key: 'USE_GPU', isJson: false, isBool: true },
        'bot-lang': { key: 'BOT_LANGUAGE', isJson: false },
        'debug': { key: 'DEBUG_MODE', isJson: false, isBool: true },
        'models-dir': { key: 'MODELS_LLM_DIR', isJson: false },
        'sd-models-dir': { key: 'MODELS_SD_DIR', isJson: false },
        'sd-model-url': { key: 'SD_MODEL_URL', isJson: false },
        'sd-args': { key: 'SD_ARGS', isJson: false }
    };

    for (const [fieldId, config] of Object.entries(allFields)) {
        if (unsavedChanges[fieldId]) {
            const el = document.getElementById('field-' + fieldId);
            if (el) {
                let value = config.isBool ? (el.checked ? 'true' : 'false') : el.value;
                await saveSetting(config.key, value, config.isJson, false);
                clearUnsaved(fieldId);
            }
        }
    }

    updateSaveButton();
    showToast(t('ui.launcher.settings.saved', 'Все настройки сохранены'), 'success');
}


async function saveAllChanges() {
    const fields = {
        'token': { key: 'BOT_TOKEN', id: 'field-token', isJson: false },
        'channel': { key: 'TARGET_CHANNEL_ID', id: 'field-channel', isJson: false },
        'gpu': { key: 'USE_GPU', id: 'field-gpu', isJson: false, isCheckbox: true },
        'debug': { key: 'DEBUG_MODE', id: 'field-debug', isJson: false, isCheckbox: true },
        'models-dir': { key: 'MODELS_LLM_DIR', id: 'field-models-dir', isJson: false },
        'sd-models-dir': { key: 'MODELS_SD_DIR', id: 'field-sd-models-dir', isJson: false },
        'sd-model-url': { key: 'SD_MODEL_URL', id: 'field-sd-model-url', isJson: false },
        'sd-args': { key: 'SD_ARGS', id: 'field-sd-args', isJson: false }
    };

    const btn = document.getElementById('save-all-btn');
    if (!btn) return;
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<svg class="icon"><use href="#icon-save"></use></svg> <span>' + t('ui.launcher.settings.saving', 'Сохранение...') + '</span>';

    // Save prompts first
    await saveLlmPrompts(false);
    await saveSdPrompts(false);

    let saved = 0;
    let failed = 0;

    for (const fieldId of unsavedChanges) {
        const field = fields[fieldId];
        if (!field) continue;

        const el = document.getElementById(field.id);
        if (!el) continue;

        let value = field.isCheckbox ? (el.checked ? 'true' : 'false') : el.value;
        if (field.key === 'BOT_LANGUAGE' && value === 'launcher') value = '';

        try {
            await saveSetting(field.key, value, field.isJson, false);
            clearUnsaved(fieldId);
            saved++;
        } catch (e) {
            failed++;
        }
    }

    btn.disabled = false;
    btn.innerHTML = originalText;

    if (saved > 0 && failed === 0) {
        showToast(t('ui.launcher.settings.saved', 'Все настройки сохранены'), 'success');
    } else if (failed > 0) {
        showToast(t('ui.launcher.settings.save_partial', 'Сохранено {saved}, ошибок: {failed}', { saved, failed }), 'error');
    }
}

async function saveSetting(key, value, isJson = false, showNotification = false, fieldId = null) {
    if (typeof value === 'number') value = parseFloat(value);
    // Debounce rapid saves
    if (saveTimeout) clearTimeout(saveTimeout);
    return new Promise((resolve, reject) => {
        saveTimeout = setTimeout(async () => {
            try {
                const res = await fetch('/api/settings', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ key, value, isJson }) });
                if (res.ok) {
                    if (fieldId) clearUnsaved(fieldId);
                    resolve();
                } else {
                    const errorText = await res.text();
                    reject(new Error('Save failed: ' + errorText));
                }
            } catch (e) {
                reject(e);
            }
        }, 100);
    });
}

// Load GPU info
async function loadGpuInfo() {
    console.log('[Settings] loadGpuInfo called');
    try {
        const res = await fetch('/api/gpu_info');
        console.log('[Settings] GPU info response:', res.status);
        const data = await res.json();
        console.log('[Settings] GPU info data:', data);
        const gpuInfoEl = document.getElementById('gpu-info');
        if (!gpuInfoEl) {
            console.error('[Settings] gpu-info element not found');
            return;
        }

        if (data.detected) {
            gpuInfoEl.className = 'gpu-info detected';
            gpuInfoEl.innerHTML = `
                        <div style="font-weight: 600; margin-bottom: 0.25rem;">${data.name}</div>
                        <div class="gpu-info-details">${data.cuda ? 'CUDA • ' : ''}${data.memory ? data.memory + ' GB' : ''}</div>
                    `;
        } else {
            gpuInfoEl.className = 'gpu-info not-detected';
            gpuInfoEl.innerHTML = `<div>${t('ui.launcher.web.gpu_not_found', 'GPU not found')}</div><div class="gpu-info-details">${t('ui.launcher.web.gpu_fallback_cpu', 'CPU will be used (slower)')}</div>`;
        }
    } catch (e) {
        const gpuInfoEl = document.getElementById('gpu-info');
        gpuInfoEl.className = 'gpu-info not-detected';
        gpuInfoEl.innerHTML = `<div>${t('ui.launcher.web.gpu_detect_failed', 'Failed to detect GPU')}</div>`;
    }
}
window.loadGpuInfo = loadGpuInfo;