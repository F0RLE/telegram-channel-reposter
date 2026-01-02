
declare global {
    interface Window {
        showPage: (pageId: string, btn?: HTMLElement | null) => void;
        updateActiveNavButton: (pageId: string) => void;
        initNavigation: () => void;
    }
}

// Global showPage function
window.showPage = function(pageId: string, btn: HTMLElement | null = null): void {
    console.log('[Navigation] Showing page:', pageId);

    // Hide all pages
    document.querySelectorAll('.page').forEach(page => {
        (page as HTMLElement).classList.remove('active');
        (page as HTMLElement).style.display = 'none';
    });

    // Show target page
    const targetPage = document.getElementById('page-' + pageId);
    if (targetPage) {
        targetPage.style.display = 'block';
        // Small delay to allow display:block to apply before adding class for animation (if any)
        requestAnimationFrame(() => {
            targetPage.classList.add('active');
        });

        // Save current page
        localStorage.setItem('last_page', pageId);

        // Update window title if needed
        // document.title = `Flux Platform - ${pageId}`;
    } else {
        console.error('[Navigation] Page not found:', pageId);
    }

    // Update sidebar buttons
    window.updateActiveNavButton(pageId);
};

window.updateActiveNavButton = function(pageId: string): void {
    document.querySelectorAll('.nav-btn').forEach(b => {
        b.classList.remove('active');
        if (b.getAttribute('data-page') === pageId) {
            b.classList.add('active');
        }
    });
};

window.initNavigation = function(): void {
    // Add click handlers to sidebar buttons
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const pageId = btn.getAttribute('data-page');
            if (pageId) {
                window.showPage(pageId, btn as HTMLElement);
            }
        });
    });

    // Restore last page or default to home
    const lastPage = localStorage.getItem('last_page') || 'home';
    window.showPage(lastPage);
};

// Auto-init on load
document.addEventListener('DOMContentLoaded', () => {
    window.initNavigation();
});

export {}; // Make it a module
