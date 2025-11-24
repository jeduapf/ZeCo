/**
 * Landing Page Component
 * 
 * This is the entry point of the application where users choose their access level:
 * - Guest Access (HTTP): For temporary guests who want to view the menu
 * - Staff Access (HTTPS): For authenticated staff members (requires certificate)
 * 
 * The HTTP/HTTPS split provides security for staff features while keeping
 * guest access simple and fast.
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

export default function LandingPage() {
    const navigate = useNavigate();

    // State to show loading indicator while checking HTTPS connection
    const [checkingHttps, setCheckingHttps] = useState(false);

    // State to control certificate installation instructions modal
    const [showCertInstructions, setShowCertInstructions] = useState(false);

    /**
     * Handle Guest button click
     * 
     * Guests use HTTP and don't need any authentication.
     * They are redirected to the menu page to browse items.
     */
    const handleGuest = () => {
        navigate('/menu');
    };

    /**
     * Handle Staff button click
     * 
     * This function checks if the user can access the HTTPS version:
     * 1. If already on HTTPS, go directly to login
     * 2. If on HTTP, try to access HTTPS endpoint to check if certificate is trusted
     * 3. If certificate check fails, show installation instructions
     * 
     * Why this works:
     * - Self-signed certificates cause browsers to block fetch() requests
     * - If fetch succeeds, certificate is trusted → redirect to HTTPS login
     * - If fetch fails, certificate not trusted → show instructions
     */
    const handleStaff = async () => {
        // If already on HTTPS, just go to login
        if (window.location.protocol === 'https:') {
            navigate('/login');
            return;
        }

        setCheckingHttps(true);
        const hostname = window.location.hostname;

        // Try to fetch from HTTPS health endpoint to check if certificate is trusted
        const httpsUrl = `https://${hostname}/api/v1/health`;

        try {
            // 'no-cors' mode prevents CORS issues but still detects certificate errors
            await fetch(httpsUrl, { mode: 'no-cors' });

            // If we reach here, the certificate is trusted by the browser
            // Redirect to HTTPS login page
            window.location.href = `https://${hostname}/login`;
        } catch (e) {
            // Fetch failed, likely because certificate is not trusted
            // Show installation instructions to the user
            setShowCertInstructions(true);
        } finally {
            setCheckingHttps(false);
        }
    };

    /**
     * Download the certificate file
     * 
     * The certificate (zeco.crt) is served from /public/zeco.crt
     * Users need to download and install this to trust the HTTPS connection
     */
    const downloadCert = () => {
        window.location.href = '/zeco.crt';
    };

    /**
     * Retry staff access after certificate installation
     * 
     * After users install the certificate, they click this button
     * to redirect to the HTTPS login page.
     */
    const retryStaff = () => {
        const hostname = window.location.hostname;
        window.location.href = `https://${hostname}/login`;
    };

    return (
        <div className="landing-page" style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            height: '80vh',
            gap: '2rem',
            textAlign: 'center'
        }}>
            <h1>Welcome to ZeCo</h1>

            {/* Main choice: Guest or Staff */}
            {!showCertInstructions ? (
                <div style={{ display: 'flex', gap: '2rem' }}>
                    <button
                        onClick={handleGuest}
                        style={{ padding: '1rem 2rem', fontSize: '1.2rem', cursor: 'pointer' }}
                    >
                        I am a Guest
                    </button>

                    <button
                        onClick={handleStaff}
                        disabled={checkingHttps}
                        style={{ padding: '1rem 2rem', fontSize: '1.2rem', cursor: 'pointer' }}
                    >
                        {checkingHttps ? 'Checking Connection...' : 'I am Staff / Connected User'}
                    </button>
                </div>
            ) : (
                /* Certificate installation instructions */
                <div style={{ maxWidth: '600px', padding: '2rem', border: '1px solid #ccc', borderRadius: '8px' }}>
                    <h2>Security Certificate Required</h2>
                    <p>To access the Staff area securely, you need to install our security certificate.</p>

                    {/* Step 1: Download Certificate */}
                    <div style={{ margin: '2rem 0' }}>
                        <button
                            onClick={downloadCert}
                            style={{ padding: '0.8rem 1.5rem', fontSize: '1rem', marginRight: '1rem', backgroundColor: '#4CAF50', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
                        >
                            1. Download Certificate
                        </button>
                    </div>

                    {/* Installation instructions */}
                    <p style={{ fontSize: '0.9rem', color: '#666' }}>
                        After downloading, please install the certificate on your device.
                    </p>
                    <p style={{ fontSize: '0.9rem', color: '#666' }}>
                        (Settings &gt; Install Certificate &gt; Trusted Root Certification Authorities)
                    </p>

                    {/* Step 2: Retry connection */}
                    <div style={{ marginTop: '2rem' }}>
                        <button
                            onClick={retryStaff}
                            style={{ padding: '0.8rem 1.5rem', fontSize: '1rem', cursor: 'pointer' }}
                        >
                            2. I have installed it - Connect
                        </button>
                    </div>

                    {/* Back button to return to main menu */}
                    <button
                        onClick={() => setShowCertInstructions(false)}
                        style={{ marginTop: '1rem', background: 'none', border: 'none', textDecoration: 'underline', cursor: 'pointer' }}
                    >
                        Back
                    </button>
                </div>
            )}
        </div>
    );
}
