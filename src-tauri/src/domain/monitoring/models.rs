//! Monitoring Domain Models
//!
//! System resource statistics types.

use serde::Serialize;
use specta::Type;

/// Complete system statistics
#[derive(Debug, Clone, Serialize, Type)]
pub struct SystemStats {
    pub cpu: CpuStats,
    pub ram: RamStats,
    pub gpu: Option<GpuStats>,
    pub vram: Option<VramStats>,
    pub disk: DiskStats,
    pub network: NetworkStats,
    pub pid: u32,
}

/// GPU statistics from NVML
#[derive(Debug, Clone, Serialize, Type)]
pub struct GpuStats {
    pub usage: u32,
    pub memory_used: u64,
    pub memory_total: u64,
    pub temp: u32,
    pub name: String,
}

/// VRAM usage statistics
#[derive(Debug, Clone, Serialize, Type)]
pub struct VramStats {
    pub percent: f32,
    pub used_gb: f32,
    pub total_gb: f32,
}

/// CPU statistics
#[derive(Debug, Clone, Serialize, Type)]
pub struct CpuStats {
    pub percent: f32,
    pub cores: usize,
    pub name: String,
}

/// RAM statistics
#[derive(Debug, Clone, Serialize, Type)]
pub struct RamStats {
    pub percent: f32,
    pub used_gb: f32,
    pub total_gb: f32,
    pub available_gb: f32,
}

/// Disk I/O and usage statistics
#[derive(Debug, Clone, Serialize, Type)]
pub struct DiskStats {
    pub read_rate: f64,
    pub write_rate: f64,
    pub utilization: f32,
    pub total_gb: f32,
    pub used_gb: f32,
}

/// Network throughput statistics
#[derive(Debug, Clone, Serialize, Type)]
pub struct NetworkStats {
    pub download_rate: f64,
    pub upload_rate: f64,
    pub total_received: u64,
    pub total_sent: u64,
    pub utilization: f32,
}
