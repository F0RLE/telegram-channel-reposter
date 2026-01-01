use once_cell::sync::Lazy;
// use serde::Serialize; -- removed redundant import
use nvml_wrapper::Nvml;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Mutex;
use std::time::Duration;
use std::time::Instant;
use sysinfo::{CpuRefreshKind, Disks, MemoryRefreshKind, Networks, RefreshKind, System};
use tauri::{AppHandle, Emitter};

use crate::models::{
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

pub fn get_stats() -> SystemStats {
    let mut monitor = MONITOR.lock().unwrap();
    monitor.sys.refresh_cpu_all();
    monitor.sys.refresh_memory();
    monitor.networks.refresh();
    // Refresh processes for Disk I/O (lightweight refresh of disk usage only)
    monitor.sys.refresh_processes_specifics(
        sysinfo::ProcessesToUpdate::All,
        false, // don't remove dead processes
        sysinfo::ProcessRefreshKind::new().with_disk_usage(),
    );

    let now = Instant::now();
    let elapsed = now.duration_since(monitor.last_update).as_secs_f64();

    let cpu_percent = monitor.sys.global_cpu_usage();
    let cpus = monitor.sys.cpus();
    let cpu_name = cpus
        .first()
        .map(|c| c.brand().to_string())
        .unwrap_or_else(|| "Unknown".to_string());
    let cpu_cores = cpus.len();

    let total_memory = monitor.sys.total_memory() as f64;
    let available_memory = monitor.sys.available_memory() as f64;
    let used_memory = total_memory - available_memory;
    let ram_percent = if total_memory > 0.0 {
        (used_memory / total_memory * 100.0) as f32
    } else {
        0.0
    };

    let mut total_recv: u64 = 0;
    let mut total_sent: u64 = 0;
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

    let mut total_disk_space: u64 = 0;
    let mut total_disk_used: u64 = 0;

    // Disk Usage Calculation (Sum of all processes)
    let mut disk_read_bytes: u64 = 0;
    let mut disk_written_bytes: u64 = 0;

    for process in monitor.sys.processes().values() {
        let usage = process.disk_usage();
        disk_read_bytes += usage.read_bytes;
        disk_written_bytes += usage.written_bytes;
    }

    // refresh_processes refreshes since last call, so these values ARE the rate if called approx every second.
    // However, to be precise with `elapsed` (which might be 1.01s or 0.99s), we can divide by elapsed.
    // usage.read_bytes is "bytes read since last refresh".
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

    // Refresh and iterate disks (reuse existing Disks instance)
    monitor.disks.refresh();
    for disk in &monitor.disks {
        total_disk_space += disk.total_space();
        total_disk_used += disk.total_space().saturating_sub(disk.available_space());
    }

    let bytes_to_gb = |b: f64| (b / 1024.0 / 1024.0 / 1024.0) as f32;

    // GPU Logic
    let mut gpu_stats: Option<GpuStats> = None;
    let mut vram_stats: Option<VramStats> = None;

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
            total_sent: total_sent,
            utilization: 0.0,
        },
        pid: std::process::id(),
    }
}

static MONITORING_ACTIVE: AtomicBool = AtomicBool::new(false);

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

/// Stop the system monitoring loop gracefully
pub fn stop_monitoring() {
    MONITORING_ACTIVE.store(false, Ordering::SeqCst);
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_get_stats_sanity_check() {
        let stats = get_stats();

        // CPU
        assert!(
            stats.cpu.percent >= 0.0 && stats.cpu.percent <= 100.0,
            "CPU percent out of range"
        );
        assert!(stats.cpu.cores > 0, "CPU cores should be > 0");

        // RAM
        assert!(
            stats.ram.percent >= 0.0 && stats.ram.percent <= 100.0,
            "RAM percent out of range"
        );
        assert!(stats.ram.total_gb > 0.0, "Total RAM should be > 0");
    }
}
