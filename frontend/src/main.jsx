import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import './css/theme.css'
import './css/index.css'
import App from './App.jsx'

// Context Providers
import { BrowserRouter } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext';
// import { CartProvider } from './context/CartContext';

createRoot(document.getElementById('root')).render(
  /**
   * Root component with all context providers
   * 
   * This structure ensures every component in the app can access:
   * - Routing functionality (useNavigate, useLocation, etc.)
   * - Authentication state (user, login, logout, etc.)
   * - Shopping cart state (cart, addItem, removeItem, etc.)
   */

  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
)
