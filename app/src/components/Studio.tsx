import { motion, useReducedMotion } from 'motion/react'
import { useRef, useState, type PointerEvent, type WheelEvent } from 'react'
import type { ReferenceItem, StudioSeed } from '../lib/types'
import { ChatDock } from './ChatDock'
import { GarmentStudy } from './GarmentStudy'

type StudioProps = {
  seed: StudioSeed
  onReset: () => void
}

type Viewport = {
  x: number
  y: number
  zoom: number
}

const referencePositions = [
  { x: 205, y: 164, rotate: -6 },
  { x: 960, y: 174, rotate: 5 },
  { x: 1032, y: 590, rotate: -3 },
]

function ReferenceCard({ reference, index }: { reference: ReferenceItem; index: number }) {
  const position = referencePositions[index % referencePositions.length]
  return (
    <motion.article
      className="canvas-reference"
      style={{ left: position.x, top: position.y, rotate: position.rotate }}
      initial={{ opacity: 0, scale: 0.92, y: 18 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      transition={{ delay: 0.35 + index * 0.12, duration: 0.55 }}
    >
      <div className="canvas-reference__image">
        {reference.previewUrl ? (
          <img src={reference.previewUrl} alt="" />
        ) : (
          <span className="reference-link-mark">↗</span>
        )}
      </div>
      <footer>
        <span>REF / {String(index + 1).padStart(2, '0')}</span>
        <strong>{reference.name}</strong>
      </footer>
    </motion.article>
  )
}

export function Studio({ seed, onReset }: StudioProps) {
  const reduceMotion = useReducedMotion()
  const [viewport, setViewport] = useState<Viewport>({ x: 0, y: 0, zoom: 0.86 })
  const [revision, setRevision] = useState(1)
  const dragOrigin = useRef<{ pointerX: number; pointerY: number; x: number; y: number } | null>(null)

  const setZoom = (zoom: number) => {
    setViewport((current) => ({ ...current, zoom: Math.min(1.35, Math.max(0.55, zoom)) }))
  }

  const onWheel = (event: WheelEvent<HTMLDivElement>) => {
    setZoom(viewport.zoom - event.deltaY * 0.0007)
  }

  const startPan = (event: PointerEvent<HTMLDivElement>) => {
    if ((event.target as HTMLElement).closest('button, article, figure')) return
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

  return (
    <main className="studio-shell">
      <ChatDock
        objectName={seed.objectName}
        referenceCount={seed.references.length}
        onProjectRefresh={() => setRevision((current) => current + 1)}
      />

      <section className="studio-space">
        <header className="studio-header">
          <div className="studio-wordmark">
            SOMETHINGS<span>—ON</span>
          </div>
          <div className="studio-project">
            <span>PROJECT / 001</span>
            <strong>{seed.objectName.toUpperCase()}</strong>
          </div>
          <div className="studio-actions">
            <button type="button" onClick={onReset}>Start over</button>
            <span>STUDY {String(revision).padStart(3, '0')}</span>
          </div>
        </header>

        <div
          className="canvas-viewport"
          onWheel={onWheel}
          onPointerDown={startPan}
          onPointerMove={pan}
          onPointerUp={stopPan}
          onPointerCancel={stopPan}
        >
          <motion.div
            className="canvas-plane"
            style={{
              transform: `translate(calc(-50% + ${viewport.x}px), calc(-50% + ${viewport.y}px)) scale(${viewport.zoom})`,
            }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: reduceMotion ? 0 : 0.8 }}
          >
            {seed.references.map((reference, index) => (
              <ReferenceCard key={reference.id} reference={reference} index={index} />
            ))}

            {seed.references.length === 0 && seed.selectedBrands.slice(0, 3).map((brand, index) => {
              const position = referencePositions[index]
              return (
                <motion.article
                  className="trait-note"
                  key={brand.id}
                  style={{ left: position.x, top: position.y, rotate: position.rotate }}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 + index * 0.1 }}
                >
                  <small>TASTE SIGNAL / {String(index + 1).padStart(2, '0')}</small>
                  <strong>{brand.name}</strong>
                  <p>{brand.tags.join(' / ')}</p>
                  <span>Confirm these traits in chat</span>
                </motion.article>
              )
            })}

            <motion.div
              className="canvas-design"
              initial={{ opacity: 0, scale: 0.94 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: reduceMotion ? 0 : 0.2, duration: reduceMotion ? 0 : 0.7 }}
            >
              <GarmentStudy label={seed.objectName} />
              <div className="design-selection" aria-hidden="true">
                <i /><i /><i /><i />
              </div>
            </motion.div>

            <div className="canvas-note canvas-note--one">KEEP / WEIGHT</div>
            <div className="canvas-note canvas-note--two">QUESTION / NECKLINE</div>
          </motion.div>

          <div className="canvas-controls" aria-label="Canvas zoom controls">
            <button type="button" onClick={() => setZoom(viewport.zoom - 0.1)} aria-label="Zoom out">−</button>
            <span>{Math.round(viewport.zoom * 100)}%</span>
            <button type="button" onClick={() => setZoom(viewport.zoom + 0.1)} aria-label="Zoom in">+</button>
            <button type="button" onClick={() => setViewport({ x: 0, y: 0, zoom: 0.86 })}>Center</button>
          </div>

          <p className="canvas-help">Drag the space / scroll to scale</p>
        </div>

        <aside className="version-rail" aria-label="Design versions">
          <span>VERSIONS</span>
          <button type="button" className="version-thumb is-current" aria-label="Current version 1">
            <i>01</i>
            <b>BASE</b>
          </button>
          <button type="button" className="version-add" aria-label="Create a new version">+</button>
        </aside>

        <footer className="studio-footer">
          <span>SELECTED / OBJECT 001</span>
          <p>
            {seed.selectedBrands.length
              ? seed.selectedBrands.map((brand) => brand.name).join(' · ')
              : 'NO LABELS SELECTED'}
          </p>
          <span>AUTHORED CHANGES ONLY</span>
        </footer>
      </section>
    </main>
  )
}
