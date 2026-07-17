import { motion, useReducedMotion } from 'motion/react'
import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type KeyboardEvent,
  type MouseEvent,
  type PointerEvent,
  type WheelEvent,
} from 'react'
import type { ReferenceCatalogItem, ReferenceItem, StudioSeed } from '../lib/types'
import { CanvasContextMenu, type CanvasMenuAction } from './CanvasContextMenu'
import { CastingPanel, type PresentationRender } from './CastingPanel'
import { ChatDock } from './ChatDock'
import { DevDayLookStudy } from './demo'
import { GarmentStudy } from './GarmentStudy'
import { InspirationPanel } from './InspirationPanel'

type StudioProps = {
  seed: StudioSeed
  onReferencesChange: (references: ReferenceItem[]) => void
  onReset: () => void
}

type Viewport = {
  x: number
  y: number
  zoom: number
  tilt: number
}

type ContextMenuPoint = { x: number; y: number }
type DemoVersionNumber = 1 | 2 | 3

type BackendVersion = {
  id: string
  version_number: number
  requested_change: string
  status: 'concept' | 'ready'
  asset_url?: string | null
}

const defaultViewport: Viewport = { x: 0, y: 20, zoom: 1.08, tilt: 0 }

const demoVersions: Array<{
  number: DemoVersionNumber
  code: string
  label: string
  change: string
}> = [
  { number: 1, code: 'WASH', label: 'Washed flight', change: 'Charcoal abrasion / full flight proportion' },
  { number: 2, code: 'SEAM', label: 'Inside-out', change: 'Exposed construction / orange bartacks' },
  { number: 3, code: 'CROP', label: 'Mineral crop', change: 'Cropped utility / mineral olive surface' },
]

const referencePositions = [
  { x: 252, y: 128, rotate: -4 },
  { x: 982, y: 126, rotate: 5 },
  { x: 1062, y: 520, rotate: -3 },
  { x: 120, y: 520, rotate: 4 },
  { x: 354, y: 618, rotate: -4 },
  { x: 852, y: 638, rotate: 3 },
  { x: 294, y: 72, rotate: 2 },
  { x: 1140, y: 284, rotate: -5 },
]

const clamp = (value: number, minimum: number, maximum: number) =>
  Math.min(maximum, Math.max(minimum, value))

