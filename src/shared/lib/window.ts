// Window control functions for Tauri desktop application

declare function showToast(message: string, type: string, duration?: number): void;
declare function t(key: string, fallback?: string): string;
declare function loadTranslations(lang: string): Promise<void>;
declare function applyTranslations(): void;
declare function initEmojiFlags(): void;
declare function updateLangButtons(): void;
declare function updateState(): Promise<void>;
declare function loadSettings(): void;
declare function control(action: string, service: string): Promise<void>;
declare function getSystemLanguage(): Promise<string>;
declare function hideCloseConfirmModal(): void;
declare function confirmClose(): void;
declare function hideLlmStartModal(): void;
declare function hideReinstallSdModal(): void;
declare function hideSdInstallModal(): void;
declare function showSdReinstallProgress(): void;
declare function hideSdReinstallProgress(): void;
declare function updateMaximizeIcon(isMaximized: boolean): void;
declare let langModalShown: boolean;

let isClosing: boolean = false;
window.minimizeWindow = async function (): Promise<void> {
    if (window.__TAURI__) {
        try {
            await window.__TAURI__.core.invoke('minimize_window');
        } catch (e) {
            console.error("Failed to minimize:", e);
        }
    } else if (window.electronAPI && window.electronAPI.minimize) {
        window.electronAPI.minimize();
    } else {
        console.log('Minimize window (Mock)');
    }
};

window.toggleMaximizeWindow = async function (): Promise<void> {
    if (window.__TAURI__) {
        try {
            // Let backend handle the toggle state
            await window.__TAURI__.core.invoke('maximize_window');
            // We can rely on resize event to update icon, or manually check after short delay
        } catch (e) {
            console.error("Failed to toggle maximize:", e);
        }
    } else if (window.electronAPI && window.electronAPI.toggleMaximize) {
        window.electronAPI.toggleMaximize();
    } else {
        console.log('Toggle maximize window (Mock)');
    }
};

// Update maximize icon based on window state (global function for Electron)
window.updateMaximizeIcon = function (isMaximized: boolean): void {
    const maximizeIcon = document.getElementById('maximize-icon');
    if (!maximizeIcon) return;

    if (isMaximized) {
        // Show restore icon (two overlapping squares)
        maximizeIcon.innerHTML = '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"/>';
    } else {
        // Show maximize icon (expand)
        maximizeIcon.innerHTML = '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8h4V4m12 4h-4V4m4 12h-4v4M4 16h4v4"/>';
    }
};

window.showCloseConfirmModal = function (): void {
    const modal = document.getElementById('close-confirm-modal');
    if (!modal) return;

    // Add blur and show modal
    document.body.classList.add('launcher-blur');
    modal.classList.add('show');

    // Simple click outside to close
    modal.onclick = function (e) {
        if (e.target === modal) {
            hideCloseConfirmModal();
        }
    };
};

window.hideCloseConfirmModal = function (): void {
    const modal = document.getElementById('close-confirm-modal');
    if (!modal) return;
    document.body.classList.remove('launcher-blur');
    modal.classList.remove('show');
};


window.confirmCloseFromModal = function (): void {
    try { hideCloseConfirmModal(); } catch (e) { }
    // Proceed with actual shutdown flow
    confirmClose();
};

window.confirmClose = async function (): Promise<void> {
    isClosing = true;

    // Use backend command to close (exit(0))
    if (window.__TAURI__) {
        try {
            await window.__TAURI__.core.invoke('close_window');
        } catch (e) {
            console.error("Failed to invoke close_window:", e);
        }
    } else {
        // Mock / Web fallback
        try {
            window.close();
            setTimeout(() => { if (!document.hidden) window.location.href = 'about:blank'; }, 100);
        } catch (e) { window.location.href = 'about:blank'; }
    }
};

