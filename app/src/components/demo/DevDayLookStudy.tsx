import { motion, useReducedMotion } from 'motion/react'
import { useId, type ComponentProps } from 'react'

export type DevDayLookVersion = 1 | 2 | 3

export type DevDayLookStudyProps = Omit<
  ComponentProps<typeof motion.svg>,
  'aria-label' | 'children' | 'version'
> & {
  version: DevDayLookVersion
  /** Replaces the built-in description announced for this image. */
  label?: string
}

const versionDescriptions: Record<DevDayLookVersion, string> = {
  1: 'a washed charcoal bomber with roomy flight proportions',
  2: 'an inside-out bomber with exposed construction and orange bartacks',
  3: 'a cropped mineral-olive bomber with modular utility pockets',
}

type StudyPartProps = {
  idPrefix: string
}

type SettingProps = StudyPartProps & {
  reduced: boolean
  version: DevDayLookVersion
}

function StudyDefs({ idPrefix }: StudyPartProps) {
  return (
    <defs>
      <linearGradient id={`${idPrefix}-backdrop`} x1="0" y1="0" x2="0.85" y2="1">
        <stop offset="0" stopColor="#292926" />
        <stop offset="0.52" stopColor="#20201e" />
        <stop offset="1" stopColor="#151514" />
      </linearGradient>
      <linearGradient id={`${idPrefix}-sun`} x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stopColor="#d8c6a0" stopOpacity="0.32" />
        <stop offset="1" stopColor="#9a8766" stopOpacity="0.02" />
      </linearGradient>
      <linearGradient id={`${idPrefix}-skin`} x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stopColor="#b48162" />
        <stop offset="0.58" stopColor="#96664e" />
        <stop offset="1" stopColor="#6e4738" />
      </linearGradient>
      <linearGradient id={`${idPrefix}-tee`} x1="0" y1="0" x2="0.8" y2="1">
        <stop offset="0" stopColor="#f1efe7" />
        <stop offset="0.55" stopColor="#d9d6cc" />
        <stop offset="1" stopColor="#a9a79f" />
      </linearGradient>
      <linearGradient id={`${idPrefix}-trouser`} x1="0" y1="0" x2="1" y2="0.8">
        <stop offset="0" stopColor="#252725" />
        <stop offset="0.5" stopColor="#111210" />
        <stop offset="1" stopColor="#343531" />
      </linearGradient>
      <linearGradient id={`${idPrefix}-charcoal`} x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stopColor="#5a5955" />
        <stop offset="0.45" stopColor="#373835" />
        <stop offset="1" stopColor="#1e201e" />
      </linearGradient>
      <linearGradient id={`${idPrefix}-reverse`} x1="0" y1="0" x2="0.9" y2="1">
        <stop offset="0" stopColor="#77736a" />
        <stop offset="0.48" stopColor="#54534e" />
        <stop offset="1" stopColor="#343531" />
      </linearGradient>
      <linearGradient id={`${idPrefix}-olive`} x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stopColor="#7a816c" />
        <stop offset="0.5" stopColor="#59624f" />
        <stop offset="1" stopColor="#343c31" />
      </linearGradient>
      <pattern id={`${idPrefix}-concrete`} width="22" height="18" patternUnits="userSpaceOnUse">
        <circle cx="3" cy="4" r="0.65" fill="#f4f1e7" opacity="0.055" />
        <circle cx="16" cy="13" r="0.45" fill="#070707" opacity="0.2" />
        <path d="M7 16l5-1M18 3l2 .4" stroke="#f4f1e7" strokeWidth="0.45" opacity="0.04" />
      </pattern>
      <pattern
        id={`${idPrefix}-wash`}
        width="28"
        height="24"
        patternUnits="userSpaceOnUse"
        patternTransform="rotate(-8)"
      >
        <path d="M-3 8C4 3 10 14 17 8s12-1 16 2" fill="none" stroke="#f0eee6" strokeWidth="2.6" opacity="0.075" />
        <circle cx="9" cy="20" r="2.1" fill="#f0eee6" opacity="0.045" />
      </pattern>
    </defs>
  )
}

