/**
 * Flux Platform TypeScript Types
 * @module lib/types
 */

// ============================================
// Settings Types
// ============================================

export interface AppSettings {
    theme: string;
    language: string;
    use_gpu: boolean;
    debug_mode: boolean;
}

export interface GenerationConfig {
    llm_temp: number;
    llm_ctx: number;
    sd_steps: number;
    sd_cfg: number;
    sd_width: number;
    sd_height: number;
    sd_sampler: string;
    sd_scheduler: string;
}

// ============================================
// Module Types
// ============================================

export type ModuleStatus = 'stopped' | 'starting' | 'running' | 'stopping' | 'error';

export interface Module {
    id: string;
    name: string;
    description: string;
    status: ModuleStatus;
    icon?: string;
    version?: string;
}

export interface ModuleConfig {
    [key: string]: string | number | boolean;
}

// ============================================
// System Monitor Types
// ============================================

export interface SystemStats {
    cpu_percent: number;
    ram_percent: number;
    ram_used_gb: number;
    ram_total_gb: number;
    disk_percent: number;
    disk_used_gb: number;
    disk_total_gb: number;
    network_up: number;
    network_down: number;
}

export interface GpuInfo {
    name: string;
    util_percent: number;
    memory_used_mb: number;
    memory_total_mb: number;
    memory_percent: number;
    temperature: number;
}

// ============================================
// Download Types
// ============================================

export type DownloadStatus = 'pending' | 'downloading' | 'completed' | 'error' | 'cancelled';

export interface DownloadProgress {
    id: string;
    filename: string;
    status: DownloadStatus;
    progress: number;
    downloaded_bytes: number;
    total_bytes: number;
    speed_bps: number;
    eta_seconds: number;
}

// ============================================
// Chat Types
// ============================================

export interface ChatMessage {
    id: string;
    role: 'user' | 'assistant' | 'system';
    content: string;
    timestamp: Date;
    attachments?: string[];
}

// ============================================
// UI Types
// ============================================

export interface ToastOptions {
    message: string;
    type: 'success' | 'error' | 'warning' | 'info';
    duration?: number;
}

export interface ModalOptions {
    title: string;
    message: string;
    confirmText?: string;
    cancelText?: string;
    onConfirm?: () => void;
    onCancel?: () => void;
}

// ============================================
// Tauri Command Response Types
// ============================================

export interface TauriResponse<T> {
    success: boolean;
    data?: T;
    error?: string;
}

// ============================================
// Translation Types
// ============================================

export type TranslationDictionary = Record<string, string>;
