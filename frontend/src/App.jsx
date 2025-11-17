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
import Menu from './pages/MenuPage'
import Checkout from './pages/CheckoutPage'
import LoginPage from './pages/LoginPage'
import AdminPage from './pages/AdminPage'
import About from './pages/AboutPage'
import ProtectedRoute from './routes/ProtectedRoute'
import translations from './locales/en.json'
import './css/App.css'

function App() {
  return (
    <>
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