function EditorialSetting({ idPrefix, reduced, version }: SettingProps) {
  return (
    <g aria-hidden="true">
      <rect width="440" height="520" fill={`url(#${idPrefix}-backdrop)`} />
      <rect width="440" height="520" fill={`url(#${idPrefix}-concrete)`} />
      <motion.path
        d="M286 18h136v170L349 255l-89-87Z"
        fill={`url(#${idPrefix}-sun)`}
        animate={reduced ? { opacity: 0.72 } : { opacity: [0.62, 0.78, 0.62] }}
        transition={reduced ? { duration: 0 } : { duration: 10, ease: 'easeInOut', repeat: Infinity }}
      />

      <g fill="none" stroke="#e8e3d8" strokeWidth="0.7" opacity="0.13">
        <path d="M18 18h404v484H18z" />
        <path d="M18 430h404M18 456h404" />
        <path d="M301 76h121M320 102h102M339 128h83" />
        <path d="M51 430 29 502M389 430l24 72" />
      </g>

      <g fill="none" stroke="#080807" strokeLinecap="round" opacity="0.38">
        <path d="M74 38c8 102 16 220 35 392" strokeWidth="9" />
        <path d="M77 53C49 36 34 36 18 43M79 55C52 59 36 72 22 91M78 51c-5-25-14-35-27-45M80 54c21-22 37-28 57-26M81 57c26 4 43 15 57 34" strokeWidth="4" />
      </g>

      <path d="M193 431 73 487h272l-99-56Z" fill="#050505" opacity="0.27" />
      <g fill="none" stroke="#ebe7dc" strokeWidth="1" opacity="0.32">
        <path d={`M27 32h${26 + version * 7}M27 38h18`} />
        <path d="M332 32h81M369 38h44" />
        <path d="M27 487h104M27 493h62" />
        <path d="M326 487h87M357 493h56" />
      </g>

      <g fill="#e9e5da" opacity="0.35">
        <circle cx="18" cy="430" r="1.5" />
        <circle cx="422" cy="430" r="1.5" />
        <circle cx="220" cy="18" r="1.25" />
      </g>
    </g>
  )
}

function LowerModel({ idPrefix }: StudyPartProps) {
  return (
    <g>
      <path
        d="M176 301c20-5 68-5 88 0l-7 82 8 82-34 1-10-100h-3l-10 100-35-1 9-82Z"
        fill={`url(#${idPrefix}-trouser)`}
        stroke="#080908"
        strokeWidth="1.4"
      />
      <g fill="none" stroke="#696a63" strokeWidth="0.8" opacity="0.52">
        <path d="M220 308v58M183 383c10 3 20 4 30 3M227 386c11 1 21 0 31-3" />
        <path d="M179 320c10 5 19 7 30 7M231 327c10 0 20-2 29-7" strokeDasharray="2 3" />
        <path d="M193 331c-5 41-7 84-6 130M247 331c5 41 7 84 6 130" opacity="0.38" />
      </g>
      <path d="M171 460h38l12 13-4 9h-53c-3-9-1-16 7-22Z" fill="#0b0c0b" stroke="#5c5d57" strokeWidth="1.1" />
      <path d="M231 460h31l17 12-2 10h-56l-3-8Z" fill="#0b0c0b" stroke="#5c5d57" strokeWidth="1.1" />
      <path d="M165 476h52M222 476h55" stroke="#b8b6ad" strokeWidth="1" opacity="0.42" />
    </g>
  )
}

