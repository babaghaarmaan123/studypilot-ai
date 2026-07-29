import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'

import App from './App'
import { AuthProvider } from '@/context/AuthContext'
import { ThemeProvider } from '@/context/ThemeContext'
import { ToastProvider } from '@/context/ToastContext'
import { TooltipProvider } from '@/components/ui/tooltip'
import '@/components/charts/setup'

/*
 * react-calendar's stylesheet is imported here, and deliberately before
 * index.css, rather than from the Calendar page that uses it.
 *
 * The Calendar page is a lazy route, so its CSS is emitted as a separate chunk
 * that the browser injects at runtime after the main stylesheet. That put the
 * library's `background: white`, red weekends and blue selection permanently
 * ahead of the theme, whatever index.css said. Importing it into the entry
 * bundle puts both files in one stylesheet, in this order, so the theme
 * overrides that follow win on source order the way they are written to.
 */
import 'react-calendar/dist/Calendar.css'
import './index.css'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ThemeProvider>
      <ToastProvider>
        <TooltipProvider delayDuration={200}>
          <BrowserRouter>
            <AuthProvider>
              <App />
            </AuthProvider>
          </BrowserRouter>
        </TooltipProvider>
      </ToastProvider>
    </ThemeProvider>
  </StrictMode>,
)
