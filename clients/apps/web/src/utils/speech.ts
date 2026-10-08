/** Read a list of lines aloud, one after another, through the browser's
 * speech synthesis. One queue at a time: starting a new one stops the old,
 * and `stop` cancels whatever is left. */

let speaking = false
let epoch = 0
const listeners = new Set<() => void>()

const emit = () => {
  for (const listener of listeners) listener()
}

export const canSpeak = (): boolean =>
  typeof window !== 'undefined' && 'speechSynthesis' in window

export const subscribeSpeaking = (listener: () => void): (() => void) => {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

export const getSpeakingSnapshot = (): boolean => speaking
export const getSpeakingServerSnapshot = (): boolean => false

const setSpeaking = (next: boolean) => {
  if (speaking === next) return
  speaking = next
  emit()
}

export const stopSpeaking = (): void => {
  epoch += 1
  if (canSpeak()) window.speechSynthesis.cancel()
  setSpeaking(false)
}

export const speakLines = (lines: readonly string[], lang = 'en'): void => {
  if (!canSpeak()) return
  const queue = lines.map((line) => line.trim()).filter(Boolean)
  if (queue.length === 0) return
  const myEpoch = ++epoch
  window.speechSynthesis.cancel()
  setSpeaking(true)
  let index = 0
  const next = () => {
    if (myEpoch !== epoch) return
    if (index >= queue.length) {
      setSpeaking(false)
      return
    }
    const utterance = new SpeechSynthesisUtterance(queue[index])
    index += 1
    utterance.lang = lang
    utterance.onend = next
    utterance.onerror = next
    window.speechSynthesis.speak(utterance)
  }
  next()
}