function UnderLayer({ idPrefix }: StudyPartProps) {
  return (
    <g>
      <path d="M210 106v34c2 8 18 8 21 0v-34Z" fill={`url(#${idPrefix}-skin)`} stroke="#4d332a" strokeWidth="1" />
      <path
        d="M196 137c7 5 15 8 24 8s17-3 24-8l10 174c-23 9-46 9-69 0Z"
        fill={`url(#${idPrefix}-tee)`}
        stroke="#77766f"
        strokeWidth="1.15"
      />
      <path d="M205 140c2 11 7 17 15 17s13-6 15-17" fill="none" stroke="#7f7d75" strokeWidth="1.2" />
      <g fill="none" stroke="#8a8880" strokeWidth="0.75" opacity="0.52">
        <path d="M196 181c8 4 16 5 24 5s16-1 24-5M191 292c19 5 39 5 58 0" />
        <path d="M207 168c-5 35-5 74-1 116M233 168c5 35 5 74 1 116" opacity="0.42" />
      </g>
    </g>
  )
}

function ModelHead({ idPrefix }: StudyPartProps) {
  return (
    <g>
      <path
        d="M204 77c0-16 7-25 18-25 13 0 20 11 18 29l-4 18c-3 12-9 18-16 18-9-1-15-9-18-21Z"
        fill={`url(#${idPrefix}-skin)`}
        stroke="#4a3028"
        strokeWidth="1.15"
      />
      <path d="M204 80c-2-19 6-30 19-30 13 0 20 10 18 27-8-1-15-4-21-10-5 6-10 10-16 13Z" fill="#171816" />
      <path d="M233 77c1 17-3 29-13 39 8 0 14-6 17-17l3-18Z" fill="#684235" opacity="0.46" />
      <path d="M205 104c8 6 20 7 30 1" fill="none" stroke="#d3a184" strokeWidth="0.55" opacity="0.2" />
    </g>
  )
}

function ModelHands({ idPrefix }: StudyPartProps) {
  return (
    <g fill={`url(#${idPrefix}-skin)`} stroke="#4d332a" strokeWidth="0.9">
      <path d="M143 288c4-2 14-1 19 2l-1 19c-3 7-10 9-15 4-4-8-5-16-3-25Z" />
      <path d="M278 290c5-3 15-4 19-1 2 9 1 18-4 25-6 4-12 1-15-6Z" />
      <g fill="none" stroke="#d3a184" strokeWidth="0.55" opacity="0.48">
        <path d="m147 298 1 12M151 297l1 14M155 298v11M293 298l-1 12M289 297l-1 14M285 298v11" />
      </g>
    </g>
  )
}

type PatchProps = {
  x: number
  y: number
  rotate?: number
  fill: string
  ink: string
}

function DevDayPatch({ x, y, rotate = 0, fill, ink }: PatchProps) {
  return (
    <g transform={`translate(${x} ${y}) rotate(${rotate})`} aria-hidden="true">
      <rect width="31" height="17" rx="1" fill={fill} stroke={ink} strokeWidth="0.75" />
      <path d="M3 8.5h25" stroke={ink} strokeWidth="0.45" opacity="0.55" />
      <g fill="none" stroke={ink} strokeWidth="1.2">
        <path d="M4 4h8v9H4zM16 4h11M16 8.5h11M16 13h7" />
        <path d="m6 6 4 5M10 6l-4 5" strokeWidth="0.7" opacity="0.5" />
      </g>
    </g>
  )
}

type ZipperProps = {
  color: string
  x: number
  yStart: number
  yEnd: number
}

function Zipper({ color, x, yStart, yEnd }: ZipperProps) {
  const teeth = Array.from(
    { length: Math.max(1, Math.floor((yEnd - yStart) / 7)) },
    (_, index) => yStart + index * 7,
  )

  return (
    <g fill="none" stroke={color} opacity="0.82">
      <path d={`M${x} ${yStart}V${yEnd}`} strokeWidth="0.7" />
      {teeth.map((y, index) => (
        <path key={`${x}-${index}`} d={`M${x - 2.1} ${y}h4.2`} strokeWidth="0.65" />
      ))}
      <path d={`M${x - 2.8} ${yStart + 4}h5.6v7h-5.6z`} strokeWidth="0.8" />
    </g>
  )
}

