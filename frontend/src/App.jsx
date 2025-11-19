/**
 * Root Application Component
 * 
 * This component:
 * 1. Defines all application routes
 * 2. Wraps protected routes with ProtectedRoute
 * 3. Provides main layout structure
 * 4. Handles 404 pages
 */

import React from 'react'
import { Routes, Route } from 'react-router-dom'
import NavBar from './components/NavBar'
import LicenseActivation from './components/LicenseActivation'
import Menu from './pages/MenuPage'
import Checkout from './pages/CheckoutPage'
import LoginPage from './pages/LoginPage'
import AdminPage from './pages/AdminPage'
import About from './pages/AboutPage'
import ProtectedRoute from './routes/ProtectedRoute'
import translations from './locales/en.json'
import './css/App.css'

function App() {
  const [isLicenseValid, setIsLicenseValid] = React.useState(true);

  React.useEffect(() => {
    // Check status on mount
    const checkLicense = async () => {
      try {
        // We use a direct fetch or api call. 
        // Note: api.get uses /api/v1 base, so we just need /license/status
        await import('./services/api').then(module => module.default.get('/license/status'));
        setIsLicenseValid(true);
      } catch (error) {
        // The event listener will handle 402, but we can also set it here if we want to be sure
        if (error.status === 402) {
          setIsLicenseValid(false);
        }
      }
    };

    checkLicense();

    const handleExpiration = () => setIsLicenseValid(false);
    window.addEventListener('license-expired', handleExpiration);

    return () => window.removeEventListener('license-expired', handleExpiration);
  }, []);

  const handleActivationSuccess = () => {
    setIsLicenseValid(true);
    // Optional: reload to ensure clean state
    window.location.reload();
  };

  return (
    <>
      {!isLicenseValid && <LicenseActivation onSuccess={handleActivationSuccess} />}
      <NavBar translations={translations} />
      <main className="main-content">
        <Routes>
          <Route path='/' element={<About translations={translations} />} />
          <Route path="/menu" element={<Menu translations={translations} />} />
          <Route path="/checkout" element={<Checkout translations={translations} />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/admin" element={
            <ProtectedRoute requireAdmin={true}>
              <AdminPage />
            </ProtectedRoute>
          } />
        </Routes>
      </main>
    </>
  )
}

export default App