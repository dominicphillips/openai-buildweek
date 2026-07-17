import { GarmentIconFrame, type GarmentIconProps } from './GarmentIconFrame'

export function PantsIcon({ title, ...props }: GarmentIconProps) {
  return (
    <GarmentIconFrame title={title} {...props}>
      <path d="M32 16h56l5.5 31.5-8.2 77.5H64.8L60 69.5 55.2 125H34.7l-8.2-77.5L32 16Z" />
      <g strokeWidth="1.5" strokeOpacity="0.55">
        <path d="M29.4 27h61.2" />
        <path d="M60 27v21.5c0 5.2 3.4 8.7 8.2 8.7" />
        <path d="M30.6 38.2c5.5 6 10.6 8.8 17 9.1M89.4 38.2c-5.5 6-10.6 8.8-17 9.1" />
        <path d="M35.5 117.3h18.9M65.6 117.3h18.9" />
      </g>
    </GarmentIconFrame>
  )
}