type BartackProps = {
  x: number
  y: number
  rotate?: number
}

function Bartack({ x, y, rotate = 0 }: BartackProps) {
  return (
    <g transform={`translate(${x} ${y}) rotate(${rotate})`} fill="none" stroke="#f06a2a" strokeWidth="1.2">
      <path d="M0 0v7M2.8 0v7M5.6 0v7" />
    </g>
  )
}

const flightLeftSleeve = 'M178 141c-24 1-42 12-58 36 2 26 9 60 22 114l22 1c-1-35-4-77 5-116l15-21Z'
const flightRightSleeve = 'M262 141c24 1 42 12 58 36-2 26-9 60-22 114l-22 1c1-35 4-77-5-116l-15-21Z'
const flightLeftBody = 'M180 141l32-5 7 17-8 162-51-5 4-137Z'
const flightRightBody = 'M260 141l-32-5-7 17 8 162 51-5-4-137Z'

function WashedFlightBomber({ idPrefix }: StudyPartProps) {
  return (
    <g>
      <g fill={`url(#${idPrefix}-charcoal)`} stroke="#111310" strokeWidth="1.35">
        <path d={flightLeftSleeve} />
        <path d={flightRightSleeve} />
        <path d={flightLeftBody} />
        <path d={flightRightBody} />
      </g>
      <g fill={`url(#${idPrefix}-wash)`} opacity="0.85">
        <path d={flightLeftSleeve} />
        <path d={flightRightSleeve} />
        <path d={flightLeftBody} />
        <path d={flightRightBody} />
      </g>

      <path d="m180 141 32-5 8 15-12 17-15-18Z" fill="#292b28" stroke="#7d7b74" strokeWidth="1" />
      <path d="m260 141-32-5-8 15 12 17 15-18Z" fill="#292b28" stroke="#7d7b74" strokeWidth="1" />

      <g fill="#20221f" stroke="#77766f" strokeWidth="0.8">
        <path d="m160 296 51 4v15l-51-5Z" />
        <path d="m229 300 51-4v14l-51 5Z" />
        <path d="m141 281 23 1v12l-22-1Z" />
        <path d="m276 282 23-1-1 12-22 1Z" />
      </g>

      <g fill="none" stroke="#aaa79f" strokeWidth="0.8" opacity="0.58">
        <path d="M166 172c12 11 25 15 41 14M274 172c-12 11-25 15-41 14" />
        <path d="m171 235 34-17M269 235l-34-17" />
        <path d="M143 220c7 4 14 6 21 6M297 220c-7 4-14 6-21 6" />
        <path d="M166 258c12 5 25 6 38 4M274 258c-12 5-25 6-38 4" strokeDasharray="2 3" />
      </g>

      <g fill="#181a18" stroke="#929089" strokeWidth="0.75">
        <path d="M126 186h22l2 28-20 2Z" />
        <path d="M129 190h18M139 190v23" />
      </g>
      <Zipper x={212} yStart={169} yEnd={300} color="#b4b1a8" />
      <Zipper x={228} yStart={169} yEnd={300} color="#b4b1a8" />
      <DevDayPatch x={172} y={186} rotate={-2} fill="#d7d3c8" ink="#171816" />
    </g>
  )
}

const reverseLeftSleeve = 'M177 141 146 147 117 181l11 30 16-12 1 92 20 4 8-88 14-51Z'
const reverseRightSleeve = 'M263 141 294 147 323 181l-11 30-16-12-1 92-20 4-8-88-14-51Z'
const reverseLeftBody = 'M181 141l32-5 7 19-8 163-50-8 3-139Z'
const reverseRightBody = 'M259 141l-32-5-7 19 8 163 50-8-3-139Z'

