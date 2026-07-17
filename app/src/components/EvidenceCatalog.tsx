import { useEffect, useMemo, useState } from 'react'
import type { ReferenceCatalogItem } from '../lib/types'
import { ScrollArea } from './ui/ScrollArea'

type EvidenceCatalogProps = {
  selectedIds: string[]
  selectionCount: number
  onToggle: (item: ReferenceCatalogItem) => void
}

export function EvidenceCatalog({ selectedIds, selectionCount, onToggle }: EvidenceCatalogProps) {
  const [items, setItems] = useState<ReferenceCatalogItem[]>([])
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading')

  useEffect(() => {
    const controller = new AbortController()
    fetch('/api/references?limit=30', {
      headers: { Accept: 'application/json' },
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) throw new Error('catalog unavailable')
        return (await response.json()) as ReferenceCatalogItem[]
      })
      .then((catalog) => {
        setItems(catalog)
        setStatus('ready')
      })
      .catch((error: Error) => {
        if (error.name !== 'AbortError') setStatus('error')
      })
    return () => controller.abort()
  }, [])

  const visibleItems = useMemo(() => {
    const normalized = query.trim().toLowerCase()
    if (!normalized) return items
    return items.filter((item) =>
      [
        item.title,
        item.object_type,
        item.description,
        item.metadata.label_association.name,
        item.metadata.silhouette,
        ...item.metadata.tags,
        ...item.metadata.materials,
      ]
        .join(' ')
        .toLowerCase()
        .includes(normalized),
    )
  }, [items, query])

  return (
    <section className="evidence-catalog" aria-label="Local inspiration catalog">
      <header>
        <div>
          <span>LOCAL STUDIES / 30</span>
          <h2>Start with something concrete.</h2>
          <p>Project-authored silhouettes tagged by material, construction, proportion, and research trait.</p>
        </div>
        <label>
          <span>Search the shelf</span>
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="bomber, white tee, wide rib…" />
        </label>
      </header>

      <ScrollArea className="evidence-scroll" type="always" scrollHideDelay={0}>
        {status === 'loading' && <p className="panel-state">Opening thirty local studies…</p>}
        {status === 'error' && (
          <div className="panel-state">
            <strong>The local shelf is offline.</strong>
            <span>You can still add your own references. Start the API on port 43174 to browse the seeded set.</span>
          </div>
        )}
        {status === 'ready' && (
          <div className="evidence-grid">
            {visibleItems.map((item) => {
              const selected = selectedIds.includes(item.id)
              const disabled = !selected && selectionCount >= 3
              return (
                <button
                  type="button"
                  key={item.id}
                  className={selected ? 'is-selected' : undefined}
                  aria-pressed={selected}
                  disabled={disabled}
                  onClick={() => onToggle(item)}
                >
                  <div>
                    <img src={item.image_url} alt={item.image_alt} />
                    <span>{String(item.metadata.seed_order).padStart(2, '0')}</span>
                  </div>
                  <strong>{item.title}</strong>
                  <small>{item.metadata.label_association.name} / TRAIT LINK</small>
                  <i aria-hidden="true">{selected ? '×' : '+'}</i>
                </button>
              )
            })}
          </div>
        )}
      </ScrollArea>
      <footer>
        <span>Original project studies · no scraped product imagery</span>
        <strong>{selectionCount} / 3 SELECTED</strong>
      </footer>
    </section>
  )
}
