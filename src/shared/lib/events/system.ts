/**
 * System Events - Subscribe to system monitoring events from Rust backend
 *
 * The backend emits 'system_stats' events every second with full system info.
 * This replaces polling via setInterval + invoke.
 */

import type { SystemStats } from '@shared/types';

// Callback storage for system stats updates
type StatsCallback = (stats: SystemStats) => void;
let systemStatsCallback: StatsCallback | null = null;
let unlistenFn: (() => void) | null = null;

/**
 * Subscribe to system stats events
 * @param callback - Called with stats object on each update
 * @returns Unsubscribe function
 */
export async function subscribeToSystemStats(callback: StatsCallback): Promise<() => void> {
    systemStatsCallback = callback;

    // Use Tauri's listen API
    if (window.__TAURI__) {
        const { listen } = await import('@tauri-apps/api/event');

        unlistenFn = await listen<SystemStats>('system_stats', (event) => {
            if (systemStatsCallback) {
                systemStatsCallback(event.payload);
            }
        });

        return unlistenFn;
    } else {
        console.warn('Tauri not available, falling back to polling');
        return fallbackPolling(callback);
    }
}

/**
 * Unsubscribe from system stats events
 */
export function unsubscribeFromSystemStats(): void {
    systemStatsCallback = null;
    if (unlistenFn) {
        unlistenFn();
        unlistenFn = null;
    }
}

/**
 * Fallback polling for non-Tauri environments (testing)
 */
async function fallbackPolling(callback: StatsCallback): Promise<() => void> {
    const pollInterval = setInterval(async () => {
        try {
            let stats: SystemStats | null = null;

            if (window.__TAURI__) {
                stats = await window.__TAURI__.core.invoke<SystemStats>('get_system_stats');
            } else {
                // Fetch from bridge interceptor (Mock Mode)
                const res = await fetch('/api/system_stats');
                if (res.ok) {
                    stats = await res.json();
                }
            }

            if (stats && callback) {
                callback(stats);
            }
        } catch (e) {
            console.error('Polling error:', e);
        }
    }, 1000);

    return () => clearInterval(pollInterval);
}

/**
 * Get current system stats (one-time, for compatibility)
 * Prefer subscribeToSystemStats for continuous updates
 */
export async function getSystemStatsOnce(): Promise<SystemStats | null> {
    if (window.__TAURI__) {
        return await window.__TAURI__.core.invoke<SystemStats>('get_system_stats');
    }
    return null;
}