function ExposedConstructionBomber({ idPrefix }: StudyPartProps) {
  return (
    <g>
      <g fill={`url(#${idPrefix}-reverse)`} stroke="#171815" strokeWidth="1.3">
        <path d={reverseLeftSleeve} />
        <path d={reverseRightSleeve} />
        <path d={reverseLeftBody} />
        <path d={reverseRightBody} />
      </g>

      <g fill="#b9b4a8" fillOpacity="0.2" stroke="#d9d4c8" strokeWidth="1.2">
        <path d="m172 197 36 8-6 50-34-12Z" />
        <path d="m268 197-36 8 6 50 34-12Z" />
        <path d="m165 276 46 8 1 26-50-8Z" />
        <path d="m275 276-46 8-1 26 50-8Z" />
      </g>

      <g fill="none" stroke="#ded8ca" opacity="0.72">
        <path d="M181 142c-8 31-12 73-11 125M259 142c8 31 12 73 11 125" strokeWidth="3" />
        <path d="m146 149 26 24M294 149l-26 24M128 211l16-12M312 211l-16-12" strokeWidth="3" />
        <path d="M163 310c16 5 32 7 49 8M277 310c-16 5-32 7-49 8" strokeWidth="3" />
      </g>
      <g fill="none" stroke="#292a26" strokeWidth="0.75" strokeDasharray="2 2" opacity="0.92">
        <path d="M181 142c-8 31-12 73-11 125M259 142c8 31 12 73 11 125" />
        <path d="m146 149 26 24M294 149l-26 24M128 211l16-12M312 211l-16-12" />
        <path d="M163 310c16 5 32 7 49 8M277 310c-16 5-32 7-49 8" />
        <path d="m172 197 36 8-6 50-34-12ZM268 197l-36 8 6 50 34-12Z" />
      </g>

      <g fill="none" stroke="#f06a2a" strokeWidth="1.1">
        <path d="m213 137 7 18-9 19M227 137l-7 18 9 19" />
        <path d="M146 286h18M276 286h18" />
      </g>
      <Zipper x={212} yStart={176} yEnd={301} color="#f06a2a" />
      <Zipper x={228} yStart={176} yEnd={301} color="#f06a2a" />
      <Bartack x={169} y={194} rotate={-75} />
      <Bartack x={265} y={194} rotate={75} />
      <Bartack x={168} y={251} rotate={-8} />
      <Bartack x={266} y={251} rotate={8} />
      <Bartack x={146} y={278} rotate={90} />
      <Bartack x={294} y={278} rotate={90} />
      <DevDayPatch x={234} y={178} rotate={2} fill="#242522" ink="#f06a2a" />
    </g>
  )
}

const oliveLeftSleeve = 'M177 138 148 141 123 165l4 28 16-8-2 103 21 4 10-77 13-62Z'
const oliveRightSleeve = 'M263 138 292 141 317 165l-4 28-16-8 2 103-21 4-10-77-13-62Z'
const oliveLeftBody = 'M181 138l31-5 7 18-7 116-53-4 5-101Z'
const oliveRightBody = 'M259 138l-31-5-7 18 7 116 53-4-5-101Z'

