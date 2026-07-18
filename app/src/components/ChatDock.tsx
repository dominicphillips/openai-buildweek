import { ChatKit, useChatKit } from '@openai/chatkit-react'
import { useCallback, useEffect, useRef, useState } from 'react'

type ChatDockProps = {
  projectId: string
  objectName: string
  referenceCount: number
  activeVersionId?: string
  externalBusy?: boolean
  onProjectRefresh: (createdVersion?: { id: string; number: number }) => void | Promise<void>
  onWorkingChange?: (working: boolean) => void
}

type AgentStatus = 'checking' | 'online' | 'offline'

const editIntents = [
  {
    label: 'Fit',
    prompt:
      'Change only the fit: describe one exact silhouette or proportion adjustment. Keep material, construction, color, finish, trims, camera, and background unchanged.',
  },
  {
    label: 'Material',
    prompt:
      'Change only the material: describe one exact fabric or surface substitution. Keep fit, construction, color, trims, camera, and background unchanged.',
  },
  {
    label: 'Construction',
    prompt:
      'Change only the construction: describe one exact seam, closure, pocket, collar, cuff, or hem adjustment. Keep every other garment detail, camera, and background unchanged.',
  },
  {
    label: 'Finish',
    prompt:
      'Change only the finish: describe one exact wash, abrasion, distressing, dye, or repair treatment. Keep fit, material, construction, trims, camera, and background unchanged.',
  },
]

