/**
 * Flux Platform Tauri Bridge
 * Typed IPC layer for Tauri v2 Commands
 *
 * Maps legacy Electron/HTTP API calls to Tauri v2 Commands
 */

import type { SystemStats, AppSettings, Module, TranslationDictionary } from '../types';

// Type definitions for Tauri API
interface TauriInvoke {
    <T>(cmd: string, args?: Record<string, unknown>): Promise<T>;
}

interface TauriWindow {
    minimize: () => void;
    maximize: () => void;
    unmaximize: () => void;
    close: () => void;
    isMaximized: () => Promise<boolean>;
    toggleMaximize: () => void;
}

interface TauriListen {
    <T>(event: string, handler: (payload: { payload: T }) => void): Promise<() => void>;
}

// Detect Tauri environment
const isTauri = !!window.__TAURI__;

// Get Tauri APIs or create mocks
let invoke: TauriInvoke;
let getCurrentWindow: () => TauriWindow;
let listen: TauriListen;

if (isTauri && window.__TAURI__) {
    invoke = window.__TAURI__.core.invoke;
    getCurrentWindow = window.__TAURI__.window.getCurrentWindow;
    listen = window.__TAURI__.event.listen;
    console.log("[Tauri Bridge] Running in Tauri mode");
} else {
    console.warn("[Tauri Bridge] Running in MOCK MODE for browser testing");

    // Mock implementations
    invoke = async <T>(cmd: string, args?: Record<string, unknown>): Promise<T> => {
        console.log(`[Mock Invoke] ${cmd}`, args);

        switch (cmd) {
            case 'get_settings':
                return { LANGUAGE: 'en', THEME: 'dark' } as T;
            case 'get_translations':
                return {} as T;
            case 'get_modules':
                return [] as T;
            case 'get_system_stats':
                return {
                    cpu: { percent: Math.floor(Math.random() * 30) + 10 },
                    ram: { percent: Math.floor(Math.random() * 40) + 20, used_gb: 8.5, total_gb: 32 },
                    gpu: { usage: Math.floor(Math.random() * 50), memory_used: 4, memory_total: 12 },
                    vram: { percent: Math.floor(Math.random() * 60), used_gb: 6, total_gb: 12 },
                    disk: { utilization: 45, used_gb: 200, total_gb: 500 },
                    network: { download_rate: 1024, upload_rate: 50000 }
                } as T;
            case 'control_module':
                return true as T;
            case 'get_system_language':
                return 'en' as T;
            default:
                return null as T;
        }
    };

    getCurrentWindow = () => ({
        minimize: () => console.log('[Mock] Minimize'),
        maximize: () => console.log('[Mock] Maximize'),
        unmaximize: () => console.log('[Mock] Unmaximize'),
        close: () => console.log('[Mock] Close'),
        isMaximized: async () => false,
        toggleMaximize: () => console.log('[Mock] Toggle Maximize')
    });

    listen = async <T>(_event: string, _handler: (payload: { payload: T }) => void) => {
        console.log(`[Mock Listen] Subscribed to ${_event}`);
        return () => {}; // Unlisten
    };
}

// Export typed invoke function
export { invoke, getCurrentWindow, listen, isTauri };

// Expose generic event listener
window.listenToEvent = async <T>(event: string, callback: (data: { payload: T }) => void) => {
    return await listen(event, callback);
};

// Polyfill window.electronAPI for legacy compatibility
const appWindow = getCurrentWindow();
window.electronAPI = {
    minimize: () => appWindow.minimize(),
    toggleMaximize: async () => {
        if (isTauri) {
            const isMaximized = await appWindow.isMaximized();
            if (isMaximized) appWindow.unmaximize();
            else appWindow.maximize();
        } else {
            appWindow.toggleMaximize();
        }
    },
    close: () => appWindow.close()
};

