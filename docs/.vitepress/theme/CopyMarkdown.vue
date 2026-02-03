<script setup>
import { ref } from 'vue'
import { useData } from 'vitepress'

const { page } = useData()
const copied = ref(false)

async function copyMarkdown() {
  try {
    // Construct the raw GitHub URL
    const basePath = 'https://raw.githubusercontent.com/GoogleCloudPlatform/agent-starter-pack/main/docs/'
    const filePath = page.value.relativePath
    const rawUrl = basePath + filePath

    // Fetch the raw markdown
    const response = await fetch(rawUrl)
    if (!response.ok) throw new Error('Failed to fetch')

    const markdown = await response.text()

    // Copy to clipboard
    await navigator.clipboard.writeText(markdown)

    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch (error) {
    console.error('Failed to copy markdown:', error)
    alert('Failed to copy markdown. Please try again.')
  }
}
</script>

<template>
  <button
    class="copy-markdown-btn"
    @click="copyMarkdown"
    :title="copied ? 'Copied!' : 'Copy page as Markdown'"
  >
    <span v-if="copied">✓</span>
    <span v-else>📋</span>
  </button>
</template>

<style scoped>
.copy-markdown-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 6px 8px;
  font-size: 14px;
  color: var(--vp-c-text-3);
  background: transparent;
  border: 1px solid var(--vp-c-divider);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
  min-width: 32px;
  min-height: 32px;
}

.copy-markdown-btn:hover {
  color: var(--vp-c-text-1);
  background: var(--vp-c-bg-soft);
}
</style>
