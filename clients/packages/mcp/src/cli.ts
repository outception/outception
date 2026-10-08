import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js'
import { createServer } from './server'

const main = async () => {
  const baseUrl = process.env.OUTCEPTION_API_URL || 'https://api.outception.com'
  const server = createServer({
    baseUrl,
    token: process.env.OUTCEPTION_API_TOKEN,
    skillsDir: process.env.OUTCEPTION_SKILLS_DIR,
  })
  await server.connect(new StdioServerTransport())
}

main().catch((error: unknown) => {
  process.stderr.write(
    `${error instanceof Error ? error.message : String(error)}\n`,
  )
  process.exit(1)
})
