import { motion, useReducedMotion } from 'motion/react'
import type { ComponentProps } from 'react'
import { PantsIcon, ShoeIcon, TShirtIcon } from '../icons'

export type LiveGarmentIllustrationProps = Omit<
  ComponentProps<typeof motion.svg>,
  'aria-label' | 'children'
> & {
  /** Exposes the scene as an image. Without a label it remains decorative. */
  label?: string
}

export function LiveGarmentIllustration({
  label,
  style,
  ...props
}: LiveGarmentIllustrationProps) {
  const reduceMotion = useReducedMotion()

  return (
    <motion.svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width={props.width ?? '100%'}
      viewBox="0 0 720 400"
      preserveAspectRatio={props.preserveAspectRatio ?? 'xMidYMid meet'}
      role={label ? 'img' : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
      focusable={props.focusable ?? 'false'}
      initial={false}
      style={{ display: 'block', height: 'auto', overflow: 'visible', ...style }}
    >
      <g
        fill="none"
        stroke="currentColor"
        strokeWidth="1"
        strokeOpacity="0.16"
        vectorEffect="non-scaling-stroke"
      >
        <path d="M28 82V38h44M648 38h44v44M28 318v44h44M648 362h44v-44" />
        <path d="M360 28v316" strokeDasharray="1 11" />
        <path d="M52 316h616" />
        <circle cx="360" cy="316" r="4" />
      </g>

      <motion.path
        d="M52 316h616"
        fill="none"
        stroke="currentColor"
        strokeWidth="1"
        strokeOpacity="0.14"
        strokeDasharray="3 14"
        vectorEffect="non-scaling-stroke"
        animate={
          reduceMotion
            ? { strokeDashoffset: 0, strokeOpacity: 0.14 }
            : { strokeDashoffset: [0, -68], strokeOpacity: [0.1, 0.22, 0.1] }
        }
        transition={reduceMotion ? { duration: 0 } : { duration: 14, ease: 'linear', repeat: Infinity }}
      />

      <motion.g
        opacity="0.54"
        animate={reduceMotion ? { x: 0, y: 0 } : { x: [0, -3, 0], y: [0, 4, 0] }}
        transition={reduceMotion ? { duration: 0 } : { duration: 11, ease: 'easeInOut', repeat: Infinity }}
      >
        <PantsIcon x="94" y="58" width="166" height="194" aria-hidden="true" />
      </motion.g>

      <motion.g
        opacity="0.92"
        animate={reduceMotion ? { y: 0 } : { y: [0, -5, 0] }}
        transition={reduceMotion ? { duration: 0 } : { duration: 9, ease: 'easeInOut', repeat: Infinity }}
      >
        <TShirtIcon x="258" y="40" width="206" height="240" aria-hidden="true" />
      </motion.g>

      <motion.g
        opacity="0.76"
        animate={reduceMotion ? { x: 0, y: 0 } : { x: [0, 5, 0], y: [0, -2, 0] }}
        transition={reduceMotion ? { duration: 0 } : { duration: 12, ease: 'easeInOut', repeat: Infinity }}
      >
        <ShoeIcon x="426" y="80" width="240" height="280" aria-hidden="true" />
      </motion.g>

      <g fill="currentColor" opacity="0.42" aria-hidden="true">
        <circle cx="94" cy="316" r="2" />
        <circle cx="626" cy="316" r="2" />
      </g>
    </motion.svg>
  )
}
