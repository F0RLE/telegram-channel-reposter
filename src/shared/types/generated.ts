// AUTO-GENERATED FILE - DO NOT EDIT
// Source: src-tauri models with #[derive(specta::Type)]

// System Stats
export interface SystemStats {
    cpu: CpuStats;
    ram: RamStats;
    gpu: GpuStats | null;
    vram: VramStats | null;
    disk: DiskStats;
    network: NetworkStats;
    pid: number;
}

export interface CpuStats {
    percent: number;
    cores: number;
    name: string;
}

export interface RamStats {
    percent: number;
    used_gb: number;
    total_gb: number;
    available_gb: number;
}

export interface GpuStats {
    usage: number;
    memory_used: number;
    memory_total: number;
    temp: number;
    name: string;
}

export interface VramStats {
    percent: number;
    used_gb: number;
    total_gb: number;
}

export interface DiskStats {
    read_rate: number;
    write_rate: number;
    utilization: number;
    total_gb: number;
    used_gb: number;
}

export interface NetworkStats {
    download_rate: number;
    upload_rate: number;
    total_received: number;
    total_sent: number;
    utilization: number;
}

// Settings
export interface AppSettings {
    theme: string;
    language: string;
    use_gpu: boolean;
    debug_mode: boolean;
    api_base_url: string;
}

// Chat
export interface ChatMessage {
    id: number | null;
    role: string;
    content: string;
    timestamp: number;
}

export interface ChatAttachment {
    name: string;
    type: string;
    size: number;
    data_base64: string;
}

export interface ChatApiResponse {
    ok: boolean;
    reply: ChatApiReply | null;
    error: string | null;
}

export interface ChatApiReply {
    text: string | null;
    type: string | null;
    images: string[] | null;
}
