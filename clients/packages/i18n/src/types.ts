import type en from './locales/en'

export type Translations = typeof en

type LeafPaths<T> = T extends object
  ? '_mode' extends keyof T
    ? never
    : {
        [K in keyof T & string]: '_mode' extends keyof T[K]
          ? K
          : T[K] extends object
            ? `${K}.${LeafPaths<T[K]>}`
            : K
      }[keyof T & string]
  : never

export type TranslationKey = LeafPaths<Translations>

// Get the literal string value at a dot-separated path
type ValueAtPath<
  T,
  Path extends string,
> = Path extends `${infer First}.${infer Rest}`
  ? First extends keyof T
    ? ValueAtPath<T[First], Rest>
    : never
  : Path extends keyof T
    ? T[Path]
    : never

// Recursively extract {placeholder} names from a string
type ExtractPlaceholders<S extends string> =
  S extends `${string}{${infer Key}}${infer Rest}`
    ? Key | ExtractPlaceholders<Rest>
    : never

// Get all required interpolation keys for a translation key
// Plurals always require 'count' + any {placeholders} in the templates
type InterpolationKeys<K extends TranslationKey> =
  ValueAtPath<Translations, K> extends infer V
    ? '_mode' extends keyof V
      ? 'count' | ExtractPlaceholders<V[Exclude<keyof V, '_mode'>] & string>
      : V extends string
        ? ExtractPlaceholders<V>
        : never
    : never

type InterpolationValue = string | number | { toString(): string }

type InterpolationsRecord<Keys extends string> = {
  [K in Keys]: K extends 'count' ? number : InterpolationValue
}

// The translate function type with conditional interpolations
export type TranslateFn = <K extends TranslationKey>(
  key: K,
  ...args: InterpolationKeys<K> extends never
    ? []
    : [interpolations: InterpolationsRecord<InterpolationKeys<K>>]
) => string
