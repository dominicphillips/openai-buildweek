import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { useEffect, useRef } from 'react'

type DemoVersionNumber = 1 | 2 | 3

type AuthoritativeVersion = {
  version_number: number
  requested_change: string
  preserve?: string[]
  avoid?: string[]
  asset_url?: string | null
}

type GarmentSpecPanelProps = {
  open: boolean
  objectName: string
  demoVersion?: {
    number: DemoVersionNumber
    change: string
  }
  version?: AuthoritativeVersion
  onClose: () => void
}

type DemoSpec = {
  fields: Array<{ label: string; value: string }>
  keep: string[]
  avoid: string[]
}

const sharedAvoid = [
  'Logos, graphics, or borrowed brand codes',
  'Changes to the blank white T-shirt',
  'Editorial changes to wearer, pose, place, or light',
  'Any construction change not named in CHANGE',
]

const demoSpecs: Record<DemoVersionNumber, DemoSpec> = {
  1: {
    fields: [
      { label: 'Category', value: 'Bomber jacket / outerwear' },
      { label: 'Fit / silhouette', value: 'Relaxed flight volume / dropped shoulder' },
      { label: 'Body length', value: 'Full length / low hip' },
      { label: 'Shell / material', value: 'Washed charcoal matte nylon' },
      { label: 'Lining', value: 'Tonal lightweight lining' },
      { label: 'Finish', value: 'Abraded surface / repaired wear' },
      { label: 'Closure', value: 'Two-way metal center-front zip' },
      { label: 'Pockets', value: 'Low-profile front welt pockets' },
      { label: 'Collar / cuffs / hem', value: 'Tonal 1×1 rib' },
    ],
    keep: [
      'Bomber category and relaxed flight volume',
      'Washed charcoal shell and distressed finish',
      'Blank white T-shirt as a separate layer',
      'Two-way center-front zip and tonal rib',
      'Front three-quarter inspection view',
    ],
    avoid: sharedAvoid,
  },
  2: {
    fields: [
      { label: 'Category', value: 'Bomber jacket / outerwear' },
      { label: 'Fit / silhouette', value: 'Relaxed flight volume / dropped shoulder' },
      { label: 'Body length', value: 'Full length / low hip' },
      { label: 'Shell / material', value: 'Washed charcoal matte nylon' },
      { label: 'Lining', value: 'Tonal lightweight lining' },
      { label: 'Finish', value: 'Exposed seam allowances / safety-orange bartacks' },
      { label: 'Closure', value: 'Two-way metal center-front zip' },
      { label: 'Pockets', value: 'Low-profile front welt pockets' },
      { label: 'Collar / cuffs / hem', value: 'Tonal 1×1 rib' },
    ],
    keep: [
      'Bomber category and relaxed flight volume',
      'Washed charcoal shell and distressed finish',
      'Blank white T-shirt as a separate layer',
      'Two-way center-front zip and tonal rib',
      'Front three-quarter inspection view',
    ],
    avoid: sharedAvoid,
  },
  3: {
    fields: [
      { label: 'Category', value: 'Bomber jacket / outerwear' },
      { label: 'Fit / silhouette', value: 'Relaxed flight volume / dropped shoulder' },
      { label: 'Body length', value: 'High-hip crop / approximately 90 mm shorter' },
      { label: 'Shell / material', value: 'Washed charcoal matte nylon' },
      { label: 'Lining', value: 'Tonal lightweight lining' },
      { label: 'Finish', value: 'Exposed seam allowances / safety-orange bartacks' },
      { label: 'Closure', value: 'Two-way metal center-front zip' },
      { label: 'Pockets', value: 'Low-profile front welt pockets' },
      { label: 'Collar / cuffs / hem', value: 'Tonal 1×1 rib' },
    ],
    keep: [
      'Relaxed flight volume, dropped shoulder, and sleeve shape',
      'Washed charcoal shell, exposed seams, and orange bartacks',
      'Blank white T-shirt as a separate layer',
      'Two-way center-front zip and tonal rib',
      'Front three-quarter inspection view',
    ],
    avoid: sharedAvoid,
  },
}

function ListOrUnknown({ items }: { items?: string[] }) {
  if (!items?.length) return <p className="spec-unknown">Not set</p>
  return (
    <ul>
      {items.map((item) => <li key={item}>{item}</li>)}
    </ul>
  )
}

