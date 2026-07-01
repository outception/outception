import { schemas } from '@outception-com/client'
import { FieldPath, FieldValues, UseFormSetError } from 'react-hook-form'

export const setValidationErrors = <TFieldValues extends FieldValues>(
  errors: schemas['ValidationError'][],
  setError: UseFormSetError<TFieldValues>,
  slice: number = 1,
  discriminators?: string[] | undefined,
): void => {
  errors.forEach((error) => {
    let loc = error.loc.slice(slice)
    if (discriminators && discriminators.includes(loc[0] as string)) {
      loc = loc.slice(1)
    }
    setError(loc.join('.') as FieldPath<TFieldValues>, {
      type: error.type,
      message: error.msg,
    })
  })
}

/**
 * Product-specific validation error handler with advanced discriminated union filtering.
 * Use this for Product and ProductPrice forms that use Pydantic discriminated unions.
 * For other forms, use the simpler setValidationErrors function.
 */
export const setProductValidationErrors = <TFieldValues extends FieldValues>(
  errors: schemas['ValidationError'][],
  setError: UseFormSetError<TFieldValues>,
  slice: number = 1,
  discriminators?: string[] | undefined,
): void => {
  errors.forEach((error) => {
    // Skip errors with no message or invalid message
    if (
      !error.msg ||
      error.msg.trim() === '' ||
      error.msg === 'undefined' ||
      error.msg === 'null'
    ) {
      return
    }

    let loc = error.loc.slice(slice)

    // Filter out discriminator fields from the path
    loc = loc.filter((segment) => {
      const segmentStr = String(segment)

      // Skip if in explicit discriminators list
      if (discriminators && discriminators.includes(segmentStr)) {
        return false
      }

      // Skip Pydantic function validators (e.g., "function-after[...]")
      if (
        segmentStr.startsWith('function-after[') ||
        segmentStr.startsWith('function-before[')
      ) {
        return false
      }

      // Skip union discriminator types (PascalCase containing "Create", "Update", or "Base")
      // These are FastAPI/Pydantic discriminated union field names like ProductCreateOneTime
      if (
        /^[A-Z][a-zA-Z]*(?:Create|Update|Base)[a-zA-Z]*$/.test(segmentStr) &&
        !segmentStr.match(/^[A-Z]{2,}/) // Allow acronyms like "ID"
      ) {
        return false
      }

      return true
    })

    // Only set error if we have a valid field path
    if (loc.length > 0) {
      const fieldPath = loc.join('.')
      setError(fieldPath as FieldPath<TFieldValues>, {
        type: error.type,
        message: error.msg,
      })
    }
  })
}

export const extractApiErrorMessage = (
  error: { detail?: string | { msg?: string }[] | unknown },
  fallback: string = 'An unexpected error occurred',
): string => {
  if (typeof error?.detail === 'string') return error.detail
  if (Array.isArray(error?.detail)) return error.detail[0]?.msg || fallback
  return fallback
}

/**
 * Recursively searches a react-hook-form FieldErrors object for the first
 * error message string. Handles nested fields like `prices.0.price_amount`.
 */
export const findFirstErrorMessage = (
  obj: unknown,
  depth: number = 0,
): string | undefined => {
  if (depth > 10 || !obj || typeof obj !== 'object') return undefined
  if (
    'message' in obj &&
    typeof (obj as Record<string, unknown>).message === 'string'
  ) {
    return (obj as Record<string, unknown>).message as string
  }
  for (const value of Object.values(obj)) {
    const msg = findFirstErrorMessage(value, depth + 1)
    if (msg) return msg
  }
  return undefined
}
