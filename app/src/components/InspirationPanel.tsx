import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { useEffect, useMemo, useRef, useState } from 'react'
import type { Brand, InspirationFacets, ReferenceCatalogItem } from '../lib/types'
import { ScrollArea } from './ui/ScrollArea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/Select'

type InspirationPanelProps = {
  open: boolean
  objectName: string
  selectedBrands: Brand[]
  pulledIds: string[]
  onToggleReference: (item: ReferenceCatalogItem) => void
  onClose: () => void
}

const CONTEXT_FILTER = '__context__'
const ALL_FILTER = '__all__'

const compact = (values: Array<string | undefined>) =>
  [...new Set(values.map((value) => value?.trim()).filter((value): value is string => Boolean(value)))]

const productBrand = (item: ReferenceCatalogItem) =>
  item.brand?.trim() ||
  item.metadata.brand?.trim() ||
  item.metadata.label_association.name.trim() ||
  'Source unlisted'

const productName = (item: ReferenceCatalogItem) =>
  item.product_name?.trim() || item.metadata.product_name?.trim() || item.title.trim()

const sourceUrl = (item: ReferenceCatalogItem) => {
  const candidate = item.source_url?.trim() || item.metadata.source_url?.trim()
  if (!candidate) return undefined
  try {
    const parsed = new URL(candidate)
    return parsed.protocol === 'https:' || parsed.protocol === 'http:' ? parsed.href : undefined
  } catch {
    return undefined
  }
}

const neutralAttributes = (item: ReferenceCatalogItem) =>
  compact([
    ...(item.neutral_attributes ?? []),
    ...(item.metadata.neutral_attributes ?? []),
    ...item.metadata.label_association.matched_traits,
    item.metadata.silhouette,
    ...item.metadata.materials,
    ...item.metadata.construction,
    ...item.metadata.tags,
  ])

const tokens = (value: string) =>
  new Set(
    value
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, ' ')
      .split(/\s+/)
      .filter((token) => token.length > 2)
      .map((token) => (token.length > 4 ? token.replace(/s$/, '') : token)),
  )

const matchesObjectContext = (item: ReferenceCatalogItem, objectName: string) => {
  const contextTokens = tokens(objectName)
  if (contextTokens.size === 0) return true
  const itemTokens = tokens(`${item.object_type} ${item.category} ${productName(item)} ${neutralAttributes(item).join(' ')}`)
  return [...contextTokens].some((token) => itemTokens.has(token))
}

