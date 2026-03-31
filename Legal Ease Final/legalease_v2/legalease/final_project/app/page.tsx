'use client'
import { useAuth } from '@/components/auth-provider'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Scale, Plus, Clock, CheckCircle, AlertCircle, FileText, Trash2, ChevronRight, ShieldAlert, Shield, ShieldCheck, Search } from 'lucide-react'
import { ThemeToggle } from '@/components/theme-toggle'

interface Document { id: string; name: string; page_count: number }
interface Case {
  id: string; title: string; status: string; created_at: string;
  summary?: string; risk_score?: number; risk_explanation?: string;
  documents: Document[]
}

export default function DashboardPage() {
  const [cases, setCases] = useState<Case[]>([])
  const [loading, setLoading] = useState(true)
  const { user } = useAuth()
  const displayName = user?.user_metadata?.full_name ?? user?.email ?? 'User'

  const fetchCases = () => {
    fetch('/api/cases')
      .then(r => r.json())
      .then(d => setCases(d.cases ?? []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchCases() }, [])

  const deleteCase = async (e: React.MouseEvent, id: string) => {
    e.preventDefault()
    e.stopPropagation()
    await fetch(`/api/cases/${id}`, { method: 'DELETE' })
    setCases(c => c.filter(x => x.id !== id))
  }

  const statusBadge = (status: string) => {
    if (status === 'ready') return (
      <span className="flex items-center gap-1.5 text-xs font-medium text-emerald-400 bg-emerald-400/10 px-2.5 py-1 rounded-full">
        <CheckCircle className="w-3 h-3" /> Ready
      </span>
    )
    if (status === 'processing') return (
      <span className="flex items-center gap-1.5 text-xs font-medium text-amber-400 bg-amber-400/10 px-2.5 py-1 rounded-full">
        <Clock className="w-3 h-3 animate-pulse" /> Processing
      </span>
    )
    return (
      <span className="flex items-center gap-1.5 text-xs font-medium text-red-400 bg-red-400/10 px-2.5 py-1 rounded-full">
        <AlertCircle className="w-3 h-3" /> Error
      </span>
    )
  }

  const riskBadge = (score?: number) => {
    if (!score) return null
    if (score <= 3) return (
      <span className="flex items-center gap-1 text-xs font-medium text-emerald-400 bg-emerald-400/10 px-2 py-0.5 rounded-full" title={`Risk: ${score}/10`}>
        <ShieldCheck className="w-3 h-3" /> {score}/10
      </span>
    )
    if (score <= 6) return (
      <span className="flex items-center gap-1 text-xs font-medium text-amber-400 bg-amber-400/10 px-2 py-0.5 rounded-full" title={`Risk: ${score}/10`}>
        <Shield className="w-3 h-3" /> {score}/10
      </span>
    )
    return (
      <span className="flex items-center gap-1 text-xs font-medium text-red-400 bg-red-400/10 px-2 py-0.5 rounded-full" title={`Risk: ${score}/10`}>
        <ShieldAlert className="w-3 h-3" /> {score}/10
      </span>
    )
  }

  return (
    <div className="min-h-screen bg-background">

      {/* ── HEADER ── */}
      <header className="border-b border-border/50 bg-card/30 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">

          {/* LEFT: logo + name + divider + user */}
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-primary/20 border border-primary/30 flex items-center justify-center">
              <Scale className="w-4 h-4 text-primary" />
            </div>
            <div>
              <p className="text-sm font-semibold tracking-tight">LegalEase AI</p>
              <p className="text-xs text-muted-foreground">Document Intelligence</p>
            </div>

            {/* Divider */}
            <div className="w-px h-6 bg-border/60 mx-1" />

            {/* User avatar + name — inline with logo (was in red box) */}
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-full bg-primary/20 border border-primary/30 flex items-center justify-center">
                <span className="text-xs font-semibold text-primary">
                  {displayName.charAt(0).toUpperCase()}
                </span>
              </div>
              <span className="text-sm font-medium text-foreground/80 hidden sm:block">
                {displayName}
              </span>
            </div>
          </div>

          {/* RIGHT: theme toggle (green box) + New Case */}
          <div className="flex items-center gap-2 sm:gap-3">
            <ThemeToggle />
            <Link href="/cross-search">
              <button className="flex items-center gap-1.5 sm:gap-2 bg-secondary text-secondary-foreground border border-border/50 px-3 sm:px-4 py-1.5 sm:py-2 rounded-lg text-xs sm:text-sm font-medium hover:bg-secondary/80 transition-colors shrink-0">
                <Search className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                <span className="hidden sm:inline">Global Search</span>
              </button>
            </Link>
            <Link href="/upload">
              <button className="flex items-center gap-1.5 sm:gap-2 bg-primary text-primary-foreground px-3 sm:px-4 py-1.5 sm:py-2 rounded-lg text-xs sm:text-sm font-medium hover:bg-primary/90 transition-colors shrink-0">
                <Plus className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                <span className="hidden sm:inline">New Case</span>
              </button>
            </Link>
          </div>

        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-10">
        <div className="mb-10">
          <h1 className="text-3xl font-semibold tracking-tight mb-2">Case Library</h1>
          <p className="text-muted-foreground">Upload legal documents and interrogate them with AI.</p>
        </div>

        {cases.length > 0 && (
          <div className="grid grid-cols-3 gap-4 mb-10">
            {[
              { label: 'Total Cases', value: cases.length },
              { label: 'Ready', value: cases.filter(c => c.status === 'ready').length },
              { label: 'Documents', value: cases.reduce((n, c) => n + (c.documents?.length ?? 0), 0) },
            ].map(s => (
              <div key={s.label} className="bg-card border border-border/50 rounded-xl p-5">
                <p className="text-2xl font-semibold tabular-nums">{s.value}</p>
                <p className="text-xs text-muted-foreground mt-1">{s.label}</p>
              </div>
            ))}
          </div>
        )}

        {loading && (
          <div className="space-y-3">
            {[1,2,3].map(i => (
              <div key={i} className="h-20 bg-card border border-border/50 rounded-xl animate-pulse" />
            ))}
          </div>
        )}

        {!loading && cases.length === 0 && (
          <div className="border border-dashed border-border/60 rounded-2xl p-16 text-center">
            <div className="w-14 h-14 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center mx-auto mb-5">
              <Scale className="w-7 h-7 text-primary" />
            </div>
            <h2 className="text-lg font-semibold mb-2">No cases yet</h2>
            <p className="text-muted-foreground text-sm mb-6">Upload your first legal document to start analysing.</p>
            <Link href="/upload">
              <button className="flex items-center gap-2 bg-primary text-primary-foreground px-5 py-2.5 rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors mx-auto">
                <Plus className="w-4 h-4" />
                Upload Document
              </button>
            </Link>
          </div>
        )}

        <div className="space-y-3">
          {cases.map((c, i) => (
            <Link key={c.id} href={`/workspace?caseId=${c.id}`}>
              <div
                className="group bg-card border border-border/50 rounded-xl px-5 py-4 hover:border-primary/40 hover:bg-card/80 transition-all cursor-pointer animate-fade-up"
                style={{ animationDelay: `${i * 60}ms`, animationFillMode: 'both', opacity: 0 }}
              >
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-lg bg-secondary flex items-center justify-center shrink-0">
                    <FileText className="w-5 h-5 text-muted-foreground group-hover:text-primary transition-colors" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-sm truncate">{c.title}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {c.documents?.length ?? 0} doc{c.documents?.length !== 1 ? 's' : ''} · {new Date(c.created_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    {riskBadge(c.risk_score)}
                    {statusBadge(c.status)}
                  </div>
                  <ChevronRight className="w-4 h-4 text-muted-foreground group-hover:text-foreground transition-colors shrink-0" />
                  <button
                    onClick={(e) => deleteCase(e, c.id)}
                    className="opacity-0 group-hover:opacity-100 transition-opacity p-1.5 rounded-md hover:bg-destructive/20 hover:text-destructive text-muted-foreground"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
                {c.summary && (
                  <p className="text-xs text-muted-foreground mt-2.5 ml-14 line-clamp-2 leading-relaxed">{c.summary}</p>
                )}
              </div>
            </Link>
          ))}
        </div>
      </main>

      {/* ── FIXED BOTTOM-RIGHT: theme toggle floating (purple box) ── */}
      {/* Already handled in header (green box). 
          If you ALSO want it bottom-right, uncomment this block: */}
      {/*
      <div className="fixed bottom-6 right-6 z-50">
        <ThemeToggle />
      </div>
      */}

    </div>
  )
}