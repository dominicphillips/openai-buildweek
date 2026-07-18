import { GarmentIconFrame, type GarmentIconProps } from './GarmentIconFrame'

export function BomberIcon({ title, ...props }: GarmentIconProps) {
  return (
    <GarmentIconFrame title={title} {...props}>
      <path d="M43 18c4.8 4 10.5 6 17 6s12.2-2 17-6l19 11c5 15 10 33 15 53l-19 7-8-24 2 45c-8 3.5-16.7 5.2-26 5.2S42 113.5 34 110l2-45-8 24-19-7c5-20 10-38 15-53l19-11Z" />
      <g strokeWidth="1.5" strokeOpacity="0.55">
        <path d="M47 20.5C49 28.2 53.3 32 60 32s11-3.8 13-11.5" />
        <path d="M60 32v81M34 103.5c8 3 16.7 4.5 26 4.5s18-1.5 26-4.5" />
        <path d="M24 29c4.5 9.5 8.5 21.5 12 36M96 29c-4.5 9.5-8.5 21.5-12 36" />
        <path d="m43 68-7 13h15M77 68l7 13H69" />
        <path d="m11.5 76.5 18.5 6.8M108.5 76.5 90 83.3" />
      </g>
    </GarmentIconFrame>
  )
}
