import { useId, type ReactNode, type SVGProps } from 'react'

export type GarmentIconProps = Omit<SVGProps<SVGSVGElement>, 'children'> & {
  /** Adds an accessible name and exposes the SVG as an image. */
  title?: string
}

type GarmentIconFrameProps = GarmentIconProps & {
  children: ReactNode
}

export function GarmentIconFrame({ title, children, ...props }: GarmentIconFrameProps) {
  const generatedTitleId = useId()
  const hasAccessibleName = Boolean(title || props['aria-label'] || props['aria-labelledby'])
  const labelledBy = title
    ? [generatedTitleId, props['aria-labelledby']].filter(Boolean).join(' ')
    : props['aria-labelledby']

  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width={props.width ?? '1em'}
      height={props.height ?? '1em'}
      viewBox="0 0 120 140"
      fill={props.fill ?? 'none'}
      stroke={props.stroke ?? 'currentColor'}
      strokeWidth={props.strokeWidth ?? 2}
      strokeLinecap={props.strokeLinecap ?? 'round'}
      strokeLinejoin={props.strokeLinejoin ?? 'round'}
      role={props.role ?? (hasAccessibleName ? 'img' : undefined)}
      aria-hidden={props['aria-hidden'] ?? (hasAccessibleName ? undefined : true)}
      aria-labelledby={labelledBy || undefined}
      focusable={props.focusable ?? 'false'}
    >
      {title ? <title id={generatedTitleId}>{title}</title> : null}
      {children}
    </svg>
  )
}
