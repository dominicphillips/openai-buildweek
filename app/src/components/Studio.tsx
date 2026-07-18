import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type KeyboardEvent,
  type MouseEvent,
  type PointerEvent,
} from 'react'
import type { ReferenceCatalogItem, ReferenceItem, StudioSeed } from '../lib/types'
import { CanvasContextMenu, type CanvasMenuAction } from './CanvasContextMenu'
import { CastingPanel, type PresentationRender } from './CastingPanel'
import { ChatDock } from './ChatDock'
import { GarmentSpecPanel } from './GarmentSpecPanel'
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
  preserve?: string[]
  avoid?: string[]
  status: 'concept' | 'ready'
  asset_url?: string | null
}

type ProjectSnapshot = {
  versions?: BackendVersion[]
  presentations?: PresentationRender[]
  link_references?: Array<{ url: string }>
}

type StudioSelection = {
  versionId: string
  presentationId: string | null
}

type StoredStudioView = StudioSelection & {
  demoVersion: DemoVersionNumber
  found: boolean
}

const defaultViewport: Viewport = { x: 0, y: 20, zoom: 1.08, tilt: 0 }

const demoVersions: Array<{
  number: DemoVersionNumber
  code: string
  label: string
  change: string
  keep: string
  imageUrl: string
}> = [
  {
    number: 1,
    code: 'WASH',
    label: 'Washed flight',
    change: 'Washed charcoal / full flight length',
    keep: 'T-shirt / camera / pose',
    imageUrl: '/devday/devday-look-v1.png',
  },
  {
    number: 2,
    code: 'SEAM',
    label: 'Inside-out',
    change: 'Exposed seams / orange bartacks',
    keep: 'Flight shape / T-shirt / camera / pose',
    imageUrl: '/devday/devday-look-v2.png',
  },
  {
    number: 3,
    code: 'CROP',
    label: 'High-hip crop',
    change: 'High-hip crop / body −90 mm',
    keep: 'Seams / T-shirt / camera / pose',
    imageUrl: '/devday/devday-look-v3.png',
  },
]

const newestVersion = (versions: BackendVersion[], rasterOnly = false) =>
  versions.reduce<BackendVersion | undefined>((newest, candidate) => {
    if (rasterOnly && !candidate.asset_url) return newest
    if (!newest || candidate.version_number > newest.version_number) return candidate
    return newest
  }, undefined)

const latestReadyPresentation = (
  presentations: PresentationRender[],
  versionId: string,
) =>
  [...presentations]
    .reverse()
    .find(
      (candidate) =>
        candidate.status === 'ready' &&
        Boolean(candidate.asset_url) &&
        candidate.design_version_id === versionId,
    )

const studioViewStorageKey = (projectId: string) =>
  `somethings-on:studio-view:${projectId}:v1`

const loadStudioView = (projectId: string): StoredStudioView => {
  const fallback: StoredStudioView = {
    versionId: '',
    presentationId: null,
    demoVersion: 3,
    found: false,
  }

  try {
    const raw = window.localStorage.getItem(studioViewStorageKey(projectId))
    if (!raw) return fallback
    const stored = JSON.parse(raw) as Partial<StoredStudioView>
    const versionId =
      typeof stored.versionId === 'string' && stored.versionId.length <= 200
        ? stored.versionId
        : ''
    const presentationId =
      typeof stored.presentationId === 'string' && stored.presentationId.length <= 200
        ? stored.presentationId
        : null
    const demoVersion =
      stored.demoVersion === 1 || stored.demoVersion === 2 || stored.demoVersion === 3
        ? stored.demoVersion
        : 3
    return { versionId, presentationId, demoVersion, found: true }
  } catch {
    return fallback
  }
}

