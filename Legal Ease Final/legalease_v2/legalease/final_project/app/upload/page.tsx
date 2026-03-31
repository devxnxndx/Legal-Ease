'use client'

import { useState, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { Upload, Scale, ArrowLeft, Loader2, FileText, X, CheckCircle, Plus } from 'lucide-react'
import { toast } from 'sonner'
import Link from 'next/link'
import { ThemeToggle } from '@/components/theme-toggle'
import { useAuth } from '@/components/auth-provider'

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

export default function UploadPage() {
  const router = useRouter()
  const { user } = useAuth()
  const displayName = user?.user_metadata?.full_name ?? user?.email ?? 'User'
  const fileRef = useRef<HTMLInputElement>(null)
  const [caseTitle, setCaseTitle] = useState('')
  const [files, setFiles] = useState<File[]>([])
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState('')
  const [dragOver, setDragOver] = useState(false)

  const addFiles = (incoming: FileList | File[]) => {
    const newFiles: File[] = []
    for (const f of Array.from(incoming)) {
      if (f.type !== 'application/pdf') {
        toast.error(`"${f.name}" is not a PDF — skipped.`)
        continue
      }
      if (f.size > 50 * 1024 * 1024) {
        toast.error(`"${f.name}" exceeds 50 MB — skipped.`)
        continue
      }
      if (files.some(existing => existing.name === f.name && existing.size === f.size)) continue
      newFiles.push(f)
    }
    if (newFiles.length) setFiles(prev => [...prev, ...newFiles])
  }

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index))
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    addFiles(e.dataTransfer.files)
  }

  const handleSubmit = async () => {
    if (!caseTitle.trim()) {
      toast.error('Enter a case title first.')
      return
    }
    if (files.length === 0) {
      toast.error('Select at least one PDF file.')
      return
    }

    setUploading(true)
    try {
      setUploadProgress(`Processing 1 of ${files.length}: ${files[0].name}`)
      const fd = new FormData()
      fd.append('title', caseTitle.trim())
      fd.append('file', files[0])

      const res = await fetch('/api/cases/upload', { method: 'POST', body: fd })
      const data = await parseApiResponse(res)
      const caseId = data.caseId

      for (let i = 1; i < files.length; i++) {
        setUploadProgress(`Processing ${i + 1} of ${files.length}: ${files[i].name}`)
        const fd2 = new FormData()
        fd2.append('caseId', caseId)
        fd2.append('file', files[i])

        const res2 = await fetch('/api/cases/upload-doc', { method: 'POST', body: fd2 })

        try {
          await parseApiResponse(res2)
        } catch (err: any) {
          toast.error(`Failed to add "${files[i].name}": ${err.message ?? 'Unknown error'}`)
        }
      }

      toast.success(`Case created with ${files.length} document${files.length > 1 ? 's' : ''}!`)
      router.push(`/workspace?caseId=${caseId}`)
    } catch (err: any) {
      toast.error(err.message ?? 'Upload failed')
    } finally {
      setUploading(false)
      setUploadProgress('')
    }
  }

  const formatSize = (b: number) =>
    b > 1024 * 1024 ? `${(b / 1024 / 1024).toFixed(1)} MB` : `${(b / 1024).toFixed(0)} KB`

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border/50 bg-card/30 backdrop-blur-sm">
        <div className="max-w-2xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/">
              <button className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors">
                <ArrowLeft className="w-4 h-4" /> Back
              </button>
            </Link>

            <div className="w-px h-4 bg-border" />

            <div className="flex items-center gap-2">
              <Scale className="w-4 h-4 text-primary" />
              <span className="text-sm font-medium">LegalEase AI</span>
            </div>

            <div className="w-px h-4 bg-border/60" />

            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-full bg-primary/20 border border-primary/30 flex items-center justify-center">
                <span className="text-xs font-semibold text-primary">
                  {displayName.charAt(0).toUpperCase()}
                </span>
              </div>
              <span className="text-sm font-medium text-foreground/80 hidden sm:block">
                {displayName}
              </span>
            </div>
          </div>

          <ThemeToggle />
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-6 py-12">
        <div className="mb-10">
          <h1 className="text-2xl font-semibold tracking-tight mb-1.5">New Case</h1>
          <p className="text-muted-foreground text-sm">
            Upload one or more legal PDFs and our AI will index every page for Q&A.
          </p>
        </div>

        <div className="space-y-6">
          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground/80">Case Title</label>
            <input
              type="text"
              placeholder="e.g. Smith v. Jones — Service Agreement 2024"
              value={caseTitle}
              onChange={e => setCaseTitle(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSubmit()}
              className="w-full bg-card border border-border/60 rounded-lg px-4 py-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary/50 transition-all"
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground/80">Documents (PDF)</label>
            <div
              onClick={() => fileRef.current?.click()}
              onDrop={handleDrop}
              onDragOver={e => {
                e.preventDefault()
                setDragOver(true)
              }}
              onDragLeave={() => setDragOver(false)}
              className={`relative border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${dragOver
                  ? 'border-primary/60 bg-primary/5'
                  : 'border-border/50 hover:border-primary/40 hover:bg-card/50'
                }`}
            >
              <div className="w-12 h-12 rounded-xl bg-secondary flex items-center justify-center mx-auto mb-4">
                <Upload className="w-6 h-6 text-muted-foreground" />
              </div>
              <p className="text-sm font-medium mb-1">
                {files.length === 0 ? 'Drop your PDFs here' : 'Drop more PDFs here'}
              </p>
              <p className="text-xs text-muted-foreground">
                or click to browse · PDF only · Max 50 MB each
              </p>
              <input
                ref={fileRef}
                type="file"
                accept="application/pdf"
                multiple
                className="hidden"
                onChange={e => {
                  if (e.target.files) addFiles(e.target.files)
                  e.target.value = ''
                }}
              />
            </div>

            {files.length > 0 && (
              <div className="space-y-2 mt-3">
                {files.map((f, i) => (
                  <div
                    key={`${f.name}-${f.size}`}
                    className="flex items-center gap-4 bg-card border border-primary/30 rounded-xl px-5 py-3"
                  >
                    <div className="w-9 h-9 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center shrink-0">
                      <FileText className="w-4 h-4 text-primary" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{f.name}</p>
                      <p className="text-xs text-muted-foreground mt-0.5">{formatSize(f.size)}</p>
                    </div>
                    <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
                    <button
                      onClick={e => {
                        e.stopPropagation()
                        removeFile(i)
                      }}
                      className="p-1.5 rounded-md hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
                <button
                  onClick={() => fileRef.current?.click()}
                  className="w-full flex items-center justify-center gap-2 border border-dashed border-border/50 hover:border-primary/40 rounded-xl py-2.5 text-xs text-muted-foreground hover:text-foreground transition-all"
                >
                  <Plus className="w-3.5 h-3.5" /> Add more documents
                </button>
              </div>
            )}
          </div>

          {uploading && (
            <div className="bg-card border border-border/50 rounded-xl p-4">
              <div className="flex items-center gap-3 mb-3">
                <Loader2 className="w-4 h-4 text-primary animate-spin" />
                <p className="text-sm font-medium">{uploadProgress || 'Processing…'}</p>
              </div>
              <div className="space-y-1.5 text-xs text-muted-foreground pl-7">
                <p>Extracting text from all pages</p>
                <p>Generating semantic embeddings</p>
                <p>Running AI analysis (summary, risk, clauses, deadlines)</p>
                <p>Indexing into vector database</p>
              </div>
            </div>
          )}

          <button
            onClick={handleSubmit}
            disabled={uploading || !caseTitle.trim() || files.length === 0}
            className="w-full flex items-center justify-center gap-2 bg-primary text-primary-foreground py-3 rounded-lg text-sm font-medium hover:bg-primary/90 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
          >
            {uploading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" /> Processing…
              </>
            ) : (
              <>
                <Upload className="w-4 h-4" /> Upload {files.length > 1 ? `${files.length} Documents` : '& Analyse'}
              </>
            )}
          </button>
        </div>
      </main>
    </div>
  )
}