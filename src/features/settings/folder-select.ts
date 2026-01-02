/**
 * Folder Selection Feature
 * Handles folder selection dialogs for model directories
 */

declare function showToast(message: string, type: string, duration?: number, title?: string): void;
declare function t(key: string, fallback?: string): string;
declare function markUnsaved(fieldId: string): void;
declare function saveSetting(key: string, value: unknown, notify?: boolean, reload?: boolean, fieldId?: string): Promise<void>;

/**
 * Paste LLM models directory from clipboard
 */
export async function pasteModelsDir(): Promise<void> {
    try {
        const text = await navigator.clipboard.readText();
        const modelsDirField = document.getElementById('field-models-dir') as HTMLInputElement | null;
        if (modelsDirField) {
            modelsDirField.value = text;
            markUnsaved('models-dir');
            showToast(t('ui.launcher.button.pasted', 'Путь вставлен'), 'success', 1500);
        }
    } catch (e) {
        showToast(t('ui.launcher.button.paste_failed', 'Не удалось вставить'), 'error');
    }
}

/**
 * Select LLM models folder via Windows dialog
 */
export async function selectModelsFolder(): Promise<void> {
    try {
        showToast(t('ui.launcher.button.opening_folder_dialog', 'Открывается диалог выбора папки...'), 'info', 1000);
        const res = await fetch('/api/select_folder', { method: 'POST' });
        const data = await res.json();
        if (data.ok && data.path) {
            const modelsDirField = document.getElementById('field-models-dir') as HTMLInputElement | null;
            if (modelsDirField) {
                modelsDirField.value = data.path;
                markUnsaved('models-dir');
                await saveSetting('MODELS_LLM_DIR', data.path, false, false, 'models-dir');
                showToast(t('ui.launcher.button.folder_selected', 'Папка выбрана'), 'success', 1500);
            }
        } else {
            if (data.error && !data.error.includes("не выбрана")) {
                showToast(data.error || t('ui.launcher.button.folder_select_failed', 'Не удалось выбрать папку'), 'error');
            }
        }
    } catch (e) {
        showToast(t('ui.launcher.button.folder_select_failed', 'Не удалось выбрать папку') + ': ' + (e as Error).message, 'error');
    }
}

/**
 * Paste SD models directory from clipboard
 */
export async function pasteSdModelsDir(): Promise<void> {
    try {
        const text = await navigator.clipboard.readText();
        const modelsDirField = document.getElementById('field-sd-models-dir') as HTMLInputElement | null;
        if (modelsDirField) {
            modelsDirField.value = text;
            markUnsaved('sd-models-dir');
            showToast(t('ui.launcher.button.pasted', 'Путь вставлен'), 'success', 1500);
        }
    } catch (e) {
        showToast(t('ui.launcher.button.paste_failed', 'Не удалось вставить'), 'error');
    }
}

/**
 * Select SD models folder via Windows dialog
 */
export async function selectSdModelsFolder(): Promise<void> {
    try {
        showToast(t('ui.launcher.button.opening_folder_dialog', 'Открывается диалог выбора папки...'), 'info', 1000);
        const res = await fetch('/api/select_folder', { method: 'POST' });
        const data = await res.json();
        if (data.ok && data.path) {
            const modelsDirField = document.getElementById('field-sd-models-dir') as HTMLInputElement | null;
            if (modelsDirField) {
                modelsDirField.value = data.path;
                markUnsaved('sd-models-dir');
                await saveSetting('MODELS_SD_DIR', data.path, false, false, 'sd-models-dir');
                showToast(t('ui.launcher.button.folder_selected', 'Папка выбрана'), 'success', 1500);
            }
        } else {
            if (data.error && !data.error.includes("не выбрана")) {
                showToast(data.error || t('ui.launcher.button.folder_select_failed', 'Не удалось выбрать папку'), 'error');
            }
        }
    } catch (e) {
        showToast(t('ui.launcher.button.folder_select_failed', 'Не удалось выбрать папку') + ': ' + (e as Error).message, 'error');
    }
}

// Register on window for backward compatibility
window.pasteModelsDir = pasteModelsDir;
window.selectModelsFolder = selectModelsFolder;
window.pasteSdModelsDir = pasteSdModelsDir;
window.selectSdModelsFolder = selectSdModelsFolder;
