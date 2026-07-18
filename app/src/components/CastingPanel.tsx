import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { useEffect, useMemo, useState } from 'react'
import { ScrollArea } from './ui/ScrollArea'

type CastingControls = {
  body_build: string
  stature: string
  skin_tone: string
  presentation: string
  adult_age: string
  pose_access: string
  continuity: string
}

type CastingPreset = {
  id: string
  display_name: string
  one_line_mood: string
  wardrobe_context: string
  pose: string
  setting: string
  lighting: string
}

type CastingCollection = {
  variation_controls: Record<string, string | string[]>
  ux_copy: Record<string, string>
  presets: CastingPreset[]
}

export type PresentationRender = {
  id: string
  design_version_id: string
  preset_id: string
  status: string
  asset_url?: string
  error_code?: string
}

type CastingPanelProps = {
  open: boolean
  projectId: string
  designVersionId?: string
  selectedPresetId?: string
  blocked?: boolean
  onPreviewPreset: (preset: CastingPreset) => void
  onPresentationReady: (presentation: PresentationRender) => void
  onPendingChange?: (pending: boolean, direction?: string) => void
  onClose: () => void
}

const defaultControls: CastingControls = {
  body_build: 'varied',
  stature: 'varied',
  skin_tone: 'varied',
  presentation: 'varied',
  adult_age: 'varied-adult',
  pose_access: 'varied',
  continuity: 'new-fictional-casting',
}

const controlLabels: Record<keyof CastingControls, string> = {
  body_build: 'Body build',
  stature: 'Stature',
  skin_tone: 'Skin tone',
  presentation: 'Presentation',
  adult_age: 'Adult age',
  pose_access: 'Pose / access',
  continuity: 'Continuity',
}

