import * as Speech from 'expo-speech'

/** Read headlines aloud, one after another, so the wall can be listened to
 * hands-free — a native capability a web page can't offer. A tiny external
 * store exposes whether speech is active so UI can show a stop affordance. */

let speaking = false
// Every start/stop bumps the epoch; a speak chain captures its epoch and bails
// the moment it's superseded. Needed because Android fires `onDone` (not
// `onStopped`) when Speech.stop() interrupts an utterance, so without this a
// stale chain would resume and interleave with a newly-started one.
let epoch = 0

/** Whether speech is active, read when the action sheet opens to toggle the
 * Listen/Stop label. */
export const getSpeakingSnapshot = () => speaking

export const stopSpeaking = () => {
  if (!speaking) return
  epoch += 1
  speaking = false
  void Speech.stop()
}

/** Speak each title in turn. Stops cleanly if `stopSpeaking` is called or a new
 * queue starts. `language` should be the reader's locale (BCP-47), matching the
 * server-translated headline text. */
export const speakHeadlines = (titles: string[], language?: string) => {
  const queue = titles.map((t) => t.trim()).filter(Boolean)
  if (queue.length === 0) return
  const myEpoch = ++epoch
  void Speech.stop()
  speaking = true

  let index = 0
  const next = () => {
    if (myEpoch !== epoch) return // superseded by a newer start/stop
    if (index >= queue.length) {
      speaking = false
      return
    }
    const line = queue[index]
    index += 1
    Speech.speak(line, {
      language,
      onDone: next,
      onStopped: () => {},
      onError: next,
    })
  }
  next()
}
