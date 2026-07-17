import { ChatKit, useChatKit } from '@openai/chatkit-react'
import { useCallback, useEffect, useState } from 'react'

type ChatDockProps = {
  projectId: string
  objectName: string
  referenceCount: number
  onProjectRefresh: () => void
}

type AgentStatus = 'checking' | 'online' | 'offline'

export function ChatDock({ projectId, objectName, referenceCount, onProjectRefresh }: ChatDockProps) {
  const [status, setStatus] = useState<AgentStatus>('checking')
  const [domainKey, setDomainKey] = useState('')
  const [errorMessage, setErrorMessage] = useState('')
  const [responding, setResponding] = useState(false)

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

  const { control } = useChatKit({
    api: {
      url: `/api/projects/${projectId}/chatkit`,
      domainKey: domainKey || 'not-configured',
    },
    theme: 'dark',
    frameTitle: 'SOMETHINGS-ON design conversation',
    header: { enabled: false },
    history: { enabled: false },
    composer: {
      placeholder: 'Describe the next change…',
      attachments: { enabled: false },
    },
    threadItemActions: { feedback: false, retry: true },
    onEffect: ({ name }) => {
      if (name === 'design.version.created') onProjectRefresh()
    },
    onResponseStart: () => setResponding(true),
    onResponseEnd: () => {
      setResponding(false)
      onProjectRefresh()
    },
    onError: ({ error }) => {
      setResponding(false)
      setErrorMessage(error.message || 'The studio conversation disconnected.')
    },
  })

  return (
    <aside className="chat-dock" aria-label="Design conversation">
      <div className="chat-dock__header">
        <div>
          <span className={`connection-dot connection-dot--${status}`} />
          <strong>DESIGN GUIDE</strong>
        </div>
        <span>{responding ? 'WORKING' : status === 'online' ? 'LIVE' : 'LOCAL'}</span>
      </div>

      {status === 'online' ? (
        <ChatKit control={control} className="chatkit-frame" />
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
            <span>AGENT CONNECTION</span>
            <p>
              The local design service is connected. Add a ChatKit domain key to mount the hosted conversation surface; this fallback keeps the studio usable meanwhile.
            </p>
            <button type="button" onClick={() => void checkBackend()}>
              Check again ↗
            </button>
          </div>
          {errorMessage && <p className="chat-error" role="alert">{errorMessage}</p>}
          <div className="fallback-composer" aria-disabled="true">
            <span>Describe the next change…</span>
            <i>↗</i>
          </div>
        </div>
      )}
    </aside>
  )
}
