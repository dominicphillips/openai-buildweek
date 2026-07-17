import { useMemo, useState } from 'react'
import { Ritual } from './components/Ritual'
import { Studio } from './components/Studio'
import { brands } from './data/brands'
import type { ReferenceItem, RitualStage, StudioSeed } from './lib/types'

const firstStage: RitualStage = 'arrival'

function App() {
  const [stage, setStage] = useState<RitualStage>(firstStage)
  const [selectedBrandIds, setSelectedBrandIds] = useState<string[]>([])
  const [objectName, setObjectName] = useState('white T-shirt')
  const [references, setReferences] = useState<ReferenceItem[]>([])

  const seed = useMemo<StudioSeed>(
    () => ({
      selectedBrands: brands.filter((brand) => selectedBrandIds.includes(brand.id)),
      objectName: objectName.trim() || 'white T-shirt',
      references,
    }),
    [objectName, references, selectedBrandIds],
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
    setObjectName('white T-shirt')
    setStage(firstStage)
  }

  if (stage === 'studio') {
    return <Studio seed={seed} onReset={reset} />
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
      removeReference={removeReference}
    />
  )
}

export default App
