import type { TranslationDictionary, AppSettings } from '@shared/types';
import { invoke, isTauri } from '@shared/api/tauri';

let translations: TranslationDictionary = {};
// Initialize global currentLang
// We will set this properly in initializeI18n
window.currentLang = 'en';
let langModalShown: boolean = false;

export async function initializeI18n() {
    const saved = localStorage.getItem('web_launcher_language');
    if (saved) {
        await loadTranslations(saved);
    } else {
        const sys = await getSystemLanguage();
        await loadTranslations(sys);
    }
}

// Fallback/Default English Translations
// Removed: using public/locales/en.json now

async function getSystemLanguage(): Promise<string> {
    try {
        // First try to get from backend if in Tauri (more accurate for system locale)
        if (isTauri) {
             const sysLang = await invoke<string>('get_system_language');
             if (sysLang) return normalizeLang(sysLang);
        }
        // Fallback to browser
        return normalizeLang(navigator.language);
    } catch (e) {
        console.error("Failed to get system language:", e);
        return 'en';
    }
}

function normalizeLang(lang: string): string {
    const code = lang.toLowerCase().split(/[_-]/)[0];
    if (['ru', 'en', 'zh'].includes(code)) return code;
    return 'en';
}
window.getSystemLanguage = getSystemLanguage;

import { en } from './locales/en';
import { ru } from './locales/ru';
import { zh } from './locales/zh';

// Map of all available locales
const LOCALES: Record<string, TranslationDictionary> = {
    en,
    ru,
    zh,
    'en-US': en,
    'ru-RU': ru
};

async function loadTranslations(lang: string | null = null): Promise<void> {
    try {
        const langToLoad = lang || window.currentLang;

        // Initialize empty to reset previous state
        translations = {};

        // Direct import load
        if (LOCALES[langToLoad]) {
            translations = LOCALES[langToLoad];
        } else {
            // Fallback to English
            console.warn(`Locale ${langToLoad} not found, falling back to English`);
            translations = en;
        }

        // Always merge with enTranslations if keys are missing (or if translations is empty)
        // This ensures at least English text shows up instead of keys
        if (langToLoad !== 'en' && langToLoad !== 'en-US') {
             translations = { ...en, ...translations };
        }


        window.currentLang = langToLoad;

        if (lang) {
            // Save to localStorage
            localStorage.setItem('web_launcher_language', lang);

            // Update Backend Settings
            if (isTauri) {
                try {
                    // Fetch current settings first
                    const currentSettings = await invoke<AppSettings>('get_settings');
                    if (currentSettings) {
                        currentSettings.language = lang;
                        // Save full object
                        await invoke('save_settings', { settings: currentSettings });
                    }
                } catch (e) { console.error("Native settings save failed", e); }
            } else {
                try {
                    await fetch('/api/settings', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ key: 'LANGUAGE', value: lang })
                    });
                     // BOT_LANGUAGE removed as it's not in AppSettings
                } catch (e) {
                    console.error("Failed to save language setting:", e);
                }
            }
        }

        try {
            applyTranslations();
        } catch (e) {
            console.error("applyTranslations failed:", e);
        }

        try {
            initEmojiFlags();
            updateLangButtons();
            if (typeof window.updateCurrentLangFlag === 'function') {
                window.updateCurrentLangFlag();
            }
        } catch (e) {
             console.error("UI update failed:", e);
        }
    } catch (e: any) {
        console.error("Failed to load translations:", e);
        // Debug: show actual error
        showToast(`Translation Error: ${e?.message || e}`, 'error', 5000);
    }
}
window.loadTranslations = loadTranslations;

// Language Switcher Logic
const langFlagClasses: Record<string, string> = { en: 'flag-gb', ru: 'flag-ru', zh: 'flag-cn' };

// Toggle sliding menu
window.toggleLangMenu = function (): void {
    const menu = document.getElementById('lang-menu-items');
    if (menu) {
        menu.classList.toggle('open');
    }
};

window.toggleSidebarLangMenu = function (): void {
    const menu = document.getElementById('sidebar-lang-menu');
    if (menu) {
        menu.classList.toggle('open');
    }
};

// Close menu when clicking outside
document.addEventListener('click', function (e: Event): void {
    const target = e.target as HTMLElement;
    // Top bar switcher
    const root = document.querySelector('.lang-switcher-root');
    const menu = document.getElementById('lang-menu-items');
    if (menu && menu.classList.contains('open') && root && !root.contains(target)) {
        menu.classList.remove('open');
    }

    // Sidebar switcher
    const sidebarRoot = document.querySelector('.sidebar-lang-switcher');
    const sidebarMenu = document.getElementById('sidebar-lang-menu');
    if (sidebarMenu && sidebarMenu.classList.contains('open') && sidebarRoot && !sidebarRoot.contains(target)) {
        sidebarMenu.classList.remove('open');
    }
});

// Update UI based on current language
function updateLangSwitcherUI(): void {
    // Update Current Language Button Icon
    const triggerBtn = document.getElementById('current-lang-trigger');
    if (triggerBtn) {
        // Clear existing icon
        triggerBtn.innerHTML = '';

        // Create new flag span
        const span = document.createElement('span');
        span.className = `flag-icon ${langFlagClasses[window.currentLang] || 'flag-gb'}`;
        triggerBtn.appendChild(span);
    }

    // Highlight active in menu
    document.querySelectorAll('.lang-menu-items .lang-btn').forEach(btn => {
        const el = btn as HTMLElement;
        const lang = btn.getAttribute('data-lang');
        if (lang === window.currentLang) {
            el.style.display = 'none';
        } else {
            el.style.display = 'flex';
            el.style.opacity = '1';
        }
    });
}

