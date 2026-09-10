import * as Haptics from 'expo-haptics'
import { Alert, Platform, Share } from 'react-native'
import { getTranslations } from '@outception-com/i18n'
import { showActionSheet, type SheetOption } from '@/utils/actionSheet'
import { getLocaleSnapshot } from '@/utils/locale'
import { hideSource } from '@/utils/hiddenSources'
import {
  speakHeadlines,
  stopSpeaking,
  getSpeakingSnapshot,
} from '@/utils/listen'
import { addMutedWord } from '@/utils/mutedWords'
import { isHttpUrl, openExternalUrl, type NewsItem } from '@/utils/news'

/** Candidate words for mute-a-word: distinct words from the headline with
 * leading/trailing punctuation trimmed (inner punctuation stays, matching the
 * web - isMuted is a substring match on the raw title, so a "Trump's"
 * flattened to "Trumps" would never match anything), longer than three
 * characters, deduped
 * case-insensitively but offered in their printed casing, capped at eight so
 * the sheet stays scannable. */
const muteWordCandidates = (title: string): string[] => {
  const seen = new Set<string>()
  const out: string[] = []
  for (const raw of title.split(/\s+/)) {
    const word = raw.replace(/^[^\p{L}\p{N}]+|[^\p{L}\p{N}]+$/gu, '')
    if (word.length <= 3) continue
    const key = word.toLowerCase()
    if (seen.has(key)) continue
    seen.add(key)
    out.push(word)
    if (out.length >= 8) break
  }
  return out
}

/** Present a list of choices. iOS gets the native alert, which lists them all.
 *
 * Android CANNOT: react-native's Alert maps buttons onto an AndroidX dialog's
 * positive/negative/neutral slots and slices the list to the first three, so
 * this menu's later rows - mute-a-word, mute-the-source, even Cancel - were
 * dropped without a trace. There it renders the app's own sheet instead. */
const present = (
  title: string,
  options: SheetOption[],
  cancel: string,
): void => {
  if (Platform.OS === 'android') {
    showActionSheet({ title, options, cancel })
    return
  }
  Alert.alert(title, undefined, [
    ...options.map((option) => ({
      text: option.label,
      style: option.destructive ? ('destructive' as const) : undefined,
      onPress: option.onPress,
    })),
    { text: cancel, style: 'cancel' as const },
  ])
}

/** Long-press actions for a headline: the platform share sheet (which carries
 * its own Copy action on both OSes - no clipboard module needed OTA-side),
 * listen (text-to-speech), open, mute-a-word, and hide-the-source. When the
 * card's full item list is passed, Listen reads from the tapped headline
 * onward so the wall can be heard hands-free. */
export const showHeadlineActions = (
  item: NewsItem,
  source: { id: string; name: string },
  cardItems?: NewsItem[],
): void => {
  void Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium)
  const t = getTranslations(getLocaleSnapshot())
  const speaking = getSpeakingSnapshot()
  const from = cardItems?.findIndex((it) => it.id === item.id) ?? -1
  const toRead =
    from >= 0 ? cardItems!.slice(from).map((it) => it.title) : [item.title]
  present(
    item.title,
    [
      {
        label: speaking ? t.news.menu.stopListening : t.news.menu.listen,
        onPress: () =>
          speaking
            ? stopSpeaking()
            : speakHeadlines(toRead, getLocaleSnapshot()),
      },
      {
        label: t.news.menu.share,
        onPress: () => {
          if (!isHttpUrl(item.url)) return
          void Share.share(
            { message: `${item.title}\n${item.url}`, url: item.url },
            { dialogTitle: item.title },
          ).catch(() => {})
        },
      },
      {
        label: t.news.menu.open,
        onPress: () => openExternalUrl(item.url),
      },
      {
        label: t.news.menu.muteWord,
        onPress: () => {
          // Second sheet: pick which word from this headline to mute. Words are
          // muted lowercased (the store lowercases), but shown as printed.
          const words = muteWordCandidates(item.title)
          if (words.length === 0) return
          present(
            t.news.menu.muteWord,
            words.map((w) => ({ label: w, onPress: () => addMutedWord(w) })),
            t.news.menu.cancel,
          )
        },
      },
      {
        label: t.news.menu.muteSource.replace('{source}', source.name),
        destructive: true,
        onPress: () => hideSource(source.id),
      },
    ],
    t.news.menu.cancel,
  )
}