function relevance(item: ReferenceCatalogItem, objectName: string, selectedBrands: Brand[]) {
  const selectedSignals = new Set(
    selectedBrands.flatMap((brand) => [brand.id.toLowerCase(), brand.name.toLowerCase()]),
  )
  const brand = productBrand(item).toLowerCase()
  const labelId = item.metadata.label_association.id.toLowerCase()
  const brandMatch = selectedSignals.has(brand) || selectedSignals.has(labelId)
  return (
    Number(matchesObjectContext(item, objectName)) * 6 +
    Number(brandMatch) * 3 -
    item.metadata.seed_order / 1000
  )
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
  const [facets, setFacets] = useState<InspirationFacets | null>(null)
  const [query, setQuery] = useState('')
  const [activeCategory, setActiveCategory] = useState(CONTEXT_FILTER)
  const [activeBrand, setActiveBrand] = useState(ALL_FILTER)
  const [status, setStatus] = useState<'idle' | 'loading' | 'ready' | 'error'>('idle')
  const [requestVersion, setRequestVersion] = useState(0)
  const panelRef = useRef<HTMLElement>(null)
  const closeButtonRef = useRef<HTMLButtonElement>(null)
  const onCloseRef = useRef(onClose)

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
      if (event.key !== 'Escape' || event.defaultPrevented) return
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

  useEffect(() => {
    if (!open || facets) return
    const controller = new AbortController()
    void fetch('/api/inspiration/facets', {
      headers: { Accept: 'application/json' },
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) throw new Error('catalog facets unavailable')
        setFacets((await response.json()) as InspirationFacets)
      })
      .catch(() => undefined)
    return () => controller.abort()
  }, [facets, open])

  useEffect(() => {
    if (!open) return
    const controller = new AbortController()
    const request = window.setTimeout(() => {
      const parameters = new URLSearchParams({ limit: '30' })
      const search = [activeCategory === CONTEXT_FILTER ? objectName : '', query.trim()]
        .filter(Boolean)
        .join(' ')
      if (search) parameters.set('query', search)
      if (activeCategory !== CONTEXT_FILTER && activeCategory !== ALL_FILTER) {
        parameters.append('categories', activeCategory)
      }
      if (activeBrand !== ALL_FILTER) parameters.append('brands', activeBrand)

      setStatus('loading')
      void fetch(`/api/inspiration?${parameters.toString()}`, {
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
        .catch((error: unknown) => {
          if (error instanceof DOMException && error.name === 'AbortError') return
          setStatus('error')
        })
    }, 180)

    return () => {
      window.clearTimeout(request)
      controller.abort()
    }
  }, [activeBrand, activeCategory, objectName, open, query, requestVersion])

  useEffect(() => {
    setActiveCategory(CONTEXT_FILTER)
  }, [objectName])

  const products = useMemo(
    () => items.filter((item) => Boolean(sourceUrl(item))),
    [items],
  )

  const categories = useMemo(
    () => facets?.categories.map((entry) => entry.value) ?? compact(products.map((item) => item.category)).sort((left, right) => left.localeCompare(right)),
    [facets, products],
  )

  const brands = useMemo(
    () => facets?.brands.map((entry) => entry.value) ?? compact(products.map(productBrand)).sort((left, right) => left.localeCompare(right)),
    [facets, products],
  )

  const visibleItems = useMemo(() => {
    return [...products]
      .filter((item) => activeCategory !== CONTEXT_FILTER || matchesObjectContext(item, objectName))
      .sort((left, right) => relevance(right, objectName, selectedBrands) - relevance(left, objectName, selectedBrands))
  }, [activeCategory, objectName, products, selectedBrands])

  const pulledCount = pulledIds.length
  const hasFilters = query.trim() || activeCategory !== CONTEXT_FILTER || activeBrand !== ALL_FILTER
  const resetFilters = () => {
    setQuery('')
    setActiveCategory(CONTEXT_FILTER)
    setActiveBrand(ALL_FILTER)
  }

  return (
    <AnimatePresence>
      {open && (
        <motion.aside
          ref={panelRef}
          className="inspiration-panel"
          role="dialog"
          aria-modal="false"
          aria-labelledby="inspiration-title"
          initial={{ opacity: 0, y: reduceMotion ? 0 : -24 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: reduceMotion ? 0 : -18 }}
          transition={{ duration: reduceMotion ? 0 : 0.28, ease: [0.22, 1, 0.36, 1] }}
        >
          <header className="inspiration-panel__header">
            <div>
              <span>INSPIRATION</span>
              <h2 id="inspiration-title">Product library</h2>
              <p>Browse products. Pull one onto the canvas or open its source.</p>
            </div>
            <button ref={closeButtonRef} type="button" onClick={onClose} aria-label="Close inspiration">
              Close ×
            </button>
          </header>

          <div className="inspiration-panel__filters">
            <label className="inspiration-search">
              <span>Search products or attributes</span>
              <input
                type="search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="bomber, washed nylon, cropped…"
              />
            </label>
            <div className="inspiration-filter">
              <span id="inspiration-object-filter">Object context</span>
              <Select value={activeCategory} onValueChange={setActiveCategory}>
                <SelectTrigger aria-labelledby="inspiration-object-filter">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent align="start">
                  <SelectItem value={CONTEXT_FILTER}>Related to {objectName}</SelectItem>
                  <SelectItem value={ALL_FILTER}>All objects</SelectItem>
                  {categories.map((category) => <SelectItem value={category} key={category}>{category}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="inspiration-filter">
              <span id="inspiration-brand-filter">Brand source</span>
              <Select value={activeBrand} onValueChange={setActiveBrand}>
                <SelectTrigger aria-labelledby="inspiration-brand-filter">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent align="start">
                  <SelectItem value={ALL_FILTER}>All brands</SelectItem>
                  {brands.map((brand) => <SelectItem value={brand} key={brand}>{brand}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="inspiration-results" aria-live="polite">
              <span>{visibleItems.length} products</span>
              {pulledCount > 0 && <span>{pulledCount} on canvas</span>}
              {hasFilters && <button type="button" onClick={resetFilters}>Clear filters</button>}
            </div>
          </div>

          <ScrollArea className="inspiration-scroll" type="always" scrollHideDelay={0}>
            {status === 'loading' && <p className="panel-state">Opening the product library…</p>}
            {status === 'error' && (
              <div className="panel-state">
                <strong>The product library is unavailable.</strong>
                <span>Nothing was changed.</span>
                <button type="button" onClick={() => setRequestVersion((current) => current + 1)}>
                  Try again
                </button>
              </div>
            )}
            {status === 'ready' && products.length === 0 && (
              <div className="panel-state">
                <strong>No sourced product objects are available yet.</strong>
                <span>Unsourced illustrations are excluded from this library.</span>
              </div>
            )}
            {status === 'ready' && products.length > 0 && (
              <div className="inspiration-grid">
                {visibleItems.map((item) => {
                  const pulled = pulledIds.includes(item.id)
                  const attributes = neutralAttributes(item)
                  const officialSource = sourceUrl(item)
                  return (
                    <article className={pulled ? 'is-pulled' : undefined} key={item.id}>
                      <div className="inspiration-card__image">
                        <img
                          src={item.image_url}
                          alt={item.image_alt || `${productBrand(item)} ${productName(item)} product reference`}
                          loading="lazy"
                          decoding="async"
                        />
                        {pulled && <strong>ON CANVAS</strong>}
                      </div>
                      <div className="inspiration-card__copy">
                        <div className="inspiration-card__identity">
                          <span>{productBrand(item)}</span>
                          <span>{item.category}</span>
                        </div>
                        <h3>{productName(item)}</h3>
                        <ul aria-label="Neutral attributes">
                          {attributes.slice(0, 3).map((attribute) => <li key={attribute}>{attribute}</li>)}
                        </ul>
                        <div className="inspiration-card__actions">
                          {officialSource && (
                            <a href={officialSource} target="_blank" rel="noopener noreferrer">
                              View source <span aria-hidden="true">↗</span>
                            </a>
                          )}
                          <button type="button" onClick={() => onToggleReference(item)}>
                            {pulled ? 'Remove from canvas' : 'Pull beside design'} <i>{pulled ? '×' : '+'}</i>
                          </button>
                        </div>
                      </div>
                    </article>
                  )
                })}
                {visibleItems.length === 0 && (
                  <div className="panel-state inspiration-empty-filter">
                    <strong>No products match this context.</strong>
                    <span>Clear the filters or search another construction detail.</span>
                    <button type="button" onClick={resetFilters}>Show related objects</button>
                  </div>
                )}
              </div>
            )}
          </ScrollArea>
        </motion.aside>
      )}
    </AnimatePresence>
  )
}
