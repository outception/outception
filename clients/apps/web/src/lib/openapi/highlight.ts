import 'server-only'
import { createHighlighterCore, type HighlighterCore } from 'shiki/core'
import { createOnigurumaEngine } from 'shiki/engine/oniguruma'
import langBash from 'shiki/langs/bash.mjs'
import langJson from 'shiki/langs/json.mjs'
import langPython from 'shiki/langs/python.mjs'
import langTypescript from 'shiki/langs/typescript.mjs'
import themeCatppuccinLatte from 'shiki/themes/catppuccin-latte.mjs'
import themePoimandres from 'shiki/themes/poimandres.mjs'
import { themeConfig } from '../../../shiki.config.mjs'

let highlighterPromise: Promise<HighlighterCore> | null = null

const getHighlighter = (): Promise<HighlighterCore> => {
  if (!highlighterPromise) {
    highlighterPromise = createHighlighterCore({
      langs: [langBash, langJson, langPython, langTypescript],
      themes: [themeCatppuccinLatte, themePoimandres],
      engine: createOnigurumaEngine(() => import('shiki/wasm')),
    })
  }
  return highlighterPromise
}

/**
 * Server-side highlight that emits the same dual-theme `.shiki` markup the MDX
 * pipeline produces, so globals.css styles it identically (light/dark swap).
 */
export async function highlightCode(
  code: string,
  lang: 'bash' | 'json' | 'python' | 'typescript',
): Promise<string> {
  const highlighter = await getHighlighter()
  return highlighter.codeToHtml(code, {
    lang,
    themes: themeConfig,
    defaultColor: false,
  })
}
