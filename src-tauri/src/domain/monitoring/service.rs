//! Monitoring Domain Service
//!
//! System resource monitoring with background event emission.

use nvml_wrapper::Nvml;
use once_cell::sync::Lazy;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Mutex;
use std::time::{Duration, Instant};
use sysinfo::{CpuRefreshKind, Disks, MemoryRefreshKind, Networks, RefreshKind, System};
use tauri::{AppHandle, Emitter};

use super::models::{
    CpuStats, DiskStats, GpuStats, NetworkStats, RamStats, SystemStats, VramStats,
};

struct Monitor {
    sys: System,
    networks: Networks,
    disks: Disks,
    last_update: Instant,
    last_net_recv: u64,
    last_net_sent: u64,
    nvml: Option<Nvml>,
}

static MONITOR: Lazy<Mutex<Monitor>> = Lazy::new(|| {
    let nvml = Nvml::init().ok();

    Mutex::new(Monitor {
        sys: System::new_with_specifics(
            RefreshKind::new()
                .with_cpu(CpuRefreshKind::everything())
                .with_memory(MemoryRefreshKind::everything()),
        ),
        networks: Networks::new_with_refreshed_list(),
        disks: Disks::new_with_refreshed_list(),
        last_update: Instant::now(),
        last_net_recv: 0,
        last_net_sent: 0,
        nvml,
    })
});

static MONITORING_ACTIVE: AtomicBool = AtomicBool::new(false);

/// Get current system statistics
pub fn get_stats() -> SystemStats {
    let mut monitor = MONITOR.lock().unwrap();
    monitor.sys.refresh_cpu_all();
    monitor.sys.refresh_memory();
    monitor.networks.refresh();
    monitor.sys.refresh_processes_specifics(
        sysinfo::ProcessesToUpdate::All,
        false,
        sysinfo::ProcessRefreshKind::new().with_disk_usage(),
    );

    let now = Instant::now();
    let elapsed = now.duration_since(monitor.last_update).as_secs_f64();

    // CPU
    let cpu_percent = monitor.sys.global_cpu_usage();
    let cpus = monitor.sys.cpus();
    let cpu_name = cpus
        .first()
        .map(|c| c.brand().to_string())
        .unwrap_or_else(|| "Unknown".to_string());
    let cpu_cores = cpus.len();

    // RAM
    let total_memory = monitor.sys.total_memory() as f64;
    let available_memory = monitor.sys.available_memory() as f64;
    let used_memory = total_memory - available_memory;
    let ram_percent = if total_memory > 0.0 {
        (used_memory / total_memory * 100.0) as f32
    } else {
        0.0
    };

    // Network
    let (mut total_recv, mut total_sent) = (0u64, 0u64);
    for (_name, data) in monitor.networks.iter() {
        total_recv += data.total_received();
        total_sent += data.total_transmitted();
    }
    let download_rate = if elapsed > 0.0 && monitor.last_net_recv > 0 {
        (total_recv.saturating_sub(monitor.last_net_recv)) as f64 / elapsed
    } else {
        0.0
    };
    let upload_rate = if elapsed > 0.0 && monitor.last_net_sent > 0 {
        (total_sent.saturating_sub(monitor.last_net_sent)) as f64 / elapsed
    } else {
        0.0
    };

    monitor.last_update = now;
    monitor.last_net_recv = total_recv;
    monitor.last_net_sent = total_sent;

    // Disk
    let (mut total_disk_space, mut total_disk_used) = (0u64, 0u64);
    let (mut disk_read_bytes, mut disk_written_bytes) = (0u64, 0u64);
    for process in monitor.sys.processes().values() {
        let usage = process.disk_usage();
        disk_read_bytes += usage.read_bytes;
        disk_written_bytes += usage.written_bytes;
    }
    let read_rate = if elapsed > 0.0 {
        disk_read_bytes as f64 / elapsed
    } else {
        0.0
    };
    let write_rate = if elapsed > 0.0 {
        disk_written_bytes as f64 / elapsed
    } else {
        0.0
    };

    monitor.disks.refresh();
    for disk in &monitor.disks {
        total_disk_space += disk.total_space();
        total_disk_used += disk.total_space().saturating_sub(disk.available_space());
    }

    let bytes_to_gb = |b: f64| (b / 1024.0 / 1024.0 / 1024.0) as f32;

    // GPU
    let (mut gpu_stats, mut vram_stats) = (None, None);
    if let Some(nvml) = &monitor.nvml {
        if let Ok(device) = nvml.device_by_index(0) {
            if let Ok(util) = device.utilization_rates() {
                if let Ok(mem) = device.memory_info() {
                    let total_vram = mem.total as f64;
                    let used_vram = mem.used as f64;
                    let vram_percent = if total_vram > 0.0 {
                        (used_vram / total_vram * 100.0) as f32
                    } else {
                        0.0
                    };

                    gpu_stats = Some(GpuStats {
                        usage: util.gpu,
                        memory_used: mem.used,
                        memory_total: mem.total,
                        temp: device
                            .temperature(
                                nvml_wrapper::enum_wrappers::device::TemperatureSensor::Gpu,
                            )
                            .unwrap_or(0),
                        name: device.name().unwrap_or_else(|_| "NVIDIA GPU".to_string()),
                    });
                    vram_stats = Some(VramStats {
                        percent: vram_percent,
                        used_gb: bytes_to_gb(used_vram),
                        total_gb: bytes_to_gb(total_vram),
                    });
                }
            }
        }
    }

    SystemStats {
        cpu: CpuStats {
            percent: cpu_percent,
            cores: cpu_cores,
            name: cpu_name,
        },
        ram: RamStats {
            percent: ram_percent,
            used_gb: bytes_to_gb(used_memory),
            total_gb: bytes_to_gb(total_memory),
            available_gb: bytes_to_gb(available_memory),
        },
        gpu: gpu_stats,
        vram: vram_stats,
        disk: DiskStats {
            read_rate,
            write_rate,
            utilization: if total_disk_space > 0 {
                (total_disk_used as f64 / total_disk_space as f64 * 100.0) as f32
            } else {
                0.0
            },
            total_gb: bytes_to_gb(total_disk_space as f64),
            used_gb: bytes_to_gb(total_disk_used as f64),
        },
        network: NetworkStats {
            download_rate,
            upload_rate,
            total_received: total_recv,
            total_sent,
            utilization: 0.0,
        },
        pid: std::process::id(),
    }
}

/// Start background monitoring thread
pub fn start_monitoring(app: AppHandle, interval_ms: u64) {
    if MONITORING_ACTIVE.swap(true, Ordering::SeqCst) {
        return;
    }

    std::thread::spawn(move || loop {
        if !MONITORING_ACTIVE.load(Ordering::SeqCst) {
            break;
        }
        let stats = get_stats();
        let _ = app.emit("system_stats", &stats);
        std::thread::sleep(Duration::from_millis(interval_ms));
    });
}

/// Stop monitoring
pub fn stop_monitoring() {
    MONITORING_ACTIVE.store(false, Ordering::SeqCst);
}
