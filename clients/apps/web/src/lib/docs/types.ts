export type DocSet = 'docs' | 'handbook'

export interface DocFrontmatter {
  title?: string
  sidebarTitle?: string
  description?: string
  /** Present on API-reference pages: e.g. "GET /v1/news/sources" */
  openapi?: string
}

export interface NavLeaf {
  kind: 'leaf'
  title: string
  /** slug segments relative to the set root, e.g. ["integrate", "authentication"] */
  slug: string[]
  /** absolute path, e.g. "/docs/integrate/authentication" */
  href: string
}

export interface NavGroup {
  kind: 'group'
  title: string
  items: NavNode[]
}

export type NavNode = NavLeaf | NavGroup

export interface NavTab {
  title: string
  icon?: string
  items: NavNode[]
}

export interface DocRedirect {
  source: string
  destination: string
}

export interface DocsManifest {
  set: DocSet
  /** "/docs" or "/handbook" */
  basePath: string
  name: string
  tabs: NavTab[]
}

export interface TocHeading {
  depth: 2 | 3
  title: string
  id: string
}
