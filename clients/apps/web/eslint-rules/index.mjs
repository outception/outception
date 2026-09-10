import noClassnameBox from './no-classname-box.mjs'
import noClassnameText from './no-classname-text.mjs'
import noNextImage from './no-next-image.mjs'
import noRawHtmlLayout from './no-raw-html-layout.mjs'
import noStyleBox from './no-style-box.mjs'
import noStyleText from './no-style-text.mjs'
import noToastErrorDetail from './no-toast-error-detail.mjs'

/** @type {import('eslint').ESLint.Plugin} */
const outceptionPlugin = {
  meta: {
    name: 'outception',
  },
  rules: {
    'no-classname-box': noClassnameBox,
    'no-classname-text': noClassnameText,
    'no-next-image': noNextImage,
    'no-raw-html-layout': noRawHtmlLayout,
    'no-style-box': noStyleBox,
    'no-style-text': noStyleText,
    'no-toast-error-detail': noToastErrorDetail,
  },
}

export default outceptionPlugin
