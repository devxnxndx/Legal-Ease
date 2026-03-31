'use client'

import { useEffect, useRef, useState } from 'react'
import { Volume2, ChevronDown, Loader2, Square } from 'lucide-react'

interface Voice {
  id: string
  name: string
}

interface Props {
  text: string
  disabled?: boolean
  onSpokenSummary?: (summary: string) => void
}

export function VoiceSettings({ text, disabled, onSpokenSummary }: Props) {
  const [voices, setVoices] = useState<Voice[]>([])
  const [selectedVoiceId, setSelectedVoiceId] = useState<string>('')
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [playing, setPlaying] = useState(false)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  // ── Fetch ElevenLabs voice list on mount ────────────────────────────────
  useEffect(() => {
    fetch('/api/voice/voices')
      .then(async (res) => {
        if (!res.ok) throw new Error('Failed to load voices')
        return res.json()
      })
      .then((data) => {
        const list: Voice[] = (data.voices ?? []).map(
          (v: { id: string; name: string }) => ({ id: v.id, name: v.name })
        )
        setVoices(list)
        // Pre-select the first voice returned (Rachel by default)
        if (list.length > 0 && !selectedVoiceId) {
          setSelectedVoiceId(list[0].id)
        }
      })
      .catch((err) => console.error('voice list error:', err))
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // ── Cleanup audio on unmount ────────────────────────────────────────────
  useEffect(() => {
    return () => stopAudio()
  }, [])

  const stopAudio = () => {
    if (audioRef.current) {
      audioRef.current.pause()
      if (audioRef.current.src?.startsWith('blob:')) {
        URL.revokeObjectURL(audioRef.current.src)
      }
      audioRef.current = null
    }
    setPlaying(false)
  }

  // ── Speak ───────────────────────────────────────────────────────────────
  const speak = async () => {
    if (!text.trim() || loading) return

    // If already playing, stop instead
    if (playing) {
      stopAudio()
      return
    }

    setLoading(true)

    try {
      const res = await fetch('/api/voice/speak', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text,
          // Pass the selected ElevenLabs voice_id (not language)
          voice_id: selectedVoiceId || undefined,
        }),
      })

      if (!res.ok) {
        const errText = await res.text()
        console.error('TTS error:', errText)
        throw new Error(errText)
      }

      const spokenSummary = res.headers.get('X-Spoken-Summary')
      if (spokenSummary) {
        onSpokenSummary?.(decodeURIComponent(spokenSummary))
      }

      const blob = await res.blob()
      const url = URL.createObjectURL(blob)

      stopAudio() // cancel any previous playback

      const audio = new Audio(url)
      audioRef.current = audio

      audio.onended = () => {
        URL.revokeObjectURL(url)
        setPlaying(false)
      }
      audio.onerror = () => {
        URL.revokeObjectURL(url)
        setPlaying(false)
      }

      await audio.play()
      setPlaying(true)
    } catch (error) {
      console.error('speak error:', error)
      setPlaying(false)
    } finally {
      setLoading(false)
    }
  }

  const currentVoiceName =
    voices.find((v) => v.id === selectedVoiceId)?.name ?? 'Voice'

  return (
    <div className="flex items-center gap-2">

      {/* ── Voice picker ── */}
      <div className="relative">
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          className="flex items-center gap-1.5 rounded-lg border border-border/50 bg-card/50 px-3 py-1.5 text-xs transition-colors hover:bg-accent"
        >
          <span className="text-muted-foreground max-w-[100px] truncate">
            {voices.length === 0 ? 'Loading…' : currentVoiceName}
          </span>
          <ChevronDown className="h-3 w-3 text-muted-foreground shrink-0" />
        </button>

        {open && voices.length > 0 && (
          <div className="absolute bottom-full left-0 z-20 mb-1 w-56 max-h-64 overflow-y-auto rounded-xl border border-border/50 bg-card p-1 shadow-xl">
            {voices.map((voice) => (
              <button
                key={voice.id}
                type="button"
                onClick={() => {
                  setSelectedVoiceId(voice.id)
                  setOpen(false)
                }}
                className={`w-full rounded-lg px-3 py-2 text-left text-xs transition-colors ${
                  voice.id === selectedVoiceId
                    ? 'bg-primary/15 text-primary'
                    : 'text-foreground/80 hover:bg-accent'
                }`}
              >
                {voice.name}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* ── Read aloud / Stop button ── */}
      <button
        type="button"
        onClick={speak}
        disabled={disabled || loading || !text.trim()}
        className="flex items-center gap-1.5 rounded-lg border border-primary/25 bg-primary/15 px-3 py-1.5 text-xs text-primary transition-colors hover:bg-primary/25 disabled:cursor-not-allowed disabled:opacity-40"
      >
        {loading ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : playing ? (
          <Square className="h-3.5 w-3.5" />
        ) : (
          <Volume2 className="h-3.5 w-3.5" />
        )}
        {loading ? 'Speaking…' : playing ? 'Stop' : 'Read aloud'}
      </button>
    </div>
  )
}