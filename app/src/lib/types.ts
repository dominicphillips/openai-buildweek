export type RitualStage =
  | 'arrival'
  | 'sound'
  | 'breath'
  | 'headspace'
  | 'brands'
  | 'object'
  | 'references'
  | 'threshold'
  | 'studio'

export type Brand = {
  id: string
  name: string
  tags: string[]
  seed?: boolean
}

export type ReferenceItem = {
  id: string
  kind: 'image' | 'link'
  name: string
  previewUrl?: string
  source?: string
}

export type StudioSeed = {
  selectedBrands: Brand[]
  objectName: string
  references: ReferenceItem[]
}
