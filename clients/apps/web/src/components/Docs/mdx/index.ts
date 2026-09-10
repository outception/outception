import type { MDXComponents } from 'mdx/types'
import { Accordion, AccordionGroup } from './Accordion'
import { Danger, Info, Note, Tip, Warning } from './Callout'
import { Card, CardGroup } from './Card'
import { CodeGroup } from './CodeGroup'
import { ParamField } from './ParamField'
import { Step, Steps } from './Steps'

/** Mintlify-compatible MDX components used by the migrated docs/handbook content. */
export const docsMdxComponents: MDXComponents = {
  Note,
  Info,
  Tip,
  Warning,
  Danger,
  Card,
  CardGroup,
  Steps,
  Step,
  CodeGroup,
  Accordion,
  AccordionGroup,
  ParamField,
}
