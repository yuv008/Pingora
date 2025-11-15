import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import '@/styles/globals.css';
import { Providers } from '@/components/providers';
import { Toaster } from '@/components/ui/toaster';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: {
    default: 'API Monitor Platform',
    template: '%s | API Monitor Platform',
  },
  description: 'Production-ready API monitoring with real-time alerts and 3D visualizations',
  keywords: [
    'API monitoring',
    'uptime monitoring',
    'performance monitoring',
    'real-time alerts',
    'incident management',
  ],
  authors: [{ name: 'API Monitor Team' }],
  creator: 'API Monitor Platform',
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: process.env.NEXT_PUBLIC_APP_URL,
    title: 'API Monitor Platform',
    description: 'Production-ready API monitoring with real-time alerts and 3D visualizations',
    siteName: 'API Monitor Platform',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'API Monitor Platform',
    description: 'Production-ready API monitoring with real-time alerts and 3D visualizations',
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <Providers>
          {children}
          <Toaster />
        </Providers>
      </body>
    </html>
  );
}
