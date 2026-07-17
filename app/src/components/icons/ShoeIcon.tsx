import { GarmentIconFrame, type GarmentIconProps } from './GarmentIconFrame'

export function ShoeIcon({ title, ...props }: GarmentIconProps) {
  return (
    <GarmentIconFrame title={title} {...props}>
      <path d="M11 91.5c7.8-3.9 14.7-10.8 18.2-19.4l9.7-23.8c1-2.5 4.3-3.4 6.5-1.8l26.3 20.8c7.5 6 15.4 9.3 25.7 11.4 9.7 2 14.6 6.6 14.6 13.8v4.2c-5.5 5.8-14.3 8.8-26.5 8.8H21.6C13.1 105.5 8 101.7 8 96.3c0-2.2 1-3.8 3-4.8Z" />
      <g strokeWidth="1.5" strokeOpacity="0.55">
        <path d="M9 94.5c13.5 3.1 31.3 4.7 53.4 4.7h48.4" />
        <path d="m45.5 49.2-5.7 12.9c5.7 3.5 11.3 5.2 17 5.2 4.6 0 9.5-.7 14.9-2.1" />
        <path d="m50 63.8 7.2-4.8M56.2 68.5l7.2-4.8M62.4 73l7-4.7" />
        <path d="M29.2 72.1c9.3 6.1 19.7 9.2 31.2 9.2h31.5M29.2 72.1 29 92" />
        <path d="M91 79c-5 2.6-7.8 6.6-8.3 12" />
      </g>
    </GarmentIconFrame>
  )
}
