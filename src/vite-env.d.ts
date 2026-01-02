/**
 * Flux Platform Global Type Declarations
 * Extends Window interface with global functions and properties
 */

/// <reference types="vite/client" />

// Extend Window interface with global functions
declare global {
    interface Window {
        // Tauri API
        __TAURI__?: {
            core: {
                invoke: <T>(cmd: string, args?: Record<string, unknown>) => Promise<T>;
            };
            window: {
                getCurrentWindow: () => {
                    minimize: () => void;
                    maximize: () => void;
                    unmaximize: () => void;
                    close: () => void;
                    isMaximized: () => Promise<boolean>;
                    toggleMaximize: () => void;
                };
            };
            event: {
                listen: <T>(event: string, handler: (payload: { payload: T }) => void) => Promise<() => void>;
            };
        };

        // Electron API polyfill
        electronAPI?: {
            minimize: () => void;
            toggleMaximize: () => void;
            close: () => void;
        };

        // Page navigation
        showPage: (pageId: string, btn?: HTMLElement | null) => void;
        _pageTransitionTimeout?: ReturnType<typeof setTimeout> | null;

        // Window controls
        minimizeWindow: () => void;
        toggleMaximizeWindow: () => void;
        closeWindow: () => void;
        showCloseConfirmModal: () => void;
        hideCloseConfirmModal: () => void;
        confirmCloseFromModal: () => void;

        // Language/i18n
        setLanguage: (lang: string) => void;
        changeLanguage: (lang: string) => Promise<void>;
        toggleLangMenu: () => void;
        toggleLangDropdown: (page?: string) => void;
        selectLangInModal: (lang: string) => void;
        confirmLanguage: () => void;
        currentLang: string;
        updateLangButtons: () => void;
        updateCurrentLangFlag: () => void;
        toggleSidebarLangMenu: () => void;
        translations: Record<string, Record<string, string>>;
        currentLanguage: string;
        t: (key: string, fallback?: string, params?: Record<string, unknown>) => string;

        // Splash/First launch
        hideSplashScreen: () => void;
        checkFirstLaunch: () => Promise<void>;

        // Chat functions
        sendChat: () => void;
        clearChat: () => void;
        pickChatFiles: () => void;
        toggleVoiceInput: () => void;

        // Downloads functions
        openDownloadSettings: () => void;
        closeDownloadSettings: () => void;
        closeDownloadSettingsOnOverlay: (event: Event) => void;
        updateSpeedDisplay: (value: string) => void;
        saveDownloadSettings: () => void;

        // Module functions
        hideModuleSettingsModal: () => void;
        saveModuleSettings: () => void;
        fetchModulesCached: () => Promise<{ items?: unknown[]; modules?: unknown[] }>;

        // SD Install Modal
        showSdInstallModal: () => void;
        hideSdInstallModal: () => void;
        confirmSdInstall: () => void;
        hideReinstallSdModal: () => void;
        confirmReinstallSdAction: () => void;
        confirmReinstallSd: () => void;
        hideSdReinstallProgress: () => void;
        cancelModelDownload: () => void;

        // LLM Modal
        showLlmStartModal: () => void;
        hideLlmStartModal: () => void;
        confirmLlmStart: () => void;

        // Console/Debug functions
        setLogView: (view: string, btn: HTMLElement) => void;
        setDebugTab: (tab: string, btn: HTMLElement | null) => void;
        clearLogs: () => void;
        loadCardWidths: () => void;

        // Settings functions
        control: (action: string, service: string) => Promise<void>;
        selectSdModel: (name: string) => Promise<void>;
        deleteSdModel: (name: string) => Promise<void>;
        selectLlmModel: (name: string, type: string) => Promise<void>;
        saveLlmPrompts: (showNotification?: boolean) => Promise<void>;
        saveSdPrompts: (showNotification?: boolean) => Promise<void>;
        saveAllChanges: () => Promise<void>;
        loadGpuInfo: () => Promise<void>;

        // Chat/Model functions
        pasteModelsDir: () => void;
        selectModelsFolder: () => Promise<void>;
        pasteSdModelsDir: () => void;
        selectSdModelsFolder: () => Promise<void>;
        downloadModel: () => Promise<void>;
        hideModelDownloadModal: () => void;
        updateSystemStats: (stats: unknown) => void;
        debugSwitchTab: (tab: string, btn: HTMLElement) => void;

        // Prompt/Preset functions
        showPromptTab: (tab: string, btn: HTMLElement | null) => void;
        applyPreset: (preset: string) => void;
        setAspect: (w: number, h: number) => void;

        // Toast/Feedback
        showToast: (message: string, type?: string, duration?: number) => void;
        showActionFeedback: (element: HTMLElement, success?: boolean) => void;

        // Event listener
        listenToEvent: <T>(event: string, callback: (data: { payload: T }) => void) => Promise<() => void>;

        // Sound effects
        soundFX?: {
            playHover: () => void;
            playClick: () => void;
            playToggle: (state: boolean) => void;
        };

         // Audio
        webkitAudioContext?: typeof AudioContext;

        // Init/Global functions
        initEmojiFlags: () => void;
        loadGpuInfo: () => Promise<void>;
        loadTranslations: () => Promise<void>;
        renderLogs: (force?: boolean) => void;
        pollLogs: () => void;
        checkSdInstalled: () => void;
        deleteLauncherLog: () => void;
        confirmClose: () => void;

        // Utility functions
        safeFetchJson: <T>(url: string, defaultValue: T, options?: RequestInit) => Promise<T>;
        safeJsonParse: <T>(text: string, defaultValue: T) => T;
        updateState: () => Promise<void>;

        // Module management
        removeActiveModule: (slot: string) => Promise<void>;
        installModule: (moduleId: string, repoUrl: string) => Promise<void>;
        removeModule: (path: string) => Promise<void>;
        showInstallModal: () => void;

        // Settings functions
        showSettingsSection: (sectId: string, btn: HTMLElement | null) => void;
        setTab: (tab: string, btn: HTMLElement | null) => void;
        setCardWidth: (btn: HTMLElement, width: string) => void;
        toggleNavItem: (pageId: string, enabled: boolean) => void;
        initTaskbarToggles: () => void;
        toggleTaskbarItem: (pageId: string) => void;
        toggleMonitorItem: (monitorId: string, enabled: boolean) => void;
        updateMonitorPanelVisibility: () => void;
        initMonitorToggles: () => void;
        toggleMonitorBtn: (monitorId: string) => void;
        startResize: (e: MouseEvent, handle: HTMLElement) => void;

        // Settings module helpers
        openModuleSettings: (moduleId: string) => void;
        toggleModule: (moduleId: string) => Promise<void>;
        viewModuleLogs: (moduleId: string) => void;
        addModule: (category: string) => void;
        uninstallModule: (moduleId: string) => Promise<void>;
    }

    // Global variables
    var modulesTab: HTMLElement | null;
    var translations: Record<string, Record<string, string>>;
    var currentLanguage: string;
    var currentLang: string;
    var launcherLogBuffer: unknown[];
    var currentModuleId: string | null;
    var resizeState: {
        isResizing: boolean;
        card: HTMLElement | null;
        startX: number;
        startWidth: string;
        hasSwitched: boolean;
    };

    // Global functions (available without window. prefix)
    function showPage(pageId: string, btn?: HTMLElement | null): void;

    // Module management
    function removeActiveModule(slot: string): Promise<void>;
    function installModule(moduleId: string, repoUrl: string): Promise<void>;
    function removeModule(path: string): Promise<void>;
    function showInstallModal(): void;
    function updateState(): Promise<void>;
    function updateLangButtons(): void;
    function updateMaximizeIcon(isMaximized?: boolean): void;
    function showLlmStartModal(): void;
    function hideLlmStartModal(): void;
    function applyTranslationsToPage(): void;
    function showToast(message: string, type?: string, duration?: number): void;
    function showActionFeedback(element: HTMLElement, success?: boolean): void;
    function t(key: string, fallback?: string, params?: Record<string, unknown>): string;
    function hideModuleSettingsModal(): void;
    function stopDownloadsPolling(): void;
    function startDownloadsPolling(): void;
    function getRandomChatQuestion(): string;
    function loadSettings(): void;
    function loadSdModels(): void;
    function loadLlmModels(): void;
    function initDebugPage(): void;
    function loadModulesTab(): void;
    function saveLlmPrompts(showNotification?: boolean): Promise<void>;
    function saveSdPrompts(showNotification?: boolean): Promise<void>;
    function updateSaveButton(): void;
    function hideModelDownloadModal(): void;
    function checkFirstLaunch(): Promise<void>;
    function initEmojiFlags(): void;
    function loadGpuInfo(): Promise<void>;
    function loadTranslations(): Promise<void>;
    function renderLogs(force?: boolean): void;
    function pollLogs(): void;
    function checkSdInstalled(): void;
    function deleteLauncherLog(): void;
    function updateSystemStats(data?: any): void;
    function loadModules(): void;
}

export {};
