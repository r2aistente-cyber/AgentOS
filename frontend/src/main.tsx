import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import StandaloneChat from './StandaloneChat.tsx'

// Ruteo mínimo sin librería: /chat -> ventana de chat standalone (window.open),
// cualquier otra ruta -> Hub completo.
const isChatWindow = window.location.pathname.replace(/\/+$/, '') === '/chat'

createRoot(document.getElementById('root')!).render(
  <StrictMode>{isChatWindow ? <StandaloneChat /> : <App />}</StrictMode>,
)