window.changeLanguage = async function (lang: string): Promise<void> {
    window.currentLang = lang;
    // Save to localStorage immediately
    localStorage.setItem('web_launcher_language', lang);

    // Load and apply translations immediately
    await loadTranslations(lang);
    // Force re-apply translations
    applyTranslations();
    // Restore emoji flags after translations
    initEmojiFlags();
    updateLangButtons();
    // Update dynamic content
    updateState().then(() => {
        // Ensure emojis are restored after state update
        initEmojiFlags();
        updateLangButtons();
    });

    // Sync LANGUAGE (launcher language) and clear BOT_LANGUAGE so bot uses launcher language
    // Sync LANGUAGE (launcher language) and clear BOT_LANGUAGE so bot uses launcher language
    if (window.__TAURI__) {
        try {
            await window.__TAURI__.core.invoke('save_setting', { key: 'LANGUAGE', value: lang });
            await window.__TAURI__.core.invoke('save_setting', { key: 'BOT_LANGUAGE', value: '' });
        } catch (e) { console.error("Native settings sync failed", e); }
    } else {
        try {
            await fetch('/api/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ key: 'LANGUAGE', value: lang })
            });
            // Clear BOT_LANGUAGE so bot uses LANGUAGE (launcher language)
            await fetch('/api/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ key: 'BOT_LANGUAGE', value: '' })
            });
        } catch (e) {
            console.error("Failed to sync LANGUAGE:", e);
        }
    }

    showToast(t('ui.launcher.web.language_changed', 'Language changed'), 'success');
};

window.selectLangInModal = function (lang: string): void {
    document.querySelectorAll('.lang-option').forEach(opt => opt.classList.remove('selected'));
    const option = document.querySelector(`.lang-option[data-lang="${lang}"]`);
    if (option) {
        option.classList.add('selected');
    }
    window.currentLang = lang;
};

window.confirmLanguage = async function (): Promise<void> {
    await loadTranslations(window.currentLang);
    applyTranslations();
    initEmojiFlags();
    updateLangButtons();
    updateState().then(() => {
        initEmojiFlags();
        updateLangButtons();
    });
    // Sync language with backend
    try {
        await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ key: 'LANGUAGE', value: window.currentLang })
        });
        // Clear BOT_LANGUAGE so bot uses LANGUAGE (launcher language)
        await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ key: 'BOT_LANGUAGE', value: '' })
        });
    } catch (e) {
        console.error("Failed to sync language:", e);
    }
    document.getElementById('lang-modal').style.display = 'none';
    langModalShown = true;
    localStorage.setItem('web_launcher_lang_set', 'true');
    showToast(t('ui.launcher.web.language_changed', 'Language changed'), 'success');
}

window.checkFirstLaunch = async function (): Promise<void> {
    // First, try to load saved user language
    const savedLang = localStorage.getItem('web_launcher_language');

    if (savedLang && (savedLang === 'en' || savedLang === 'ru')) {
        // User has previously selected a language, use it
        window.currentLang = savedLang;
        await loadTranslations(savedLang);
        return;
    }

    // No saved language, try to get from backend settings
    try {
        const res = await fetch('/api/settings');
        const data = await res.json();
        if (data.BOT_LANGUAGE && (data.BOT_LANGUAGE === 'en' || data.BOT_LANGUAGE === 'ru')) {
            window.currentLang = data.BOT_LANGUAGE;
            await loadTranslations(data.BOT_LANGUAGE);
            localStorage.setItem('web_launcher_language', data.BOT_LANGUAGE);
            return;
        }
    } catch (e) {
        console.error("Failed to load language from settings:", e);
    }

    // No saved language, use system language
    const systemLang = await getSystemLanguage();
    window.currentLang = systemLang;
    await loadTranslations(systemLang);
    localStorage.setItem('web_launcher_language', systemLang);
};

window.hideSplashScreen = function (): void {
    const splash = document.getElementById('splash-screen');
    if (splash) {
        splash.style.opacity = '0';
        splash.style.transition = 'opacity 0.5s ease';
        setTimeout(() => {
            splash.style.display = 'none';
        }, 500);
    }
};

// Initialize App
document.addEventListener('DOMContentLoaded', async () => {
    try {
        await window.checkFirstLaunch();

        // Initial UI Updates
        applyTranslations();
        initEmojiFlags();
        updateLangButtons();

        // Hide Splash Screen
        setTimeout(window.hideSplashScreen, 500);

        // Start Loops
        updateState().then(() => {
            initEmojiFlags();
            updateLangButtons();
        });
    } catch (e) {
        console.error("Initialization failed:", e);
        // Ensure splash screen goes away even on error
        setTimeout(window.hideSplashScreen, 1000);
    }
});

/**
 * @deprecated SD settings moved to module-settings.html
 */
function updateSdSettingsLock(installed: boolean): void {
    // SD settings moved to module-settings.html, this function is no longer needed
    return;
}

/**
 * @deprecated SD install check no longer needed
 */
async function checkSdInstalled(): Promise<void> {
    // SD install check disabled - no longer needed
    return;
}

window.showSdInstallModal = function (): void {
    const modal = document.getElementById('sd-install-modal');
    if (modal) {
        modal.style.display = 'flex';
        modal.classList.add('show');
    }
};

