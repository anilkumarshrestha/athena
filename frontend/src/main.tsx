import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

// No StrictMode: its double-invoked effects would generate (and pay for) every story twice.
createRoot(document.getElementById('root')!).render(<App />)