function ModularOliveBomber({ idPrefix }: StudyPartProps) {
  return (
    <g>
      <g fill={`url(#${idPrefix}-olive)`} stroke="#1f241d" strokeWidth="1.35">
        <path d={oliveLeftSleeve} />
        <path d={oliveRightSleeve} />
        <path d={oliveLeftBody} />
        <path d={oliveRightBody} />
      </g>

      <path d="m197 137 15-4 8 18-13 18-17-23ZM243 137l-15-4-8 18 13 18 17-23Z" fill="#394235" stroke="#939a82" strokeWidth="1" />
      <path d="m160 251 52 2v14l-53-4ZM280 251l-52 2v14l53-4Z" fill="#394235" stroke="#8e957e" strokeWidth="0.9" />

      <g fill="#485342" stroke="#a0a68f" strokeWidth="0.8">
        <path d="M170 177h38l2 49-40-3Z" />
        <path d="M232 174h39l-1 52-40 1Z" />
        <path d="M176 229h34v27l-36-2Z" />
        <path d="M230 230h34l2 24-36 2Z" />
        <path d="m278 192 24 3-2 39-25-2Z" />
      </g>

      <g fill="none" stroke="#c2c6af" strokeWidth="0.8" opacity="0.78">
        <path d="M170 188h38M232 186h38M177 239h33M230 240h35M278 203l23 3" />
        <path d="M189 177v48M251 174v52M289 194l-2 38" strokeDasharray="2 3" />
        <path d="m163 162 28 12M277 162l-28 12" />
      </g>

      <g fill="#aeb49b" stroke="#30382c" strokeWidth="0.65">
        <rect x="165" y="166" width="5" height="59" rx="1" />
        <rect x="270" y="166" width="5" height="59" rx="1" />
        <rect x="149" y="205" width="5" height="52" rx="1" transform="rotate(4 151.5 231)" />
        <rect x="286" y="205" width="5" height="52" rx="1" transform="rotate(-4 288.5 231)" />
      </g>
      <g fill="none" stroke="#c5cab4" strokeWidth="1">
        <circle cx="168" cy="231" r="3" />
        <circle cx="272" cy="231" r="3" />
        <path d="M165 250h7M268 250h7M146 273h18M276 273h18" />
      </g>

      <Zipper x={212} yStart={171} yEnd={250} color="#c4c8b1" />
      <Zipper x={228} yStart={171} yEnd={250} color="#c4c8b1" />
      <DevDayPatch x={174} y={193} rotate={-1} fill="#d4d5c5" ink="#283024" />
    </g>
  )
}

type BomberProps = StudyPartProps & {
  version: DevDayLookVersion
}

function Bomber({ idPrefix, version }: BomberProps) {
  if (version === 1) return <WashedFlightBomber idPrefix={idPrefix} />
  if (version === 2) return <ExposedConstructionBomber idPrefix={idPrefix} />
  return <ModularOliveBomber idPrefix={idPrefix} />
}

export function DevDayLookStudy({ version, label, style, ...props }: DevDayLookStudyProps) {
  const reduced = Boolean(useReducedMotion())
  const idPrefix = `dev-day-${useId().replace(/:/g, '')}`
  const accessibleLabel =
    label ??
    `Look ${version}: fictional non-identifiable adult model, age 25 or older, in a Los Angeles editorial setting, wearing a white T-shirt beneath ${versionDescriptions[version]}.`

  return (
    <motion.svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width={props.width ?? '100%'}
      viewBox="0 0 440 520"
      preserveAspectRatio={props.preserveAspectRatio ?? 'xMidYMid meet'}
      role="img"
      aria-label={accessibleLabel}
      focusable={props.focusable ?? 'false'}
      initial={false}
      strokeLinecap="round"
      strokeLinejoin="round"
      style={{ display: 'block', height: 'auto', overflow: 'hidden', ...style }}
    >
      <StudyDefs idPrefix={idPrefix} />
      <EditorialSetting idPrefix={idPrefix} reduced={reduced} version={version} />

      <motion.ellipse
        cx="220"
        cy="470"
        rx="72"
        ry="12"
        fill="#050505"
        animate={reduced ? { opacity: 0.3, scaleX: 1 } : { opacity: [0.28, 0.22, 0.28], scaleX: [1, 0.985, 1] }}
        transition={reduced ? { duration: 0 } : { duration: 8.5, ease: 'easeInOut', repeat: Infinity }}
        style={{ transformOrigin: '220px 470px' }}
      />

      <motion.g
        aria-hidden="true"
        animate={reduced ? { y: 0 } : { y: [0, -1.2, 0] }}
        transition={reduced ? { duration: 0 } : { duration: 8.5, ease: 'easeInOut', repeat: Infinity }}
      >
        <LowerModel idPrefix={idPrefix} />
        <UnderLayer idPrefix={idPrefix} />
        <Bomber idPrefix={idPrefix} version={version} />
        <ModelHands idPrefix={idPrefix} />
        <ModelHead idPrefix={idPrefix} />
      </motion.g>
    </motion.svg>
  )
}
