/**
 * License Activation Modal Component
 * 
 * This is a full-screen overlay modal that appears when the application
 * license is invalid or expired (402 Payment Required response from backend).
 * 
 * The modal blocks access to the entire application until a valid license
 * key is entered and activated.
 * 
 * Props:
 * - onSuccess: Callback function called when license activation succeeds
 */
import React, { useState } from 'react';
import api from '../services/api';
import '../css/App.css'; // Reusing main CSS for now, or inline styles

const LicenseActivation = ({ onSuccess }) => {
  // License key input state (JWT string)
  const [key, setKey] = useState('');

  // Loading state during API call
  const [loading, setLoading] = useState(false);

  // Error message state
  const [error, setError] = useState(null);

  /**
   * Handle License Activation Form Submission
   * 
   * This sends the license key to POST /api/v1/license endpoint.
   * The backend validates the JWT signature and expiration before accepting it.
   * 
   * @param {Event} e - Form submit event
   */
  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      // Send license key to backend
      // Backend will verify JWT signature and expiration
      await api.post('/license', { key });

      // Call parent's success handler (usually reloads the page)
      onSuccess();
    } catch (err) {
      // Display error message (invalid key, expired, etc.)
      setError(err.message || 'Failed to activate license');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="license-overlay" style={{
      position: 'fixed',
      top: 0,
      left: 0,
      width: '100%',
      height: '100%',
      backgroundColor: 'rgba(0, 0, 0, 0.9)',
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      zIndex: 9999,  // Ensure it appears above all other elements
      color: 'white',
      flexDirection: 'column'
    }}>
      <div className="license-card" style={{
        backgroundColor: '#1a1a1a',
        padding: '2rem',
        borderRadius: '8px',
        maxWidth: '500px',
        width: '90%',
        textAlign: 'center',
        border: '1px solid #333'
      }}>
        <h2 style={{ marginBottom: '1rem', color: '#ff4444' }}>Application Locked</h2>
        <p style={{ marginBottom: '2rem', color: '#ccc' }}>
          Your license has expired or is invalid. Please enter a valid license key to continue.
        </p>

        <form onSubmit={handleSubmit}>
          {/* License Key Input (multiline for long JWT strings) */}
          <textarea
            value={key}
            onChange={(e) => setKey(e.target.value)}
            placeholder="Paste your license key here..."
            style={{
              width: '100%',
              height: '100px',
              marginBottom: '1rem',
              padding: '0.5rem',
              backgroundColor: '#333',
              border: '1px solid #555',
              color: 'white',
              borderRadius: '4px',
              resize: 'vertical'
            }}
            required
          />

          {/* Error Message Display */}
          {error && (
            <div style={{ color: '#ff4444', marginBottom: '1rem', fontSize: '0.9rem' }}>
              {error}
            </div>
          )}

          {/* Activation Button */}
          <button
            type="submit"
            disabled={loading}
            style={{
              padding: '0.75rem 1.5rem',
              backgroundColor: loading ? '#555' : '#4CAF50',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: loading ? 'not-allowed' : 'pointer',
              fontSize: '1rem',
              width: '100%'
            }}
          >
            {loading ? 'Activating...' : 'Activate License'}
          </button>
        </form>

        {/* Help Text */}
        <div style={{ marginTop: '2rem', fontSize: '0.8rem', color: '#888' }}>
          <p>Need a license? Contact the administrator.</p>
        </div>
      </div>
    </div>
  );
};

export default LicenseActivation;
