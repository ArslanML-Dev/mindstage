import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "MindStage — The Classroom That Becomes Anything",
  description: "AI turns a teacher's notes into a live, cinematic lesson synced to every student's screen.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">
        <header className="border-b border-line">
          <nav className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4">
            <Link href="/" className="font-display text-xl tracking-wide">
              Mind<span className="text-gold">Stage</span>
            </Link>
            <div className="flex gap-5 text-sm text-mist">
              <Link href="/teach" className="hover:text-white">Teach</Link>
              <Link href="/join" className="hover:text-white">Join a class</Link>
            </div>
          </nav>
        </header>
        <main className="mx-auto max-w-6xl px-5 py-8">{children}</main>
      </body>
    </html>
  );
}
