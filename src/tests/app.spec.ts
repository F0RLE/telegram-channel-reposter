import { test, expect } from '@playwright/test';

/**
 * Flux Platform E2E Tests
 * Testing basic navigation and UI functionality
 */

test.describe('Flux Platform', () => {
    test.beforeEach(async ({ page }) => {
        // Navigate to app and wait for splash to disappear
        await page.goto('/');
        // Wait for splash screen to fade out
        await page.waitForSelector('#splash-screen', { state: 'hidden', timeout: 10000 });
    });

    test.describe('Page Load', () => {
        test('should load the main page with sidebar', async ({ page }) => {
            // Sidebar should be present
            await expect(page.locator('#sidebar')).toBeAttached();

            // Home page should be active
            await expect(page.locator('#page-home')).toBeAttached();
        });

        test('should load SVG icons from external sprite', async ({ page }) => {
            // Check that icon sprite container was injected
            await expect(page.locator('#svg-icons-sprite')).toBeAttached();

            // At least one icon should be using the sprite
            const iconUse = page.locator('svg use[href^="#icon-"]').first();
            await expect(iconUse).toBeAttached();
        });

        test('should initialize event handlers', async ({ page }) => {
            // Check console for event handler initialization message
            const logs: string[] = [];
            page.on('console', msg => logs.push(msg.text()));

            // Reload to capture initialization
            await page.reload();
            await page.waitForSelector('#splash-screen', { state: 'hidden', timeout: 10000 });

            // Should have initialized event handlers
            expect(logs.some(log => log.includes('[EventHandlers]'))).toBeTruthy();
        });
    });

    test.describe('Sidebar Navigation', () => {
        test('should navigate to chat page', async ({ page }) => {
            // Click on Chat nav item
            const chatBtn = page.locator('.nav-btn[data-page="chat"]');
            await chatBtn.click();

            // Chat page should be visible
            await expect(page.locator('#page-chat')).toBeVisible();
            await expect(page.locator('#chat-container')).toBeVisible();
        });

        test('should navigate to modules page', async ({ page }) => {
            const modulesBtn = page.locator('.nav-btn[data-page="modules"]');
            await modulesBtn.click();

            await expect(page.locator('#page-modules')).toBeVisible();
        });

        test('should navigate to settings page', async ({ page }) => {
            const settingsBtn = page.locator('.nav-btn[data-page="settings"]');
            await settingsBtn.click();

            await expect(page.locator('#page-settings')).toBeVisible();
        });

        test('should navigate to console page', async ({ page }) => {
            const consoleBtn = page.locator('.nav-btn[data-page="debug"]');
            await consoleBtn.click();

            await expect(page.locator('#page-debug')).toBeVisible();
            await expect(page.locator('#console-container')).toBeVisible();
        });

        test('should navigate to downloads page', async ({ page }) => {
            const downloadsBtn = page.locator('.nav-btn[data-page="downloads"]');
            await downloadsBtn.click();

            await expect(page.locator('#page-downloads')).toBeVisible();
        });

        test('should navigate back to home', async ({ page }) => {
            // Go to chat first
            await page.locator('.nav-btn[data-page="chat"]').click();
            await expect(page.locator('#page-chat')).toBeVisible();

            // Go back to home
            await page.locator('.nav-btn[data-page="home"]').click();
            await expect(page.locator('#page-home')).toBeVisible();
        });
    });

    test.describe('Language Switcher', () => {
        test('should toggle language menu', async ({ page }) => {
            // Language menu items should be collapsed initially
            const langMenu = page.locator('#lang-menu-items');

            // Click language trigger
            const langTrigger = page.locator('#current-lang-trigger');
            await langTrigger.click();

            // Menu should expand (has 'open' class or visible)
            await expect(langMenu).toBeVisible();
        });
    });
});
