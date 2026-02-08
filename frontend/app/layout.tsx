import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
    title: 'Sovereign-SRE | Self-Healing Infrastructure',
    description: 'Autonomous SRE system that detects, diagnoses, and fixes infrastructure issues',
    keywords: ['SRE', 'DevOps', 'AI', 'Automation', 'Infrastructure'],
};

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <html lang="en" className="dark" suppressHydrationWarning>
            <body className="min-h-screen bg-cyber-black antialiased" suppressHydrationWarning>
                {children}
            </body>
        </html>
    );
}
