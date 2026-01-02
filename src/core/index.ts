/**
 * Core Module - Centralized exports
 *
 * Usage:
 *   import { invoke, systemStats, t } from '@core';
 */

// API (Tauri bridge)
export * from './api';

// State (Signals)
export * from './state';

// Events (System stats, etc.)
export * from './events';

// i18n - re-export everything from the module
export * from './i18n';