window.setLanguage = async function (lang: string): Promise<void> {
    // Optimistic UI update
    window.currentLang = lang;
    updateLangSwitcherUI();

    // Close menu after selection
    const menu = document.getElementById('lang-menu-items');
    if (menu) menu.classList.remove('open');

    await loadTranslations(lang);
}

// Update current flag on page load and language change
window.updateCurrentLangFlag = function () {
    updateLangSwitcherUI();
}

// Deprecated functions (noop)
window.toggleLangDropdown = function () { };
window.updateLangButtons = function () { updateLangSwitcherUI(); };

function t(key: string, defaultText: string = ''): string {
    return translations[key] || defaultText || key;
}
window.t = t;

function applyTranslations(): void {
    // Note: We don't need to store flags here because we restore them using String.fromCodePoint
    // which ensures consistent emoji display regardless of what was there before

    document.querySelectorAll('[data-i18n]').forEach(el => {
        // Skip language option buttons - they should keep their emoji flags
        if (el.classList.contains('lang-option') || el.classList.contains('lang-dropdown-btn')) {
            return;
        }

        // Save original English text on first pass
        if (!el.hasAttribute('data-original-text')) {
             if (el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement) {
                if (el.type !== 'password' && el.type !== 'text') {
                    // Start of placeholder handling
                }
             } else if (el instanceof HTMLOptionElement) {
                 el.setAttribute('data-original-text', el.textContent || '');
             } else {
                 // For text content, try to find the text node
                 const textNodes = Array.from(el.childNodes).filter(n => n.nodeType === 3);
                 if (textNodes.length > 0) {
                     el.setAttribute('data-original-text', textNodes[0].textContent?.trim() || '');
                 } else if (el.textContent?.trim()) {
                     el.setAttribute('data-original-text', el.textContent.trim());
                 }
             }
        }

        const key = el.getAttribute('data-i18n');
        const originalText = el.getAttribute('data-original-text') || el.textContent || '';
        const text = t(key, originalText);

        if (el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement) {
            if (el.type === 'password' || el.type === 'text') {
                // Only update placeholder, not value
                if (!el.value || el.value === el.getAttribute('data-original-value')) {
                    el.placeholder = text;
                }
            } else {
                el.placeholder = text;
            }
        } else if (el instanceof HTMLOptionElement) {
             el.textContent = text;
        } else {
            // For text content, preserve structure but update text
            // Check if this element has children with data-i18n (they will be processed separately)
            const i18nChild = el.querySelector('[data-i18n]');
            if (i18nChild && i18nChild !== el) {
                // This element has a child with data-i18n, skip it (child will be processed)
                return;
            }

            // This element itself has data-i18n, update its text
            if (el.children.length === 0 || el.querySelector('svg')) {
                // If it's a simple text element or has only SVG icon, update text
                const svg = el.querySelector('svg');
                if (svg) {
                    // Preserve SVG, update text after it
                    const textNode = Array.from(el.childNodes).find(n => n.nodeType === 3);
                    if (textNode) {
                        textNode.textContent = ' ' + text;
                    } else {
                        el.appendChild(document.createTextNode(' ' + text));
                    }
                } else {
                    el.textContent = text;
                }
            } else {
                // Complex element, try to update only text nodes
                const textNodes = Array.from(el.childNodes).filter(n => n.nodeType === 3);
                if (textNodes.length > 0) {
                    // Update first text node, remove others
                    textNodes[0].textContent = text;
                    textNodes.slice(1).forEach(n => n.remove());
                } else {
                    // No text nodes, replace all content
                    el.textContent = text;
                }
            }
        }
    });

    // Apply placeholders with data-i18n-placeholder
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
        const key = el.getAttribute('data-i18n-placeholder');
        if (!el.hasAttribute('data-original-placeholder')) {
             if (el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement) {
                 el.setAttribute('data-original-placeholder', el.placeholder);
             }
        }

        if (el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement) {
            const originalPh = el.getAttribute('data-original-placeholder') || el.placeholder;
            el.placeholder = t(key, originalPh);
        }
    });

    // Apply titles (tooltips) with data-i18n-title
    document.querySelectorAll('[data-i18n-title]').forEach(el => {
        const key = el.getAttribute('data-i18n-title');
        const element = el as HTMLElement;
        if (!element.hasAttribute('data-original-title')) {
            element.setAttribute('data-original-title', element.title);
        }
        const originalTitle = element.getAttribute('data-original-title') || element.title;
        element.title = t(key, originalTitle);
    });

    // Keep language button state in sync (flags are SVG, not emoji)
    updateLangButtons();
}
window.applyTranslations = applyTranslations;

function updateLangButtonsHelper() {
    // Helper for legacy support if needed, but main logic is in updateLangSwitcherUI
}

function initEmojiFlags(): void {
    // Backward-compat: older code calls this; our flags are SVG so we just sync state.
    updateLangButtons();
}
window.initEmojiFlags = initEmojiFlags;
