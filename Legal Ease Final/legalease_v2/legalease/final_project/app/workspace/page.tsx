'use client'

import { useEffect, useRef, useState, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import Link from 'next/link'
import {
  ArrowLeft, Send, Mic, MicOff, Loader2, Scale, BookOpen,
  Tag, Calendar, ShieldAlert, Shield, ShieldCheck, FileText, ChevronDown, ChevronUp,
  Paperclip
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

interface ClauseTag {
  id: string
  tag_type: string
  excerpt: string
  page_number: number
}

interface Deadline {
  id: string
  deadline_date: string
  event: string
  description: string
  page_number: number
}

interface CaseInfo {
  id: string
  title: string
  status: string
  summary?: string
  risk_score?: number
  risk_explanation?: string
}

async function parseApiResponse(res: Response) {
  const raw = await res.text()

  let data: any = {}
  try {
    data = raw ? JSON.parse(raw) : {}
  } catch {
    if (!res.ok) {
      throw new Error(raw || `Request failed with status ${res.status}`)
    }
    throw new Error('Server returned invalid JSON')
  }

  if (!res.ok) {
    throw new Error(
      data?.detail ||
      data?.error ||
      data?.message ||
      raw ||
      `Request failed with status ${res.status}`
    )
  }

  return data
}

const TAG_COLORS: Record<string, string> = {
  indemnity: 'bg-red-400/15 text-red-400 border-red-400/20',
  limitation_of_liability: 'bg-amber-400/15 text-amber-400 border-amber-400/20',
  termination: 'bg-orange-400/15 text-orange-400 border-orange-400/20',
  confidentiality: 'bg-violet-400/15 text-violet-400 border-violet-400/20',
  payment: 'bg-emerald-400/15 text-emerald-400 border-emerald-400/20',
  non_compete: 'bg-pink-400/15 text-pink-400 border-pink-400/20',
  ip_assignment: 'bg-cyan-400/15 text-cyan-400 border-cyan-400/20',
  dispute_resolution: 'bg-blue-400/15 text-blue-400 border-blue-400/20',
  force_majeure: 'bg-yellow-400/15 text-yellow-400 border-yellow-400/20',
  warranty: 'bg-lime-400/15 text-lime-400 border-lime-400/20',
  governing_law: 'bg-teal-400/15 text-teal-400 border-teal-400/20',
  data_protection: 'bg-indigo-400/15 text-indigo-400 border-indigo-400/20',
}

function formatTagType(t: string) {
  return t.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

function WorkspaceInner() {
  const searchParams = useSearchParams()
  const caseId = searchParams.get('caseId') ?? ''

  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [recording, setRecording] = useState(false)
  const [caseInfo, setCaseInfo] = useState<CaseInfo | null>(null)
  const [tags, setTags] = useState<ClauseTag[]>([])
  const [deadlines, setDeadlines] = useState<Deadline[]>([])
  const [showAnalysis, setShowAnalysis] = useState(true)
  const [uploadingDoc, setUploadingDoc] = useState(false)
  const [chatStatus, setChatStatus] = useState('Searching documents…')
  const [pdfUrl, setPdfUrl] = useState<string | null>(null)
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null)
  const [pdfPanelOpen, setPdfPanelOpen] = useState(true)

  const mediaRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const docFileRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (!caseId) return
    fetch(`/api/cases/${caseId}/chat`)
      .then(parseApiResponse)
      .then(d => {
        if (d.messages) {
          setMessages(
            d.messages.map((m: any) => ({
              role: m.role,
              content: m.content,
              sources: m.sources,
            }))
          )
        }
      })
      .catch(err => console.error('Failed to fetch chat history:', err))
  }, [caseId])

  useEffect(() => {
    if (!caseId) return
    fetch('/api/cases')
      .then(parseApiResponse)
      .then(d => {
        const c = (d.cases ?? []).find((x: any) => x.id === caseId)
        if (c) setCaseInfo(c)
      })
      .catch(err => console.error('Failed to fetch cases:', err))
  }, [caseId])

  useEffect(() => {
    if (!caseId) return
    fetch(`/api/cases/${caseId}/tags`)
      .then(parseApiResponse)
      .then(d => setTags(d.tags ?? []))
      .catch(err => console.error('Failed to fetch tags:', err))
  }, [caseId])

  useEffect(() => {
    if (!caseId) return
    fetch(`/api/cases/${caseId}/deadlines`)
      .then(parseApiResponse)
      .then(d => setDeadlines(d.deadlines ?? []))
      .catch(err => console.error('Failed to fetch deadlines:', err))
  }, [caseId])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    const ta = textareaRef.current
    if (!ta) return
    ta.style.height = 'auto'
    ta.style.height = Math.min(ta.scrollHeight, 160) + 'px'
  }, [input])

  const refetchCaseInfo = () => {
    fetch('/api/cases')
      .then(parseApiResponse)
      .then(d => {
        const c = (d.cases ?? []).find((x: any) => x.id === caseId)
        if (c) setCaseInfo(c)
      })
      .catch(err => console.error('Failed to refetch cases:', err))
  }

  const refetchTags = () => {
    fetch(`/api/cases/${caseId}/tags`)
      .then(parseApiResponse)
      .then(d => setTags(d.tags ?? []))
      .catch(err => console.error('Failed to refetch tags:', err))
  }

  const fetchPdfUrl = (documentId?: string) => {
    const docParam = documentId ? `?documentId=${documentId}` : ''
    fetch(`/api/cases/${caseId}/pdf${docParam}`)
      .then(parseApiResponse)
      .then(d => {
        if (d.url) setPdfUrl(d.url)
      })
      .catch(err => console.error('Failed to fetch PDF URL:', err))
  }

  const refetchDeadlines = () => {
    fetch(`/api/cases/${caseId}/deadlines`)
      .then(parseApiResponse)
      .then(d => setDeadlines(d.deadlines ?? []))
      .catch(err => console.error('Failed to refetch deadlines:', err))
  }

  useEffect(() => {
    if (!caseId || !caseInfo) return
    const docs = (caseInfo as any).documents
    if (docs && docs.length > 0) {
      const firstDoc = docs[0]
      setSelectedDocumentId(firstDoc.id)
      fetchPdfUrl(firstDoc.id)
    } else if (caseInfo) {
      fetchPdfUrl()
    }
  }, [caseId, caseInfo?.id])

  const uploadAdditionalDoc = async (file: File) => {
    if (!file || !caseId) return
    if (file.type !== 'application/pdf') {
      toast.error('Only PDF files are supported.')
      return
    }
    if (file.size > 50 * 1024 * 1024) {
      toast.error('File must be under 50 MB.')
      return
    }

    setUploadingDoc(true)
    try {
      const fd = new FormData()
      fd.append('caseId', caseId)
      fd.append('file', file)

      const res = await fetch('/api/cases/upload-doc', { method: 'POST', body: fd })
      const data = await parseApiResponse(res)

      toast.success(`Added "${file.name}" — ${data.chunkCount} chunks indexed.`)
      refetchCaseInfo()
      refetchTags()
      refetchDeadlines()
      if (data.documentId) {
        setSelectedDocumentId(data.documentId)
        fetchPdfUrl(data.documentId)
      }
    } catch (err: any) {
      toast.error(err.message ?? 'Failed to add document.')
    } finally {
      setUploadingDoc(false)
      if (docFileRef.current) docFileRef.current.value = ''
    }
  }

  const sendMessage = async (text: string) => {
    if (!text.trim() || !caseId || sending) return

    const history = messages.map(m => ({ role: m.role, content: m.content }))

    setMessages(m => [...m, { role: 'user', content: text.trim() }])
    setInput('')
    setSending(true)
    setChatStatus('Searching documents…')

    try {
      const res = await fetch(`/api/cases/${caseId}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text.trim(), history }),
      })

      if (!res.ok) {
        const raw = await res.text()
        let e: any = {}
        try {
          e = raw ? JSON.parse(raw) : {}
        } catch {
          throw new Error(raw || 'Failed')
        }
        throw new Error(e.detail ?? e.error ?? e.message ?? 'Failed')
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
      setChatStatus('Searching documents…')
    }
  }

  const toggleRecording = async () => {
    if (recording) {
      mediaRef.current?.stop()
      setRecording(false)
      return
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mr = new MediaRecorder(stream)

      chunksRef.current = []
      mr.ondataavailable = e => chunksRef.current.push(e.data)
      mr.onstop = async () => {
        stream.getTracks().forEach(t => t.stop())

        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        const fd = new FormData()
        fd.append('audio', blob, 'rec.webm')
        fd.append('mimeType', 'audio/webm')

        try {
          const res = await fetch('/api/voice/transcribe', { method: 'POST', body: fd })
          const d = await parseApiResponse(res)
          if (d.transcript) sendMessage(d.transcript)
          else toast.error('Could not transcribe.')
        } catch {
          toast.error('Transcription failed.')
        }
      }

      mr.start()
      mediaRef.current = mr
      setRecording(true)
    } catch {
      toast.error('Microphone access denied.')
    }
  }

  const riskBadge = (score?: number) => {
    if (!score) return null

    if (score <= 3) {
      return (
        <div className="flex items-center gap-2 text-emerald-400">
          <ShieldCheck className="w-5 h-5" />
          <p className="text-sm font-semibold">{score}/10 — Low Risk</p>
        </div>
      )
    }

    if (score <= 6) {
      return (
        <div className="flex items-center gap-2 text-amber-400">
          <Shield className="w-5 h-5" />
          <p className="text-sm font-semibold">{score}/10 — Medium Risk</p>
        </div>
      )
    }

    return (
      <div className="flex items-center gap-2 text-red-400">
        <ShieldAlert className="w-5 h-5" />
        <p className="text-sm font-semibold">{score}/10 — High Risk</p>
      </div>
    )
  }

  const suggestions = [
    'Summarise the key terms of this document',
    'What are the obligations of each party?',
    'Are there any liability clauses?',
    'What is the termination procedure?',
  ]

  if (!caseId) {
    return (
      <div className="min-h-screen flex items-center justify-center text-muted-foreground">
        No case selected.{' '}
        <Link href="/" className="ml-2 text-primary underline">
          Go back
        </Link>
      </div>
    )
  }

  const hasAnalysis =
    caseInfo?.summary || caseInfo?.risk_score || tags.length > 0 || deadlines.length > 0

  return (
    <div className="h-screen flex flex-col bg-background">
      <header className="border-b border-border/50 bg-card/30 backdrop-blur-sm shrink-0">
        <div className="px-6 py-3 flex items-center gap-4">
          <Link href="/">
            <button className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors">
              <ArrowLeft className="w-4 h-4" /> Cases
            </button>
          </Link>

          <div className="w-px h-4 bg-border" />

          <div className="flex items-center gap-2">
            <Scale className="w-4 h-4 text-primary" />
            <span className="text-sm font-medium">LegalEase AI</span>
          </div>

          {caseInfo?.title && (
            <>
              <div className="w-px h-4 bg-border" />
              <span className="text-sm text-muted-foreground truncate max-w-[200px]">
                {caseInfo.title}
              </span>
            </>
          )}

          <div className="ml-auto flex items-center gap-3">
            <button
              onClick={() => setPdfPanelOpen(o => !o)}
              className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors px-2.5 py-1.5 rounded-lg hover:bg-secondary"
              title={pdfPanelOpen ? 'Hide PDF viewer' : 'Show PDF viewer'}
            >
              <FileText className="w-3.5 h-3.5" />
              {pdfPanelOpen ? 'Hide PDF' : 'Show PDF'}
            </button>
            <div className="font-mono text-xs text-muted-foreground bg-secondary px-2.5 py-1 rounded-md">
              {caseId.slice(0, 8)}
            </div>
          </div>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {pdfPanelOpen && (
          <div className="w-[45%] min-w-[320px] border-r border-border/50 flex flex-col bg-card/10 shrink-0">
            {(caseInfo as any)?.documents?.length > 1 && (
              <div className="px-3 py-2 border-b border-border/40 flex gap-2 overflow-x-auto shrink-0">
                {((caseInfo as any).documents as any[]).map((doc: any) => (
                  <button
                    key={doc.id}
                    onClick={() => {
                      setSelectedDocumentId(doc.id)
                      fetchPdfUrl(doc.id)
                    }}
                    className={`text-xs px-3 py-1.5 rounded-lg whitespace-nowrap transition-all ${
                      selectedDocumentId === doc.id
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-secondary text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    {doc.name}
                  </button>
                ))}
              </div>
            )}

            <div className="flex-1 overflow-hidden">
              {pdfUrl ? (
                <iframe
                  src={pdfUrl}
                  className="w-full h-full border-0"
                  title="PDF Viewer"
                />
              ) : (
                <div className="flex flex-col items-center justify-center h-full text-muted-foreground gap-3">
                  <Loader2 className="w-6 h-6 animate-spin" />
                  <p className="text-sm">Loading document…</p>
                </div>
              )}
            </div>
          </div>
        )}

        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          {hasAnalysis && (
            <div className="border-b border-border/50 bg-card/20 shrink-0">
              <div className="px-6">
                <button
                  onClick={() => setShowAnalysis(!showAnalysis)}
                  className="w-full flex items-center justify-between py-2.5 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
                >
                  <span className="flex items-center gap-2">
                    <FileText className="w-3.5 h-3.5" />
                    Document Analysis
                  </span>
                  {showAnalysis ? (
                    <ChevronUp className="w-3.5 h-3.5" />
                  ) : (
                    <ChevronDown className="w-3.5 h-3.5" />
                  )}
                </button>

                {showAnalysis && (
                  <div className="pb-4 space-y-4 animate-fade-up">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {caseInfo?.summary && (
                        <div className="bg-card border border-border/50 rounded-xl p-4">
                          <p className="text-xs font-medium text-muted-foreground mb-2 flex items-center gap-1.5">
                            <BookOpen className="w-3 h-3" /> Summary
                          </p>
                          <p className="text-xs leading-relaxed text-foreground/80">
                            {caseInfo.summary}
                          </p>
                        </div>
                      )}

                      {caseInfo?.risk_score && (
                        <div className="bg-card border border-border/50 rounded-xl p-4">
                          <p className="text-xs font-medium text-muted-foreground mb-2 flex items-center gap-1.5">
                            <ShieldAlert className="w-3 h-3" /> Risk Assessment
                          </p>
                          <div className="mb-2">{riskBadge(caseInfo.risk_score)}</div>
                          {caseInfo.risk_explanation && (
                            <p className="text-xs text-foreground/60 leading-relaxed">
                              {caseInfo.risk_explanation}
                            </p>
                          )}
                        </div>
                      )}
                    </div>

                    {tags.length > 0 && (
                      <div>
                        <p className="text-xs font-medium text-muted-foreground mb-2 flex items-center gap-1.5">
                          <Tag className="w-3 h-3" /> Detected Clauses
                        </p>
                        <div className="flex flex-wrap gap-1.5">
                          {tags.map(tag => (
                            <span
                              key={tag.id}
                              className={`text-xs px-2.5 py-1 rounded-full border cursor-default transition-colors ${
                                TAG_COLORS[tag.tag_type] ??
                                'bg-secondary text-muted-foreground border-border/40'
                              }`}
                              title={tag.excerpt}
                            >
                              {formatTagType(tag.tag_type)}
                              <span className="ml-1 opacity-50">p.{tag.page_number}</span>
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {deadlines.length > 0 && (
                      <div>
                        <p className="text-xs font-medium text-muted-foreground mb-2 flex items-center gap-1.5">
                          <Calendar className="w-3 h-3" /> Key Dates & Deadlines
                        </p>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                          {deadlines.map(dl => (
                            <div
                              key={dl.id}
                              className="bg-card border border-border/50 rounded-lg px-3 py-2.5 flex items-start gap-3"
                            >
                              <div className="w-8 h-8 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center shrink-0 mt-0.5">
                                <Calendar className="w-3.5 h-3.5 text-primary" />
                              </div>
                              <div className="min-w-0">
                                <p className="text-xs font-medium truncate">{dl.event}</p>
                                <p className="text-xs text-primary/80 font-mono mt-0.5">
                                  {dl.deadline_date}
                                </p>
                                {dl.description && (
                                  <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                                    {dl.description}
                                  </p>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          <div className="flex-1 overflow-y-auto">
            <div className="px-6 py-6 space-y-6">
              {messages.length === 0 && (
                <div className="py-12 text-center">
                  <div className="w-14 h-14 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center mx-auto mb-5">
                    <BookOpen className="w-7 h-7 text-primary" />
                  </div>
                  <h2 className="text-lg font-semibold mb-2">Document ready for analysis</h2>
                  <p className="text-muted-foreground text-sm mb-8">
                    Ask anything — answers are grounded in your document with page citations.
                  </p>
                  <div className="grid grid-cols-2 gap-3 max-w-xl mx-auto">
                    {suggestions.map(s => (
                      <button
                        key={s}
                        onClick={() => sendMessage(s)}
                        className="text-left text-xs bg-card border border-border/50 hover:border-primary/40 hover:bg-card/80 rounded-xl p-3.5 text-muted-foreground hover:text-foreground transition-all"
                      >
                        {s}
                      </button>
                    ))}
                  </div>
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
                    className={`max-w-[78%] space-y-2 flex flex-col ${
                      m.role === 'user' ? 'items-end' : 'items-start'
                    }`}
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
                            className="text-xs bg-secondary border border-border/40 text-muted-foreground rounded-full px-2.5 py-0.5"
                            title={s.snippet}
                          >
                            {s.document_name} · p.{s.page}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {sending && messages[messages.length - 1]?.role !== 'ai' && (
                <div className="flex gap-3">
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

          <div className="border-t border-border/50 bg-card/30 backdrop-blur-sm shrink-0 px-6 py-4">
            <div>
              <div className="flex gap-3 items-end bg-card border border-border/60 rounded-2xl px-4 py-3 focus-within:border-primary/50 focus-within:ring-1 focus-within:ring-primary/20 transition-all">
                <textarea
                  ref={textareaRef}
                  className="flex-1 bg-transparent text-sm placeholder:text-muted-foreground resize-none outline-none max-h-40 leading-relaxed"
                  placeholder="Ask anything about your document…"
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

                <div className="flex items-center gap-2 shrink-0">
                  <input
                    ref={docFileRef}
                    type="file"
                    accept="application/pdf"
                    className="hidden"
                    onChange={e => {
                      if (e.target.files?.[0]) uploadAdditionalDoc(e.target.files[0])
                    }}
                  />

                  <button
                    onClick={() => docFileRef.current?.click()}
                    disabled={uploadingDoc}
                    className="p-2 rounded-xl text-muted-foreground hover:text-foreground hover:bg-secondary disabled:opacity-40 transition-all"
                    title="Add another PDF to this case"
                  >
                    {uploadingDoc ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Paperclip className="w-4 h-4" />
                    )}
                  </button>

                  <button
                    onClick={toggleRecording}
                    className={`p-2 rounded-xl transition-all ${
                      recording
                        ? 'bg-red-500/20 text-red-400 animate-pulse-ring'
                        : 'text-muted-foreground hover:text-foreground hover:bg-secondary'
                    }`}
                    title={recording ? 'Stop recording' : 'Voice input'}
                  >
                    {recording ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
                  </button>

                  <button
                    onClick={() => sendMessage(input)}
                    disabled={sending || !input.trim()}
                    className="p-2 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
                    title="Send (Enter)"
                  >
                    {sending ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Send className="w-4 h-4" />
                    )}
                  </button>
                </div>
              </div>

              <div style={{ fontSize: '12px', color: '#666', marginTop: '8px', paddingLeft: '4px' }}>
                This tool explains legal documents. It does not provide legal advice.
              </div>

              <p className="text-center text-xs text-muted-foreground mt-2">
                Enter to send · Shift+Enter for new line · 📎 to add documents
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function WorkspacePage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center">
          <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
        </div>
      }
    >
      <WorkspaceInner />
    </Suspense>
  )
}