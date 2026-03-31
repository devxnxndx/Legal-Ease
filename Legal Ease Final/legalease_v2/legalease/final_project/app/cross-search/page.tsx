'use client'

import { useState, useRef, useEffect, Suspense } from 'react'
import Link from 'next/link'
import {
  ArrowLeft, Search, Loader2, Scale, BookOpen
} from 'lucide-react'
import { toast } from 'sonner'
import { VoiceSettings } from '@/components/voice-settings'

interface Source {
  chunk_id: string
  page: number
  snippet: string
  document_name: string
}

interface Message {
  role: 'user' | 'ai'
  content: string
  sources?: Source[]
}

export default function CrossSearchPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [chatStatus, setChatStatus] = useState('Searching all documents…')

  const bottomRef = useRef<HTMLDivElement>(null)
  const isFirstLoad = useRef(true)

  useEffect(() => {
    if (isFirstLoad.current && messages.length > 0) {
      bottomRef.current?.scrollIntoView({ behavior: 'auto' })
      isFirstLoad.current = false
    } else {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages])

  const sendMessage = async (text: string) => {
    if (!text.trim() || sending) return

    const history = messages.map(m => ({ role: m.role, content: m.content }))

    setMessages(m => [...m, { role: 'user', content: text.trim() }])
    setInput('')
    setSending(true)
    setChatStatus('Searching all documents…')

    try {
      const res = await fetch(`/api/search/cross-case`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text.trim(), history }),
      })

      if (!res.ok) {
        throw new Error('Search failed')
      }
      
      if (!res.body) {
        throw new Error('No response body from server')
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()

      let buffer = ''
      let aiText = ''
      let sources: Source[] = []
      let aiAdded = false

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue

          try {
            const ev = JSON.parse(line.slice(6))

            if (ev.type === 'status') {
              setChatStatus(ev.message ?? 'Working…')
            } else if (ev.type === 'sources') {
              sources = ev.sources ?? []
              setChatStatus('Generating answer…')
            } else if (ev.type === 'token') {
              if (!aiAdded) {
                setMessages(m => [...m, { role: 'ai', content: '', sources }])
                aiAdded = true
              }
              aiText += ev.token
              setMessages(m => {
                const u = [...m]
                u[u.length - 1] = { role: 'ai', content: aiText, sources }
                return u
              })
            } else if (ev.type === 'error') {
              toast.error(ev.error)
            } else if (ev.type === 'done') {
              setChatStatus('Done')
            }
          } catch {
            // ignore malformed SSE chunks
          }
        }
      }
    } catch (e: any) {
      toast.error(e.message ?? 'Error getting response')
    } finally {
      setSending(false)
      setChatStatus('Searching all documents…')
    }
  }

  return (
    <div className="h-screen flex flex-col bg-background">
      {/* Header */}
      <header className="border-b border-border/50 bg-card/30 backdrop-blur-sm shrink-0">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-3 flex items-center gap-2 sm:gap-4">
          <Link href="/">
            <button className="flex items-center gap-1.5 sm:gap-2 text-xs sm:text-sm text-muted-foreground hover:text-foreground transition-colors">
              <ArrowLeft className="w-4 h-4" /> <span className="hidden sm:inline">Dashboard</span>
            </button>
          </Link>

          <div className="w-px h-4 bg-border hidden sm:block" />

          <div className="flex items-center gap-2">
            <Scale className="w-4 h-4 text-primary" />
            <span className="text-sm font-medium">Global Search</span>
          </div>

          <div className="ml-auto flex items-center">
             <span className="text-xs text-muted-foreground mr-1 hidden sm:block">Cross-Case AI Engine</span>
          </div>
        </div>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-6 space-y-6">
          {messages.length === 0 && (
            <div className="py-12 text-center animate-fade-in">
              <div className="w-14 h-14 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center mx-auto mb-5">
                <Search className="w-7 h-7 text-primary" />
              </div>
              <h2 className="text-lg font-semibold mb-2">Cross-Case Search</h2>
              <p className="text-muted-foreground text-sm max-w-sm mx-auto">
                Ask a question and LegalEase will scan ALL your uploaded cases and documents simultaneously to provide an aggregated answer.
              </p>
            </div>
          )}

          {messages.map((m, i) => (
            <div
              key={i}
              className={`flex gap-3 ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {m.role === 'ai' && (
                <div className="w-7 h-7 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center shrink-0 mt-0.5">
                  <Scale className="w-3.5 h-3.5 text-primary" />
                </div>
              )}

              <div
                className={`max-w-[85%] sm:max-w-[78%] space-y-2 flex flex-col ${m.role === 'user' ? 'items-end' : 'items-start'}`}
              >
                <div
                  className={`rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap ${
                    m.role === 'user'
                      ? 'bg-primary text-primary-foreground rounded-br-sm'
                      : 'bg-card border border-border/50 rounded-bl-sm'
                  }`}
                >
                  {m.content}
                  {m.role === 'ai' && (
                    <div className="mt-2">
                      <VoiceSettings text={m.content} />
                    </div>
                  )}
                </div>

                {m.role === 'ai' && m.sources && m.sources.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {m.sources.map((s, si) => (
                      <span
                        key={si}
                        className="text-xs bg-secondary border border-border/40 text-muted-foreground rounded-lg px-2.5 py-1 flex items-center gap-1.5 max-w-full truncate"
                        title={s.snippet}
                      >
                        <BookOpen className="w-3 h-3 shrink-0" />
                        <span className="truncate">{s.document_name}</span>
                        <span className="opacity-60 ml-1 shrink-0">p.{s.page}</span>
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}

          {sending && messages[messages.length - 1]?.role !== 'ai' && (
            <div className="flex gap-3 animate-fade-in">
              <div className="w-7 h-7 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center shrink-0">
                <Scale className="w-3.5 h-3.5 text-primary" />
              </div>
              <div className="bg-card border border-border/50 rounded-2xl rounded-bl-sm px-4 py-3">
                <div className="flex gap-1.5 items-center h-4">
                  <span className="text-xs text-muted-foreground mr-2">{chatStatus}</span>
                  {[0, 1, 2].map(i => (
                    <div
                      key={i}
                      className="w-1.5 h-1.5 rounded-full bg-primary/60 animate-bounce"
                      style={{ animationDelay: `${i * 0.15}s` }}
                    />
                  ))}
                </div>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </div>

      {/* Input Bar */}
      <div className="border-t border-border/50 bg-card/30 backdrop-blur-sm shrink-0 px-4 sm:px-6 py-3 sm:py-4">
        <div className="max-w-4xl mx-auto">
          <div style={{ fontSize: "12px", color: "#666", marginBottom: "8px", paddingLeft: "4px" }}>
            This tool explains legal documents. It does not provide legal advice.
          </div>
          <div className="flex gap-2 sm:gap-3 items-end bg-card border border-border/60 rounded-2xl px-4 py-3 focus-within:border-primary/50 focus-within:ring-1 focus-within:ring-primary/20 transition-all">
            <textarea
              className="flex-1 bg-transparent text-sm placeholder:text-muted-foreground resize-none outline-none max-h-40 leading-relaxed"
              placeholder="Search across all your cases..."
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  sendMessage(input)
                }
              }}
              rows={1}
            />

            <button
              onClick={() => sendMessage(input)}
              disabled={sending || !input.trim()}
              className="p-1.5 sm:p-2 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-40 disabled:cursor-not-allowed transition-all shrink-0"
              title="Send (Enter)"
            >
              {sending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Search className="w-4 h-4" />
              )}
            </button>
          </div>
          
          <p className="text-center text-xs text-muted-foreground mt-2 hidden sm:block">
            Enter to search · Shift+Enter for new line
          </p>
        </div>
      </div>
    </div>
  )
}
