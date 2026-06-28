import 'server-only'
import { dereference } from '@scalar/openapi-parser'
import { promises as fs } from 'node:fs'
import path from 'node:path'
import type {
  ApiBody,
  ApiOperation,
  ApiParam,
  ApiResponse,
  SchemaObject,
} from './types'

interface OpenApiDoc {
  servers?: { url: string }[]
  paths?: Record<string, Record<string, RawOperation>>
}
interface RawOperation {
  summary?: string
  description?: string
  parameters?: ApiParam[]
  requestBody?: {
    required?: boolean
    content?: Record<string, { schema?: SchemaObject }>
  }
  responses?: Record<
    string,
    { description?: string; content?: Record<string, { schema?: SchemaObject }> }
  >
}

const SPEC_PATH = path.join(process.cwd(), 'content', 'openapi.yaml')
const DEFAULT_BASE_URL = 'https://api.outception.com'

let specPromise: Promise<OpenApiDoc> | null = null

const loadSpec = (): Promise<OpenApiDoc> => {
  if (!specPromise) {
    specPromise = fs.readFile(SPEC_PATH, 'utf8').then(async (raw) => {
      const { schema } = await dereference(raw)
      return (schema ?? {}) as OpenApiDoc
    })
  }
  return specPromise
}

/** Prefer a JSON media type, else the first one declared. */
const pickMediaType = (
  content?: Record<string, { schema?: SchemaObject }>,
): [string, SchemaObject | undefined] | undefined => {
  if (!content) return undefined
  const keys = Object.keys(content)
  if (keys.length === 0) return undefined
  const jsonKey = keys.find((k) => k.includes('json')) ?? keys[0]
  return [jsonKey, content[jsonKey]?.schema]
}

const normalizeBody = (op: RawOperation): ApiBody | undefined => {
  if (!op.requestBody) return undefined
  const picked = pickMediaType(op.requestBody.content)
  if (!picked) return undefined
  return {
    mediaType: picked[0],
    schema: picked[1],
    required: op.requestBody.required ?? false,
  }
}

const normalizeResponses = (op: RawOperation): ApiResponse[] =>
  Object.entries(op.responses ?? {}).map(([status, response]) => {
    const picked = pickMediaType(response.content)
    return {
      status,
      description: response.description,
      mediaType: picked?.[0],
      schema: picked?.[1],
    }
  })

/** Parse a frontmatter `openapi` value like "GET /v1/news/sources". */
export const parseOperationRef = (
  ref: string,
): { method: string; path: string } | null => {
  const [method, opPath] = ref.trim().split(/\s+/, 2)
  if (!method || !opPath) return null
  return { method: method.toLowerCase(), path: opPath }
}

export async function getOperation(ref: string): Promise<ApiOperation | null> {
  const parsed = parseOperationRef(ref)
  if (!parsed) return null
  const spec = await loadSpec()
  const raw = spec.paths?.[parsed.path]?.[parsed.method]
  if (!raw) return null
  return {
    method: parsed.method,
    path: parsed.path,
    baseUrl: spec.servers?.[0]?.url ?? DEFAULT_BASE_URL,
    summary: raw.summary,
    description: raw.description,
    parameters: raw.parameters ?? [],
    body: normalizeBody(raw),
    responses: normalizeResponses(raw),
  }
}

/** Human-readable type label for a schema (e.g. "string", "array<Source>"). */
export function schemaTypeLabel(schema?: SchemaObject): string {
  if (!schema) return 'any'
  if (schema.enum) return 'enum'
  if (schema.type === 'array') {
    return `array<${schemaTypeLabel(schema.items)}>`
  }
  if (schema.anyOf || schema.oneOf) {
    const variants = (schema.anyOf ?? schema.oneOf) as SchemaObject[]
    return variants.map((variant) => schemaTypeLabel(variant)).join(' | ')
  }
  if (schema.title && schema.type === 'object') return schema.title
  return schema.type ?? schema.title ?? 'object'
}
