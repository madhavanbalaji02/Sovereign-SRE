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
                // Design tokens. Token names kept as `cyber-*` so existing
                // class names keep working; values are a neutral slate base
                // with a single blue accent and semantic status colours.
                cyber: {
                    black: '#0A0C10',      // page background
                    dark: '#0F1218',       // inset surfaces (code, logs, inputs)
                    darker: '#151922',     // raised surfaces
                    border: '#232937',     // default hairline border
                    text: '#E6E9EF',       // primary text
                    primary: '#6AA6FF',    // brand accent (links, focus, active)
                    'primary-strong': '#2F6FEB', // filled primary buttons
                    secondary: '#A78BFA',  // AI / agent accent
                    accent: '#38BDF8',     // info / secondary data accent
                    success: '#3DD68C',
                    warning: '#F5B544',
                    error: '#F2555A',
                    muted: '#8A94A6',      // secondary text
                    subtle: '#5C667A',     // tertiary text, icons
                },
            },
            fontFamily: {
                sans: ['var(--font-sans)', 'Inter', 'system-ui', 'sans-serif'],
                display: ['var(--font-sans)', 'Inter', 'system-ui', 'sans-serif'],
                mono: ['var(--font-mono)', 'JetBrains Mono', 'ui-monospace', 'monospace'],
            },
            boxShadow: {
                card: '0 1px 0 0 rgba(255,255,255,0.03) inset, 0 1px 2px rgba(0,0,0,0.4)',
                pop: '0 8px 30px rgba(0,0,0,0.45)',
            },
            animation: {
                'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
            },
        },
    },
    plugins: [],
};
