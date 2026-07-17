import { useEffect, useLayoutEffect, useRef } from 'react'

export type CanvasMenuAction = {
  id: string
  label: string
  detail?: string
  shortcut?: string
  tone?: 'default' | 'signal'
  onSelect: () => void
}

type CanvasContextMenuProps = {
  x: number
  y: number
  actions: CanvasMenuAction[]
  onClose: () => void
}

export function CanvasContextMenu({ x, y, actions, onClose }: CanvasContextMenuProps) {
  const menuRef = useRef<HTMLDivElement>(null)

  useLayoutEffect(() => {
    const menu = menuRef.current
    const canvas = menu?.offsetParent
    if (!(menu && canvas instanceof HTMLElement)) return

    const gutter = 14
    const left = Math.max(gutter, Math.min(x, canvas.clientWidth - menu.offsetWidth - gutter))
    const top = Math.max(gutter, Math.min(y, canvas.clientHeight - menu.offsetHeight - gutter))
    menu.style.left = `${left}px`
    menu.style.top = `${top}px`
  }, [actions.length, x, y])

  useEffect(() => {
    const closeOnPointer = (event: globalThis.PointerEvent) => {
      if (!menuRef.current?.contains(event.target as Node)) onClose()
    }
    const closeOnKey = (event: globalThis.KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }

    window.addEventListener('pointerdown', closeOnPointer)
    window.addEventListener('keydown', closeOnKey)
    menuRef.current?.querySelector<HTMLButtonElement>('button')?.focus()
    return () => {
      window.removeEventListener('pointerdown', closeOnPointer)
      window.removeEventListener('keydown', closeOnKey)
    }
  }, [onClose])

  return (
    <div
      ref={menuRef}
      className="canvas-context-menu"
      style={{ left: x, top: y }}
      role="menu"
      aria-label="Canvas tools"
      onContextMenu={(event) => event.preventDefault()}
      onPointerDown={(event) => event.stopPropagation()}
    >
      <header>
        <span>CANVAS TOOLS</span>
        <span>OBJECT / 001</span>
      </header>
      <div className="canvas-context-menu__actions">
        {actions.map((action) => (
          <button
            type="button"
            role="menuitem"
            key={action.id}
            aria-label={`${action.label}${action.detail ? `. ${action.detail}` : ''}`}
            className={action.tone === 'signal' ? 'is-signal' : undefined}
            onClick={() => {
              action.onSelect()
              onClose()
            }}
          >
            <span>
              <strong>{action.label}</strong>
              {action.detail && <em>{action.detail}</em>}
            </span>
            {action.shortcut && <kbd>{action.shortcut}</kbd>}
          </button>
        ))}
      </div>
      <footer>Right-click anywhere to move this menu</footer>
    </div>
  )
}
