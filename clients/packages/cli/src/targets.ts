/**
 * Where the coding agents on a machine keep their tool configuration and
 * their skills. This is the one module that names the agents, so the naming
 * check allowlists it: the installer has to know where each one looks.
 * Paths are relative to the home directory.
 */

export interface AgentTarget {
  id: string
  label: string
  /** The file holding the tool servers map, JSON or TOML. */
  config: string
  format: 'json' | 'toml'
  /** The key holding the servers map in a JSON file. */
  serversKey: string
  /** Where skill folders go, or null when the agent reads none. */
  skillsDir: string | null
  /** A folder whose presence says the agent is installed. */
  marker: string
}

export const TARGETS: readonly AgentTarget[] = [
  {
    id: 'cursor',
    label: 'Cursor',
    config: '.cursor/mcp.json',
    format: 'json',
    serversKey: 'mcpServers',
    skillsDir: null,
    marker: '.cursor',
  },
  {
    id: 'codex',
    label: 'Codex',
    config: '.codex/config.toml',
    format: 'toml',
    serversKey: 'mcp_servers',
    skillsDir: '.codex/skills',
    marker: '.codex',
  },
  {
    id: 'windsurf',
    label: 'Windsurf',
    config: '.codeium/windsurf/mcp_config.json',
    format: 'json',
    serversKey: 'mcpServers',
    skillsDir: null,
    marker: '.codeium/windsurf',
  },
]