export function ChatDock({
  projectId,
  objectName,
  referenceCount,
  activeVersionId,
  externalBusy = false,
  onProjectRefresh,
  onWorkingChange,
}: ChatDockProps) {
  const [status, setStatus] = useState<AgentStatus>('checking')
  const [domainKey, setDomainKey] = useState('')
  const [errorMessage, setErrorMessage] = useState('')
  const [responding, setResponding] = useState(false)
  const responseEndTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const pendingCreatedVersion = useRef<{ id: string; number: number } | undefined>(undefined)

  const cancelResponseEnd = useCallback(() => {
    if (!responseEndTimer.current) return
    clearTimeout(responseEndTimer.current)
    responseEndTimer.current = null
  }, [])

  const checkBackend = useCallback(async () => {
    setStatus('checking')
    try {
      const response = await fetch('/api/health', { headers: { Accept: 'application/json' } })
      if (!response.ok) throw new Error('Backend is unavailable')
      const body = (await response.json()) as {
        chatkit_ready?: boolean
        chatkit_domain_key?: string | null
      }
      setDomainKey(body.chatkit_domain_key ?? '')
      setStatus(body.chatkit_ready ? 'online' : 'offline')
    } catch {
      setStatus('offline')
    }
  }, [])

  useEffect(() => {
    void checkBackend()
  }, [checkBackend])

  useEffect(
    () => () => {
      cancelResponseEnd()
      onWorkingChange?.(false)
    },
    [cancelResponseEnd, onWorkingChange],
  )

  const chatkitUrl = `/api/projects/${projectId}/chatkit`

  const { control, focusComposer, setComposerValue } = useChatKit({
    api: {
      url: chatkitUrl,
      domainKey: domainKey || 'not-configured',
      fetch: (input, init) => {
        const headers = new Headers(input instanceof Request ? input.headers : undefined)
        new Headers(init?.headers).forEach((value, name) => headers.set(name, value))
        if (activeVersionId) {
          headers.set('X-Somethings-On-Base-Version-Id', activeVersionId)
        } else {
          headers.delete('X-Somethings-On-Base-Version-Id')
        }
        return fetch(input, { ...init, headers })
      },
    },
    theme: {
      colorScheme: 'dark',
      typography: {
        baseSize: 16,
        fontFamily: "'Helvetica Neue', Helvetica, Arial, sans-serif",
        fontFamilyMono: "SFMono-Regular, 'SF Mono', Menlo, Monaco, Consolas, monospace",
      },
      radius: 'sharp',
      density: 'compact',
      color: {
        surface: { background: '#080807', foreground: '#171715' },
        accent: { primary: '#ff4c12', level: 2 },
        grayscale: { hue: 30, tint: 1, shade: -2 },
      },
    },
    frameTitle: 'SOMETHINGS-ON design conversation',
    header: { enabled: false },
    history: { enabled: false },
    startScreen: {
      greeting: 'What changes next?',
      prompts: [],
    },
    composer: {
      placeholder: 'Keep ___. Change ___.',
      attachments: { enabled: false },
    },
    threadItemActions: { feedback: false, retry: true },
    onEffect: ({ name, data }) => {
      if (name !== 'design.version.created') return
      const versionId = typeof data?.version_id === 'string' ? data.version_id : ''
      const versionNumber =
        typeof data?.version_number === 'number' ? data.version_number : Number.NaN
      pendingCreatedVersion.current =
        versionId && Number.isFinite(versionNumber)
          ? { id: versionId, number: versionNumber }
          : undefined
    },
    onResponseStart: () => {
      cancelResponseEnd()
      pendingCreatedVersion.current = undefined
      setErrorMessage('')
      setResponding(true)
      onWorkingChange?.(true)
    },
    onResponseEnd: () => {
      cancelResponseEnd()
      responseEndTimer.current = setTimeout(() => {
        responseEndTimer.current = null
        setResponding(false)
        void (async () => {
          const createdVersion = pendingCreatedVersion.current
          pendingCreatedVersion.current = undefined
          try {
            await onProjectRefresh(createdVersion)
          } finally {
            onWorkingChange?.(false)
          }
        })()
      }, 450)
    },
    onError: ({ error }) => {
      cancelResponseEnd()
      pendingCreatedVersion.current = undefined
      setResponding(false)
      onWorkingChange?.(false)
      setErrorMessage(error.message || 'The studio conversation disconnected.')
    },
  })

  return (
    <aside className="chat-dock" aria-label="Design conversation">
      <div className="chat-dock__header">
        <strong>DESIGN</strong>
        {responding || externalBusy ? <span>WORKING</span> : null}
      </div>

      <div className="edit-intent-bar" aria-label="Start one exact garment change">
        <span>CHANGE ONE</span>
        <div>
          {editIntents.map((intent) => (
            <button
              type="button"
              key={intent.label}
              disabled={status !== 'online' || responding || externalBusy}
              onClick={() => {
                void setComposerValue({ text: intent.prompt }).then(() => focusComposer())
              }}
            >
              {intent.label}
            </button>
          ))}
        </div>
      </div>

      {status === 'online' ? (
        <div
          className={`chatkit-surface ${externalBusy ? 'is-locked' : ''}`}
          aria-busy={responding || externalBusy}
          inert={externalBusy ? true : undefined}
        >
          <ChatKit key={projectId} control={control} className="chatkit-frame" />
        </div>
      ) : (
        <div className="chat-fallback">
          <div className="fallback-thread">
            <p className="fallback-meta">SOMETHINGS-ON / 00:01</p>
            <p>
              Let’s begin with your {objectName}. What do you want to carry over
              {referenceCount > 0
                ? ' from the references: proportion, fabric, construction, mood, or something else?'
                : ': proportion, fabric, construction, mood, or something else?'}
            </p>
          </div>
          <div className="agent-setup-card">
            <span>DESIGN GUIDE PAUSED</span>
            <p>
              The conversation is taking a moment. Nothing changed. Try again.
            </p>
            <button type="button" onClick={() => void checkBackend()}>
              Try again ↗
            </button>
          </div>
          {errorMessage && <p className="chat-error" role="alert">{errorMessage}</p>}
          <div className="fallback-composer" aria-disabled="true">
            <span>Keep ___. Change ___.</span>
            <i>↗</i>
          </div>
        </div>
      )}
    </aside>
  )
}
