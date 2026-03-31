import type { Metadata } from 'next'
import './globals.css'
import { Toaster } from 'sonner'
import { AuthProvider } from '@/components/auth-provider'
import { ThemeProvider } from 'next-themes'

export const metadata: Metadata = {
  title: 'LegalEase AI — Legal Document Analysis',
  description: 'AI-powered legal document analysis with Gemini',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body className="min-h-screen bg-background antialiased" suppressHydrationWarning>
      <ThemeProvider attribute="class" defaultTheme="dark" enableSystem={false}>
        <AuthProvider>
          {children}
        </AuthProvider>
        <Toaster
          theme="dark"
          richColors
          position="top-right"
          toastOptions={{
            style: { background: 'hsl(222 40% 11%)', border: '1px solid hsl(222 35% 18%)', color: 'hsl(210 40% 94%)' },
          }}
        />
        </ThemeProvider>
      </body>
    </html>
  )
}