export function CastingPanel({
  open,
  projectId,
  designVersionId,
  selectedPresetId,
  blocked = false,
  onPreviewPreset,
  onPresentationReady,
  onPendingChange,
  onClose,
}: CastingPanelProps) {
  const reduceMotion = useReducedMotion()
  const [collection, setCollection] = useState<CastingCollection | null>(null)
  const [presetId, setPresetId] = useState(selectedPresetId ?? 'sun-faded-minimalist')
  const [controls, setControls] = useState<CastingControls>(defaultControls)
  const [status, setStatus] = useState<'idle' | 'loading' | 'ready' | 'submitting' | 'error'>('idle')
  const [message, setMessage] = useState('')

  useEffect(() => {
    if (selectedPresetId) setPresetId(selectedPresetId)
  }, [selectedPresetId])

  useEffect(() => {
    if (!open || collection || status === 'loading') return
    setStatus('loading')
    fetch('/api/casting-presets', { headers: { Accept: 'application/json' } })
      .then(async (response) => {
        if (!response.ok) throw new Error('Casting directions are unavailable.')
        return (await response.json()) as CastingCollection
      })
      .then((body) => {
        setCollection(body)
        const initial =
          body.presets.find((preset) => preset.id === (selectedPresetId ?? presetId)) ??
          body.presets[0]
        if (initial) {
          setPresetId(initial.id)
          onPreviewPreset(initial)
        }
        setStatus('ready')
      })
      .catch((error: Error) => {
        setMessage(error.message)
        setStatus('error')
      })
  }, [collection, onPreviewPreset, open, presetId, selectedPresetId, status])

  const selectedPreset = useMemo(
    () => collection?.presets.find((preset) => preset.id === presetId),
    [collection, presetId],
  )

  const choosePreset = (preset: CastingPreset) => {
    setPresetId(preset.id)
    onPreviewPreset(preset)
    setMessage('')
  }

  const makePresentation = async () => {
    if (blocked || status === 'submitting') return
    if (!designVersionId) {
      setMessage('Make the first garment version before making an editorial view.')
      return
    }
    const direction = selectedPreset?.display_name ?? presetId.replaceAll('-', ' ')
    setStatus('submitting')
    setMessage('Working on the editorial view. Your garment stays in place.')
    onPendingChange?.(true, direction)
    onClose()
    try {
      const response = await fetch(`/api/projects/${projectId}/presentations`, {
        method: 'POST',
        headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
        body: JSON.stringify({
          preset_id: presetId,
          design_version_id: designVersionId,
          controls,
        }),
      })
      const body = (await response.json()) as PresentationRender & { detail?: string }
      if (!response.ok) throw new Error(body.detail || 'That editorial view did not finish.')
      if (body.status !== 'ready' || !body.asset_url) {
        if (body.error_code === 'garment_drift') {
          throw new Error(
            "The garment changed, so this view was not saved. Try a simpler editorial direction.",
          )
        }
        throw new Error('That editorial view did not finish. The current version has not changed.')
      }
      onPresentationReady(body)
      setMessage('Editorial view ready. The design version is unchanged.')
      setStatus('ready')
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'That editorial view did not finish.')
      setStatus('ready')
    } finally {
      onPendingChange?.(false)
    }
  }

  return (
    <AnimatePresence>
      {open && (
        <motion.aside
          className="casting-panel"
          aria-label="Editorial direction"
          aria-busy={status === 'submitting'}
          initial={{ opacity: 0, x: reduceMotion ? 0 : 28 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: reduceMotion ? 0 : 22 }}
          transition={{ duration: reduceMotion ? 0 : 0.3, ease: [0.22, 1, 0.36, 1] }}
        >
          <header className="casting-panel__header">
            <div>
              <span>EDITORIAL</span>
              <h2>See it worn.</h2>
              <p>Choose the wearer, stance, setting, and light. The garment itself won’t change.</p>
            </div>
            <button type="button" onClick={onClose} aria-label="Close editorial panel">Close ×</button>
          </header>

          <ScrollArea className="casting-scroll" type="always" scrollHideDelay={0}>
            {status === 'loading' && <p className="panel-state">Opening editorial directions…</p>}
            {status === 'error' && <p className="panel-state">{message}</p>}
            {collection && (
              <div className="casting-panel__body">
                <ul className="casting-presets" aria-label="Editorial directions">
                  {collection.presets.map((preset) => (
                    <li key={preset.id}>
                      <button
                        type="button"
                        className={preset.id === presetId ? 'is-selected' : undefined}
                        aria-pressed={preset.id === presetId}
                        disabled={status === 'submitting'}
                        onClick={() => choosePreset(preset)}
                      >
                        <strong>{preset.display_name}</strong>
                        <p>{preset.one_line_mood}</p>
                        <i aria-hidden="true">{preset.id === presetId ? '●' : '○'}</i>
                      </button>
                    </li>
                  ))}
                </ul>

                {selectedPreset && (
                  <section className="casting-direction-detail">
                    <span>CURRENT DIRECTION</span>
                    <h3>{selectedPreset.display_name}</h3>
                    <dl>
                      <div><dt>Pose</dt><dd>{selectedPreset.pose}</dd></div>
                      <div><dt>Place</dt><dd>{selectedPreset.setting}</dd></div>
                      <div><dt>Light</dt><dd>{selectedPreset.lighting}</dd></div>
                    </dl>
                  </section>
                )}

                <details className="casting-controls">
                  <summary>Adjust editorial <span>+</span></summary>
                  <div>
                    {(Object.keys(defaultControls) as Array<keyof CastingControls>).map((key) => {
                      const values = collection.variation_controls[key]
                      if (!Array.isArray(values)) return null
                      return (
                        <label key={key}>
                          <span>{controlLabels[key]}</span>
                          <select
                            value={controls[key]}
                            disabled={status === 'submitting'}
                            onChange={(event) =>
                              setControls((current) => ({ ...current, [key]: event.target.value }))
                            }
                          >
                            {values.map((value) => <option value={value} key={value}>{value.replaceAll('-', ' ')}</option>)}
                          </select>
                        </label>
                      )
                    })}
                  </div>
                </details>

                <footer className="casting-panel__footer">
                  <div>
                    <strong>DESIGN UNCHANGED</strong>
                  </div>
                  <button
                    type="button"
                    className="casting-submit"
                    onClick={() => void makePresentation()}
                    disabled={status === 'submitting' || !designVersionId || blocked}
                  >
                    {status === 'submitting'
                      ? 'Working on it'
                      : blocked
                        ? 'Finish current draft first'
                      : designVersionId
                        ? 'Make editorial view'
                        : 'Make the garment first'}{' '}
                    <span>↗</span>
                  </button>
                  {blocked ? (
                    <p role="status">Finish the current draft before making an editorial view.</p>
                  ) : message ? (
                    <p role="status">{message}</p>
                  ) : !designVersionId ? (
                    <p>Choose or make a garment version before making an editorial view.</p>
                  ) : null}
                </footer>
              </div>
            )}
          </ScrollArea>
        </motion.aside>
      )}
    </AnimatePresence>
  )
}
