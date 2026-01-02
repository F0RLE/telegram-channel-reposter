/**
 * Voice Input Feature
 * Handles voice recognition via Web Speech API
 */

// We rely on vite-env.d.ts for global types, but if they fail, we cast window to any
// to avoid build blocking.

// Voice Recognition State
let recognition: any = null; // Use any to bypass strict type check if global type fails
let isRecording = false;
let finalTranscript = '';

// Offline check
function updateVoiceButtonState() {
    const btn = document.getElementById('chat-voice-btn') as HTMLButtonElement | null;
    if (!btn) return;

    if (!navigator.onLine) {
        btn.style.display = 'none';
    } else {
        btn.style.display = 'flex';
        btn.disabled = false;
        btn.style.opacity = '1';
        btn.style.cursor = 'pointer';
        btn.title = 'Voice';
    }
}

window.addEventListener('online', updateVoiceButtonState);
window.addEventListener('offline', updateVoiceButtonState);
// Check on load (wait for DOM)
setTimeout(updateVoiceButtonState, 1000);

// Check browser support
const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

/**
 * Toggle voice input recording
 */
export function toggleVoiceInput(): void {
    const voiceBtn = document.getElementById('chat-voice-btn') as HTMLElement | null;
    const chatInput = document.getElementById('chat-input') as HTMLInputElement | null;

    if (isRecording) {
        stopVoiceRecording();
        return;
    }

    if (!SpeechRecognition) {
        if ((window as any).showToast) (window as any).showToast((window as any).t('ui.launcher.web.voice_not_supported', 'Ваш браузер не поддерживает распознавание голоса'), 'error', 3000);
        return;
    }

    // Initialize Recognition
    try {
        if (!recognition) {
            recognition = new SpeechRecognition();
            recognition.continuous = true;
            recognition.interimResults = true;

            recognition.onstart = () => {
                isRecording = true;
                if ((window as any).soundFX) (window as any).soundFX.playToggle(true);

                if (voiceBtn) {
                    voiceBtn.style.color = 'var(--danger)';
                    voiceBtn.style.animation = 'pulse 1s infinite';
                }
                if (chatInput) {
                    chatInput.placeholder = (window as any).t('ui.launcher.web.voice_listening', 'Слушаю...');
                    finalTranscript = chatInput.value || ''; // Preserve existing text
                }
            };

            recognition.onend = () => {
                isRecording = false;
                if ((window as any).soundFX) (window as any).soundFX.playToggle(false);

                if (voiceBtn) {
                    voiceBtn.style.color = 'var(--text-secondary)';
                    voiceBtn.style.animation = '';
                    // Re-check online state to ensure correct styling
                    updateVoiceButtonState();
                }
                if (chatInput) {
                    chatInput.placeholder = (window as any).t('ui.launcher.web.chat_placeholder_ask', 'Спросите что-нибудь...');
                }
            };

            recognition.onresult = (event: any) => {
                let interimTranscript = '';

                for (let i = event.resultIndex; i < event.results.length; ++i) {
                    if (event.results[i].isFinal) {
                        finalTranscript += event.results[i][0].transcript + ' ';
                    } else {
                        interimTranscript += event.results[i][0].transcript;
                    }
                }

                if (chatInput) {
                    chatInput.value = finalTranscript + interimTranscript;
                    chatInput.scrollTop = chatInput.scrollHeight;
                    // Trigger input event to resize textarea if needed or update UI
                    chatInput.dispatchEvent(new Event('input', { bubbles: true }));
                }
            };

            recognition.onerror = (event: any) => {
                console.error('Voice recognition error:', event.error);
                if (event.error === 'not-allowed') {
                    if ((window as any).showToast) (window as any).showToast((window as any).t('ui.launcher.web.voice_permission_denied', 'Доступ к микрофону запрещен'), 'error', 3000);
                } else if (event.error !== 'no-speech' && event.error !== 'aborted') {
                    if ((window as any).showToast) (window as any).showToast((window as any).t('ui.launcher.web.voice_error', 'Ошибка распознавания') + `: ${event.error}`, 'error', 3000);
                }
                stopVoiceRecording(); // Stop on error
            };
        }

        // Set Language
        const lang = (window as any).currentLang || 'en';
        recognition.lang = lang === 'ru' ? 'ru-RU' : 'en-US';

        recognition.start();

    } catch (e: any) {
        console.error('Voice input initialization error:', e);
        if ((window as any).showToast) (window as any).showToast((window as any).t('ui.launcher.web.voice_init_error', 'Ошибка инициализации голоса'), 'error', 3000);
        stopVoiceRecording();
    }
}

/**
 * Stop voice recording
 */
function stopVoiceRecording(): void {
    if (recognition && isRecording) {
        recognition.stop();
        // State update handled in onend
    }
}

// Register on window for backward compatibility
(window as any).toggleVoiceInput = toggleVoiceInput;
