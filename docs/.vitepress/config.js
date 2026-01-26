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
    ['link', { href: 'https://fonts.googleapis.com/css2?family=Google+Sans:wght@300;400;500;700&family=Google+Sans+Mono:wght@400;500&family=Roboto:wght@300;400;500;700&display=swap', rel: 'stylesheet' }],
    ['style', {}, `
      :root {
        --vp-font-family-base: 'Google Sans', 'Roboto', sans-serif;
        --vp-font-family-mono: 'Google Sans Mono', 'Roboto Mono', monospace;
        --vp-font-size-base: 14px;
        --vp-line-height-base: 1.4;
        --vp-sidebar-font-size: 13px;
        --vp-c-bg: #fafafa;
        --vp-c-bg-alt: #ffffff;
        --vp-nav-height: 56px;
      }
      .dark {
        --vp-c-bg: #1a1a1a;
        --vp-c-bg-alt: #202124;
      }
      .vp-doc { font-weight: 400; }
      .vp-doc h1 { font-size: 1.75rem; font-weight: 400; margin: -1rem 0 0.75rem; color: #202124; }
      .vp-doc h2 { font-size: 1.35rem; font-weight: 500; margin: 1.25rem 0 0.5rem; color: #202124; }
      .vp-doc h3 { font-size: 1.15rem; font-weight: 500; margin: 1rem 0 0.25rem; color: #202124; }
      .vp-doc p { font-size: 14px; line-height: 1.4; margin: 0.5rem 0; color: #3c4043; }
      .vp-doc li { font-size: 14px; line-height: 1.4; color: #3c4043; margin: 0.25rem 0; }
      .vp-sidebar { background: #ffffff; border-right: 1px solid #e8eaed; }
      .vp-sidebar-link { font-size: 13px; padding: 4px 16px; color: #5f6368; border-radius: 0; }
      .vp-sidebar-link:hover { background: #f1f3f4; color: #202124; }
      .vp-sidebar-link.active { background: #e8f0fe; color: #1a73e8; font-weight: 500; }
      .content { max-width: 1200px; padding: 0 24px; }
      .VPNavBar { background: #ffffff; border-bottom: 1px solid #e8eaed; padding: 0 24px; }
      .VPNavBar .content { display: flex; justify-content: space-between; align-items: center; }
      .VPNavBarTitle { font-weight: 500; color: #202124; }
      .VPNavBar .content-body { margin-left: auto; display: flex; align-items: center; gap: 1rem; }
      .VPNavBarMenuLink { color: #5f6368; font-weight: 400; padding: 0 8px; }
      .VPNavBarMenuLink:hover { color: #202124; }
      
      /* Dark mode styles */
      .dark .vp-doc h1, .dark .vp-doc h2, .dark .vp-doc h3 { color: #e8eaed; }
      .dark .vp-doc p, .dark .vp-doc li { color: #bdc1c6; }
      .dark .vp-sidebar { background: #202124; border-right: 1px solid #3c4043; }
      .dark .vp-sidebar-link { color: #9aa0a6; }
      .dark .vp-sidebar-link:hover { background: #3c4043; color: #e8eaed; }
      .dark .vp-sidebar-link.active { background: #1e3a8a; color: #8ab4f8; }
      .dark .VPNavBar { background: #202124; border-bottom: 1px solid #3c4043; }
      .dark .VPNavBarTitle { color: #e8eaed; }
      .dark .VPNavBarMenuLink { color: #9aa0a6; }
      .dark .VPNavBarMenuLink:hover { color: #e8eaed; }
    `]
  ],

  themeConfig: {
    nav: [
      { text: 'Home', link: '/' },
      { text: 'Guide', link: '/guide/getting-started' },
      { text: 'Remote Templates', link: '/remote-templates/' },
      { text: 'Agents', link: '/agents/overview' },
      { text: 'CLI', link: '/cli' },
      { text: 'Community', link: '/guide/community-showcase' }
    ],
    sidebar: [
      {
        text: 'Getting Started',
        items: [
          { text: 'Quick Start', link: '/guide/getting-started' },
          { text: 'Why Starter Pack?', link: '/guide/why_starter_pack' },
          { text: 'Installation', link: '/guide/installation' },
          { text: 'Video Tutorials', link: '/guide/video-tutorials' }
        ]
      },
      {
        text: 'Development',
        collapsed: true,
        items: [
          { text: 'Development Guide', link: '/guide/development-guide' },
          { text: 'Data Ingestion', link: '/guide/data-ingestion' },
          { text: 'Deploy UI', link: '/guide/deploy-ui' },
          { text: 'Troubleshooting', link: '/guide/troubleshooting' }
        ]
      },
      {
        text: 'Deployment & Operations',
        collapsed: true,
        items: [
          { text: 'Deployment', link: '/guide/deployment' },
          { text: 'Observability', link: '/guide/observability' }
        ]
      },
      {
        text: 'Templates',
        collapsed: true,
        items: [
          { text: 'Agent Templates', link: '/agents/overview' },
          { text: 'Remote Templates', link: '/remote-templates/' },
          { text: 'Using Remote Templates', link: '/remote-templates/using-remote-templates' },
          { text: 'Creating Remote Templates', link: '/remote-templates/creating-remote-templates' },
          { text: 'Template Config Reference', link: '/guide/template-config-reference' }
        ]
      },
      {
        text: 'CLI Commands',
        collapsed: true,
        items: [
          { text: 'create', link: '/cli/create' },
          { text: 'enhance', link: '/cli/enhance' },
          { text: 'extract', link: '/cli/extract' },
          { text: 'upgrade', link: '/cli/upgrade' },
          { text: 'list', link: '/cli/list' },
          { text: 'register-gemini-enterprise', link: '/cli/register_gemini_enterprise' },
          { text: 'setup-cicd', link: '/cli/setup_cicd' }
        ]
      },
      {
        text: 'Community Showcase',
        link: '/guide/community-showcase'
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
