import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'Agent Starter Pack',
  description: 'Build Production AI Agents faster using Agent Starter Pack',
  base: '/agent-starter-pack/',
  head: [
    ['meta', {property: 'og:image', content: '/images/agent_starter_pack_screenshot.png'}],
    ['meta', {property: 'og:twitter:image', content: '/images/agent_starter_pack_screenshot.png'}],
    ['link', { rel: 'preconnect', href: 'https://fonts.googleapis.com' }],
    ['link', { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: '' }],
    ['link', { href: 'https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap', rel: 'stylesheet' }],
    ['style', {}, `
      :root {
        --vp-font-family-base: 'Roboto', sans-serif;
        --vp-font-family-mono: 'Roboto Mono', monospace;
        --vp-c-text-1: 0.9rem;
        --vp-font-size-base: 0.9rem;
      }
    `]
  ],

  themeConfig: {
    nav: [
      { text: 'Home', link: '/' },
      { text: 'Guide', link: '/guide/getting-started' },
      { text: 'Agents', link: '/agents/overview' },
      { text: 'CLI', link: '/cli/index.md' }
    ],
    sidebar: [
      {
        text: 'Guide',
        items: [
          { text: 'Getting Started', link: '/guide/getting-started' },
          { text: 'Development Guide', link: '/guide/development-guide' },
          { text: 'Why Starter Pack?', link: '/guide/why_starter_pack' },
          { text: 'Video Tutorials', link: '/guide/video-tutorials' },
          { text: 'Installation', link: '/guide/installation' },
          { text: 'Deployment', link: '/guide/deployment' },
          { text: 'Data Ingestion', link: '/guide/data-ingestion' },
          { text: 'Observability', link: '/guide/observability' },
          { text: 'Troubleshooting', link: '/guide/troubleshooting' }
        ]
      },
      {
        text: 'Agents',
        items: [
          { text: 'Overview', link: '/agents/overview' },

        ]
      },
      {
        text: 'CLI Reference',
        items: [
          { text: 'create', link: '/cli/create' },
          { text: 'setup-cicd', link: '/cli/setup_cicd' }
        ]
      }
    ],
    socialLinks: [
      { 
        icon: 'github',
        link: 'https://github.com/GoogleCloudPlatform/agent-starter-pack' 
      },
    ],
    search: {
      provider: 'local'
    },

    footer: {
      message: 'Released under the Apache 2.0 License.'
    }
  }
})
