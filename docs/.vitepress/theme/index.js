import DefaultTheme from 'vitepress/theme'
import CopyMarkdown from './CopyMarkdown.vue'
import './custom.css'
import { h } from 'vue'

export default {
  extends: DefaultTheme,
  Layout() {
    return h(DefaultTheme.Layout, null, {
      'doc-before': () => h('div', { class: 'copy-markdown-container' }, [
        h(CopyMarkdown)
      ])
    })
  }
}
