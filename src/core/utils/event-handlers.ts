
/**
 * Global Event Handlers
 * Handles delegated events for data-action attributes
 */

// Add global types for the functions we expect to call
declare global {
    interface Window {
        [key: string]: any;
    }
}

function initEventHandlers() {
    document.addEventListener('click', (e) => {
        const target = (e.target as HTMLElement).closest('[data-action]');
        if (target) {
            const action = target.getAttribute('data-action');
            if (action && typeof window[action] === 'function') {
                // Determine args (optional)
                const args = target.getAttribute('data-args');
                if (args) {
                    try {
                        window[action](...JSON.parse(args));
                    } catch (e) {
                        console.error('Failed to parse args for action', action, e);
                        window[action]();
                    }
                } else {
                    window[action](target); // Pass element as first arg context
                }
            } else {
                console.warn(`Action '${action}' not found on window object`);
            }
        }
    });

    // Handle specific specific non-action UI logic if needed
    // e.g. closing modals on outside click (often handled in specific files but good to have fallback)
}

// Initialize on load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initEventHandlers);
} else {
    initEventHandlers();
}

export {};
