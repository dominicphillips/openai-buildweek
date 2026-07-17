import { GarmentIconFrame, type GarmentIconProps } from './GarmentIconFrame'

export function TShirtIcon({ title, ...props }: GarmentIconProps) {
  return (
    <GarmentIconFrame title={title} {...props}>
      <path d="M42 17.5c3.7 4.2 9.7 6.3 18 6.3s14.3-2.1 18-6.3l21 10.4 13.5 25.7-18.2 9.5-9.1-16.8v72.6c-16.7 4-33.7 4-50.4 0V46.3l-9.1 16.8-18.2-9.5L21 27.9l21-10.4Z" />
      <g strokeWidth="1.5" strokeOpacity="0.55">
        <path d="M47 20.7C49.2 28.2 53.6 32 60 32s10.8-3.8 13-11.3" />
        <path d="m13.6 49.2 18.2 9.5M106.4 49.2l-18.2 9.5" />
        <path d="M34.8 112.4c16.7 3.6 33.7 3.6 50.4 0" />
      </g>
    </GarmentIconFrame>
  )
}
