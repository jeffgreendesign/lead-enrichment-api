import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Lead Enrichment Dashboard",
  description: "Dashboard for the lead enrichment API",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-neutral-950 text-neutral-100 min-h-screen">
        <header className="border-b border-neutral-800 px-6 py-4">
          <div className="mx-auto flex max-w-7xl items-center justify-between">
            <h1 className="text-lg font-semibold tracking-tight">
              Lead Enrichment Dashboard
            </h1>
            <nav className="flex gap-4 text-sm text-neutral-400">
              <a
                href="https://github.com/jeffgreendesign/lead-enrichment-api"
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-neutral-100 transition-colors"
              >
                GitHub
              </a>
              <a
                href={`${process.env.LEAD_API_URL || ""}/docs`}
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-neutral-100 transition-colors"
              >
                API Docs
              </a>
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-7xl px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
