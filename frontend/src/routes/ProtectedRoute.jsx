/**
 * Protected Route Component
 * 
 * This is a wrapper for routes that require authentication and/or specific roles.
 * It acts as a bouncer at a club - checking credentials before letting you in.
 * 
 * How it works:
 * 1. Check if user is authenticated
 * 2. If not, redirect to login (saving intended destination)
 * 3. If yes, check if user has required role
 * 4. If yes, render the component
 * 5. If no, show access denied page
 * 
 * Example usage:
 * <Route path="/admin" element={
 *   <ProtectedRoute requiredRole={USER_ROLES.ADMIN}>
 *     <AdminDashboard />
 *   </ProtectedRoute>
 * } />
 */

import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { USER_ROLES, isAdmin, isStaff } from '../constants';

const ProtectedRoute = ({
  children,
  requiredRole = null,
  requiredRoles = [],
  requireStaff = false,
  requireAdmin = false,
  fallbackPath = '/login'
}) => {
  const { token, isLoading, user } = useAuth();
  const location = useLocation();

  /**
   * Show loading state while checking authentication
   * Prevents flash of redirect before auth check completes
   */
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  /**
   * Not authenticated - redirect to login
   * 
   * We save the current location in state so after login,
   * we can redirect the user back to where they were trying to go.
   * 
   * Example flow:
   * 1. User tries to visit /admin (not logged in)
   * 2. Redirect to /login with state: { from: '/admin' }
   * 3. User logs in successfully
   * 4. Redirect to /admin (from saved state)
   */
  if (!token) {
    return <Navigate to={fallbackPath} state={{ from: location }} replace />;
  }

  /**
   * Check role requirements
   * Uses constants from constants.js (synced with backend Pydantic enums)
   */

  // Check single required role (case-insensitive, using helper function)
  if (requireAdmin && !isAdmin(user?.role)) {
    return <Navigate to="/" replace />
  }

  if (requiredRole && user?.role?.toLowerCase() !== requiredRole.toLowerCase()) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <h1 className="text-4xl font-bold text-gray-800 mb-4">
            {'Access denied'}
          </h1>
          <p className="text-gray-600 mb-4">You do not have permission to view this page.</p>
          <button
            onClick={() => window.history.back()}
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            Back
          </button>
        </div>
      </div>
    );
  }

  // Check multiple possible roles
  if (requiredRoles.length > 0 && !requiredRoles.map(r => r.toLowerCase()).includes(user?.role?.toLowerCase())) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <h1 className="text-4xl font-bold text-gray-800 mb-4">
            {'Access denied'}
          </h1>
          <p className="text-gray-600">
            {'Staff only'}
          </p>
        </div>
      </div>
    );
  }

  // Check staff requirement (case-insensitive, using helper function)
  if (requireStaff && !isStaff(user?.role)) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <h1 className="text-4xl font-bold text-gray-800 mb-4">
            {'Access denied'}
          </h1>
          <p className="text-gray-600">
            {'Staff only'}
          </p>
        </div>
      </div>
    );
  }

  /**
   * All checks passed - render the protected component
   */
  return children;
};

export default ProtectedRoute;