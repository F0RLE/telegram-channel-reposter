/**
 * Flux Platform - Main Application Entry Point
 * @module app
 */

// ============================================
// Core Imports
// ============================================

// Initialize Tauri bridge first (sets up window.electronAPI and fetch interceptor)
import './lib/tauri';

// Initialize window management
import './lib/window';

// Initialize internationalization
import './i18n';

// ============================================
// Feature Imports
// ============================================

import './features/chat/chat';
import './features/downloads/downloads';
import './features/modules/modules';
import './features/settings/settings';
import './features/debug/debug';
import './features/monitoring/monitoring';

// ============================================
// Component Imports
// ============================================

import './components/sidebar/sidebar';
import './components/toast/toast';
import './components/effects/particles';

// ============================================
// Utility Imports
// ============================================

import './lib/utils/dom';
import './lib/utils/sound';
import './lib/data/settings';

// ============================================
// Application Initialization
// ============================================

console.log('[Flux Platform] Application initialized');
