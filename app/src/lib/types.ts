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
  /** Official label name for sourced product references. */
  brand?: string
  /** Product-page name. Falls back to title for legacy catalog rows. */
  product_name?: string
  category: string
  object_type: string
  description: string
  /** Public product page retained for source lineage. */
  source_url?: string
  /** Neutral, editable qualities observed in the object. */
  neutral_attributes?: string[]
  image_url: string
  image_alt: string
  metadata: {
    seed_order: number
    /** Optional aliases keep the existing catalog response backward-compatible. */
    brand?: string
    product_name?: string
    source_url?: string
    neutral_attributes?: string[]
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

export type InspirationFacets = {
  total: number
  brands: Array<{ value: string; count: number }>
  categories: Array<{ value: string; count: number }>
  object_types: Array<{ value: string; count: number }>
}

export type StudioSeed = {
  projectId: string
  demoMode: boolean
  selectedBrands: Brand[]
  objectName: string
  references: ReferenceItem[]
}
