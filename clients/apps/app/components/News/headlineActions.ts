import * as Haptics from 'expo-haptics'
import { Alert, Share } from 'react-native'
import { getTranslations } from '@outception-com/i18n'
import { getLocaleSnapshot } from '@/utils/locale'
import { hideSource } from '@/utils/hiddenSources'
import {
  speakHeadlines,
  stopSpeaking,
  getSpeakingSnapshot,
} from '@/utils/listen'
import { openExternalUrl, type NewsItem } from '@/utils/news'

/** Long-press actions for a headline: the platform share sheet (which carries
 * its own Copy action on both OSes — no clipboard module needed OTA-side),
 * listen (text-to-speech), open, and hide-the-source. Native Alert keeps the
 * sheet dependency-free. When the card's full item list is passed, Listen reads
 * from the tapped headline onward so the wall can be heard hands-free. */
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
  Alert.alert(item.title, undefined, [
    {
      text: speaking ? t.news.menu.stopListening : t.news.menu.listen,
      onPress: () =>
        speaking ? stopSpeaking() : speakHeadlines(toRead, getLocaleSnapshot()),
    },
    {
      text: t.news.menu.share,
      onPress: () => {
        void Share.share(
          { message: `${item.title}\n${item.url}`, url: item.url },
          { dialogTitle: item.title },
        ).catch(() => {})
      },
    },
    {
      text: t.news.menu.open,
      onPress: () => openExternalUrl(item.url),
    },
    {
      text: t.news.menu.muteSource.replace('{source}', source.name),
      style: 'destructive',
      onPress: () => hideSource(source.id),
    },
    { text: t.news.menu.cancel, style: 'cancel' },
  ])
}