const presentationLabel = (presetId: string) =>
  presetId.replaceAll('-', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())

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
  const [initialView] = useState(() => loadStudioView(seed.projectId))
  const [viewport, setViewport] = useState<Viewport>(defaultViewport)
  const [activeDemoVersion, setActiveDemoVersion] = useState<DemoVersionNumber>(
    initialView.demoVersion,
  )
  const [backendVersions, setBackendVersions] = useState<BackendVersion[]>([])
  const [backendPresentations, setBackendPresentations] = useState<PresentationRender[]>([])
  const [selection, setSelection] = useState<StudioSelection>({
    versionId: initialView.versionId,
    presentationId: initialView.presentationId,
  })
  const [inspirationOpen, setInspirationOpen] = useState(false)
  const [castingOpen, setCastingOpen] = useState(false)
  const [specOpen, setSpecOpen] = useState(false)
  const [contextMenu, setContextMenu] = useState<ContextMenuPoint | null>(null)
  const [projectHydrated, setProjectHydrated] = useState(false)
  const [generationWorking, setGenerationWorking] = useState(false)
  const [generationError, setGenerationError] = useState('')
  const [editorialDirection, setEditorialDirection] = useState<string | null>(null)
  const [failedDemoImages, setFailedDemoImages] = useState<string[]>([])
  const canvasRef = useRef<HTMLDivElement>(null)
  const syncedReferenceIds = useRef(new Set<string>())
  const serverReferenceUrls = useRef(new Set<string>())
  const initialGenerationProjects = useRef(new Set<string>())
  const dragOrigin = useRef<{ pointerX: number; pointerY: number; x: number; y: number } | null>(null)

  useEffect(() => {
    try {
      window.localStorage.setItem(
        studioViewStorageKey(seed.projectId),
        JSON.stringify({
          versionId: selection.versionId,
          presentationId: selection.presentationId,
          demoVersion: activeDemoVersion,
        }),
      )
    } catch {
      // The authoritative version history remains on the backend if storage is unavailable.
    }
  }, [activeDemoVersion, seed.projectId, selection])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const handleWheel = (event: globalThis.WheelEvent) => {
      event.preventDefault()

      const bounds = canvas.getBoundingClientRect()
      if (bounds.width === 0 || bounds.height === 0) return

      const pointerX = event.clientX - bounds.left - bounds.width / 2
      const pointerY = event.clientY - bounds.top - bounds.height / 2
      const deltaScale = event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? bounds.height : 1
      const verticalDelta = event.deltaY * deltaScale
      const tiltDelta = (event.deltaY || event.deltaX) * deltaScale
      const shouldTilt = event.shiftKey

      setContextMenu(null)
      setViewport((current) => {
        if (shouldTilt) {
          return { ...current, tilt: clamp(current.tilt + tiltDelta * 0.018, -12, 12) }
        }

        const zoom = clamp(current.zoom * Math.exp(-verticalDelta * 0.0012), 0.35, 4)
        const ratio = zoom / current.zoom
        return {
          ...current,
          zoom,
          x: pointerX - (pointerX - current.x) * ratio,
          y: pointerY - (pointerY - current.y) * ratio,
        }
      })
    }

    canvas.addEventListener('wheel', handleWheel, { passive: false })
    return () => canvas.removeEventListener('wheel', handleWheel)
  }, [])

  const applyProjectSnapshot = useCallback(
    (
      snapshot: ProjectSnapshot,
      options: {
        preferredVersionId?: string
        showCanonical?: boolean
        restoreLatestPresentation?: boolean
      } = {},
    ) => {
      const versions = snapshot.versions ?? []
      const presentations = snapshot.presentations ?? []
      const newest = newestVersion(versions, true) ?? newestVersion(versions)
      setBackendVersions(versions)
      setBackendPresentations(presentations)
      serverReferenceUrls.current = new Set(
        (snapshot.link_references ?? []).map((reference) => reference.url),
      )
      setSelection((current) => {
        const preferredVersion = versions.find(
          (candidate) => candidate.id === options.preferredVersionId,
        )
        const currentVersion = versions.find((candidate) => candidate.id === current.versionId)
        const versionId = preferredVersion?.id ?? currentVersion?.id ?? newest?.id ?? ''
        const currentPresentation = presentations.find(
          (candidate) =>
            candidate.id === current.presentationId &&
            candidate.status === 'ready' &&
            Boolean(candidate.asset_url) &&
            candidate.design_version_id === versionId,
        )
        const restoredPresentation = options.restoreLatestPresentation
          ? latestReadyPresentation(presentations, versionId)
          : undefined
        return {
          versionId,
          presentationId: options.showCanonical
            ? null
            : (currentPresentation?.id ?? restoredPresentation?.id ?? null),
        }
      })
      setProjectHydrated(true)
    },
    [],
  )

  const refreshProject = useCallback(async (
    options?: Parameters<typeof applyProjectSnapshot>[1],
  ) => {
    const response = await fetch(`/api/projects/${seed.projectId}`, {
      headers: { Accept: 'application/json' },
    })
    if (!response.ok) return
    applyProjectSnapshot((await response.json()) as ProjectSnapshot, options)
  }, [applyProjectSnapshot, seed.projectId])

  const handleProjectRefresh = useCallback(
    async (createdVersion?: { id: string; number: number }) => {
      await refreshProject(
        createdVersion
          ? { preferredVersionId: createdVersion.id, showCanonical: true }
          : undefined,
      )
    },
    [refreshProject],
  )

  const handleEditorialPending = useCallback((pending: boolean, direction?: string) => {
    setEditorialDirection(pending ? direction ?? 'Selected direction' : null)
  }, [])

  const createInitialVersion = useCallback(async () => {
    const generationKey = `${seed.projectId}:${seed.objectName.trim().toLowerCase()}`
    if (initialGenerationProjects.current.has(generationKey)) return
    initialGenerationProjects.current.add(generationKey)
    setGenerationError('')
    setGenerationWorking(true)
    try {
      const response = await fetch(`/api/projects/${seed.projectId}/versions`, {
        method: 'POST',
        headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
        body: JSON.stringify({
          requested_change: `Create the first product-view study for the ${seed.objectName}.`,
          preserve: ['full garment visibility', 'production-legible construction'],
          avoid: ['logos or readable text', 'a person or extra styling'],
        }),
      })
      const body = (await response.json()) as BackendVersion & { detail?: string }
      if (!response.ok) throw new Error(body.detail || 'The first version did not finish.')
      await refreshProject({ preferredVersionId: body.id, showCanonical: true })
    } catch (error) {
      initialGenerationProjects.current.delete(generationKey)
      setGenerationError(
        error instanceof Error ? error.message : 'The first version did not finish.',
      )
    } finally {
      setGenerationWorking(false)
    }
  }, [refreshProject, seed.objectName, seed.projectId])

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
        const snapshot = (await response.json()) as ProjectSnapshot
        applyProjectSnapshot(snapshot, {
          restoreLatestPresentation: !initialView.found,
        })
        if (!(snapshot.versions ?? []).some((version) => Boolean(version.asset_url))) {
          await createInitialVersion()
        }
      })
      .catch(() => undefined)
    return () => controller.abort()
  }, [applyProjectSnapshot, createInitialVersion, initialView.found, seed.objectName, seed.projectId, seed.selectedBrands])

  useEffect(() => {
    if (!projectHydrated) return
    for (const reference of seed.references) {
      if (syncedReferenceIds.current.has(reference.id)) continue

      if (reference.kind === 'image' && reference.file) {
        syncedReferenceIds.current.add(reference.id)
        const form = new FormData()
        form.append('file', reference.file)
        void fetch(`/api/projects/${seed.projectId}/references`, {
          method: 'POST',
          headers: { Accept: 'application/json' },
          body: form,
        }).catch(() => syncedReferenceIds.current.delete(reference.id))
        continue
      }

      const explicitSource = reference.source?.startsWith('http://') || reference.source?.startsWith('https://')
        ? reference.source
        : undefined
      const url =
        explicitSource ??
        (reference.kind === 'catalog' && reference.previewUrl
          ? new URL(reference.previewUrl, window.location.origin).toString()
          : reference.source)
      if (url?.startsWith('http://') || url?.startsWith('https://')) {
        if (serverReferenceUrls.current.has(url)) {
          syncedReferenceIds.current.add(reference.id)
          continue
        }
        syncedReferenceIds.current.add(reference.id)
        serverReferenceUrls.current.add(url)
        void fetch(`/api/projects/${seed.projectId}/reference-links`, {
          method: 'POST',
          headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
          body: JSON.stringify({ url, label: reference.name }),
        })
          .then((response) => {
            if (!response.ok) {
              syncedReferenceIds.current.delete(reference.id)
              serverReferenceUrls.current.delete(url)
              return
            }
          })
          .catch(() => {
            syncedReferenceIds.current.delete(reference.id)
            serverReferenceUrls.current.delete(url)
          })
      }
    }
  }, [projectHydrated, seed.projectId, seed.references])

  const setZoom = (zoom: number) => {
    setViewport((current) => ({ ...current, zoom: clamp(zoom, 0.35, 4) }))
  }

  const setTilt = (tilt: number) => {
    setViewport((current) => ({ ...current, tilt: clamp(tilt, -12, 12) }))
  }

  const openInspiration = () => {
    setContextMenu(null)
    setCastingOpen(false)
    setSpecOpen(false)
    setInspirationOpen(true)
  }

  const openCasting = () => {
    setContextMenu(null)
    setInspirationOpen(false)
    setSpecOpen(false)
    setCastingOpen(true)
  }

  const openSpec = () => {
    setContextMenu(null)
    setInspirationOpen(false)
    setCastingOpen(false)
    setSpecOpen(true)
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
      s: openSpec,
      Escape: () => {
        setContextMenu(null)
        setInspirationOpen(false)
        setCastingOpen(false)
        setSpecOpen(false)
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
    const origin = dragOrigin.current
    if (!origin) return
    const { clientX, clientY } = event
    setViewport((current) => ({
      ...current,
      x: origin.x + clientX - origin.pointerX,
      y: origin.y + clientY - origin.pointerY,
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
        name: item.product_name ?? item.metadata.product_name ?? item.title,
        previewUrl: item.image_url,
        source: item.source_url ?? item.metadata.source_url ?? 'product-inspiration-catalog',
        labelId: item.metadata.label_association.id,
        labelName: item.brand ?? item.metadata.brand ?? item.metadata.label_association.name,
        tags: item.neutral_attributes ?? item.metadata.neutral_attributes ?? item.metadata.tags,
      },
    ])
  }

  const removeReference = (referenceId: string) => {
    onReferencesChange(seed.references.filter((reference) => reference.id !== referenceId))
  }

  const selectBackendVersion = (versionId: string) => {
    setSelection((current) => {
      if (current.versionId === versionId) return current
      const linkedPresentation = latestReadyPresentation(backendPresentations, versionId)
      return {
        versionId,
        presentationId: linkedPresentation?.id ?? null,
      }
    })
  }

  const contextActions: CanvasMenuAction[] = [
    {
      id: 'inspiration',
      label: 'Open inspiration',
      detail: 'Browse sourced products',
      shortcut: 'I',
      tone: 'signal',
      onSelect: openInspiration,
    },
    {
      id: 'casting',
      label: 'Open editorial',
      detail: 'Cast, style, and place the look',
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

  const backendVersion =
    backendVersions.find((item) => item.id === selection.versionId) ??
    newestVersion(backendVersions, true) ??
    newestVersion(backendVersions)
  const presentation =
    backendPresentations.find(
      (candidate) =>
        candidate.id === selection.presentationId &&
        candidate.design_version_id === backendVersion?.id &&
        candidate.status === 'ready' &&
        Boolean(candidate.asset_url),
    ) ?? null
  const hasBackendRender = Boolean(backendVersion?.asset_url)
  const hasAnyBackendRaster = backendVersions.some((item) => Boolean(item.asset_url))
  const usePreparedDemo = seed.demoMode && !hasAnyBackendRaster
  const demoVersion = demoVersions[activeDemoVersion - 1]
  const seededDemoVersion = seed.demoMode
    ? demoVersions.find((item) => item.number === backendVersion?.version_number)
    : undefined
  const demoImageFailed = failedDemoImages.includes(demoVersion.imageUrl)
  const keepNote = usePreparedDemo
    ? demoVersion.keep
    : (seededDemoVersion?.keep ?? backendVersion?.preserve?.[0]?.trim())
  const changeNote = usePreparedDemo
    ? demoVersion.change
    : (seededDemoVersion?.change ?? backendVersion?.requested_change.trim())
  const railVersions = backendVersions.some((item) => item.status === 'ready' && item.asset_url)
    ? backendVersions
        .filter((item) => item.status === 'ready' && item.asset_url)
        .sort((left, right) => left.version_number - right.version_number)
    : [{ id: 'base', version_number: 1, requested_change: 'No raster yet', status: 'concept' as const }]
  const workingState = editorialDirection
    ? {
        key: 'editorial',
        title: 'WORKING ON IT',
        detail: `EDITORIAL / ${editorialDirection.toUpperCase()}`,
        note: 'Pose, place, and light are changing. The garment stays.',
      }
    : generationWorking
      ? {
          key: 'generation',
          title: 'WORKING ON IT',
          detail: 'APPLYING YOUR CHANGE',
          note: 'The current version stays here until the next draft is ready.',
        }
      : null

  return (
    <main className="studio-shell">
      <ChatDock
        projectId={seed.projectId}
        objectName={seed.objectName}
        referenceCount={seed.references.length}
        activeVersionId={backendVersion?.asset_url ? backendVersion.id : undefined}
        externalBusy={Boolean(editorialDirection)}
        onProjectRefresh={handleProjectRefresh}
        onWorkingChange={setGenerationWorking}
      />

      <section className="studio-space">
        <header className="studio-header">
          <div className="studio-wordmark">
            SOMETHINGS<span>—ON</span>
          </div>
          <div
            className="studio-project"
            title={seed.demoMode ? 'DEV DAY / 001 · DISTRESSED BOMBER + WHITE TEE' : `PROJECT / 001 · ${seed.objectName.toUpperCase()}`}
          >
            <span>{seed.demoMode ? 'DEV DAY / 001' : 'PROJECT / 001'}</span>
            <i aria-hidden="true">·</i>
            <strong>{seed.demoMode ? 'DISTRESSED BOMBER + WHITE TEE' : seed.objectName.toUpperCase()}</strong>
          </div>
          <div className="studio-actions">
            <button
              type="button"
              className={inspirationOpen ? 'is-active' : undefined}
              onClick={() => (inspirationOpen ? setInspirationOpen(false) : openInspiration())}
            >
              Inspiration
            </button>
            <button
              type="button"
              className={castingOpen ? 'is-active' : undefined}
              onClick={() => (castingOpen ? setCastingOpen(false) : openCasting())}
            >
              Editorial
            </button>
            <button
              type="button"
              className={specOpen ? 'is-active' : undefined}
              onClick={() => (specOpen ? setSpecOpen(false) : openSpec())}
              aria-haspopup="dialog"
              aria-expanded={specOpen}
            >
              Spec
            </button>
            <button type="button" onClick={onReset}>New garment</button>
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
          designVersionId={backendVersion?.asset_url ? backendVersion.id : undefined}
          selectedPresetId={presentation?.preset_id}
          blocked={generationWorking}
          onPreviewPreset={() => undefined}
          onPresentationReady={(nextPresentation) => {
            setBackendPresentations((current) => [
              ...current.filter((candidate) => candidate.id !== nextPresentation.id),
              nextPresentation,
            ])
            setSelection({
              versionId: nextPresentation.design_version_id,
              presentationId: nextPresentation.id,
            })
          }}
          onPendingChange={handleEditorialPending}
          onClose={() => setCastingOpen(false)}
        />

        <GarmentSpecPanel
          open={specOpen}
          objectName={seed.objectName}
          demoVersion={usePreparedDemo ? { number: activeDemoVersion, change: demoVersion.change } : undefined}
          version={usePreparedDemo ? undefined : backendVersion}
          onClose={() => setSpecOpen(false)}
        />

        <div
          ref={canvasRef}
          className="canvas-viewport"
          tabIndex={0}
          aria-label="Infinite design canvas. Drag or use arrow keys to pan, scroll to zoom, and shift-scroll or bracket keys to tilt. Right-click for canvas tools."
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
              className={`canvas-design ${workingState ? 'is-working' : ''}`}
              aria-busy={Boolean(workingState)}
              initial={{ opacity: 0, scale: 0.94 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: reduceMotion ? 0 : 0.2, duration: reduceMotion ? 0 : 0.7 }}
            >
              {presentation?.asset_url ? (
                <figure className="presentation-study">
                  <img
                    src={presentation.asset_url}
                    alt={`Editorial presentation in ${presentationLabel(presentation.preset_id)}`}
                  />
                  <figcaption>
                    <span>
                      {backendVersion
                        ? `EDITORIAL / VERSION ${String(backendVersion.version_number).padStart(2, '0')}`
                        : 'EDITORIAL'}
                    </span>
                    <strong>DESIGN UNCHANGED</strong>
                  </figcaption>
                </figure>
              ) : backendVersion?.asset_url ? (
                <figure className="presentation-study design-version-study">
                  <img
                    key={backendVersion.asset_url}
                    src={backendVersion.asset_url}
                    alt={`Current design version ${backendVersion.version_number}: ${backendVersion.requested_change}`}
                  />
                  <figcaption>
                    <span>DESIGN / VERSION {String(backendVersion.version_number).padStart(2, '0')}</span>
                    <strong>{backendVersion.requested_change.toUpperCase()}</strong>
                  </figcaption>
                </figure>
              ) : usePreparedDemo && !demoImageFailed ? (
                <figure className="devday-look-study devday-photo-study">
                  <img
                    key={demoVersion.imageUrl}
                    src={demoVersion.imageUrl}
                    alt={`Generated DevDay design study, version ${activeDemoVersion}: ${demoVersion.label} distressed bomber and T-shirt`}
                    onError={() => {
                      setFailedDemoImages((current) =>
                        current.includes(demoVersion.imageUrl)
                          ? current
                          : [...current, demoVersion.imageUrl],
                      )
                    }}
                  />
                  <figcaption>
                    <span>DEV DAY / VERSION {String(activeDemoVersion).padStart(2, '0')}</span>
                    <strong>{demoVersion.label.toUpperCase()}</strong>
                    <small>DESIGN STUDY / PREPARED VERSION</small>
                  </figcaption>
                </figure>
              ) : (
                <div className="image-generation-empty" role="status">
                  <span>VERSION 01</span>
                  <strong>{generationError || 'Making the first product view.'}</strong>
                  <p>{generationError ? 'Your brief is saved.' : seed.objectName}</p>
                  {generationError && (
                    <button type="button" onClick={() => void createInitialVersion()}>
                      Try again
                    </button>
                  )}
                </div>
              )}
              <div className="design-selection" aria-hidden="true">
                <i /><i /><i /><i />
              </div>
              <AnimatePresence mode="wait">
                {workingState && (
                  <motion.div
                    key={workingState.key}
                    className="canvas-work-state"
                    role="status"
                    aria-live="polite"
                    aria-atomic="true"
                    initial={{ opacity: 0, y: reduceMotion ? 0 : 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: reduceMotion ? 0 : -8 }}
                    transition={{ duration: reduceMotion ? 0 : 0.26 }}
                  >
                    <span>{workingState.title}</span>
                    <strong>{workingState.detail}</strong>
                    <p>{workingState.note}</p>
                    <div className="canvas-work-state__mark" aria-hidden="true">
                      <i /><i /><i />
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>

            {(presentation?.asset_url || hasBackendRender || (usePreparedDemo && !demoImageFailed)) && (
              <>
                {keepNote && (
                  <div className="canvas-note canvas-note--one" title={`KEEP / ${keepNote}`}>
                    KEEP / {keepNote.toUpperCase()}
                  </div>
                )}
                {changeNote && (
                  <div className="canvas-note canvas-note--two" title={`CHANGE / ${changeNote}`}>
                    CHANGE / {changeNote.toUpperCase()}
                  </div>
                )}
              </>
            )}
          </motion.div>

          {!inspirationOpen && !castingOpen && !specOpen && (
            <>
              <div className="canvas-controls" aria-label="Canvas view controls">
                <button type="button" onClick={() => setZoom(viewport.zoom / 1.25)} aria-label="Zoom out">−</button>
                <span>{Math.round(viewport.zoom * 100)}%</span>
                <button type="button" onClick={() => setZoom(viewport.zoom * 1.25)} aria-label="Zoom in">+</button>
                <button type="button" onClick={() => setTilt(viewport.tilt - 2)} aria-label="Tilt left">↶</button>
                <span>{Math.round(viewport.tilt)}°</span>
                <button type="button" onClick={() => setTilt(viewport.tilt + 2)} aria-label="Tilt right">↷</button>
                <button type="button" onClick={() => setViewport(defaultViewport)}>Center</button>
              </div>

              {contextMenu && (
                <CanvasContextMenu
                  x={contextMenu.x}
                  y={contextMenu.y}
                  actions={contextActions}
                  onClose={closeContextMenu}
                />
              )}
            </>
          )}
        </div>

        <aside className="version-rail" aria-label="Design versions">
          <span>VERSIONS</span>
          {usePreparedDemo
            ? demoVersions.map((item) => (
                <button
                  type="button"
                  key={item.number}
                  className={`version-thumb ${activeDemoVersion === item.number ? 'is-current' : ''}`}
                  aria-label={`Version ${item.number}: ${item.label}`}
                  aria-pressed={activeDemoVersion === item.number}
                  onClick={() => {
                    setActiveDemoVersion(item.number)
                  }}
                >
                  <i>{String(item.number).padStart(2, '0')}</i>
                  <b>{item.label}</b>
                </button>
              ))
            : railVersions.map((item) => (
                <button
                  type="button"
                  key={item.id}
                  className={`version-thumb ${backendVersion?.id === item.id || (!backendVersion && item.id === 'base') ? 'is-current' : ''}`}
                  aria-label={`Version ${item.version_number}: ${item.requested_change}`}
                  aria-pressed={backendVersion?.id === item.id || (!backendVersion && item.id === 'base')}
                  onClick={() => {
                    if (item.id === 'base') return
                    selectBackendVersion(item.id)
                  }}
                  title={item.requested_change}
                >
                  <i>{String(item.version_number).padStart(2, '0')}</i>
                  <b>{item.status === 'ready' ? item.requested_change : 'Start'}</b>
                </button>
              ))}
        </aside>
      </section>
    </main>
  )
}
