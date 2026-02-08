/** @type {import('tailwindcss').Config} */
module.exports = {
    darkMode: 'class',
    content: [
        './pages/**/*.{js,ts,jsx,tsx,mdx}',
        './components/**/*.{js,ts,jsx,tsx,mdx}',
        './app/**/*.{js,ts,jsx,tsx,mdx}',
    ],
    theme: {
        extend: {
            colors: {
                // Cyberpunk color palette
                cyber: {
                    black: '#0a0a0f',
                    dark: '#0f0f1a',
                    darker: '#1a1a2e',
                    primary: '#00ffff',    // Cyan
                    secondary: '#ff00ff',  // Magenta
                    accent: '#ffff00',     // Yellow
                    success: '#00ff88',    // Green
                    warning: '#ffaa00',    // Orange
                    error: '#ff3366',      // Red
                    muted: '#4a4a6a',
                },
            },
            fontFamily: {
                mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
                display: ['Orbitron', 'sans-serif'],
            },
            animation: {
                'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
                'glow': 'glow 2s ease-in-out infinite alternate',
                'scan': 'scan 8s linear infinite',
                'flicker': 'flicker 0.15s infinite',
            },
            keyframes: {
                glow: {
                    '0%': { boxShadow: '0 0 5px #00ffff, 0 0 10px #00ffff' },
                    '100%': { boxShadow: '0 0 10px #00ffff, 0 0 20px #00ffff, 0 0 30px #00ffff' },
                },
                scan: {
                    '0%': { backgroundPosition: '0% 0%' },
                    '100%': { backgroundPosition: '0% 100%' },
                },
                flicker: {
                    '0%, 100%': { opacity: '1' },
                    '50%': { opacity: '0.8' },
                },
            },
            boxShadow: {
                'neon-cyan': '0 0 10px #00ffff, 0 0 20px #00ffff',
                'neon-magenta': '0 0 10px #ff00ff, 0 0 20px #ff00ff',
                'neon-green': '0 0 10px #00ff88, 0 0 20px #00ff88',
            },
        },
    },
    plugins: [],
};
