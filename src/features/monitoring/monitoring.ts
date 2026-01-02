/**
 * Monitoring Feature - Signals-based Implementation
 *
 * Uses @preact/signals-core for efficient reactive DOM updates.
 * Only the changed values will trigger DOM updates.
 */

import { subscribeToSystemStats } from '@core/events';
import { effect } from '@preact/signals-core';
import {
    updateSystemStats,
    cpuPercent,
    ramPercent,
    gpuPercent,
    vramPercent,
    systemStats,
    cpuDisplay,
    ramDisplay
} from '@core/state';
import type { SystemStats } from '@types';

// ============================================================================
// DOM Element Cache (for performance)
// ============================================================================

interface DOMElements {
    cpuVal: HTMLElement | null;
    cpuBar: HTMLElement | null;
    ramVal: HTMLElement | null;
    ramBar: HTMLElement | null;
    gpuVal: HTMLElement | null;
    gpuBar: HTMLElement | null;
    vramVal: HTMLElement | null;
    vramBar: HTMLElement | null;
    diskVal: HTMLElement | null;
    diskBar: HTMLElement | null;
    netVal: HTMLElement | null;
    netBar: HTMLElement | null;
}

let elements: DOMElements | null = null;

function cacheElements(): DOMElements {
    return {
        cpuVal: document.getElementById('cpu-percent'),
        cpuBar: document.getElementById('cpu-progress'),
        ramVal: document.getElementById('ram-percent'),
        ramBar: document.getElementById('ram-progress'),
        gpuVal: document.getElementById('gpu-util'),
        gpuBar: document.getElementById('gpu-progress'),
        vramVal: document.getElementById('gpu-memory'),
        vramBar: document.getElementById('vram-progress'),
        diskVal: document.getElementById('disk-usage'),
        diskBar: document.getElementById('disk-progress'),
        netVal: document.getElementById('network-status'),
        netBar: document.getElementById('network-progress'),
    };
}

// ============================================================================
// Format Helpers
// ============================================================================

function formatSpeed(bytes: number): string {
    const mb = bytes / (1024 * 1024);
    if (mb < 1000) return `${mb.toFixed(1)} MB/s`;
    return `${(mb / 1024).toFixed(1)} GB/s`;
}

function formatNetRate(bytes: number): string {
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(1)} MB/s`;
}

// ============================================================================
// Reactive Effects (Signals-powered)
// ============================================================================

function setupReactiveEffects() {
    const el = elements!;

    // CPU - only updates when cpuPercent changes
    effect(() => {
        const pct = cpuPercent.value;
        if (el.cpuVal) el.cpuVal.textContent = `${Math.round(pct)}%`;
        if (el.cpuBar) el.cpuBar.style.width = `${pct}%`;
    });

    // RAM - only updates when ram data changes
    effect(() => {
        const stats = systemStats.value;
        if (!stats?.ram || !el.ramVal || !el.ramBar) return;

        const { used_gb, total_gb, percent } = stats.ram;
        el.ramVal.textContent = `${used_gb.toFixed(1)} / ${total_gb.toFixed(1)} GB`;
        el.ramBar.style.width = `${percent}%`;
    });

    // GPU - only updates when gpu data changes
    effect(() => {
        const stats = systemStats.value;
        if (!el.gpuVal || !el.gpuBar) return;

        if (stats?.gpu) {
            const usage = stats.gpu.usage;
            el.gpuVal.textContent = `${usage}%`;
            el.gpuBar.style.width = `${Math.min(100, usage)}%`;
        } else {
            el.gpuVal.textContent = '--';
            el.gpuBar.style.width = '0%';
        }
    });

    // VRAM - only updates when vram data changes
    effect(() => {
        const stats = systemStats.value;
        if (!el.vramVal || !el.vramBar) return;

        if (stats?.vram) {
            const { used_gb, total_gb, percent } = stats.vram;
            el.vramVal.textContent = `${used_gb.toFixed(1)} / ${total_gb.toFixed(1)} GB`;
            el.vramBar.style.width = `${percent}%`;
        } else {
            el.vramVal.textContent = '--';
            el.vramBar.style.width = '0%';
        }
    });

    // Disk - only updates when disk data changes
    effect(() => {
        const stats = systemStats.value;
        if (!stats?.disk || !el.diskVal || !el.diskBar) return;

        const { read_rate, write_rate, utilization, used_gb, total_gb } = stats.disk;
        el.diskVal.textContent = `R: ${formatSpeed(read_rate)} W: ${formatSpeed(write_rate)}`;
        el.diskBar.style.width = `${utilization}%`;
        el.diskVal.title = `Space: ${used_gb.toFixed(1)} / ${total_gb.toFixed(1)} GB`;
    });

    // Network - only updates when network data changes
    effect(() => {
        const stats = systemStats.value;
        if (!stats?.network || !el.netVal || !el.netBar) return;

        const { download_rate, upload_rate } = stats.network;
        el.netVal.textContent = `↓${formatNetRate(download_rate)}  ↑${formatNetRate(upload_rate)}`;
        el.netBar.style.width = '50%';

        if (download_rate > 1024 || upload_rate > 1024) {
            el.netBar.classList.add('pulse');
        } else {
            el.netBar.classList.remove('pulse');
        }
    });
}

// ============================================================================
// Initialization
// ============================================================================

function initMonitoring(): void {
    console.log('[Monitoring] Initializing with Signals...');

    // Cache DOM elements once
    elements = cacheElements();

    if (!elements.cpuVal) {
        console.warn('[Monitoring] DOM not ready or elements missing');
        return;
    }

    // Setup reactive effects (they auto-update on signal changes)
    setupReactiveEffects();

    // Subscribe to Tauri events → update signal
    subscribeToSystemStats((stats: any) => {
        updateSystemStats(stats as SystemStats);
    });

    console.log('[Monitoring] Signals-based monitoring active');
}

// Ensure init runs even if DOMContentLoaded missed
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initMonitoring);
} else {
    initMonitoring();
}
