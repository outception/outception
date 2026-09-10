import { experiments } from './experiments'

export { experiments }

export type ExperimentName = keyof typeof experiments

export type ExperimentVariant<T extends ExperimentName> =
  (typeof experiments)[T]['variants'][number]

export function getDefaultVariant<T extends ExperimentName>(
  experimentName: T,
): ExperimentVariant<T> {
  return experiments[experimentName].defaultVariant as ExperimentVariant<T>
}

export function getExperimentNames(): ExperimentName[] {
  return Object.keys(experiments) as ExperimentName[]
}
