'use client'

import { useEffect, useRef, useState } from 'react'
import { Loader2, Mic, Square } from 'lucide-react'

interface Props {
    onTranscript: (transcript: string) => void
    disabled?: boolean
}

function pickRecorderMimeType() {
    if (typeof window === 'undefined' || typeof MediaRecorder === 'undefined') {
        return ''
    }

    const candidates = [
        'audio/ogg;codecs=opus',
        'audio/webm;codecs=opus',
        'audio/mp4',
    ]

    for (const candidate of candidates) {
        if (MediaRecorder.isTypeSupported(candidate)) {
            return candidate
        }
    }

    return ''
}

function getFileNameForMimeType(mimeType: string) {
    if (mimeType.includes('ogg')) return 'recording.ogg'
    if (mimeType.includes('mp4')) return 'recording.m4a'
    if (mimeType.includes('webm')) return 'recording.webm'
    return 'recording.webm'
}

export function VoiceRecorder({ onTranscript, disabled }: Props) {
    const [recording, setRecording] = useState(false)
    const [transcribing, setTranscribing] = useState(false)
    const [error, setError] = useState<string>('')

    const mediaRecorderRef = useRef<MediaRecorder | null>(null)
    const mediaStreamRef = useRef<MediaStream | null>(null)
    const chunksRef = useRef<BlobPart[]>([])

    useEffect(() => {
        return () => {
            mediaRecorderRef.current?.stop()
            mediaStreamRef.current?.getTracks().forEach((track) => track.stop())
        }
    }, [])

    const startRecording = async () => {
        if (disabled || recording || transcribing) return

        try {
            setError('')
            chunksRef.current = []

            const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
            mediaStreamRef.current = stream

            const mimeType = pickRecorderMimeType()
            const recorder = mimeType
                ? new MediaRecorder(stream, { mimeType })
                : new MediaRecorder(stream)

            mediaRecorderRef.current = recorder

            recorder.ondataavailable = (event: BlobEvent) => {
                if (event.data.size > 0) {
                    chunksRef.current.push(event.data)
                }
            }

            recorder.onerror = (event: Event) => {
                console.error(event)
                setError('Microphone recording failed.')
            }

            recorder.onstop = async () => {
                setRecording(false)
                setTranscribing(true)

                try {
                    const finalMimeType =
                        recorder.mimeType || mimeType || 'audio/webm'
                    const blob = new Blob(chunksRef.current, { type: finalMimeType })

                    if (!blob.size) {
                        throw new Error('Empty recording.')
                    }

                    const formData = new FormData()
                    formData.append('audio', blob, getFileNameForMimeType(finalMimeType))
                    formData.append('mimeType', finalMimeType)

                    const res = await fetch('/api/voice/transcribe', {
                        method: 'POST',
                        body: formData,
                    })

                    if (!res.ok) {
                        throw new Error(await res.text())
                    }

                    const data = await res.json()
                    onTranscript(data.transcript ?? '')
                } catch (err) {
                    console.error(err)
                    setError('Could not transcribe microphone input.')
                } finally {
                    setTranscribing(false)
                    chunksRef.current = []
                    mediaStreamRef.current?.getTracks().forEach((track) => track.stop())
                    mediaStreamRef.current = null
                }
            }

            recorder.start()
            setRecording(true)
        } catch (err) {
            console.error(err)
            setError('Could not access the microphone.')
            mediaStreamRef.current?.getTracks().forEach((track) => track.stop())
            mediaStreamRef.current = null
        }
    }

    const stopRecording = () => {
        if (!recording) return
        mediaRecorderRef.current?.stop()
    }

    return (
        <div className="flex flex-col gap-2">
            <button
                type="button"
                onClick={recording ? stopRecording : startRecording}
                disabled={disabled || transcribing}
                className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${recording
                        ? 'border-red-500/25 bg-red-500/15 text-red-600 hover:bg-red-500/25'
                        : 'border-border/50 bg-card/50 text-foreground hover:bg-accent'
                    }`}
            >
                {transcribing ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : recording ? (
                    <Square className="h-3.5 w-3.5" />
                ) : (
                    <Mic className="h-3.5 w-3.5" />
                )}

                {transcribing
                    ? 'Transcribing…'
                    : recording
                        ? 'Stop recording'
                        : 'Speak'}
            </button>

            {error ? <p className="text-xs text-red-600">{error}</p> : null}
        </div>
    )
}