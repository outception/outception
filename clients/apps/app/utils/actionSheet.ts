// A pending action sheet, exposed as an external store (same pattern as
// utils/summaryOpen.ts): a plain function can raise one from a press handler
// while a single host component renders it.
//
// This exists because react-native's Alert takes AT MOST THREE buttons on
// Android - Alert.js slices the list and maps what survives onto the
// positive/negative/neutral slots of an AndroidX dialog. The headline menu
// has six, so on Android everything from "mute word" down was silently
// dropped, including Cancel. iOS keeps the native alert (it lists them all).

export type SheetOption = {
  label: string
  /** Rendered in the destructive tone, like Alert's `style: 'destructive'`. */
  destructive?: boolean
  onPress?: () => void
}

export type Sheet = {
  title: string
  options: SheetOption[]
  /** Label for the dismiss row. */
  cancel: string
}

let sheet: Sheet | null = null
const listeners = new Set<() => void>()

const emit = (): void => {
  for (const listener of listeners) listener()
}

/** Raise a sheet, replacing any open one - which is how a row can lead to a
 * second sheet (headline menu → pick a word to mute). */
export const showActionSheet = (next: Sheet): void => {
  sheet = next
  emit()
}

export const dismissActionSheet = (): void => {
  if (sheet === null) return
  sheet = null
  emit()
}

export const subscribeActionSheet = (listener: () => void): (() => void) => {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

export const getActionSheetSnapshot = (): Sheet | null => sheet
