import { useEffect, useRef, useState, type KeyboardEvent } from 'react'

export type DesignCandidateRecord = {
  id: string
  project_id: string
  generation_job_id: string
  base_version_id?: string | null
  candidate_index: 1 | 2 | 3 | 4
  requested_change: string
  preserve: string[]
  avoid: string[]
  prompt: string
  model: string
  status: 'ready' | 'selected' | 'dismissed'
  asset_id: string
  asset_url: string
  selected_version_id?: string | null
  created_at: string
  updated_at: string
}

export type SelectedCandidateVersion = {
  id: string
  version_number: number
  requested_change: string
  preserve?: string[]
  avoid?: string[]
  status: 'concept' | 'ready'
  asset_url?: string | null
}

type CandidatePickerProps = {
  projectId: string
  candidates: DesignCandidateRecord[]
  onSelected: (version: SelectedCandidateVersion, candidateId: string) => void | Promise<void>
  onDismissed: (
    dismissedCandidates: DesignCandidateRecord[],
    generationJobId: string,
  ) => void | Promise<void>
}

type CandidateAction = string | 'keep-current' | null

const candidateSlots = [1, 2, 3, 4] as const

function selectedVersionFromResponse(body: unknown): SelectedCandidateVersion | undefined {
  if (!body || typeof body !== 'object') return undefined

  const response = body as Record<string, unknown>
  if (typeof response.id !== 'string' || typeof response.version_number !== 'number') {
    return undefined
  }

  return response as unknown as SelectedCandidateVersion
}

export function CandidatePicker({
  projectId,
  candidates,
  onSelected,
  onDismissed,
}: CandidatePickerProps) {
  const dialogRef = useRef<HTMLDivElement>(null)
  const firstActionRef = useRef<HTMLButtonElement>(null)
  const previousFocus = useRef<HTMLElement | null>(null)
  const [action, setAction] = useState<CandidateAction>(null)
  const [errorMessage, setErrorMessage] = useState('')
  const [failedImages, setFailedImages] = useState<Set<string>>(() => new Set())

  const orderedCandidates = [...candidates].sort(
    (left, right) => left.candidate_index - right.candidate_index,
  )
  const requestedChange = (orderedCandidates[0]?.requested_change ?? 'New version').replace(
    /\s+Keep every other visible detail unchanged\.?$/i,
    '',
  )

  useEffect(() => {
    previousFocus.current = document.activeElement instanceof HTMLElement
      ? document.activeElement
      : null
    firstActionRef.current?.focus()
    return () => {
      if (previousFocus.current?.isConnected) previousFocus.current.focus()
    }
  }, [])

  const trapFocus = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key !== 'Tab') return
    const focusable = Array.from(
      dialogRef.current?.querySelectorAll<HTMLElement>(
        'button:not(:disabled), [href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])',
      ) ?? [],
    )
    if (focusable.length === 0) return

    const first = focusable[0]
    const last = focusable[focusable.length - 1]
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault()
      last.focus()
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault()
      first.focus()
    }
  }

  const selectCandidate = async (candidate: DesignCandidateRecord) => {
    if (action || failedImages.has(candidate.id)) return
    setAction(candidate.id)
    setErrorMessage('')

    try {
      const response = await fetch(
        `/api/projects/${encodeURIComponent(projectId)}/candidate-sets/${encodeURIComponent(candidate.generation_job_id)}/select/${encodeURIComponent(candidate.id)}`,
        {
          method: 'POST',
          headers: { Accept: 'application/json' },
        },
      )
      const body = (await response.json()) as unknown
      if (!response.ok) {
        const detail =
          body && typeof body === 'object' && typeof (body as Record<string, unknown>).detail === 'string'
            ? String((body as Record<string, unknown>).detail)
            : 'That selection did not complete.'
        throw new Error(detail)
      }

      const selectedVersion = selectedVersionFromResponse(body)
      if (!selectedVersion) throw new Error('The selected version could not be loaded.')
      await onSelected(selectedVersion, candidate.id)
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : 'That selection did not complete. Try again.',
      )
      setAction(null)
    }
  }

  const keepCurrent = async () => {
    if (action) return
    setAction('keep-current')
    setErrorMessage('')

    try {
      const jobId = orderedCandidates[0]?.generation_job_id
      if (!jobId) throw new Error('That candidate set is unavailable.')
      const response = await fetch(
        `/api/projects/${encodeURIComponent(projectId)}/candidate-sets/${encodeURIComponent(jobId)}/dismiss`,
        {
          method: 'POST',
          headers: { Accept: 'application/json' },
        },
      )
      const body = (await response.json()) as DesignCandidateRecord[] | { detail?: string }
      if (!response.ok) {
        throw new Error(
          !Array.isArray(body) && body.detail ? body.detail : 'That action did not complete.',
        )
      }
      await onDismissed(Array.isArray(body) ? body : [], jobId)
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : 'That action did not complete. Try again.',
      )
      setAction(null)
    }
  }

  return (
    <div className="candidate-picker" role="presentation">
      <div
        ref={dialogRef}
        className="candidate-picker__dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="candidate-picker-title"
        aria-describedby="candidate-picker-description"
        onKeyDown={trapFocus}
      >
        <header className="candidate-picker__header">
          <div>
            <h2 id="candidate-picker-title">SELECT A RESULT</h2>
            <p id="candidate-picker-description">{requestedChange}</p>
          </div>
        </header>

        <div className="candidate-picker__grid">
          {candidateSlots.map((slot, slotIndex) => {
            const candidate = orderedCandidates.find((item) => item.candidate_index === slot)
            const selecting = candidate ? action === candidate.id : false
            const imageFailed = candidate ? failedImages.has(candidate.id) : false

            return (
              <article
                key={slot}
                className={`candidate-card ${selecting ? 'is-selecting' : ''} ${imageFailed ? 'has-image-error' : ''}`}
                aria-busy={selecting}
              >
                <div className="candidate-card__meta">
                  <span>{String(slot).padStart(2, '0')}</span>
                </div>

                <div className="candidate-card__image">
                  {candidate ? (
                    <img
                      src={candidate.asset_url}
                      alt={`Candidate ${slot} for ${requestedChange}`}
                      draggable={false}
                      onError={() => {
                        setFailedImages((current) => new Set(current).add(candidate.id))
                      }}
                    />
                  ) : (
                    <div className="candidate-card__missing" role="status">
                      RESULT UNAVAILABLE
                    </div>
                  )}

                  {selecting && (
                    <div className="candidate-card__working" role="status" aria-live="polite">
                      <span className="loading-spinner" aria-hidden="true" />
                      <strong>SELECTING</strong>
                    </div>
                  )}

                  {imageFailed && (
                    <div className="candidate-card__missing" role="status">
                      IMAGE UNAVAILABLE
                    </div>
                  )}
                </div>

                <button
                  ref={slotIndex === 0 ? firstActionRef : undefined}
                  type="button"
                  disabled={!candidate || Boolean(action) || imageFailed}
                  onClick={() => candidate && void selectCandidate(candidate)}
                >
                  USE THIS VERSION
                </button>
              </article>
            )
          })}
        </div>

        <footer className="candidate-picker__footer">
          <button type="button" disabled={Boolean(action)} onClick={() => void keepCurrent()}>
            {action === 'keep-current' ? 'KEEPING CURRENT' : 'KEEP CURRENT'}
          </button>
          {errorMessage && <p role="alert">{errorMessage}</p>}
        </footer>
      </div>
    </div>
  )
}
