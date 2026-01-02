import {
    isPermissionGranted,
    requestPermission,
    sendNotification as sendTauriNotification
} from '@tauri-apps/plugin-notification';
import { register, isRegistered } from '@tauri-apps/plugin-global-shortcut';
import { open, save } from '@tauri-apps/plugin-dialog';
import { getCurrentWindow } from '@tauri-apps/api/window';

/**
 * Native API Facade
 * Centralizes access to native OS capabilities
 */
export const NativeAPI = {
    /**
     * Send a native system notification
     */
    async sendNotification(title: string, body: string): Promise<void> {
        try {
            let permissionGranted = await isPermissionGranted();
            if (!permissionGranted) {
                const permission = await requestPermission();
                permissionGranted = permission === 'granted';
            }

            if (permissionGranted) {
                sendTauriNotification({ title, body });
            }
        } catch (e) {
            console.error('[NativeAPI] Notification error:', e);
        }
    },

    /**
     * Register global shortcuts
     */
    /**
     * Register global shortcuts
     * Now handled by Rust backend for reliability
     */
    async registerShortcuts(): Promise<void> {
        // Handled in src-tauri/src/lib.rs
        console.log('[NativeAPI] Shortcuts managed by backend');
    },

    /**
     * Open native file dialog
     */
    async openFileDialog(options: { multiple?: boolean, directory?: boolean, filters?: any[] } = {}): Promise<string | string[] | null> {
        try {
            const selected = await open({
                multiple: options.multiple,
                directory: options.directory,
                filters: options.filters
            });
            return selected;
        } catch (e) {
            console.error('[NativeAPI] Dialog error:', e);
            return null;
        }
    }
};
