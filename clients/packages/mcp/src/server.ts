import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js'
import { ApiError, createApi, type ApiOptions } from './api'
import { defaultSkillsDir } from './skills'
import { TOOLS, parseArguments, strictSchema, type Tool } from './tools'

export interface ServerOptions extends ApiOptions {
  skillsDir?: string
}

export const SERVER_NAME = 'outception'
export const SERVER_VERSION = '0.1.0'

/** The MCP server with every tool registered. Errors come back as tool
 * errors with the status, never as thrown exceptions over the wire. */
export const createServer = (options: ServerOptions): McpServer => {
  const api = createApi(options)
  const env = { skillsDir: options.skillsDir ?? defaultSkillsDir() }
  const server = new McpServer({ name: SERVER_NAME, version: SERVER_VERSION })
  for (const tool of TOOLS as readonly Tool<unknown>[]) {
    server.registerTool(
      tool.name,
      {
        description: tool.description,
        // The strict schema goes to the protocol layer too: it validates
        // before the handler runs and would otherwise strip what it does
        // not know.
        inputSchema: strictSchema(tool) as never,
        annotations: { readOnlyHint: true, openWorldHint: true },
      },
      (async (input: unknown) => {
        try {
          const result = await tool.run(api, parseArguments(tool, input), env)
          return { content: [{ type: 'text', text: result.text }] }
        } catch (error) {
          const message =
            error instanceof ApiError
              ? `The API answered ${error.status}.`
              : error instanceof Error
                ? error.message
                : 'The tool failed.'
          return { content: [{ type: 'text', text: message }], isError: true }
        }
      }) as never,
    )
  }
  return server
}
