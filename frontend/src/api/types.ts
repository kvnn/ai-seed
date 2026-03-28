export type RunStatus =
  | 'draft'
  | 'research_ready'
  | 'brand_ready'
  | 'site_ready'
  | 'approved'
  | 'published'
  | 'failed'

export type RunStage = 'research' | 'brand' | 'site'

export type AuthUser = {
  id: string
  email: string
  name?: string | null
  is_admin: boolean
  created_at: string
}

export type AuthResponse = {
  user: AuthUser
  access_token: string
  token_type: string
}

export type BackendRootEntry = {
  name: string
  kind: 'dir' | 'file' | 'other'
}

export type BackendRootResponse = {
  root_name: string
  generated_at: string
  entries: BackendRootEntry[]
}

export type ResearchArtifact = {
  summary: string
  source_label: string
  recommended_audience: string
  key_facts: string[]
  cautions: string[]
}

export type BrandArtifact = {
  vision: string
  value: string
  voice: string
  brand_imagery: string[]
  color_palette_hex: string[]
}

export type GeneratedFile = {
  path: string
  media_type?: string | null
  content: string
}

export type SiteArtifact = {
  title: string
  description: string
  entrypoint: string
  files: GeneratedFile[]
}

export type RunResponse = {
  id: string
  status: RunStatus
  source_url?: string | null
  brief: string
  preferred_style?: string | null
  publish_slug: string
  required_facts: string[]
  banned_claims: string[]
  research?: ResearchArtifact | null
  brand?: BrandArtifact | null
  site?: SiteArtifact | null
  next_actions: string[]
  preview_url?: string | null
  published_path?: string | null
  failed_stage?: RunStage | null
  last_error?: string | null
  created_at: string
  updated_at: string
  published_at?: string | null
}

export type RunListResponse = {
  runs: RunResponse[]
}

export type RunCreateRequest = {
  brief: string
  source_url?: string
  preferred_style?: string
  publish_slug?: string
  required_facts: string[]
  banned_claims: string[]
}
