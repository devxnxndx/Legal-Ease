'use client'
import { useTheme } from 'next-themes'
import { Sun, Moon } from 'lucide-react'
import { useEffect, useState } from 'react'

export function ThemeToggle() {
  const { theme, setTheme } = useTheme()
  const [mounted, setMounted] = useState(false)
  useEffect(() => setMounted(true), [])
  if (!mounted) return null  // avoid hydration mismatch

  return (
    <button
      onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
      className="p-2 rounded-lg border border-border/50 bg-card/50 hover:bg-accent transition-colors"
      aria-label="Toggle theme"
    >
      {theme === 'dark'
        ? <Sun className="w-4 h-4 text-muted-foreground" />
        : <Moon className="w-4 h-4 text-muted-foreground" />}
    </button>
  )
}