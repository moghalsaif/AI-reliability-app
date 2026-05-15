import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'AI Reliability Lab',
  description: 'Reliability Engineering for AI Agents',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark">
      <body className={inter.className}>
        <div className="min-h-screen bg-background">
          <nav className="border-b border-border px-6 py-4">
            <div className="flex items-center justify-between max-w-7xl mx-auto">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
                  <span className="text-primary-foreground font-bold text-sm">RL</span>
                </div>
                <h1 className="text-lg font-semibold">AI Reliability Lab</h1>
              </div>
              <div className="flex gap-6 text-sm text-muted-foreground">
                <a href="/" className="hover:text-foreground transition-colors">Traces</a>
                <a href="/reflections" className="hover:text-foreground transition-colors">Reflections</a>
                <a href="/reliability" className="hover:text-foreground transition-colors">Reliability</a>
                <a href="/benchmarks" className="hover:text-foreground transition-colors">Benchmarks</a>
              </div>
            </div>
          </nav>
          <main className="max-w-7xl mx-auto px-6 py-8">
            {children}
          </main>
        </div>
      </body>
    </html>
  )
}
