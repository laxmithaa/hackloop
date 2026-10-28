import type { Metadata } from 'next';
import './globals.css';
import { AppProvider } from '@/components/AppProvider';
export const metadata: Metadata = { title: 'Healthcare Bill Navigator', description: 'A simpler way to understand hospital bills.' };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="en"><body><AppProvider>{children}</AppProvider></body></html>; }