function ReferenceCard({
  reference,
  index,
  onRemove,
}: {
  reference: ReferenceItem
  index: number
  onRemove: () => void
}) {
  const position = referencePositions[index % referencePositions.length]
  return (
    <motion.article
      className="canvas-reference"
      style={{ left: position.x, top: position.y, rotate: position.rotate }}
      initial={{ opacity: 0, scale: 0.92, y: 18 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      transition={{ delay: 0.18 + index * 0.08, duration: 0.45 }}
    >
      <button
        type="button"
        className="canvas-reference__remove"
        onClick={onRemove}
        aria-label={`Remove ${reference.name} from canvas`}
      >
        ×
      </button>
      <div className="canvas-reference__image">
        {reference.previewUrl ? (
          <img src={reference.previewUrl} alt={reference.name} />
        ) : (
          <span className="reference-link-mark" aria-hidden="true">↗</span>
        )}
      </div>
      <footer>
        <span>REF / {String(index + 1).padStart(2, '0')}</span>
        <strong>{reference.name}</strong>
        {reference.labelName && <em>{reference.labelName} / TRAIT LINK</em>}
      </footer>
    </motion.article>
  )
}

export function Studio({ seed, onReferencesChange, onReset }: StudioProps) {
  const reduceMotion = useReducedMotion()
  const [viewport, setViewport] = useState<Viewport>(defaultViewport)
  const [activeVersion, setActiveVersion] = useState<DemoVersionNumber>(1)
  const [backendVersions, setBackendVersions] = useState<BackendVersion[]>([])
  const [activeBackendVersionId, setActiveBackendVersionId] = useState('')
  const [revisionCount, setRevisionCount] = useState(1)
  const [inspirationOpen, setInspirationOpen] = useState(false)
  const [castingOpen, setCastingOpen] = useState(false)
  const [contextMenu, setContextMenu] = useState<ContextMenuPoint | null>(null)
  const [castingPreset, setCastingPreset] = useState('Sun-Faded Minimalist')
  const [presentation, setPresentation] = useState<PresentationRender | null>(null)
  const canvasRef = useRef<HTMLDivElement>(null)
  const syncedReferenceIds = useRef(new Set<string>())
  const dragOrigin = useRef<{ pointerX: number; pointerY: number; x: number; y: number } | null>(null)

  const applyProjectSnapshot = useCallback((snapshot: { versions?: BackendVersion[] }) => {
    const versions = snapshot.versions ?? []
    setBackendVersions(versions)
    setActiveBackendVersionId((current) =>
      versions.some((version) => version.id === current) ? current : (versions.at(-1)?.id ?? ''),
    )
  }, [])

  const refreshProject = useCallback(async () => {
    const response = await fetch(`/api/projects/${seed.projectId}`, {
      headers: { Accept: 'application/json' },
    })
    if (!response.ok) return
    applyProjectSnapshot((await response.json()) as { versions?: BackendVersion[] })
  }, [applyProjectSnapshot, seed.projectId])

  useEffect(() => {
    const controller = new AbortController()
    void fetch(`/api/projects/${seed.projectId}`, {
      method: 'PUT',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify({
        object_name: seed.objectName,
        taste_signals: seed.selectedBrands.map((brand) => ({
          id: brand.id,
          name: brand.name,
          tags: brand.tags,
        })),
      }),
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) return
        applyProjectSnapshot((await response.json()) as { versions?: BackendVersion[] })
      })
      .catch(() => undefined)
    return () => controller.abort()
  }, [applyProjectSnapshot, seed.objectName, seed.projectId, seed.selectedBrands])

  useEffect(() => {
    for (const reference of seed.references) {
      if (syncedReferenceIds.current.has(reference.id)) continue
      syncedReferenceIds.current.add(reference.id)

      if (reference.kind === 'image' && reference.file) {
        const form = new FormData()
        form.append('file', reference.file)
        void fetch(`/api/projects/${seed.projectId}/references`, {
          method: 'POST',
          headers: { Accept: 'application/json' },
          body: form,
        }).catch(() => undefined)
        continue
      }

      const url =
        reference.kind === 'catalog' && reference.previewUrl
          ? new URL(reference.previewUrl, window.location.origin).toString()
          : reference.source
      if (url?.startsWith('http://') || url?.startsWith('https://')) {
        void fetch(`/api/projects/${seed.projectId}/reference-links`, {
          method: 'POST',
          headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
          body: JSON.stringify({ url, label: reference.name }),
        }).catch(() => undefined)
      }
    }
  }, [seed.projectId, seed.references])

  const setZoom = (zoom: number) => {
    setViewport((current) => ({ ...current, zoom: clamp(zoom, 0.35, 4) }))
  }

  const setTilt = (tilt: number) => {
    setViewport((current) => ({ ...current, tilt: clamp(tilt, -12, 12) }))
  }

  const openInspiration = () => {
    setCastingOpen(false)
    setInspirationOpen(true)
  }

  const openCasting = () => {
    setInspirationOpen(false)
    setCastingOpen(true)
  }

  const onWheel = (event: WheelEvent<HTMLDivElement>) => {
    event.preventDefault()
    setContextMenu(null)
    setViewport((current) => {
      if (event.shiftKey) {
        return { ...current, tilt: clamp(current.tilt + event.deltaY * 0.018, -12, 12) }
      }

      const bounds = event.currentTarget.getBoundingClientRect()
      const pointerX = event.clientX - bounds.left - bounds.width / 2
      const pointerY = event.clientY - bounds.top - bounds.height / 2
      const zoom = clamp(current.zoom * Math.exp(-event.deltaY * 0.0012), 0.35, 4)
      const ratio = zoom / current.zoom
      return {
        ...current,
        zoom,
        x: pointerX - (pointerX - current.x) * ratio,
        y: pointerY - (pointerY - current.y) * ratio,
      }
    })
  }

  const onKeyboard = (event: KeyboardEvent<HTMLDivElement>) => {
    const panDistance = event.shiftKey ? 48 : 24
    const actions: Partial<Record<string, () => void>> = {
      ArrowLeft: () => setViewport((current) => ({ ...current, x: current.x - panDistance })),
      ArrowRight: () => setViewport((current) => ({ ...current, x: current.x + panDistance })),
      ArrowUp: () => setViewport((current) => ({ ...current, y: current.y - panDistance })),
      ArrowDown: () => setViewport((current) => ({ ...current, y: current.y + panDistance })),
      '-': () => setZoom(viewport.zoom / 1.25),
      '=': () => setZoom(viewport.zoom * 1.25),
      '+': () => setZoom(viewport.zoom * 1.25),
      '[': () => setTilt(viewport.tilt - 2),
      ']': () => setTilt(viewport.tilt + 2),
      '0': () => setViewport(defaultViewport),
      i: openInspiration,
      m: openCasting,
      Escape: () => {
        setContextMenu(null)
        setInspirationOpen(false)
        setCastingOpen(false)
      },
    }
    const action = actions[event.key]
    if (!action) return
    event.preventDefault()
    action()
  }

  const startPan = (event: PointerEvent<HTMLDivElement>) => {
    setContextMenu(null)
    if ((event.target as HTMLElement).closest('button, input, select, textarea, a, [role="menuitem"]')) return
    event.currentTarget.focus()
    event.currentTarget.setPointerCapture(event.pointerId)
    dragOrigin.current = {
      pointerX: event.clientX,
      pointerY: event.clientY,
      x: viewport.x,
      y: viewport.y,
    }
  }

  const pan = (event: PointerEvent<HTMLDivElement>) => {
    if (!dragOrigin.current) return
    setViewport((current) => ({
      ...current,
      x: dragOrigin.current!.x + event.clientX - dragOrigin.current!.pointerX,
      y: dragOrigin.current!.y + event.clientY - dragOrigin.current!.pointerY,
    }))
  }

  const stopPan = (event: PointerEvent<HTMLDivElement>) => {
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId)
    }
    dragOrigin.current = null
  }

  const openContextMenu = (event: MouseEvent<HTMLDivElement>) => {
    event.preventDefault()
    const bounds = event.currentTarget.getBoundingClientRect()
    setContextMenu({
      x: clamp(event.clientX - bounds.left, 14, Math.max(14, bounds.width - 336)),
      y: clamp(event.clientY - bounds.top, 14, Math.max(14, bounds.height - 430)),
    })
  }

  const closeContextMenu = () => {
    setContextMenu(null)
    window.requestAnimationFrame(() => canvasRef.current?.focus())
  }

  const toggleCatalogReference = (item: ReferenceCatalogItem) => {
    const exists = seed.references.some((reference) => reference.id === item.id)
    if (exists) {
      onReferencesChange(seed.references.filter((reference) => reference.id !== item.id))
      return
    }
    onReferencesChange([
      ...seed.references,
      {
        id: item.id,
        kind: 'catalog',
        name: item.title,
        previewUrl: item.image_url,
        source: 'local-reference-catalog',
        labelId: item.metadata.label_association.id,
        labelName: item.metadata.label_association.name,
        tags: item.metadata.tags,
      },
    ])
  }

  const removeReference = (referenceId: string) => {
    onReferencesChange(seed.references.filter((reference) => reference.id !== referenceId))
  }

  const contextActions: CanvasMenuAction[] = [
    {
      id: 'inspiration',
      label: 'Open inspiration',
      detail: '30 local garment studies',
      shortcut: 'I',
      tone: 'signal',
      onSelect: openInspiration,
    },
    {
      id: 'casting',
      label: 'Style on a model',
      detail: 'Separate lookbook render',
      shortcut: 'M',
      onSelect: openCasting,
    },
    {
      id: 'inspect',
      label: 'Inspect garment',
      detail: 'Center at 170%',
      onSelect: () => setViewport({ x: -16, y: 84, zoom: 1.7, tilt: 0 }),
    },
    {
      id: 'detail',
      label: 'Zoom to detail',
      detail: 'Move in to 400%',
      shortcut: '400%',
      onSelect: () => setZoom(4),
    },
    {
      id: 'straighten',
      label: 'Straighten canvas',
      detail: 'Keep pan and scale',
      shortcut: '0°',
      onSelect: () => setTilt(0),
    },
    {
      id: 'fit',
      label: 'Fit composition',
      detail: 'Reset pan, tilt, and scale',
      shortcut: '0',
      onSelect: () => setViewport(defaultViewport),
    },
  ]

  const version = demoVersions[activeVersion - 1]
  const backendVersion =
    backendVersions.find((item) => item.id === activeBackendVersionId) ?? backendVersions.at(-1)
  const tasteTranslation = seed.selectedBrands.length
    ? `${seed.selectedBrands.map((brand) => brand.name).join(' + ')} → ${seed.selectedBrands
        .flatMap((brand) => brand.tags)
        .slice(0, 4)
        .join(' · ')}`
    : 'OPEN TASTE'

  return (
    <main className="studio-shell">
      <ChatDock
        projectId={seed.projectId}
        objectName={seed.objectName}
        referenceCount={seed.references.length}
        onProjectRefresh={() => {
          setRevisionCount((current) => current + 1)
          void refreshProject()
        }}
      />

      <section className="studio-space">
        <header className="studio-header">
          <div className="studio-wordmark">
            SOMETHINGS<span>—ON</span>
          </div>
          <div className="studio-project">
            <span>{seed.demoMode ? 'DEMO / OPENAI DEV DAY' : 'PROJECT / 001'}</span>
            <strong>{seed.demoMode ? 'DISTRESSED BOMBER + WHITE TEE' : seed.objectName.toUpperCase()}</strong>
          </div>
          <div className="studio-actions">
            <button
              type="button"
              className={inspirationOpen ? 'is-active' : undefined}
              onClick={() => (inspirationOpen ? setInspirationOpen(false) : openInspiration())}
            >
              Inspiration <i>{String(seed.references.length).padStart(2, '0')}</i>
            </button>
            <button
              type="button"
              className={castingOpen ? 'is-active' : undefined}
              onClick={() => (castingOpen ? setCastingOpen(false) : openCasting())}
            >
              Model <i>↗</i>
            </button>
            <button type="button" onClick={onReset}>New object</button>
          </div>
        </header>

        <InspirationPanel
          open={inspirationOpen}
          objectName={seed.objectName}
          selectedBrands={seed.selectedBrands}
          pulledIds={seed.references.map((reference) => reference.id)}
          onToggleReference={toggleCatalogReference}
          onClose={() => setInspirationOpen(false)}
        />

        <CastingPanel
          open={castingOpen}
          projectId={seed.projectId}
          demoMode={seed.demoMode}
          onPreviewPreset={(preset) => setCastingPreset(preset.display_name)}
          onPresentationReady={(nextPresentation) => {
            setPresentation(nextPresentation)
          }}
          onClose={() => setCastingOpen(false)}
        />

        <div
          ref={canvasRef}
          className="canvas-viewport"
          tabIndex={0}
          aria-label="Infinite design canvas. Drag or use arrow keys to pan, scroll to zoom, and shift-scroll or bracket keys to tilt. Right-click for canvas tools."
          onWheel={onWheel}
          onKeyDown={onKeyboard}
          onPointerDown={startPan}
          onPointerMove={pan}
          onPointerUp={stopPan}
          onPointerCancel={stopPan}
          onContextMenu={openContextMenu}
        >
          <motion.div
            className="canvas-plane"
            style={{
              transform: `translate(calc(-50% + ${viewport.x}px), calc(-50% + ${viewport.y}px)) rotate(${viewport.tilt}deg) scale(${viewport.zoom})`,
            }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: reduceMotion ? 0 : 0.8 }}
          >
            {seed.references.map((reference, index) => (
              <ReferenceCard
                key={reference.id}
                reference={reference}
                index={index}
                onRemove={() => removeReference(reference.id)}
              />
            ))}

            <motion.div
              className="canvas-design"
              initial={{ opacity: 0, scale: 0.94 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: reduceMotion ? 0 : 0.2, duration: reduceMotion ? 0 : 0.7 }}
            >
              {presentation?.asset_url ? (
                <figure className="presentation-study">
                  <img src={presentation.asset_url} alt={`Fictional model presentation in ${castingPreset}`} />
                  <figcaption>
                    <span>PRESENTATION / {presentation.id}</span>
                    <strong>DESIGN UNCHANGED</strong>
                  </figcaption>
                </figure>
              ) : seed.demoMode ? (
                <figure className="devday-look-study">
                  <DevDayLookStudy
                    version={activeVersion}
                    label={`Version ${activeVersion}: fictional adult model wearing the DevDay ${version.label} distressed bomber over a white T-shirt`}
                  />
                  <figcaption>
                    <span>DEV DAY / VERSION {String(activeVersion).padStart(2, '0')}</span>
                    <strong>{version.label.toUpperCase()}</strong>
                    <small>FICTIONAL ADULT / DESIGN STUDY</small>
                  </figcaption>
                </figure>
              ) : backendVersion?.asset_url ? (
                <figure className="presentation-study design-version-study">
                  <img src={backendVersion.asset_url} alt={`Design version ${backendVersion.version_number}: ${backendVersion.requested_change}`} />
                  <figcaption>
                    <span>DESIGN / VERSION {String(backendVersion.version_number).padStart(2, '0')}</span>
                    <strong>{backendVersion.requested_change.toUpperCase()}</strong>
                  </figcaption>
                </figure>
              ) : (
                <GarmentStudy label={seed.objectName} />
              )}
              <div className="design-selection" aria-hidden="true">
                <i /><i /><i /><i />
              </div>
            </motion.div>

            <div className="canvas-note canvas-note--one">
              KEEP / {seed.demoMode ? 'WHITE TEE' : 'WEIGHT'}
            </div>
            <div className="canvas-note canvas-note--two">
              CHANGE / {seed.demoMode ? 'BOMBER SURFACE' : 'NECKLINE'}
            </div>
          </motion.div>

          <div className="canvas-controls" aria-label="Canvas view controls">
            <button type="button" onClick={() => setZoom(viewport.zoom / 1.25)} aria-label="Zoom out">−</button>
            <span>{Math.round(viewport.zoom * 100)}%</span>
            <button type="button" onClick={() => setZoom(viewport.zoom * 1.25)} aria-label="Zoom in">+</button>
            <button type="button" onClick={() => setTilt(viewport.tilt - 2)} aria-label="Tilt left">↶</button>
            <span>{Math.round(viewport.tilt)}°</span>
            <button type="button" onClick={() => setTilt(viewport.tilt + 2)} aria-label="Tilt right">↷</button>
            <button type="button" onClick={() => setViewport(defaultViewport)}>Center</button>
          </div>

          <p className="canvas-help">Drag to pan · scroll to scale · shift + scroll to tilt · right-click for tools</p>

          {contextMenu && (
            <CanvasContextMenu
              x={contextMenu.x}
              y={contextMenu.y}
              actions={contextActions}
              onClose={closeContextMenu}
            />
          )}
        </div>

        <aside className="version-rail" aria-label="Design versions">
          <span>VERSIONS</span>
          {seed.demoMode
            ? demoVersions.map((item) => (
                <button
                  type="button"
                  key={item.number}
                  className={`version-thumb ${activeVersion === item.number ? 'is-current' : ''}`}
                  aria-label={`Version ${item.number}: ${item.label}`}
                  aria-pressed={activeVersion === item.number}
                  onClick={() => {
                    setActiveVersion(item.number)
                    setPresentation(null)
                  }}
                >
                  <i>{String(item.number).padStart(2, '0')}</i>
                  <b>{item.code}</b>
                </button>
              ))
            : (backendVersions.length ? backendVersions : [{ id: 'base', version_number: 1, requested_change: 'Base', status: 'concept' as const }]).map((item) => (
                <button
                  type="button"
                  key={item.id}
                  className={`version-thumb ${backendVersion?.id === item.id || (!backendVersion && item.id === 'base') ? 'is-current' : ''}`}
                  aria-label={`Version ${item.version_number}: ${item.requested_change}`}
                  aria-pressed={backendVersion?.id === item.id}
                  onClick={() => {
                    setActiveBackendVersionId(item.id)
                    setPresentation(null)
                  }}
                >
                  <i>{String(item.version_number).padStart(2, '0')}</i>
                  <b>{item.status === 'ready' ? 'READY' : 'BASE'}</b>
                </button>
              ))}
        </aside>

        <footer className="studio-footer">
          <span>
            {seed.demoMode
              ? `V${String(activeVersion).padStart(2, '0')} / ${version.label.toUpperCase()}`
              : `V${String(backendVersion?.version_number ?? 1).padStart(2, '0')} / ${backendVersion?.status.toUpperCase() ?? 'BASE'}`}
          </span>
          <p>
            {seed.demoMode ? version.change : (backendVersion?.requested_change ?? seed.objectName)} · REFERENCE →{' '}
            {tasteTranslation}
          </p>
          <span>{presentation ? `PRESENTATION / ${castingPreset.toUpperCase()}` : `STUDY ${String(revisionCount).padStart(3, '0')}`}</span>
        </footer>
      </section>
    </main>
  )
}
