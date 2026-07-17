import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { useEffect, useMemo, useState, type FormEvent } from 'react'
import type { Brand, ReferenceItem, RitualStage } from '../lib/types'

type RitualProps = {
  stage: RitualStage
  setStage: (stage: RitualStage) => void
  brands: Brand[]
  selectedBrandIds: string[]
  toggleBrand: (brandId: string) => void
  objectName: string
  setObjectName: (name: string) => void
  references: ReferenceItem[]
  addFiles: (files: FileList | null) => void
  addLink: (url: string) => void
  removeReference: (referenceId: string) => void
}

const sequence: RitualStage[] = [
  'arrival',
  'sound',
  'breath',
  'headspace',
  'brands',
  'object',
  'references',
  'threshold',
]

const stageLabels: Record<RitualStage, string> = {
  arrival: 'Arrival',
  sound: 'Sound',
  breath: 'Pause',
  headspace: 'Attention',
  brands: 'Taste',
  object: 'Object',
  references: 'Evidence',
  threshold: 'Studio',
  studio: 'Studio',
}

function Arrow() {
  return <span aria-hidden="true">↗</span>
}

export function Ritual({
  stage,
  setStage,
  brands,
  selectedBrandIds,
  toggleBrand,
  objectName,
  setObjectName,
  references,
  addFiles,
  addLink,
  removeReference,
}: RitualProps) {
  const reduceMotion = useReducedMotion()
  const [remaining, setRemaining] = useState(30)
  const [timerRunning, setTimerRunning] = useState(false)
  const [brandQuery, setBrandQuery] = useState('')
  const [linkValue, setLinkValue] = useState('')
  const [linkError, setLinkError] = useState('')

  useEffect(() => {
    if (!timerRunning || remaining <= 0) return
    const timeout = window.setTimeout(() => {
      setRemaining((current) => Math.max(0, current - 1))
    }, 1000)
    return () => window.clearTimeout(timeout)
  }, [remaining, timerRunning])

  useEffect(() => {
    if (remaining === 0) setTimerRunning(false)
  }, [remaining])

  const filteredBrands = useMemo(() => {
    const query = brandQuery.trim().toLowerCase()
    if (!query) return brands
    return brands.filter(
      (brand) =>
        brand.name.toLowerCase().includes(query) ||
        brand.tags.some((tag) => tag.includes(query)),
    )
  }, [brandQuery, brands])

  const stageIndex = sequence.indexOf(stage)
  const back = () => {
    if (stageIndex > 0) setStage(sequence[stageIndex - 1])
  }

  const addReferenceLink = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    try {
      const parsed = new URL(linkValue)
      if (!['http:', 'https:'].includes(parsed.protocol)) throw new Error('protocol')
      addLink(parsed.toString())
      setLinkValue('')
      setLinkError('')
    } catch {
      setLinkError('Add a complete http or https URL.')
    }
  }

  const enter = {
    opacity: 0,
    y: reduceMotion ? 0 : 18,
    filter: reduceMotion ? 'none' : 'blur(8px)',
  }

  return (
    <main className="ritual-shell min-h-svh bg-[#050505] text-[#efefe8]">
      <header className="ritual-header">
        <button
          type="button"
          className="wordmark"
          onClick={() => setStage('arrival')}
          aria-label="Return to the beginning"
        >
          SOMETHINGS<span>—ON</span>
        </button>

        <div className="ritual-progress" aria-label="Onboarding progress">
          <span className="progress-label">{stageLabels[stage]}</span>
          <div className="progress-track" aria-hidden="true">
            {sequence.map((item, index) => (
              <i key={item} className={index <= stageIndex ? 'is-active' : ''} />
            ))}
          </div>
          <span className="progress-count">
            {String(Math.max(stageIndex + 1, 1)).padStart(2, '0')} / 08
          </span>
        </div>
      </header>

      {stageIndex > 0 && (
        <button type="button" className="back-button" onClick={back}>
          <span aria-hidden="true">←</span> Back
        </button>
      )}

      <AnimatePresence mode="wait">
        <motion.section
          key={stage}
          className={`ritual-stage ritual-stage--${stage}`}
          initial={enter}
          animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
          exit={{
            opacity: 0,
            y: reduceMotion ? 0 : -12,
            filter: reduceMotion ? 'none' : 'blur(6px)',
          }}
          transition={{ duration: reduceMotion ? 0 : 0.65, ease: [0.22, 1, 0.36, 1] }}
        >
          {stage === 'arrival' && (
            <div className="arrival-layout">
              <div className="arrival-index" aria-hidden="true">
                <span>001</span>
                <span>IDEA IN PROGRESS</span>
              </div>
              <div className="arrival-copy">
                <p className="eyebrow">A guided studio for fashion ideas</p>
                <h1>Start with what you notice.</h1>
                <div className="action-row">
                  <button className="primary-action" type="button" onClick={() => setStage('sound')}>
                    Begin <Arrow />
                  </button>
                  <button className="text-action" type="button" onClick={() => setStage('brands')}>
                    Skip the ritual
                  </button>
                </div>
              </div>
              <p className="arrival-note">
                Not a blank canvas.
                <br />
                A place to find the first change.
              </p>
            </div>
          )}

          {stage === 'sound' && (
            <div className="centered-copy">
              <p className="eyebrow">Before the first decision</p>
              <h1>Put on something you love.</h1>
              <p className="stage-body">We’ll wait. Silence works too.</p>
              <div className="action-row action-row--center">
                <button className="primary-action" type="button" onClick={() => setStage('breath')}>
                  I’m ready <Arrow />
                </button>
                <button className="text-action" type="button" onClick={() => setStage('breath')}>
                  Continue in silence
                </button>
              </div>
            </div>
          )}

          {stage === 'breath' && (
            <div className="breath-layout">
              <div className={`breath-orbit ${timerRunning ? 'is-running' : ''}`} aria-hidden="true">
                <span />
                <span />
                <span />
              </div>
              <div className="centered-copy breath-copy">
                <p className="eyebrow">A small pause</p>
                <h1>{remaining === 0 ? 'Ready when you are.' : 'Take 30 seconds.'}</h1>
                <p className="stage-body">
                  {remaining === 0
                    ? 'Keep the quiet, or let it go.'
                    : 'Breathe at your own pace. We’ll keep the time.'}
                </p>
                <p className="timer" aria-live="polite">
                  00:{String(remaining).padStart(2, '0')}
                </p>
                {remaining > 0 ? (
                  <div className="action-row action-row--center">
                    <button
                      className="primary-action"
                      type="button"
                      onClick={() => setTimerRunning((current) => !current)}
                    >
                      {timerRunning ? 'Pause' : remaining === 30 ? 'Start' : 'Resume'}
                    </button>
                    <button className="text-action" type="button" onClick={() => setStage('headspace')}>
                      Skip
                    </button>
                  </div>
                ) : (
                  <button className="primary-action" type="button" onClick={() => setStage('headspace')}>
                    Continue <Arrow />
                  </button>
                )}
                <p className="quiet-note">No technique. Just a pause.</p>
              </div>
            </div>
          )}

          {stage === 'headspace' && (
            <div className="centered-copy">
              <p className="eyebrow">The idea can be incomplete</p>
              <h1>You don’t need the whole idea.</h1>
              <p className="stage-body">
                Start with one detail that keeps your attention. We’ll follow it from there.
              </p>
              <button className="primary-action" type="button" onClick={() => setStage('brands')}>
                Let’s look <Arrow />
              </button>
            </div>
          )}

          {stage === 'brands' && (
            <div className="wide-stage">
              <div className="stage-heading stage-heading--split">
                <div>
                  <p className="eyebrow">Taste is a starting point</p>
                  <h1>Which labels do you return to?</h1>
                  <p className="stage-body">Choose a few. They’re references, not rules.</p>
                </div>
                <div className="selection-meta">
                  <span>Choose 3–5</span>
                  <strong>{String(selectedBrandIds.length).padStart(2, '0')}</strong>
                </div>
              </div>

              <label className="brand-search">
                <span>Search labels or qualities</span>
                <input
                  value={brandQuery}
                  onChange={(event) => setBrandQuery(event.target.value)}
                  placeholder="e.g. deconstruction"
                />
              </label>

              <div className="brand-grid">
                {filteredBrands.map((brand, index) => {
                  const selected = selectedBrandIds.includes(brand.id)
                  return (
                    <button
                      type="button"
                      className={`brand-card ${selected ? 'is-selected' : ''}`}
                      key={brand.id}
                      onClick={() => toggleBrand(brand.id)}
                      aria-pressed={selected}
                    >
                      <span className="brand-number">{String(index + 1).padStart(2, '0')}</span>
                      <strong>{brand.name}</strong>
                      <span className="brand-tags">{brand.tags.slice(0, 2).join(' · ')}</span>
                      <span className="brand-mark" aria-hidden="true">
                        {selected ? '×' : '+'}
                      </span>
                    </button>
                  )
                })}
              </div>

              <div className="wide-actions">
                <button
                  className="primary-action"
                  type="button"
                  onClick={() => setStage('object')}
                  disabled={selectedBrandIds.length === 0}
                >
                  Continue <Arrow />
                </button>
                <button className="text-action" type="button" onClick={() => setStage('object')}>
                  Skip for now
                </button>
              </div>
            </div>
          )}

          {stage === 'object' && (
            <div className="object-layout">
              <div className="stage-heading">
                <p className="eyebrow">Make it concrete</p>
                <h1>What are we making first?</h1>
                <p className="stage-body">A white tee. A cropped jacket. A bag.</p>
              </div>
              <label className="object-field">
                <span>Object / 001</span>
                <input
                  autoFocus
                  value={objectName}
                  onChange={(event) => setObjectName(event.target.value)}
                  placeholder="e.g. a white T-shirt"
                />
              </label>
              <div className="action-row">
                <button
                  className="primary-action"
                  type="button"
                  onClick={() => setStage('references')}
                  disabled={!objectName.trim()}
                >
                  Set the object <Arrow />
                </button>
                <button
                  className="text-action"
                  type="button"
                  onClick={() => {
                    setObjectName('white T-shirt')
                    setStage('references')
                  }}
                >
                  Start with a white tee
                </button>
              </div>
            </div>
          )}

          {stage === 'references' && (
            <div className="reference-layout">
              <div className="stage-heading">
                <p className="eyebrow">Evidence before adjectives</p>
                <h1>Show us what you mean.</h1>
                <p className="stage-body">
                  Add screenshots, camera-roll photos, or a link with a detail worth keeping. One is enough.
                </p>
              </div>

              <div className="reference-workbench">
                <label className="drop-zone">
                  <input
                    type="file"
                    accept="image/png,image/jpeg,image/webp"
                    multiple
                    onChange={(event) => addFiles(event.target.files)}
                    disabled={references.length >= 3}
                  />
                  <span className="drop-plus" aria-hidden="true">+</span>
                  <strong>Drop files or choose images</strong>
                  <small>PNG, JPEG, WEBP · up to 3</small>
                </label>

                <form className="link-form" onSubmit={addReferenceLink}>
                  <label htmlFor="reference-url">Or save a link card</label>
                  <div>
                    <input
                      id="reference-url"
                      type="url"
                      value={linkValue}
                      onChange={(event) => setLinkValue(event.target.value)}
                      placeholder="https://…"
                      disabled={references.length >= 3}
                    />
                    <button type="submit" disabled={!linkValue || references.length >= 3}>
                      Add
                    </button>
                  </div>
                  {linkError && <p role="alert">{linkError}</p>}
                  <small>Links are saved, not fetched, in this prototype.</small>
                </form>
              </div>

              {references.length > 0 && (
                <div className="reference-strip" aria-label="Selected references">
                  {references.map((reference, index) => (
                    <article key={reference.id} className="reference-chip">
                      {reference.previewUrl ? (
                        <img src={reference.previewUrl} alt="" />
                      ) : (
                        <span className="link-preview" aria-hidden="true">↗</span>
                      )}
                      <div>
                        <small>REF / {String(index + 1).padStart(2, '0')}</small>
                        <strong>{reference.name}</strong>
                      </div>
                      <button type="button" onClick={() => removeReference(reference.id)} aria-label={`Remove ${reference.name}`}>
                        ×
                      </button>
                    </article>
                  ))}
                </div>
              )}

              <div className="wide-actions">
                <button className="primary-action" type="button" onClick={() => setStage('threshold')}>
                  {references.length ? 'Use these references' : 'Open the studio'} <Arrow />
                </button>
                {references.length > 0 && (
                  <button className="text-action" type="button" onClick={() => setStage('threshold')}>
                    Start without analysis
                  </button>
                )}
              </div>
            </div>
          )}

          {stage === 'threshold' && (
            <div className="threshold-layout">
              <p className="eyebrow">Your starting point</p>
              <h1>
                Keep what matters.
                <br />
                <span>Change one thing.</span>
              </h1>
              <p className="stage-body">
                The object stays centered. Use the conversation on the left while your references gather around it.
              </p>
              <button className="primary-action" type="button" onClick={() => setStage('studio')}>
                Open the studio <Arrow />
              </button>
            </div>
          )}
        </motion.section>
      </AnimatePresence>

      <footer className="ritual-footer">
        <span>Creative direction stays with you.</span>
        <span>© 2026 / BUILD WEEK</span>
      </footer>
    </main>
  )
}
