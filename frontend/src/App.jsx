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
import LandingPage from './pages/LandingPage'
import ProtectedRoute from './routes/ProtectedRoute'
import translations from './locales/en.json'
import './css/App.css'

function App() {
  // License validity state - controls whether the LicenseActivation modal is shown
  const [isLicenseValid, setIsLicenseValid] = React.useState(true);

  React.useEffect(() => {
    /**
     * Check License Status on Initial Load
     * 
     * This runs once when the app mounts to verify the backend license.
     * If the license is invalid/expired, the LicenseActivation modal is shown.
     */
    const checkLicense = async () => {
      try {
        // Call backend /api/v1/license/status endpoint
        // api.get() automatically adds the /api/v1 prefix
        await import('./services/api').then(module => module.default.get('/license/status'));
        setIsLicenseValid(true);
      } catch (error) {
        // Backend returns 402 Payment Required for invalid/expired licenses
        if (error.status === 402) {
          setIsLicenseValid(false);
        }
      }
    };

    checkLicense();

    /**
     * Listen for License Expiration Events
     * 
     * The 'license-expired' event is dispatched by api.js when the backend
     * returns a 402 response during normal API calls.
     */
    const handleExpiration = () => setIsLicenseValid(false);
    window.addEventListener('license-expired', handleExpiration);

    // Cleanup: remove event listener when component unmounts
    return () => window.removeEventListener('license-expired', handleExpiration);
  }, []);

  /**
   * Handle Successful License Activation
   * 
   * Called when the user successfully activates a license via the modal.
   * Reloads the page to ensure clean state (license middleware will now pass).
   */
  const handleActivationSuccess = () => {
    setIsLicenseValid(true);
    // Reload to ensure clean state and re-run middleware checks
    window.location.reload();
  };

  // Determine if we're on HTTP or HTTPS
  // This controls which routes are available
  const isHttps = window.location.protocol === 'https:';

  return (
    <>
      {!isLicenseValid && <LicenseActivation onSuccess={handleActivationSuccess} />}
      <NavBar translations={translations} />
      <main className="main-content">
        <Routes>
          {/* Public Routes (available on both HTTP and HTTPS) */}
          <Route path='/' element={<LandingPage />} />
          <Route path='/about' element={<About translations={translations} />} />
          <Route path="/menu" element={<Menu translations={translations} />} />
          <Route path="/checkout" element={<Checkout translations={translations} />} />

          {/* 
            HTTPS-Only Routes (Conditional Rendering)
            
            These routes are only rendered when accessed via HTTPS:
            - /login: Staff login page
            - /admin: Admin dashboard (requires authentication via ProtectedRoute)
            
            WHY: Staff features require secure connections (HTTPS) because they
            involve sensitive operations like authentication and order management.
            
            If users try to access these routes via HTTP, they're redirected
            to the LandingPage where they can choose to install the certificate
            and switch to HTTPS.
          */}
          {isHttps ? (
            <>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/admin" element={
                <ProtectedRoute requireAdmin={true}>
                  <AdminPage />
                </ProtectedRoute>
              } />
            </>
          ) : (
            <>
              {/* Redirect restricted pages to Landing Page on HTTP */}
              <Route path="/login" element={<LandingPage />} />
              <Route path="/admin" element={<LandingPage />} />
            </>
          )}
        </Routes>
      </main>
    </>
  )
}

export default App