
import { subscribeToSystemStats } from '../../lib/events/system';
import type { SystemStats } from '../../lib/types';

function initMonitoring(): void {
    console.log("[Monitoring] Initializing...");
    const cpuVal = document.getElementById('cpu-percent');

    if (!cpuVal) {
        console.warn("[Monitoring] DOM not ready or elements missing");
        return;
    }

    subscribeToSystemStats((stats: any) => {
        // console.log("[Monitoring] Update", stats); // specific debug
        updateUI(stats);
    });

    if (!window.__TAURI__) {
        const titleEl = document.querySelector('[data-card-id="monitoring"] .card-title');
        if (titleEl) {
            const warningCallback = () => {
                const badge = document.createElement('span');
                badge.textContent = "(Demo Data)";
                badge.style.color = "var(--warning)";
                badge.style.fontSize = "0.8rem";
                badge.style.marginLeft = "0.5rem";
                badge.style.fontWeight = "bold";
                const titleText = titleEl.querySelector('[data-i18n]');
                if (titleText) titleText.appendChild(badge);
            };
            // Wait slightly for i18n to settle
            setTimeout(warningCallback, 500);
        }
    }
}

// Ensure init runs even if DOMContentLoaded missed
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initMonitoring);
} else {
    initMonitoring();
}

interface MonitoringStats {
    cpu?: { percent: number };
    ram?: { percent: number; used_gb?: number; total_gb?: number };
    gpu?: { usage?: number; util?: number; memory_used?: number; memory_total?: number };
    vram?: { percent: number; used_gb?: number; total_gb?: number; used?: number; total?: number };
    disk?: { utilization?: number; used_gb: number; total_gb: number; read_rate?: number; write_rate?: number };
    network?: { download_rate?: number; upload_rate?: number };
}

function updateUI(stats: any): void {
    const cpuVal = document.getElementById('cpu-percent');
    const cpuBar = document.getElementById('cpu-progress');
    const gpuVal = document.getElementById('gpu-util');
    const gpuBar = document.getElementById('gpu-progress');
    const ramVal = document.getElementById('ram-percent');
    const ramBar = document.getElementById('ram-progress');
    const vramVal = document.getElementById('gpu-memory');
    const vramBar = document.getElementById('vram-progress');
    const diskVal = document.getElementById('disk-usage');
    const diskBar = document.getElementById('disk-progress');
    const netVal = document.getElementById('network-status');
    const netBar = document.getElementById('network-progress');
    // CPU
    if (stats.cpu && cpuVal && cpuBar) {
        cpuVal.textContent = `${Math.round(stats.cpu.percent)}%`;
        cpuBar.style.width = `${stats.cpu.percent}%`;
    }

    // RAM (Show GB)
    if (stats.ram && ramVal && ramBar) {
        // Use provided GB values if available, otherwise calculate
        const used = stats.ram.used_gb ? stats.ram.used_gb.toFixed(1) : ((stats.ram.percent / 100) * 16).toFixed(1); // fallback mock total
        const total = stats.ram.total_gb ? stats.ram.total_gb.toFixed(1) : "16.0";
        ramVal.textContent = `${used} / ${total} GB`;
        ramBar.style.width = `${stats.ram.percent}%`;
    }

    // GPU (Util %)
    if (stats.gpu && gpuVal && gpuBar) {
        // Backend returns: usage, memory_used, memory_total, temp, name
        // Mock returns: util, memory
        const util = stats.gpu.usage !== undefined ? stats.gpu.usage : stats.gpu.util;
        gpuVal.textContent = `${util}%`;
        gpuBar.style.width = `${Math.min(100, util)}%`;

        // Optional: Tooltip for GPU Name/Temp?
        // For now simple integration as requested
    } else if (gpuVal) {
        gpuVal.textContent = "--";
        gpuBar.style.width = "0%";
    }

    // VRAM (Show GB)
    if (stats.vram && vramVal && vramBar) {
        // Backend returns: used_gb, total_gb, percent
        // Mock returns: used, total, percent (sometimes mixed)
        const used = stats.vram.used_gb !== undefined ? stats.vram.used_gb.toFixed(1) : (stats.vram.used ? stats.vram.used.toFixed(1) : "0.0");
        const total = stats.vram.total_gb !== undefined ? stats.vram.total_gb.toFixed(1) : (stats.vram.total ? stats.vram.total.toFixed(1) : "0.0");

        vramVal.textContent = `${used} / ${total} GB`;
        vramBar.style.width = `${stats.vram.percent}%`;
    } else if (vramVal) {
        vramVal.textContent = "--";
        vramBar.style.width = "0%";
    }

    // Disk (Show Read/Write Speed as requested, fall back to space if 0 activity?)
    // User requested: "show download/read speed... without KB".
    if (stats.disk && diskVal && diskBar) {
        // Backend v1.2 sends: utilization, used_gb, total_gb, read_rate, write_rate
        const read = stats.disk.read_rate || 0;
        const write = stats.disk.write_rate || 0;

        // Format to MB/s or GB/s only
        const fmtSpeed = (bytes: number): string => {
            const mb = bytes / (1024 * 1024);
            if (mb < 1000) return `${mb.toFixed(1)} MB/s`;
            return `${(mb/1024).toFixed(1)} GB/s`;
        };

        diskVal.textContent = `R: ${fmtSpeed(read)} W: ${fmtSpeed(write)}`;

        // Bar shows generic activity or space? User said "disk broken".
        // Let's use utilization for the bar as it's usage.
        const pct = stats.disk.utilization || 0;
        diskBar.style.width = `${pct}%`;

        // Optional: Tooltip for space
        diskVal.title = `Space: ${stats.disk.used_gb.toFixed(1)} / ${stats.disk.total_gb.toFixed(1)} GB`;
    }

    // Network (Show MB/s or GB/s rate)
    if (stats.network && netVal && netBar) {
        // Backend sends download_rate, upload_rate in bytes/sec
        const downRate = stats.network.download_rate || 0;
        const upRate = stats.network.upload_rate || 0;

        const fmtNet = (bytes: number): string => {
             const mb = bytes / (1024 * 1024);
             return `${mb.toFixed(1)} MB/s`;
        };

        netVal.innerText = `↓${fmtNet(downRate)}  ↑${fmtNet(upRate)}`;

        netBar.style.width = '50%'; // Activity indicator
        if (downRate > 1024 || upRate > 1024) netBar.classList.add('pulse');
        else netBar.classList.remove('pulse');
    }
}

function formatBytes(bytes: number, decimals: number = 1): string {
    if (!+bytes) return '0 B';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
}
