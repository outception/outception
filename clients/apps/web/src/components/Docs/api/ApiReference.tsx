import { Text } from '@outception-com/orbit'
import { Box } from '@outception-com/orbit/Box'
import { highlightCode } from '@/lib/openapi/highlight'
import { getOperation, schemaTypeLabel } from '@/lib/openapi/parse'
import { buildCodeSamples } from '@/lib/openapi/samples'
import type { ApiOperation, ApiParam } from '@/lib/openapi/types'
import { CodeSamples, type RenderedSample } from './CodeSamples'
import { SchemaProperties } from './SchemaProperties'

const METHOD_BACKGROUND: Record<
  string,
  Parameters<typeof Box>[0]['backgroundColor']
> = {
  get: 'background-success',
  post: 'background-pending',
  put: 'background-warning',
  patch: 'background-warning',
  delete: 'background-danger',
}

function MethodBadge({ method, path }: { method: string; path: string }) {
  return (
    <Box
      alignItems="center"
      columnGap="s"
      borderRadius="m"
      borderWidth={1}
      borderStyle="solid"
      borderColor="border-primary"
      backgroundColor="background-secondary"
      paddingVertical="s"
      paddingHorizontal="m"
    >
      <Box
        backgroundColor={METHOD_BACKGROUND[method] ?? 'background-secondary'}
        borderRadius="s"
        paddingHorizontal="s"
      >
        <code className="font-mono text-xs font-bold uppercase">{method}</code>
      </Box>
      <code className="text-muted-foreground font-mono text-sm break-all">{path}</code>
    </Box>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Box flexDirection="column" rowGap="s" marginTop="xl">
      <Text variant="heading-xs" as="h2">
        {title}
      </Text>
      {children}
    </Box>
  )
}

function ParamRow({ param }: { param: ApiParam }) {
  return (
    <Box
      as="li"
      flexDirection="column"
      rowGap="xs"
      paddingVertical="m"
      borderBottomWidth={1}
      borderStyle="solid"
      borderColor="border-secondary"
    >
      <Box alignItems="baseline" columnGap="s" flexWrap="wrap">
        <code className="font-mono text-sm font-medium">{param.name}</code>
        <Text variant="caption" color="muted">
          {schemaTypeLabel(param.schema)}
        </Text>
        {param.required ? (
          <Text variant="caption" color="danger">
            required
          </Text>
        ) : null}
      </Box>
      {param.description ? (
        <Text variant="body" color="muted">
          {param.description}
        </Text>
      ) : null}
    </Box>
  )
}

function ParamGroup({ title, params }: { title: string; params: ApiParam[] }) {
  if (params.length === 0) return null
  return (
    <Section title={title}>
      <Box as="ul" flexDirection="column" className="list-none pl-0">
        {params.map((param) => (
          <ParamRow key={`${param.in}-${param.name}`} param={param} />
        ))}
      </Box>
    </Section>
  )
}

async function renderSamples(op: ApiOperation): Promise<RenderedSample[]> {
  const samples = buildCodeSamples(op)
  return Promise.all(
    samples.map(async (sample) => ({
      label: sample.label,
      code: sample.code,
      html: await highlightCode(sample.code, sample.lang),
    })),
  )
}

export async function ApiReference({ operation }: { operation: string }) {
  const op = await getOperation(operation)

  if (!op) {
    const [method, path] = operation.split(/\s+/, 2)
    return (
      <Box marginBottom="l">
        <MethodBadge method={(method ?? '').toLowerCase()} path={path ?? ''} />
      </Box>
    )
  }

  const samples = await renderSamples(op)
  const success = op.responses.find((r) => r.status.startsWith('2'))
  const errors = op.responses.filter((r) => !r.status.startsWith('2'))

  return (
    <Box flexDirection="column" rowGap="m" marginBottom="xl">
      <MethodBadge method={op.method} path={op.path} />
      {op.description ? (
        <Text variant="body" color="muted">
          {op.description}
        </Text>
      ) : null}

      <Box marginTop="m">
        <CodeSamples samples={samples} />
      </Box>

      <ParamGroup
        title="Path parameters"
        params={op.parameters.filter((p) => p.in === 'path')}
      />
      <ParamGroup
        title="Query parameters"
        params={op.parameters.filter((p) => p.in === 'query')}
      />
      <ParamGroup
        title="Header parameters"
        params={op.parameters.filter((p) => p.in === 'header')}
      />

      {op.body?.schema ? (
        <Section title="Body">
          <SchemaProperties schema={op.body.schema} />
        </Section>
      ) : null}

      {success?.schema ? (
        <Section title={`Response · ${success.status}`}>
          {success.description ? (
            <Text variant="body" color="muted">
              {success.description}
            </Text>
          ) : null}
          <SchemaProperties schema={success.schema} />
        </Section>
      ) : null}

      {errors.length > 0 ? (
        <Section title="Errors">
          <Box as="ul" flexDirection="column" rowGap="xs" className="list-none pl-0">
            {errors.map((response) => (
              <Box as="li" key={response.status} columnGap="s" alignItems="baseline">
                <code className="font-mono text-sm font-medium">{response.status}</code>
                <Text variant="body" color="muted">
                  {response.description ?? ''}
                </Text>
              </Box>
            ))}
          </Box>
        </Section>
      ) : null}
    </Box>
  )
}
