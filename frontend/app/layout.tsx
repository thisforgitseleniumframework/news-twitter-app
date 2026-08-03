import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'NewsPost — News to Twitter',
  description: 'Fetch global & India news, generate AI tweet drafts, post to X',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
