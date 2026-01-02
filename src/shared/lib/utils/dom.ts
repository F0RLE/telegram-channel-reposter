// DOM Utilities

declare function hideModuleSettingsModal(): void;

declare function getRandomChatQuestion(): string;
declare function loadSettings(): void;
declare function loadSdModels(): void;
declare function loadLlmModels(): void;
declare function initDebugPage(): void;
declare function loadModulesTab(): void;

interface LauncherLogEntry {
    level: string;
    message: string;
    timestamp: string;
}

// let launcherLogBuffer: LauncherLogEntry[] = []; // use window.launcherLogBuffer from vite-env
window.launcherLogBuffer = window.launcherLogBuffer || [];
let launcherLogFlushTimeout: ReturnType<typeof setTimeout> | null = null;

function launcherLog(level: string, message: string): void {
    // Also log to console for debugging
    const consoleMethod = level === 'ERROR' ? console.error : level === 'WARN' ? console.warn : console.log;
    consoleMethod(`[LAUNCHER] ${message}`);

    // Add to buffer
    window.launcherLogBuffer.push({ level, message, timestamp: new Date().toISOString() });

    // Flush buffer every 500ms or immediately for errors
    if (level === 'ERROR' || window.launcherLogBuffer.length >= 10) {
        flushLauncherLogs();
    } else {
        if (launcherLogFlushTimeout) clearTimeout(launcherLogFlushTimeout);
        launcherLogFlushTimeout = setTimeout(flushLauncherLogs, 500);
    }
}

function flushLauncherLogs(): void {
    if (window.launcherLogBuffer.length === 0) return;

    const logs = [...window.launcherLogBuffer];
    window.launcherLogBuffer = [];

    // Send logs to server
    logs.forEach((log: any) => {
        fetch('/api/log', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ level: log.level, message: log.message })
        }).catch(err => console.error('[LAUNCHER] Failed to send log:', err));
    });
}

function deleteLauncherLog(): void {
    fetch('/api/log/delete', { method: 'POST' }).catch(err => console.error('[LAUNCHER] Failed to delete log:', err));
}

launcherLog('INFO', 'Defining showPage function...');
window.showPage = function (pageId: string, btn?: HTMLElement | null): void {
    try {
        if (!pageId) {
            return;
        }

        const targetPageId = 'page-' + pageId;
        const targetPage = document.getElementById(targetPageId);
        if (!targetPage) {
            console.error('showPage: Page not found:', targetPageId);
            return;
        }

        if (targetPage.classList.contains('active')) {
            return;
        }

        const moduleSettingsModal = document.getElementById('module-settings-modal');
        if (moduleSettingsModal && moduleSettingsModal.classList.contains('show')) {
            if (typeof hideModuleSettingsModal === 'function') {
                hideModuleSettingsModal();
            }
        }

        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                window.showPage(pageId, btn);
            });
            return;
        }

        const allPages = document.querySelectorAll('.page');
        if (allPages.length === 0) {
            console.error('showPage: No pages found!');
            return;
        }

        // Handle transition SEQUENTIALLY to avoid overlap
        // Cancel any pending transition first
        if (window._pageTransitionTimeout) {
            clearTimeout(window._pageTransitionTimeout);
            window._pageTransitionTimeout = null;
            // Immediately clean up any lingering states
            document.querySelectorAll('.page.leaving').forEach(p => {
                p.classList.remove('leaving');
            });
        }

        const currentPage = document.querySelector('.page.active');
        if (currentPage && currentPage !== targetPage) {
            currentPage.classList.remove('active');
            currentPage.classList.add('leaving');

            // Show new page immediately for snappy feel, clean up leaving state after
            targetPage.classList.add('active');

            window._pageTransitionTimeout = setTimeout(() => {
                currentPage.classList.remove('leaving');
                window._pageTransitionTimeout = null;
            }, 150); // Match --duration-normal
        } else if (!currentPage) {
            // No active page (first load), show immediately
            targetPage.classList.add('active');
        }

        const allNavBtns = document.querySelectorAll('#sidebar .nav-btn:not(.hidden)');
        allNavBtns.forEach(b => b.classList.remove('active'));
        if (btn && !btn.classList.contains('hidden')) {
            btn.classList.add('active');
        } else if (!btn) {
            const navBtn = document.querySelector(`#sidebar .nav-btn[data-page="${pageId}"]:not(.hidden)`);
            if (navBtn) {
                navBtn.classList.add('active');
            }
        }



        if (pageId === 'chat') {
            const questionEl = document.getElementById('chat-header-question');
            if (questionEl && typeof getRandomChatQuestion === 'function') {
                questionEl.textContent = getRandomChatQuestion();
            }
        }
        if (pageId === 'settings') {
            if (typeof loadSettings === 'function') {
                loadSettings();
            }
            if (typeof loadSdModels === 'function') {
                loadSdModels();
            }
            if (typeof loadLlmModels === 'function') {
                loadLlmModels();
            }
        }

        if (pageId === 'debug') {
            if (typeof initDebugPage === 'function') {
                initDebugPage();
            }
        }
        if (pageId === 'modules') {
            if (typeof loadModulesTab === 'function') {
                loadModulesTab();
            }
        }
    } catch (error) {
        console.error('Error in showPage:', error);
    }
};
launcherLog('INFO', `showPage function defined, type: ${typeof window.showPage}`);

// Test that showPage is available immediately
if (typeof window.showPage !== 'function') {
    console.error('CRITICAL: showPage function not defined!');
} else {
    console.log('✓ showPage function is available');
}

// Make sure it's also available as a global (not just window property)
if (typeof showPage === 'undefined') {
    window.showPage = window.showPage; // Already set, but ensure global
}

// #region agent log
const __AGENT_SESSION_ID = 'debug-session';
const __AGENT_RUN_ID = `ui_${Date.now()}`;
function agentLog(hypothesisId: string, location: string, message: string, data: Record<string, unknown> = {}): void {
    try {
        fetch('http://127.0.0.1:7242/ingest/3a11dd2d-0e69-46e3-9211-e035eadedf0b', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                sessionId: __AGENT_SESSION_ID,
                runId: __AGENT_RUN_ID,
                hypothesisId,
                location,
                message,
                data,
                timestamp: Date.now()
            })
        }).catch(() => { });
    } catch (e) { }
}
// #endregion
