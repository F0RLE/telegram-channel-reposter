/**
 * Signals-based State Management for Flux Platform
 *
 * Uses @preact/signals-core for reactive state updates.
 * This enables efficient DOM updates - only affected elements re-render.
 *
 * @example
 * import { systemStats, subscribe } from '@shared/lib/state/signals';
 *
 * // Subscribe to changes
 * subscribe(systemStats.cpu.percent, (value) => {
 *     document.getElementById('cpu-value').textContent = `${value}%`;
 * });
 */

import { signal, computed, effect, batch } from '@preact/signals-core';
import type { SystemStats } from '@types';

// ============================================================================
// System Monitoring Signals
// ============================================================================

/** Current system statistics - updated from Tauri events */
export const systemStats = signal<SystemStats | null>(null);

// Computed values for common UI elements
export const cpuPercent = computed(() => systemStats.value?.cpu.percent ?? 0);
export const ramPercent = computed(() => systemStats.value?.ram.percent ?? 0);
export const gpuPercent = computed(() => systemStats.value?.gpu?.usage ?? 0);
export const vramPercent = computed(() => systemStats.value?.vram?.percent ?? 0);

// Formatted values for display
export const cpuDisplay = computed(() => `${Math.round(cpuPercent.value)}%`);
export const ramDisplay = computed(() => {
    const stats = systemStats.value?.ram;
    if (!stats) return '--';
    return `${stats.used_gb.toFixed(1)} / ${stats.total_gb.toFixed(1)} GB`;
});

// ============================================================================
// Chat State Signals
// ============================================================================

export interface ChatMessageUI {
    id?: number;
    role: 'user' | 'assistant';
    content: string;
    timestamp: number;
    pending?: boolean;
}

/** Chat messages list */
export const chatMessages = signal<ChatMessageUI[]>([]);

/** Is chat sending a message? */
export const chatPending = signal(false);

/** Add a new message */
export function addMessage(msg: ChatMessageUI) {
    chatMessages.value = [...chatMessages.value, msg];
}

/** Clear all messages */
export function clearMessages() {
    chatMessages.value = [];
}

// ============================================================================
// Settings Signals
// ============================================================================

export const currentTheme = signal<'dark' | 'light'>('dark');
export const currentLanguage = signal('ru');

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Subscribe to a signal and return an unsubscribe function.
 * This is a convenience wrapper around effect().
 */
export function subscribe<T>(sig: { value: T }, callback: (value: T) => void): () => void {
    return effect(() => {
        callback(sig.value);
    });
}

/**
 * Batch multiple signal updates for performance.
 * Updates inside the callback will be batched into a single notification.
 */
export { batch };

/**
 * Update system stats from Tauri event.
 * Call this from the event listener.
 */
export function updateSystemStats(stats: SystemStats) {
    systemStats.value = stats;
}
