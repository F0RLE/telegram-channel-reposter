interface Particle {
    x: number;
    y: number;
    vx: number;
    vy: number;
    size: number;
    color: string;
}

class CyberpunkParticles {
    private canvas: HTMLCanvasElement;
    private ctx: CanvasRenderingContext2D;
    private particles: Particle[] = [];
    private mouse = { x: -100, y: -100 };
    private width = 0;
    private height = 0;

    constructor() {
        this.canvas = document.createElement('canvas');
        this.ctx = this.canvas.getContext('2d')!;
        document.body.appendChild(this.canvas);

        this.canvas.style.position = 'fixed';
        this.canvas.style.top = '0';
        this.canvas.style.left = '0';
        this.canvas.style.width = '100%';
        this.canvas.style.height = '100%';
        this.canvas.style.pointerEvents = 'none'; // Click-through
        this.canvas.style.zIndex = '-1'; // Behind everything
        this.canvas.style.filter = 'blur(4px)'; // underwater/dreamy effect

        this.resize();
        this.init();

        window.addEventListener('resize', () => this.resize());
        window.addEventListener('mousemove', (e) => {
            this.mouse.x = e.clientX;
            this.mouse.y = e.clientY;
        });

        this.animate();
    }

    resize() {
        this.width = window.innerWidth;
        this.height = window.innerHeight;
        this.canvas.width = this.width;
        this.canvas.height = this.height;
    }

    init() {
        // Create particles
        const particleCount = Math.floor((this.width * this.height) / 15000); // Density
        for (let i = 0; i < particleCount; i++) {
            this.particles.push({
                x: Math.random() * this.width,
                y: Math.random() * this.height,
                vx: (Math.random() - 0.5) * 0.2, // Slower speed
                vy: (Math.random() - 0.5) * 0.2,
                size: Math.random() * 2 + 0.5,
                color: Math.random() > 0.5 ? 'rgba(138, 43, 226, 0.3)' : 'rgba(93, 220, 255, 0.3)' // Primary & Cyan
            });
        }
    }

    animate() {
        this.ctx.clearRect(0, 0, this.width, this.height);

        this.particles.forEach(p => {
            // Update position
            p.x += p.vx;
            p.y += p.vy;

            // Mouse interaction (repel)
            const dx = this.mouse.x - p.x;
            const dy = this.mouse.y - p.y;
            const dist = Math.sqrt(dx * dx + dy * dy);
            const maxDist = 150;

            if (dist < maxDist) {
                const force = (maxDist - dist) / maxDist;
                const angle = Math.atan2(dy, dx);
                p.vx -= Math.cos(angle) * force * 0.05;
                p.vy -= Math.sin(angle) * force * 0.05;
            }

            // Wrap around screen
            if (p.x < 0) p.x = this.width;
            if (p.x > this.width) p.x = 0;
            if (p.y < 0) p.y = this.height;
            if (p.y > this.height) p.y = 0;

            // Draw
            this.ctx.beginPath();
            this.ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
            this.ctx.fillStyle = p.color;
            this.ctx.fill();

            // Connect nearby particles (grid effect)
            this.particles.forEach(p2 => {
                const dx2 = p.x - p2.x;
                const dy2 = p.y - p2.y;
                const dist2 = Math.sqrt(dx2 * dx2 + dy2 * dy2);
                if (dist2 < 100) {
                    this.ctx.beginPath();
                    this.ctx.moveTo(p.x, p.y);
                    this.ctx.lineTo(p2.x, p2.y);
                    this.ctx.strokeStyle = `rgba(138, 43, 226, ${0.1 - dist2 / 1000})`;
                    this.ctx.stroke();
                }
            });
        });

        requestAnimationFrame(() => this.animate());
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new CyberpunkParticles();
});
