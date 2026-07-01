/** A resolved (dereferenced) OpenAPI schema object. */
export type SchemaObject = {
  type?: string
  title?: string
  format?: string
  description?: string
  items?: SchemaObject
  properties?: Record<string, SchemaObject>
  required?: string[]
  enum?: unknown[]
  anyOf?: SchemaObject[]
  oneOf?: SchemaObject[]
  allOf?: SchemaObject[]
  default?: unknown
  example?: unknown
  [key: string]: unknown
}

export interface ApiParam {
  name: string
  in: 'path' | 'query' | 'header' | 'cookie'
  required: boolean
  description?: string
  schema?: SchemaObject
}

export interface ApiBody {
  mediaType: string
  schema?: SchemaObject
  required: boolean
}

export interface ApiResponse {
  status: string
  description?: string
  mediaType?: string
  schema?: SchemaObject
}

export interface ApiOperation {
  method: string
  path: string
  baseUrl: string
  summary?: string
  description?: string
  parameters: ApiParam[]
  body?: ApiBody
  responses: ApiResponse[]
}