window.hideSdInstallModal = function (): void {
    const modal = document.getElementById('sd-install-modal');
    if (modal) {
        modal.style.display = 'none';
        modal.classList.remove('show');
    }
    // Remember that user dismissed the modal
    localStorage.setItem('sd_install_dismissed', 'true');
};

window.confirmReinstallSd = function (): void {
    const modal = document.getElementById('reinstall-sd-modal');
    if (modal) {
        modal.style.display = 'flex';
        modal.classList.add('show');
    }
};

window.hideReinstallSdModal = function (): void {
    const modal = document.getElementById('reinstall-sd-modal');
    if (modal) {
        modal.style.display = 'none';
        modal.classList.remove('show');
    }
};

let sdReinstallPoll: ReturnType<typeof setInterval> | null = null;
window.showSdReinstallProgress = function (): void {
    const modal = document.getElementById('sd-reinstall-progress-modal');
    if (modal) {
        modal.style.display = 'flex';
        modal.classList.add('show');
    }
    const statusEl = document.getElementById('sd-reinstall-status');
    if (statusEl) statusEl.textContent = t('ui.launcher.web.reinstall_sd_progress_message', 'Идёт переустановка SD. Пожалуйста, подождите, это может занять несколько минут.');

    // Poll SD installation status
    if (sdReinstallPoll) clearInterval(sdReinstallPoll);
    sdReinstallPoll = setInterval(async () => {
        try {
            const res = await fetch('/api/check_sd_installed');
            if (!res.ok) return;
            const data = await res.json();
            if (data.installed === true) {
                hideSdReinstallProgress();
                showToast(t('ui.launcher.web.reinstall_sd_done', 'Переустановка SD завершена'), 'success', 2500);
                loadSettings();
                return;
            }
        } catch (e) {
            console.warn('Reinstall poll error', e);
        }
    }, 5000);
};

window.hideSdReinstallProgress = function (): void {
    const modal = document.getElementById('sd-reinstall-progress-modal');
    if (modal) {
        modal.style.display = 'none';
        modal.classList.remove('show');
    }
    if (sdReinstallPoll) {
        clearInterval(sdReinstallPoll);
        sdReinstallPoll = null;
    }
};

window.confirmReinstallSdAction = async function (): Promise<void> {
    hideReinstallSdModal();
    showSdReinstallProgress();
    showToast(t('ui.launcher.web.reinstall_sd_starting', 'Начало переустановки SD...'), 'info', 2000);
    try {
        await control('reinstall', 'sd');
    } catch (e) {
        showToast(t('ui.launcher.web.reinstall_sd_error', 'Ошибка при переустановке SD'), 'error');
        console.error('Reinstall SD error:', e);
        hideSdReinstallProgress();
    }
};

window.confirmSdInstall = async function (): Promise<void> {
    hideSdInstallModal();
    showToast(t('ui.launcher.web.sd_install_starting', 'Запуск установки Stable Diffusion...'), 'success');
    // Start SD installation
    try {
        await control('reinstall', 'sd');
    } catch (e) {
        console.error("Failed to start SD installation:", e);
        showToast(t('ui.launcher.web.sd_install_error', 'Ошибка при запуске установки'), 'error');
    }
};

// LLM Start Modal
let llmStartModalResolve: ((value: boolean) => void) | null = null;
window.showLlmStartModal = function (): Promise<boolean> {
    return new Promise((resolve) => {
        llmStartModalResolve = resolve;
        const modal = document.getElementById('llm-start-modal');
        if (modal) {
            modal.style.display = 'flex';
            modal.classList.add('show');
        }
    });
};

window.hideLlmStartModal = function (): void {
    const modal = document.getElementById('llm-start-modal');
    if (modal) {
        modal.style.display = 'none';
        modal.classList.remove('show');
    }
    if (llmStartModalResolve) {
        llmStartModalResolve(false);
        llmStartModalResolve = null;
    }
};

window.confirmLlmStart = function (): void {
    hideLlmStartModal();
    if (llmStartModalResolve) {
        llmStartModalResolve(true);
        llmStartModalResolve = null;
    }
};

// Zoom Support (Ctrl + Scroll)
// Zoom Support removed to ensure responsive browser-like behavior

// Sync maximize icon on resize (handle external snaps or backend toggles)
window.addEventListener('resize', async () => {
   if (window.__TAURI__) {
       try {
           const appWindow = window.__TAURI__.window.getCurrentWindow();
           const isMaximized = await appWindow.isMaximized();
           updateMaximizeIcon(isMaximized);
       } catch(e) {}
   }
});

