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
  designer?: {
    name: string
    role: string
    avatarUrl?: string
    avatarAlt?: string
    avatarCredit?: string
  }
}

export type ReferenceItem = {
  id: string
  kind: 'image' | 'link' | 'catalog'
  name: string
  previewUrl?: string
  source?: string
  labelId?: string
  labelName?: string
  tags?: string[]
  file?: File
}

export type ReferenceCatalogItem = {
  id: string
  title: string
  category: string
  object_type: string
  description: string
  image_url: string
  image_alt: string
  metadata: {
    seed_order: number
    silhouette: string
    materials: string[]
    construction: string[]
    palette: string[]
    tags: string[]
    label_association: {
      id: string
      name: string
      matched_traits: string[]
      basis: string
      note: string
    }
    provenance: {
      kind: string
      label: string
      note: string
      rights: string
    }
  }
}

export type StudioSeed = {
  projectId: string
  demoMode: boolean
  selectedBrands: Brand[]
  objectName: string
  references: ReferenceItem[]
}
