import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { useEffect, useMemo, useState } from 'react'
import type { Brand, ReferenceCatalogItem } from '../lib/types'
import { ScrollArea } from './ui/ScrollArea'

type InspirationPanelProps = {
  open: boolean
  objectName: string
  selectedBrands: Brand[]
  pulledIds: string[]
  onToggleReference: (item: ReferenceCatalogItem) => void
  onClose: () => void
}

function relevance(item: ReferenceCatalogItem, objectName: string, labelIds: Set<string>) {
  const object = objectName.toLowerCase()
  const objectMatch = [item.object_type, item.category, ...item.metadata.tags]
    .join(' ')
    .toLowerCase()
    .split(/\s+/)
    .some((token) => token.length > 2 && object.includes(token.replace(/s$/, '')))
  const labelMatch = labelIds.has(item.metadata.label_association.id)
  return Number(labelMatch) * 4 + Number(objectMatch) * 2 - item.metadata.seed_order / 1000
}

export function InspirationPanel({
  open,
  objectName,
  selectedBrands,
  pulledIds,
  onToggleReference,
  onClose,
}: InspirationPanelProps) {
  const reduceMotion = useReducedMotion()
  const [items, setItems] = useState<ReferenceCatalogItem[]>([])
  const [query, setQuery] = useState('')
  const [activeLabel, setActiveLabel] = useState('all')
  const [status, setStatus] = useState<'idle' | 'loading' | 'ready' | 'error'>('idle')

  useEffect(() => {
    if (!open || status !== 'idle') return
    setStatus('loading')
    fetch('/api/references?limit=30', { headers: { Accept: 'application/json' } })
      .then(async (response) => {
        if (!response.ok) throw new Error('catalog unavailable')
        return (await response.json()) as ReferenceCatalogItem[]
      })
      .then((catalog) => {
        setItems(catalog)
        setStatus('ready')
      })
      .catch(() => setStatus('error'))
  }, [open, status])

  const visibleItems = useMemo(() => {
    const labelIds = new Set(selectedBrands.map((brand) => brand.id))
    const normalizedQuery = query.trim().toLowerCase()
    return [...items]
      .filter((item) => activeLabel === 'all' || item.metadata.label_association.id === activeLabel)
      .filter((item) => {
        if (!normalizedQuery) return true
        return [
          item.title,
          item.description,
          item.object_type,
          item.metadata.label_association.name,
          item.metadata.silhouette,
          ...item.metadata.tags,
          ...item.metadata.materials,
          ...item.metadata.construction,
        ]
          .join(' ')
          .toLowerCase()
          .includes(normalizedQuery)
      })
      .sort((left, right) => relevance(right, objectName, labelIds) - relevance(left, objectName, labelIds))
  }, [activeLabel, items, objectName, query, selectedBrands])

  return (
    <AnimatePresence>
      {open && (
        <motion.aside
          className="inspiration-panel"
          aria-label="Inspiration library"
          initial={{ opacity: 0, y: reduceMotion ? 0 : -24 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: reduceMotion ? 0 : -18 }}
          transition={{ duration: reduceMotion ? 0 : 0.28, ease: [0.22, 1, 0.36, 1] }}
        >
          <header className="inspiration-panel__header">
            <div>
              <span>INSPIRATION / LOCAL CATALOG</span>
              <h2>Pull a useful piece into view.</h2>
              <p>Thirty original studies, tagged locally. Brand links describe trait overlap—not official products.</p>
            </div>
            <button type="button" onClick={onClose} aria-label="Close inspiration">
              Close ×
            </button>
          </header>

          <div className="inspiration-panel__filters">
            <label>
              <span>Search form, fabric, or construction</span>
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder={`Related to ${objectName}`}
              />
            </label>
            <div className="inspiration-labels" aria-label="Filter by selected label">
              <button
                type="button"
                className={activeLabel === 'all' ? 'is-active' : undefined}
                onClick={() => setActiveLabel('all')}
              >
                All / 30
              </button>
              {selectedBrands.map((brand) => (
                <button
                  type="button"
                  key={brand.id}
                  className={activeLabel === brand.id ? 'is-active' : undefined}
                  onClick={() => setActiveLabel(brand.id)}
                >
                  {brand.name}
                </button>
              ))}
            </div>
          </div>

          <ScrollArea className="inspiration-scroll" type="always" scrollHideDelay={0}>
            {status === 'loading' && <p className="panel-state">Opening the local catalog…</p>}
            {status === 'error' && (
              <div className="panel-state">
                <strong>The catalog service is offline.</strong>
                <span>Start the FastAPI service on port 43174, then reopen this tab.</span>
              </div>
            )}
            {status === 'ready' && (
              <div className="inspiration-grid">
                {visibleItems.map((item) => {
                  const pulled = pulledIds.includes(item.id)
                  return (
                    <article className={pulled ? 'is-pulled' : undefined} key={item.id}>
                      <div className="inspiration-card__image">
                        <img src={item.image_url} alt={item.image_alt} />
                        <span>{String(item.metadata.seed_order).padStart(2, '0')}</span>
                      </div>
                      <div className="inspiration-card__copy">
                        <span>{item.metadata.label_association.name} / TRAIT STUDY</span>
                        <h3>{item.title}</h3>
                        <p>{item.metadata.silhouette}</p>
                        <button type="button" onClick={() => onToggleReference(item)}>
                          {pulled ? 'Remove from canvas' : 'Pull to canvas'} <i>{pulled ? '×' : '↗'}</i>
                        </button>
                      </div>
                    </article>
                  )
                })}
                {visibleItems.length === 0 && <p className="panel-state">No studies match that combination.</p>}
              </div>
            )}
          </ScrollArea>
        </motion.aside>
      )}
    </AnimatePresence>
  )
}
