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
  fixture?: boolean
}

type CastingPanelProps = {
  open: boolean
  projectId: string
  demoMode?: boolean
  selectedPresetId?: string
  onPreviewPreset: (preset: CastingPreset) => void
  onPresentationReady: (presentation: PresentationRender) => void
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
  demoMode = false,
  selectedPresetId,
  onPreviewPreset,
  onPresentationReady,
  onClose,
}: CastingPanelProps) {
  const reduceMotion = useReducedMotion()
  const [collection, setCollection] = useState<CastingCollection | null>(null)
  const [presetId, setPresetId] = useState(selectedPresetId ?? 'sun-faded-minimalist')
  const [controls, setControls] = useState<CastingControls>(defaultControls)
  const [status, setStatus] = useState<'idle' | 'loading' | 'ready' | 'submitting' | 'error'>('idle')
  const [message, setMessage] = useState('')

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
        const initial = body.presets.find((preset) => preset.id === presetId) ?? body.presets[0]
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
  }, [collection, onPreviewPreset, open, presetId, status])

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
    setStatus('submitting')
    setMessage('Building a separate lookbook view…')
    if (demoMode) {
      const fixture: PresentationRender = {
        id: `demo_${presetId}`,
        design_version_id: 'demo_version',
        preset_id: presetId,
        status: 'ready',
        fixture: true,
      }
      onPresentationReady(fixture)
      setMessage('Direction applied to the local demo view. The garment version is unchanged.')
      setStatus('ready')
      return
    }
    try {
      const response = await fetch(`/api/projects/${projectId}/presentations`, {
        method: 'POST',
        headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
        body: JSON.stringify({ preset_id: presetId, controls }),
      })
      const body = (await response.json()) as PresentationRender & { detail?: string }
      if (!response.ok) throw new Error(body.detail || 'That lookbook view did not finish.')
      if (body.status !== 'ready' || !body.asset_url) {
        if (body.error_code === 'garment_drift') {
          throw new Error(
            "The garment changed in this render, so we didn't save it. Try another casting direction.",
          )
        }
        throw new Error('That lookbook view did not finish. Your design is safe.')
      }
      onPresentationReady(body)
      setMessage('Lookbook view ready. The design version is unchanged.')
      setStatus('ready')
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'That lookbook view did not finish.')
      setStatus('ready')
    }
  }

  return (
    <AnimatePresence>
      {open && (
        <motion.aside
          className="casting-panel"
          aria-label="Fictional model casting"
          initial={{ opacity: 0, x: reduceMotion ? 0 : 28 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: reduceMotion ? 0 : 22 }}
          transition={{ duration: reduceMotion ? 0 : 0.3, ease: [0.22, 1, 0.36, 1] }}
        >
          <header className="casting-panel__header">
            <div>
              <span>CASTING DIRECTION</span>
              <h2>Choose a point of view, not a person.</h2>
              <p>Pose, place, and light can change. Your garment stays untouched.</p>
            </div>
            <button type="button" onClick={onClose} aria-label="Close casting panel">Close ×</button>
          </header>

          <ScrollArea className="casting-scroll" type="always" scrollHideDelay={0}>
            {status === 'loading' && <p className="panel-state">Opening casting directions…</p>}
            {status === 'error' && <p className="panel-state">{message}</p>}
            {collection && (
              <div className="casting-panel__body">
                <ul className="casting-presets" aria-label="Casting directions">
                  {collection.presets.map((preset, index) => (
                    <li key={preset.id}>
                      <button
                        type="button"
                        className={preset.id === presetId ? 'is-selected' : undefined}
                        aria-pressed={preset.id === presetId}
                        onClick={() => choosePreset(preset)}
                      >
                        <span>{String(index + 1).padStart(2, '0')}</span>
                        <strong>{preset.display_name}</strong>
                        <p>{preset.one_line_mood}</p>
                        <i aria-hidden="true">{preset.id === presetId ? '●' : '○'}</i>
                      </button>
                    </li>
                  ))}
                </ul>

                {selectedPreset && (
                  <section className="casting-direction-detail">
                    <span>SELECTED TREATMENT</span>
                    <h3>{selectedPreset.display_name}</h3>
                    <dl>
                      <div><dt>Pose</dt><dd>{selectedPreset.pose}</dd></div>
                      <div><dt>Place</dt><dd>{selectedPreset.setting}</dd></div>
                      <div><dt>Light</dt><dd>{selectedPreset.lighting}</dd></div>
                    </dl>
                  </section>
                )}

                <details className="casting-controls">
                  <summary>Vary the casting <span>+</span></summary>
                  <p>Every control moves independently. Every generated person is a fictional adult.</p>
                  <div>
                    {(Object.keys(defaultControls) as Array<keyof CastingControls>).map((key) => {
                      const values = collection.variation_controls[key]
                      if (!Array.isArray(values)) return null
                      return (
                        <label key={key}>
                          <span>{controlLabels[key]}</span>
                          <select
                            value={controls[key]}
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
                    <span>Adults only · fictional casting · no borrowed campaigns</span>
                  </div>
                  <button
                    type="button"
                    className="casting-submit"
                    onClick={() => void makePresentation()}
                    disabled={status === 'submitting'}
                  >
                    {status === 'submitting' ? 'Making view…' : 'Make a lookbook view'} <span>↗</span>
                  </button>
                  {message && <p role="status">{message}</p>}
                </footer>
              </div>
            )}
          </ScrollArea>
        </motion.aside>
      )}
    </AnimatePresence>
  )
}
