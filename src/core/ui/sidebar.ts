
/**
 * Sidebar Logic with Visual Drag and Snap Animation
 * Uses CSS variables for layout synchronization to avoid jitter.
 */

export function initSidebar() {
    const sidebar = document.getElementById('sidebar');
    const handle = document.getElementById('sidebar-drag-handle');
    const appHeader = document.getElementById('app-header');

    if (!sidebar || !handle) return;

    // Constants
    const EXPANDED_WIDTH = 320;
    const COMPACT_WIDTH = 80;
    const SNAP_THRESHOLD = (EXPANDED_WIDTH + COMPACT_WIDTH) / 2;

    // Use CSS variable for sync
    const updateWidth = (width: number) => {
        document.documentElement.style.setProperty('--sidebar-width', `${width}px`);
    };

    // Helper to apply state
    const setCollapsed = (collapsed: boolean, animate: boolean = true) => {
        if (animate) {
            document.body.classList.add('snapping');
            setTimeout(() => document.body.classList.remove('snapping'), 300);
        } else {
            document.body.classList.remove('snapping');
        }

        if (collapsed) {
            sidebar.classList.add('collapsed');
            updateWidth(COMPACT_WIDTH);
            localStorage.setItem('sidebar_collapsed', 'true');
        } else {
            sidebar.classList.remove('collapsed');
            updateWidth(EXPANDED_WIDTH);
            localStorage.setItem('sidebar_collapsed', 'false');
        }
    };

    // Load saved state
    const savedState = localStorage.getItem('sidebar_collapsed') === 'true';
    setCollapsed(savedState, false);

    // Initial update
    updateWidth(savedState ? COMPACT_WIDTH : EXPANDED_WIDTH);

    let startX = 0;
    let startWidth = 0;
    let isDragging = false;
    let animationFrameId: number | null = null;

    // MOUSE DOWN
    handle.addEventListener('mousedown', (e) => {
        isDragging = true;
        startX = e.clientX;
        startWidth = sidebar.offsetWidth;

        // Kill transitions immediately
        document.body.classList.remove('snapping');
        sidebar.style.transition = 'none';
        if (appHeader) appHeader.style.transition = 'none';

        if (sidebar.classList.contains('collapsed')) {
            updateWidth(COMPACT_WIDTH);
            sidebar.classList.remove('collapsed');
        } else {
             updateWidth(startWidth);
        }

        document.body.style.cursor = 'col-resize';
        document.body.classList.add('no-select');
        handle.classList.add('dragging');
    });

    // MOUSE MOVE
    document.addEventListener('mousemove', (e) => {
        if (!isDragging) return;

        e.preventDefault();

        if (animationFrameId) cancelAnimationFrame(animationFrameId);

        animationFrameId = requestAnimationFrame(() => {
            const delta = e.clientX - startX;
            let newWidth = startWidth + delta;

            // Constraints
            if (newWidth < 60) newWidth = 60;
            if (newWidth > 450) newWidth = 450;

            // Visual update via CSS var
            updateWidth(newWidth);
        });
    });

    // MOUSE UP
    document.addEventListener('mouseup', (e) => {
        if (!isDragging) return;
        isDragging = false;
        if (animationFrameId) cancelAnimationFrame(animationFrameId);

        // Restore transitions
        sidebar.style.transition = '';
        if (appHeader) appHeader.style.transition = '';

        // Clear inline widths (though we use CSS vars mostly, just in case)
        sidebar.style.width = '';

        document.body.style.cursor = '';
        document.body.classList.remove('no-select');
        handle.classList.remove('dragging');

        // Decision logic
        const delta = e.clientX - startX;
        const DIRECTIONAL_THRESHOLD = 50;

        if (Math.abs(delta) < 5) {
            // Click -> Toggle
            // Check previous state implied by startWidth
            const isCompact = Math.abs(startWidth - COMPACT_WIDTH) < 20;
            setCollapsed(!isCompact, true);
        } else {
            // Drag Logic
            if (delta < -DIRECTIONAL_THRESHOLD) {
                // Dragged Left -> Collapse
                setCollapsed(true, true);
            } else if (delta > DIRECTIONAL_THRESHOLD) {
                // Dragged Right -> Expand
                setCollapsed(false, true);
            } else {
                // Weak drag -> Snap to nearest
                const currentWidth = sidebar.offsetWidth;
                if (currentWidth < SNAP_THRESHOLD) {
                    setCollapsed(true, true);
                } else {
                    setCollapsed(false, true);
                }
            }
        }
    });
}

// Auto-init
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSidebar);
} else {
    initSidebar();
}
