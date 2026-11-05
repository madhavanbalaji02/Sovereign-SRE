import type { Metadata, Viewport } from 'next';
import { Inter, JetBrains_Mono } from 'next/font/google';
import './globals.css';

const sans = Inter({ subsets: ['latin'], variable: '--font-sans', display: 'swap' });
const mono = JetBrains_Mono({ subsets: ['latin'], variable: '--font-mono', display: 'swap' });

export const metadata: Metadata = {
    title: 'Sovereign-SRE · Autonomous incident response',
    description:
        'An AI agent pipeline on AWS that detects anomalies, diagnoses root causes, proposes code fixes and waits for human approval.',
    keywords: ['SRE', 'DevOps', 'AIOps', 'AWS Bedrock', 'LangGraph', 'Incident response'],
};

export const viewport: Viewport = {
    themeColor: '#0A0C10',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
    return (
        <html lang="en" className={`dark ${sans.variable} ${mono.variable}`} suppressHydrationWarning>
            <body className="min-h-screen bg-cyber-black font-sans text-cyber-text antialiased" suppressHydrationWarning>
                {children}
            </body>
        </html>
    );
}
