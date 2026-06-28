import type { ApiOperation, SchemaObject } from './types'

export interface CodeSample {
  label: string
  lang: 'bash' | 'typescript' | 'python'
  code: string
}

/** A representative placeholder value for a schema property. */
const exampleFor = (schema?: SchemaObject): unknown => {
  if (!schema) return 'string'
  if (schema.example !== undefined) return schema.example
  if (schema.default !== undefined) return schema.default
  if (schema.enum && schema.enum.length > 0) return schema.enum[0]
  switch (schema.type) {
    case 'integer':
    case 'number':
      return 0
    case 'boolean':
      return true
    case 'array':
      return [exampleFor(schema.items)]
    case 'object':
      return buildExampleObject(schema)
    default:
      return schema.format === 'date-time' ? '2026-01-01T00:00:00Z' : 'string'
  }
}

const buildExampleObject = (schema?: SchemaObject): Record<string, unknown> => {
  const out: Record<string, unknown> = {}
  for (const [key, prop] of Object.entries(schema?.properties ?? {})) {
    out[key] = exampleFor(prop)
  }
  return out
}

const buildUrl = (op: ApiOperation): string => {
  const query = op.parameters
    .filter((p) => p.in === 'query')
    .map((p) => `${p.name}=${encodeURIComponent(String(exampleFor(p.schema)))}`)
    .join('&')
  return `${op.baseUrl}${op.path}${query ? `?${query}` : ''}`
}

const hasJsonBody = (op: ApiOperation): boolean =>
  Boolean(op.body && op.body.mediaType.includes('json'))

const bodyJson = (op: ApiOperation): string =>
  JSON.stringify(buildExampleObject(op.body?.schema), null, 2)

const curlSample = (op: ApiOperation): string => {
  const lines = [`curl -X ${op.method.toUpperCase()} "${buildUrl(op)}" \\`]
  lines.push(`  -H "Authorization: Bearer $OUTCEPTION_TOKEN" \\`)
  if (hasJsonBody(op)) {
    lines.push(`  -H "Content-Type: application/json" \\`)
    lines.push(`  -d '${bodyJson(op).replace(/\n\s*/g, ' ')}'`)
  } else {
    lines.push(`  -H "Accept: application/json"`)
  }
  return lines.join('\n')
}

const tsSample = (op: ApiOperation): string => {
  const init: string[] = [`  method: '${op.method.toUpperCase()}',`]
  const headers = [`    Authorization: \`Bearer \${process.env.OUTCEPTION_TOKEN}\`,`]
  if (hasJsonBody(op)) headers.push(`    'Content-Type': 'application/json',`)
  init.push(`  headers: {\n${headers.join('\n')}\n  },`)
  if (hasJsonBody(op)) {
    init.push(`  body: JSON.stringify(${bodyJson(op)}),`)
  }
  return [
    `const response = await fetch('${buildUrl(op)}', {`,
    init.join('\n'),
    `})`,
    ``,
    `const data = await response.json()`,
  ].join('\n')
}

const pySample = (op: ApiOperation): string => {
  const args = [`    "${buildUrl(op)}",`, `    headers=headers,`]
  if (hasJsonBody(op)) args.push(`    json=payload,`)
  const lines = [
    `import os`,
    `import requests`,
    ``,
    `headers = {"Authorization": f"Bearer {os.environ['OUTCEPTION_TOKEN']}"}`,
  ]
  if (hasJsonBody(op)) {
    lines.push(`payload = ${bodyJson(op).replace(/true/g, 'True').replace(/false/g, 'False')}`)
  }
  lines.push(
    ``,
    `response = requests.${op.method.toLowerCase()}(`,
    args.join('\n'),
    `)`,
    `data = response.json()`,
  )
  return lines.join('\n')
}

export function buildCodeSamples(op: ApiOperation): CodeSample[] {
  return [
    { label: 'cURL', lang: 'bash', code: curlSample(op) },
    { label: 'TypeScript', lang: 'typescript', code: tsSample(op) },
    { label: 'Python', lang: 'python', code: pySample(op) },
  ]
}
