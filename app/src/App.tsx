import { useEffect, useMemo, useState } from 'react'
import { Ritual } from './components/Ritual'
import { Studio } from './components/Studio'
import { brands } from './data/brands'
import type { ReferenceCatalogItem, ReferenceItem, RitualStage, StudioSeed } from './lib/types'

const defaultSessionStorageKey = 'somethings-on:studio-session:v1'
const devDaySessionStorageKey = 'somethings-on:studio-session:devday:v1'

type StoredSession = {
  completed: boolean
  selectedBrandIds: string[]
  objectName: string
  references: ReferenceItem[]
}

const emptySession: StoredSession = {
  completed: false,
  selectedBrandIds: [],
  objectName: 'T-shirt',
  references: [],
}

function loadSession(storageKey: string): StoredSession {
  try {
    const raw = window.localStorage.getItem(storageKey)
    if (!raw) return emptySession
    const stored = JSON.parse(raw) as Partial<StoredSession>
    const knownBrandIds = new Set(brands.map((brand) => brand.id))
    return {
      completed: stored.completed === true,
      selectedBrandIds: Array.isArray(stored.selectedBrandIds)
        ? stored.selectedBrandIds.filter((id) => typeof id === 'string' && knownBrandIds.has(id)).slice(0, 5)
        : [],
      objectName:
        typeof stored.objectName === 'string' && stored.objectName.trim()
          ? stored.objectName.slice(0, 160)
          : emptySession.objectName,
      references: Array.isArray(stored.references)
        ? stored.references.filter(
            (reference): reference is ReferenceItem =>
              typeof reference?.id === 'string' &&
              (reference.kind === 'link' ||
                reference.kind === 'catalog' ||
                (reference.kind === 'image' && reference.previewUrl?.startsWith('/') === true)),
          )
        : [],
    }
  } catch {
    return emptySession
  }
}

function App() {
  const [demoMode] = useState(
    () => new URLSearchParams(window.location.search).get('demo') === 'devday',
  )
  const sessionStorageKey = demoMode ? devDaySessionStorageKey : defaultSessionStorageKey
  const [initialSession] = useState(() => loadSession(sessionStorageKey))
  const [stage, setStage] = useState<RitualStage>(
    demoMode || initialSession.completed ? 'studio' : 'arrival',
  )
  const [selectedBrandIds, setSelectedBrandIds] = useState<string[]>(
    demoMode && initialSession.selectedBrandIds.length === 0
      ? ['john-elliott']
      : initialSession.selectedBrandIds,
  )
  const [objectName, setObjectName] = useState(
    demoMode ? 'DevDay distressed bomber + white T-shirt' : initialSession.objectName,
  )
  const [references, setReferences] = useState<ReferenceItem[]>(initialSession.references)

  useEffect(() => {
    if (stage !== 'studio') return
    const persistentReferences = references.filter(
      (reference) =>
        reference.kind === 'link' ||
        reference.kind === 'catalog' ||
        reference.previewUrl?.startsWith('/'),
    )
    window.localStorage.setItem(
      sessionStorageKey,
      JSON.stringify({
        completed: true,
        selectedBrandIds,
        objectName,
        references: persistentReferences,
      } satisfies StoredSession),
    )
  }, [objectName, references, selectedBrandIds, sessionStorageKey, stage])

  const seed = useMemo<StudioSeed>(
    () => ({
      projectId: demoMode ? 'devday-swag' : 'demo',
      demoMode,
      selectedBrands: brands.filter((brand) => selectedBrandIds.includes(brand.id)),
      objectName: objectName.trim() || 'T-shirt',
      references,
    }),
    [demoMode, objectName, references, selectedBrandIds],
  )

  const toggleBrand = (brandId: string) => {
    setSelectedBrandIds((current) => {
      if (current.includes(brandId)) {
        return current.filter((id) => id !== brandId)
      }
      if (current.length >= 5) return current
      return [...current, brandId]
    })
  }

  const addFiles = (files: FileList | null) => {
    if (!files) return
    const available = Math.max(0, 3 - references.length)
    const next = Array.from(files)
      .filter((file) => file.type.startsWith('image/'))
      .slice(0, available)
      .map<ReferenceItem>((file) => ({
        id: crypto.randomUUID(),
        kind: 'image',
        name: file.name,
        previewUrl: URL.createObjectURL(file),
        file,
      }))
    setReferences((current) => [...current, ...next])
  }

  const addLink = (url: string) => {
    const value = url.trim()
    if (!value || references.length >= 3) return
    setReferences((current) => [
      ...current,
      {
        id: crypto.randomUUID(),
        kind: 'link',
        name: new URL(value).hostname.replace(/^www\./, ''),
        source: value,
      },
    ])
  }

  const addCatalogReference = (item: ReferenceCatalogItem) => {
    setReferences((current) => {
      if (current.some((reference) => reference.id === item.id)) {
        return current.filter((reference) => reference.id !== item.id)
      }
      if (current.length >= 3) return current
      return [
        ...current,
        {
          id: item.id,
          kind: 'catalog',
          name: item.product_name ?? item.metadata.product_name ?? item.title,
          previewUrl: item.image_url,
          source: item.source_url ?? item.metadata.source_url ?? 'local-reference-catalog',
          labelId: item.metadata.label_association.id,
          labelName: item.brand ?? item.metadata.brand ?? item.metadata.label_association.name,
          tags: item.neutral_attributes ?? item.metadata.neutral_attributes ?? item.metadata.tags,
        },
      ]
    })
  }

  const removeReference = (referenceId: string) => {
    setReferences((current) => {
      const removed = current.find((reference) => reference.id === referenceId)
      if (removed?.previewUrl) URL.revokeObjectURL(removed.previewUrl)
      return current.filter((reference) => reference.id !== referenceId)
    })
  }

  const reset = () => {
    references.forEach((reference) => {
      if (reference.previewUrl) URL.revokeObjectURL(reference.previewUrl)
    })
    setReferences([])
    setSelectedBrandIds([])
    setObjectName('T-shirt')
    window.localStorage.setItem(
      sessionStorageKey,
      JSON.stringify({ ...emptySession, completed: true } satisfies StoredSession),
    )
    setStage('object')
  }

  if (stage === 'studio') {
    return <Studio seed={seed} onReferencesChange={setReferences} onReset={reset} />
  }

  return (
    <Ritual
      stage={stage}
      setStage={setStage}
      brands={brands}
      selectedBrandIds={selectedBrandIds}
      toggleBrand={toggleBrand}
      objectName={objectName}
      setObjectName={setObjectName}
      references={references}
      addFiles={addFiles}
      addLink={addLink}
      addCatalogReference={addCatalogReference}
      removeReference={removeReference}
    />
  )
}

export default App
