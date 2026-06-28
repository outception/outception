import { Text } from '@outception-com/orbit'
import { Box } from '@outception-com/orbit/Box'
import { schemaTypeLabel } from '@/lib/openapi/parse'
import type { SchemaObject } from '@/lib/openapi/types'

const MAX_DEPTH = 2

/** Resolve the object whose `properties` we should enumerate for a schema. */
const objectSchema = (schema?: SchemaObject): SchemaObject | undefined => {
  if (!schema) return undefined
  if (schema.properties) return schema
  if (schema.type === 'array') return objectSchema(schema.items)
  if (schema.allOf) {
    return schema.allOf.find((part) => part.properties) ?? undefined
  }
  return undefined
}

function PropertyRow({
  name,
  schema,
  required,
  depth,
}: {
  name: string
  schema: SchemaObject
  required: boolean
  depth: number
}) {
  const nested = depth < MAX_DEPTH ? objectSchema(schema) : undefined
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
        <code className="font-mono text-sm font-medium">{name}</code>
        <Text variant="caption" color="muted">
          {schemaTypeLabel(schema)}
        </Text>
        {required ? (
          <Text variant="caption" color="danger">
            required
          </Text>
        ) : null}
      </Box>
      {schema.description ? (
        <Text variant="body" color="muted">
          {schema.description}
        </Text>
      ) : null}
      {nested?.properties ? (
        <Box
          marginTop="xs"
          paddingLeft="m"
          borderLeftWidth={1}
          borderStyle="solid"
          borderColor="border-secondary"
        >
          <SchemaProperties schema={nested} depth={depth + 1} />
        </Box>
      ) : null}
    </Box>
  )
}

export function SchemaProperties({
  schema,
  depth = 0,
}: {
  schema?: SchemaObject
  depth?: number
}) {
  const target = objectSchema(schema)
  if (!target?.properties) return null
  const required = new Set(target.required ?? [])
  return (
    <Box as="ul" flexDirection="column" className="list-none pl-0">
      {Object.entries(target.properties).map(([name, prop]) => (
        <PropertyRow
          key={name}
          name={name}
          schema={prop}
          required={required.has(name)}
          depth={depth}
        />
      ))}
    </Box>
  )
}