// Intercept fetch for /api/ calls
const originalFetch = window.fetch.bind(window);
window.fetch = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    let url: string;
    if (input instanceof Request) {
        url = input.url;
    } else if (input instanceof URL) {
        url = input.toString();
    } else {
        url = input;
    }

    // Extract path from URL
    let path = url;
    try {
        if (url.startsWith('http')) {
            const u = new URL(url);
            path = u.pathname;
        }
    } catch (_e) { /* ignore */ }

    if (typeof path === 'string' && path.startsWith('/api/')) {
        console.log(`[Tauri Bridge] Intercepting: ${path}`);

        try {
            return await handleApiRequest(path, init);
        } catch (e) {
            console.error(`[Tauri Bridge] Error handling ${path}:`, e);
            return new Response(JSON.stringify({ error: String(e) }), { status: 500 });
        }
    }

    return originalFetch(input, init);
};

// API request handler
async function handleApiRequest(path: string, init?: RequestInit): Promise<Response> {
    // Log endpoint
    if (path === '/api/log' && init?.method === 'POST' && init.body) {
        if (isTauri) {
            const body = JSON.parse(init.body as string);
            await invoke('add_log', { level: body.level, message: body.message });
        }
        return jsonResponse({ success: true });
    }

    // Settings
    if (path === '/api/settings') {
        if (!init || init.method === 'GET') {
            const settings = await invoke<AppSettings>('get_settings');
            return jsonResponse(settings || {});
        }
        return jsonResponse({ success: true });
    }

    // Translations
    if (path.startsWith('/api/translations')) {
        const u = new URL('http://dummy' + path);
        const lang = u.searchParams.get('lang') || 'en';
        const translations = isTauri
            ? await invoke<TranslationDictionary>('get_translations', { lang })
            : getMockTranslations(lang);
        return jsonResponse(translations);
    }

    // System stats
    if (path === '/api/system_stats') {
        const stats = await invoke<SystemStats>('get_system_stats');
        return jsonResponse(stats);
    }

    // System state
    if (path === '/api/state') {
        return jsonResponse({
            services: { "LLM": "running", "SD": "stopped", "TTS": "running" },
            timestamp: Date.now()
        });
    }

    // System language
    if (path === '/api/system_language') {
        return jsonResponse({ language: 'en' });
    }

    // Modules
    if (path === '/api/modules') {
        const modules = await invoke<Module[]>('get_modules');
        return jsonResponse(modules || []);
    }

    // Download progress
    if (path === '/api/download_progress') {
        const progress = isTauri
            ? await invoke('get_download_progress')
            : { percent: 0, downloaded: 0, total: 0, speed: 0, completed: false };
        return jsonResponse(progress);
    }

    // Fallback
    return jsonResponse({ success: true, mocked: !isTauri });
}

// Helper: JSON response
function jsonResponse<T>(data: T): Response {
    return new Response(JSON.stringify(data), {
        headers: { 'Content-Type': 'application/json' }
    });
}

// Mock translations data
function getMockTranslations(lang: string): TranslationDictionary {
    const translations: Record<string, TranslationDictionary> = {
        en: {
            "ui.launcher.button.cancel": "Cancel",
            "ui.launcher.button.close": "Close",
            "ui.launcher.web.main_menu": "Main Menu",
            "ui.launcher.web.chat": "Chat",
            "ui.launcher.web.modules": "Modules",
            "ui.launcher.web.settings": "Settings",
            "ui.launcher.web.console": "Console",
            "ui.launcher.web.downloads": "Downloads"
        },
        ru: {
            "ui.launcher.button.cancel": "Отмена",
            "ui.launcher.button.close": "Закрыть",
            "ui.launcher.web.main_menu": "Главное меню",
            "ui.launcher.web.chat": "Чат",
            "ui.launcher.web.modules": "Модули",
            "ui.launcher.web.settings": "Настройки",
            "ui.launcher.web.console": "Консоль",
            "ui.launcher.web.downloads": "Загрузки"
        }
    };
    return translations[lang] || translations.en;
}

console.log(`[Tauri Bridge] Setup complete (Mode: ${isTauri ? "Tauri" : "Mock"})`);
