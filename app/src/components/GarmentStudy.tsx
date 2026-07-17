type GarmentStudyProps = {
  label: string
}

export function GarmentStudy({ label }: GarmentStudyProps) {
  return (
    <figure className="garment-study">
      <div className="garment-paper">
        <svg viewBox="0 0 440 520" role="img" aria-label={`Front study of ${label}`}>
          <defs>
            <linearGradient id="cloth" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0" stopColor="#f6f6f0" />
              <stop offset="0.52" stopColor="#deded7" />
              <stop offset="1" stopColor="#bdbdb7" />
            </linearGradient>
            <filter id="paper-noise">
              <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="6" result="noise" />
              <feColorMatrix in="noise" type="saturate" values="0" result="mono" />
              <feBlend in="SourceGraphic" in2="mono" mode="soft-light" />
            </filter>
            <filter id="shadow" x="-30%" y="-30%" width="160%" height="180%">
              <feDropShadow dx="0" dy="16" stdDeviation="14" floodColor="#000" floodOpacity="0.45" />
            </filter>
          </defs>
          <path
            d="M145 72 72 108 30 203l62 29 29-54v268c29 13 62 20 99 20s70-7 99-20V178l29 54 62-29-42-95-73-36c-12 31-37 48-75 48s-63-17-75-48Z"
            fill="url(#cloth)"
            filter="url(#shadow)"
          />
          <path
            d="M145 72c12 31 37 48 75 48s63-17 75-48M121 178l24-106M319 178 295 72M92 232l29-54M348 232l-29-54M121 426c65 17 133 17 198 0"
            fill="none"
            stroke="#8b8b86"
            strokeWidth="2"
            strokeDasharray="4 5"
            opacity="0.7"
          />
          <path
            d="M171 78c4 24 20 38 49 38s45-14 49-38c-13 8-29 12-49 12s-36-4-49-12Z"
            fill="#0c0c0c"
            opacity="0.93"
          />
          <path
            d="M145 72 72 108 30 203l62 29 29-54v268c29 13 62 20 99 20s70-7 99-20V178l29 54 62-29-42-95-73-36c-12 31-37 48-75 48s-63-17-75-48Z"
            fill="transparent"
            filter="url(#paper-noise)"
            opacity="0.28"
          />
        </svg>
        <div className="study-cross study-cross--tl" aria-hidden="true" />
        <div className="study-cross study-cross--br" aria-hidden="true" />
      </div>
      <figcaption>
        <span>OBJECT / 001</span>
        <strong>{label.toUpperCase()}</strong>
        <small>FRONT / BASE STUDY</small>
      </figcaption>
    </figure>
  )
}
