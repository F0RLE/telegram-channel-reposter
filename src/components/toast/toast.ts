
// Enhanced Toast System
let toastQueue: HTMLElement[] = [];
function showToast(message: string, type: string = 'info', duration: number = 3000, title: string | null = null): void {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        container.id = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    toast.innerHTML = `
                <div class="toast-content">
                    ${title ? `<div class="toast-title">${title}</div>` : ''}
                    <div class="toast-message">${message}</div>
                </div>
            `;

    container.appendChild(toast);
    toastQueue.push(toast);


    setTimeout(() => {
        toast.classList.add('leaving');
        setTimeout(() => {
            toast.remove();
            toastQueue = toastQueue.filter(t => t !== toast);
        }, 300);
    }, duration);
}
(window as any).showToast = showToast;


// Action Feedback
function showActionFeedback(type: string = 'success'): void {
    let feedback = document.getElementById('action-feedback');
    if (!feedback) {
        feedback = document.createElement('div');
        feedback.className = 'action-feedback';
        feedback.id = 'action-feedback';
        feedback.innerHTML = '<div class="action-feedback-icon"></div>';
        document.body.appendChild(feedback);
    }

    feedback.className = `action-feedback ${type}`;
    const iconElement = feedback.querySelector('.action-feedback-icon');
    if (iconElement) {
        iconElement.textContent = '';
    }
    feedback.classList.add('show');


    setTimeout(() => {
        feedback.classList.remove('show');
    }, 600);
}
(window as any).showActionFeedback = showActionFeedback;


// Skeleton Loaders
function showSkeletonLoaders(containerId: string, count: number = 3): void {
    const container = document.getElementById(containerId);
    if (!container) return;

    for (let i = 1; i <= count; i++) {
        const skeleton = document.getElementById(`${containerId}-skeleton-${i}`);
        if (skeleton) {
            skeleton.style.display = 'block';
        }
    }
}

function hideSkeletonLoaders(containerId: string, count: number = 3): void {
    for (let i = 1; i <= count; i++) {
        const skeleton = document.getElementById(`${containerId}-skeleton-${i}`);
        if (skeleton) {
            skeleton.style.display = 'none';
        }
    }
}

// Button Loading State
function setButtonLoading(button: HTMLButtonElement, loading: boolean = true): void {
    if (loading) {
        button.classList.add('loading');
        button.disabled = true;
    } else {
        button.classList.remove('loading');
        button.disabled = false;
    }
}


window.showPromptTab = function (tab: string, btn: HTMLElement | null): void {
    document.querySelectorAll('.prompt-tab-content').forEach(t => (t as HTMLElement).style.display = 'none');
    const targetTab = document.getElementById('prompt-tab-' + tab);
    if (targetTab) {
        targetTab.style.display = 'block';
    }
    if (btn && btn.parentElement) {
        btn.parentElement.querySelectorAll('button').forEach(b => {
            (b as HTMLElement).style.background = 'var(--surface)';
            (b as HTMLElement).style.color = 'var(--text-secondary)';
        });
        btn.style.background = 'var(--primary)';
        btn.style.color = 'white';
    }
};

function updateTokenCount(): void {
    const el = document.getElementById('field-llm-sys') as HTMLTextAreaElement | null;
    const text = el?.value || '';
    const count = Math.floor(text.length / 4);
    const countEl = document.getElementById('token-count-sys');
    if (countEl) countEl.innerText = String(count);
}
// Add event listener after DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    const sysField = document.getElementById('field-llm-sys');
    if (sysField) {
        sysField.addEventListener('input', updateTokenCount);
    }
    // Update status indicator periodically
    setInterval(updateDiagnostics, 5000);
    updateDiagnostics();
});

async function updateDiagnostics() {
    try {
        const res = await fetch('/api/state');
        const data = await res.json();
        const services = data.services || {};
        const allRunning = Object.values(services).every(s => s === 'running');
        const anyError = Object.values(services).some(s => s === 'error');

        const statusEl = document.getElementById('diag-status');
        if (statusEl) {
            let statusClass = 'ok';
            let statusText = t('ui.launcher.diagnostics.status_ok', 'OK');
            if (anyError) {
                statusClass = 'error';
                statusText = t('ui.launcher.status.error', 'Ошибка');
            } else if (!allRunning || Object.keys(services).length === 0) {
                statusClass = 'warning';
                statusText = t('ui.launcher.diagnostics.status_warning', 'Предупреждение');
            }
            statusEl.innerHTML = `<span class="status-indicator-live ${statusClass}"></span><span>${statusText}</span>`;
        }
    } catch (e) {
        console.error("Failed to update diagnostics:", e);
    }
}

window.applyPreset = function (name: string): void {
    const presets: Record<string, { w: number; h: number; s: number; c: number }> = {
        portrait: { w: 896, h: 1152, s: 30, c: 7.0 },
        landscape: { w: 1152, h: 896, s: 30, c: 7.0 },
        telegram: { w: 1024, h: 1024, s: 25, c: 6.5 }
    };
    const p = presets[name];
    if (p) {
        const sdW = document.getElementById('field-sd-w') as HTMLInputElement | null;
        const sdH = document.getElementById('field-sd-h') as HTMLInputElement | null;
        const sdSteps = document.getElementById('field-sd-steps') as HTMLInputElement | null;
        const sdCfg = document.getElementById('field-sd-cfg') as HTMLInputElement | null;
        if (sdW) sdW.value = String(p.w);
        if (sdH) sdH.value = String(p.h);
        if (sdSteps) sdSteps.value = String(p.s);
        if (sdCfg) sdCfg.value = String(p.c);
        const valSteps = document.getElementById('val-sd-steps');
        const valCfg = document.getElementById('val-sd-cfg');
        if (valSteps) valSteps.innerText = String(p.s);
        if (valCfg) valCfg.innerText = p.c.toFixed(1);
    }
};

window.setAspect = function (w: number, h: number): void {
    const sdW = document.getElementById('field-sd-w') as HTMLInputElement | null;
    const sdH = document.getElementById('field-sd-h') as HTMLInputElement | null;
    if (sdW) sdW.value = String(w);
    if (sdH) sdH.value = String(h);
}

function toggleAdZones(): void {
    const enabledEl = document.getElementById('field-ad-enabled') as HTMLInputElement | null;
    const enabled = enabledEl?.checked ?? false;
    document.querySelectorAll('.ad-zone-card input[type="checkbox"], .ad-zone-card input[type="range"]').forEach(el => {
        (el as HTMLInputElement).disabled = !enabled;
    });
}
