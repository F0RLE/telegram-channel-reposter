/**
 * Event Handlers - Centralized event delegation for CSP compliance
 * Replaces inline onclick handlers with event delegation
 */

// Handler registry - maps action names to handler functions
const handlers: Record<string, (element: HTMLElement, event: Event) => void> = {
    // Language
    'setLanguage': (el) => {
        const lang = el.dataset.lang;
        if (lang && window.setLanguage) window.setLanguage(lang);
    },
    'toggleLangMenu': () => window.toggleLangMenu?.(),
    'selectLangInModal': (el) => {
        const lang = el.dataset.lang;
        if (lang && window.selectLangInModal) window.selectLangInModal(lang);
    },
    'confirmLanguage': () => window.confirmLanguage?.(),

    // Window controls
    'minimizeWindow': () => window.minimizeWindow?.(),
    'toggleMaximizeWindow': () => window.toggleMaximizeWindow?.(),
    'showCloseConfirmModal': () => window.showCloseConfirmModal?.(),
    'hideCloseConfirmModal': () => window.hideCloseConfirmModal?.(),
    'confirmCloseFromModal': () => window.confirmCloseFromModal?.(),

    // Downloads
    'openDownloadSettings': () => window.openDownloadSettings?.(),
    'closeDownloadSettings': () => window.closeDownloadSettings?.(),

    // Console/Debug
    'setLogView': (el) => {
        if (window.setLogView) window.setLogView('general', el);
    },
    'clearLogs': () => window.clearLogs?.(),

    // Chat
    'clearChat': () => window.clearChat?.(),
    'pickChatFiles': () => window.pickChatFiles?.(),
    'toggleVoiceInput': () => window.toggleVoiceInput?.(),
    'sendChat': () => window.sendChat?.(),

    // Module settings
    'hideModuleSettingsModal': () => window.hideModuleSettingsModal?.(),
    'saveModuleSettings': () => window.saveModuleSettings?.(),

    // SD modals
    'hideSdInstallModal': () => window.hideSdInstallModal?.(),
    'confirmSdInstall': () => window.confirmSdInstall?.(),
    'hideReinstallSdModal': () => window.hideReinstallSdModal?.(),
    'confirmReinstallSdAction': () => window.confirmReinstallSdAction?.(),
    'hideSdReinstallProgress': () => window.hideSdReinstallProgress?.(),

    // LLM modal
    'hideLlmStartModal': () => window.hideLlmStartModal?.(),
    'confirmLlmStart': () => window.confirmLlmStart?.(),

    // Model download
    'cancelModelDownload': () => window.cancelModelDownload?.(),
};

/**
 * Initialize event delegation on document
 */
export function initEventHandlers(): void {
    // Click delegation
    document.addEventListener('click', (e) => {
        const target = e.target as HTMLElement;
        const actionEl = target.closest('[data-action]') as HTMLElement | null;

        if (actionEl) {
            const action = actionEl.dataset.action;
            if (action && handlers[action]) {
                e.preventDefault();
                handlers[action](actionEl, e);
            }
        }
    });

    // Handle modal overlay clicks (close on background click)
    document.addEventListener('click', (e) => {
        const target = e.target as HTMLElement;

        // Check if clicked on modal overlay (not the modal content)
        if (target.classList.contains('modal-overlay')) {
            const modalId = target.id;

            // Close specific modals based on ID
            if (modalId === 'module-settings-modal') {
                window.hideModuleSettingsModal?.();
            } else if (modalId === 'llm-start-modal') {
                window.hideLlmStartModal?.();
            } else if (modalId === 'reinstall-sd-modal') {
                window.hideReinstallSdModal?.();
            } else if (modalId === 'sd-reinstall-progress-modal') {
                window.hideSdReinstallProgress?.();
            } else if (modalId === 'download-settings-overlay') {
                window.closeDownloadSettings?.();
            }
        }
    });

    // Disable F12 (DevTools)
    document.addEventListener('keydown', (e) => {
        if (e.key === 'F12') {
            e.preventDefault();
            e.stopPropagation();
            console.debug('[EventHandlers] F12 disabled');
        }
    });

    // Stop propagation for modal content
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => e.stopPropagation());
    });

    console.log('[EventHandlers] Initialized event delegation');
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initEventHandlers);
} else {
    initEventHandlers();
}
