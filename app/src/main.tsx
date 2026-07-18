import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

function watchLocalPreviewBuild() {
  if (!import.meta.env.PROD || !['127.0.0.1', 'localhost'].includes(window.location.hostname)) {
    return
  }

  const currentBundle = document.querySelector<HTMLScriptElement>(
    'script[type="module"][src*="/assets/index-"]',
  )?.src
  if (!currentBundle) return

  let checking = false
  const checkForRebuild = async () => {
    if (checking || document.visibilityState === 'hidden') return
    checking = true
    try {
      const response = await fetch(`/?preview-build-check=${Date.now()}`, { cache: 'no-store' })
      if (!response.ok) return
      const nextDocument = new DOMParser().parseFromString(await response.text(), 'text/html')
      const nextSource = nextDocument
        .querySelector<HTMLScriptElement>('script[type="module"][src*="/assets/index-"]')
        ?.getAttribute('src')
      if (nextSource && new URL(nextSource, window.location.origin).href !== currentBundle) {
        window.location.reload()
      }
    } catch {
      // The preview may be between rebuilds; the next poll will try again.
    } finally {
      checking = false
    }
  }

  window.setInterval(() => void checkForRebuild(), 3000)
  document.addEventListener('visibilitychange', () => void checkForRebuild())
}

watchLocalPreviewBuild()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
