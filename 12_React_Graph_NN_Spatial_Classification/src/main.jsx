import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from '../graph_geodemographic_lab.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
