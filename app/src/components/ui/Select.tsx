import type { ComponentProps, ReactNode } from 'react'
import { Select as SelectPrimitive } from 'radix-ui'

function classes(...values: Array<string | undefined>) {
  return values.filter(Boolean).join(' ')
}

export const Select = SelectPrimitive.Root
export const SelectValue = SelectPrimitive.Value

export function SelectTrigger({
  className,
  children,
  ...props
}: ComponentProps<typeof SelectPrimitive.Trigger>) {
  return (
    <SelectPrimitive.Trigger
      className={classes('ui-select__trigger', className)}
      data-slot="select-trigger"
      {...props}
    >
      <span className="ui-select__value">{children}</span>
      <SelectPrimitive.Icon className="ui-select__icon" aria-hidden="true">⌄</SelectPrimitive.Icon>
    </SelectPrimitive.Trigger>
  )
}

export function SelectContent({
  className,
  children,
  position = 'popper',
  ...props
}: ComponentProps<typeof SelectPrimitive.Content>) {
  return (
    <SelectPrimitive.Portal>
      <SelectPrimitive.Content
        className={classes('ui-select__content', className)}
        data-slot="select-content"
        position={position}
        sideOffset={6}
        {...props}
      >
        <SelectScrollButton direction="up">↑</SelectScrollButton>
        <SelectPrimitive.Viewport className="ui-select__viewport">
          {children}
        </SelectPrimitive.Viewport>
        <SelectScrollButton direction="down">↓</SelectScrollButton>
      </SelectPrimitive.Content>
    </SelectPrimitive.Portal>
  )
}

function SelectScrollButton({ direction, children }: { direction: 'up' | 'down'; children: ReactNode }) {
  const Primitive = direction === 'up'
    ? SelectPrimitive.ScrollUpButton
    : SelectPrimitive.ScrollDownButton
  return <Primitive className="ui-select__scroll-button">{children}</Primitive>
}

export function SelectItem({
  className,
  children,
  ...props
}: ComponentProps<typeof SelectPrimitive.Item>) {
  return (
    <SelectPrimitive.Item
      className={classes('ui-select__item', className)}
      data-slot="select-item"
      {...props}
    >
      <SelectPrimitive.ItemText>{children}</SelectPrimitive.ItemText>
      <SelectPrimitive.ItemIndicator className="ui-select__indicator">●</SelectPrimitive.ItemIndicator>
    </SelectPrimitive.Item>
  )
}
