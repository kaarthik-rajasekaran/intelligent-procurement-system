import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Intelligent Procurement Management System',
  description: 'Deterministic + Analytical + Generative Procurement Workflow Automation',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="font-sans antialiased text-slate-800 bg-slate-50 min-h-screen">
        {children}
      </body>
    </html>
  );
}
