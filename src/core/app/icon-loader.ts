/**
 * Icon Loader - Loads external SVG sprite and injects into DOM
 * This enables using external SVG icons with <use href="#icon-name">
 */

const ICONS_PATH = '/assets/icons.svg';

/**
 * Loads the SVG sprite file and injects it into the document body.
 * Icons can then be used with: <svg class="icon"><use href="#icon-name"></use></svg>
 */
export async function loadIcons(): Promise<void> {
    try {
        const response = await fetch(ICONS_PATH);
        if (!response.ok) {
            console.error(`[IconLoader] Failed to load icons: ${response.status}`);
            return;
        }

        const svgText = await response.text();

        // Create a container div and inject the SVG content
        const container = document.createElement('div');
        container.id = 'svg-icons-sprite';
        container.style.display = 'none';
        container.innerHTML = svgText;

        // Insert at the beginning of body for early availability
        document.body.insertBefore(container, document.body.firstChild);

        console.log('[IconLoader] Icons loaded successfully');
    } catch (error) {
        console.error('[IconLoader] Error loading icons:', error);
    }
}

/**
 * Initialize icon loader when DOM is ready
 */
export function initIconLoader(): void {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => loadIcons());
    } else {
        loadIcons();
    }
}
