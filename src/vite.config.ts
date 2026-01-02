import { defineConfig } from 'vite'
import { fileURLToPath, URL } from 'node:url'

// https://vitejs.dev/config/
export default defineConfig({
    // Vite options tailored for Tauri development
    // prevent vite from obscuring rust errors
    clearScreen: false,

    // Tauri expects a fixed port, fail if that port is not available
    server: {
        port: 1420,
        strictPort: true,
        host: 'localhost',
        watch: {
            // tell vite to ignore watching `src-tauri`
            ignored: ['**/src-tauri/**', '**/backend/**'],
        },
    },

    // Path aliases
    resolve: {
        alias: {
            '@': fileURLToPath(new URL('./', import.meta.url)),
            '@app': fileURLToPath(new URL('./app', import.meta.url)),
            '@core': fileURLToPath(new URL('./core', import.meta.url)),
            '@features': fileURLToPath(new URL('./features', import.meta.url)),
            '@shared': fileURLToPath(new URL('./shared', import.meta.url)),
        }
    },

    // to access the Tauri environment variables set by the CLI with information about the current target
    envPrefix: ['VITE_', 'TAURI_'],

    build: {
        // Tauri uses Chromium on Windows and WebKit on macOS and Linux
        target: process.env.TAURI_PLATFORM === 'windows' ? 'chrome105' : 'safari13',
        // don't minify for debug builds
        minify: !process.env.TAURI_DEBUG ? 'esbuild' : false,
        // produce sourcemaps for debug builds
        sourcemap: !!process.env.TAURI_DEBUG,

        // Multi-page app configuration
        rollupOptions: {
            input: {
                main: fileURLToPath(new URL('./index.html', import.meta.url)),
                setup: fileURLToPath(new URL('./pages/setup.html', import.meta.url)),
                moduleSettings: fileURLToPath(new URL('./pages/module-settings.html', import.meta.url)),
            },
        },
    },
})

