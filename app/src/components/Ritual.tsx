import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { useEffect, useMemo, useState, type FormEvent } from 'react'
import type { Brand, ReferenceCatalogItem, ReferenceItem, RitualStage } from '../lib/types'
import { EvidenceCatalog } from './EvidenceCatalog'
import { PantsIcon, ShoeIcon, TShirtIcon } from './icons'
import { LiveGarmentIllustration } from './illustrations'
import { ScrollArea } from './ui/ScrollArea'

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
  addCatalogReference: (item: ReferenceCatalogItem) => void
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

const objectPresets = [
  { label: 'T-shirt', value: 'white T-shirt', Icon: TShirtIcon },
  { label: 'Pants', value: 'pair of pants', Icon: PantsIcon },
  { label: 'Shoes', value: 'pair of shoes', Icon: ShoeIcon },
]

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
  addCatalogReference,
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

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'auto' })
    document.querySelector<HTMLElement>('.ritual-stage')?.scrollTo({ top: 0, behavior: 'auto' })
  }, [stage])

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
              <p className="eyebrow">Set the room</p>
              <h1>Choose the sound.</h1>
              <p className="stage-body">
                Play one track that gets you working. Or keep it quiet.
              </p>
              <div className="action-row action-row--center">
                <button className="primary-action" type="button" onClick={() => setStage('breath')}>
                  Sound is on <Arrow />
                </button>
                <button className="text-action" type="button" onClick={() => setStage('breath')}>
                  Keep it quiet
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
                Choose labels <Arrow />
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

              <ScrollArea className="brand-scroll" type="always" scrollHideDelay={0}>
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
                        <span className="brand-identity">
                          <span className={`brand-avatar ${brand.designer?.avatarUrl ? 'has-image' : ''}`}>
                            {brand.designer?.avatarUrl ? (
                              <img src={brand.designer.avatarUrl} alt={brand.designer.avatarAlt ?? ''} />
                            ) : (
                              <svg viewBox="0 0 64 76" role="img" aria-label={`Abstract portrait placeholder for ${brand.designer?.name ?? brand.name}`}>
                                <circle cx="32" cy="24" r="14" />
                                <path d="M10 72c2-22 10-34 22-34s20 12 22 34" />
                                <path d="M5 18h54M5 28h54M5 38h54M5 48h54M5 58h54" />
                              </svg>
                            )}
                          </span>
                          <span>
                            <strong>{brand.name}</strong>
                            <small title={brand.designer?.avatarCredit}>
                              {brand.designer?.name ?? 'Identity study pending'}
                            </small>
                          </span>
                        </span>
                        <span className="brand-tags">{brand.tags.slice(0, 2).join(' · ')}</span>
                        <span className="brand-mark" aria-hidden="true">
                          {selected ? '×' : '+'}
                        </span>
                      </button>
                    )
                  })}
                </div>
              </ScrollArea>

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
                <p className="stage-body">Choose one object. The collection can come later.</p>
              </div>
              <div className="object-workbench">
                <label className="object-field">
                  <span>Object / 001</span>
                  <input
                    autoFocus
                    value={objectName}
                    onChange={(event) => setObjectName(event.target.value)}
                    placeholder="e.g. a white T-shirt"
                  />
                </label>

                <div className="object-presets" aria-label="Common garment starting points">
                  {objectPresets.map(({ label, value, Icon }) => (
                    <button
                      type="button"
                      key={value}
                      className={objectName === value ? 'is-selected' : ''}
                      aria-pressed={objectName === value}
                      onClick={() => setObjectName(value)}
                    >
                      <Icon title={`${label} outline`} />
                      <span>{label}</span>
                    </button>
                  ))}
                </div>

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
            </div>
          )}

          {stage === 'references' && (
            <div className="reference-layout">
              <div className="stage-heading reference-heading">
                <p className="eyebrow">Evidence before adjectives</p>
                <h1>Show us what you mean.</h1>
                <p className="stage-body">
                  Pull from thirty local studies, or add your own image. Keep up to three details worth carrying forward.
                </p>
              </div>

              <div className="evidence-workspace">
                <EvidenceCatalog
                  selectedIds={references.map((reference) => reference.id)}
                  selectionCount={references.length}
                  onToggle={addCatalogReference}
                />

                <aside className="reference-workbench">
                  <header>
                    <span>ADD YOUR OWN</span>
                    <p>Screenshots, camera-roll photos, or one useful link.</p>
                  </header>
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
                    <small>PNG, JPEG, WEBP · up to 3 total</small>
                  </label>

                  <form className="link-form" onSubmit={addReferenceLink}>
                    <label htmlFor="reference-url">Save a link card</label>
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
                    <small>Saved as a source card; not fetched automatically.</small>
                  </form>

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
                </aside>
              </div>

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
              <div className="threshold-copy">
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
              <div className="threshold-illustration">
                <LiveGarmentIllustration label="Animated outline studies of a T-shirt, pants, and shoe" />
                <span>LIVE STUDY / REACT + SVG</span>
              </div>
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