export function GarmentSpecPanel({
  open,
  objectName,
  demoVersion,
  version,
  onClose,
}: GarmentSpecPanelProps) {
  const reduceMotion = useReducedMotion()
  const panelRef = useRef<HTMLElement>(null)
  const closeButtonRef = useRef<HTMLButtonElement>(null)
  const onCloseRef = useRef(onClose)
  const demoSpec = demoVersion ? demoSpecs[demoVersion.number] : undefined

  useEffect(() => {
    onCloseRef.current = onClose
  }, [onClose])

  useEffect(() => {
    if (!open) return
    const previouslyFocused = document.activeElement instanceof HTMLElement
      ? document.activeElement
      : null
    const panel = panelRef.current
    const focusFrame = window.requestAnimationFrame(() => closeButtonRef.current?.focus())
    const closeOnEscape = (event: globalThis.KeyboardEvent) => {
      if (event.key !== 'Escape') return
      event.preventDefault()
      onCloseRef.current()
    }
    document.addEventListener('keydown', closeOnEscape)
    return () => {
      window.cancelAnimationFrame(focusFrame)
      document.removeEventListener('keydown', closeOnEscape)
      if (panel?.contains(document.activeElement)) previouslyFocused?.focus()
    }
  }, [open])

  const versionNumber = demoVersion?.number ?? version?.version_number
  const requestedChange = demoVersion?.change ?? version?.requested_change
  const hasCanonicalRaster = Boolean(version?.asset_url)

  return (
    <AnimatePresence>
      {open && (
        <motion.aside
          ref={panelRef}
          className="garment-spec-panel"
          role="dialog"
          aria-modal="false"
          aria-labelledby="garment-spec-title"
          initial={{ opacity: 0, x: reduceMotion ? 0 : 32 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: reduceMotion ? 0 : 24 }}
          transition={{ duration: reduceMotion ? 0 : 0.28, ease: [0.22, 1, 0.36, 1] }}
        >
          <header className="garment-spec-panel__header">
            <div>
              <span>GARMENT SPEC / {versionNumber ? `VERSION ${String(versionNumber).padStart(2, '0')}` : 'UNSET'}</span>
              <h2 id="garment-spec-title">{objectName.trim() || 'Garment'}</h2>
            </div>
            <button ref={closeButtonRef} type="button" onClick={onClose} aria-label="Close garment specification">
              Close ×
            </button>
          </header>

          <div className="garment-spec-scroll" role="region" aria-label="Garment specification details" tabIndex={0}>
            <div className="garment-spec-panel__body">
              <section className="garment-spec-change" aria-labelledby="garment-change-label">
                <span id="garment-change-label">CHANGE / CURRENT VERSION</span>
                <p>{requestedChange?.trim() || 'Not set'}</p>
              </section>

              {demoSpec ? (
                <dl className="garment-spec-fields">
                  {demoSpec.fields.map((field) => (
                    <div key={field.label}>
                      <dt>{field.label}</dt>
                      <dd>{field.value}</dd>
                    </div>
                  ))}
                </dl>
              ) : (
                <dl className="garment-spec-fields garment-spec-fields--authoritative">
                  <div>
                    <dt>Object</dt>
                    <dd>{objectName.trim() || 'Not set'}</dd>
                  </div>
                  <div>
                    <dt>Version</dt>
                    <dd>{versionNumber ? String(versionNumber).padStart(2, '0') : 'Not set'}</dd>
                  </div>
                  <div>
                    <dt>Requested change</dt>
                    <dd>{requestedChange?.trim() || 'Not set'}</dd>
                  </div>
                </dl>
              )}

              <section className="garment-spec-list" aria-labelledby="garment-keep-label">
                <h3 id="garment-keep-label">KEEP / INVARIANTS</h3>
                <ListOrUnknown items={demoSpec?.keep ?? version?.preserve} />
              </section>

              <section className="garment-spec-list garment-spec-list--avoid" aria-labelledby="garment-avoid-label">
                <h3 id="garment-avoid-label">AVOID / OUT OF SCOPE</h3>
                <ListOrUnknown items={demoSpec?.avoid ?? version?.avoid} />
              </section>

              <footer className="garment-spec-panel__footer">
                <strong>
                  {hasCanonicalRaster
                    ? 'CURRENT VERSION / HELD'
                    : demoVersion
                      ? 'PREPARED VERSION / READY TO REVIEW'
                      : 'FIRST VERSION / NOT MADE'}
                </strong>
                <p>
                  {hasCanonicalRaster
                    ? 'The next move begins here. The current version remains unchanged while the new one is made.'
                    : demoVersion
                      ? 'Use this look as a starting point, then describe the first change you want to own.'
                      : 'Describe the garment you want to make before defining the next change.'}
                </p>
              </footer>
            </div>
          </div>
        </motion.aside>
      )}
    </AnimatePresence>
  )
}
