/**
 * JWT Token Management System for FastAPI
 * Place this file in your FastAPI static directory
 */

class TokenManager {
    constructor() {
        this.TOKEN_KEY = 'access_token';
        this.baseURL = ''; // Same origin as FastAPI
        this.isRefreshing = false;
        this.refreshQueue = [];
    }

    getToken() {
        return localStorage.getItem(this.TOKEN_KEY);
    }

    setToken(token) {
        localStorage.setItem(this.TOKEN_KEY, token);
    }

    removeToken() {
        localStorage.removeItem(this.TOKEN_KEY);
    }

    isAuthenticated() {
        const token = this.getToken();
        if (!token) return false;
        
        try {
            const payload = JSON.parse(atob(token.split('.')[1]));
            const currentTime = Date.now() / 1000;
            return payload.exp > currentTime;
        } catch (error) {
            console.error('Error decoding token:', error);
            return false;
        }
    }

    getTokenInfo() {
        const token = this.getToken();
        if (!token) return null;

        try {
            const payload = JSON.parse(atob(token.split('.')[1]));
            const currentTime = Date.now() / 1000;
            const remainingSeconds = payload.exp - currentTime;
            
            return {
                expiresAt: new Date(payload.exp * 1000),
                remainingSeconds: remainingSeconds,
                remainingMinutes: remainingSeconds / 60,
                isExpired: remainingSeconds <= 0,
                username: payload.sub
            };
        } catch (error) {
            console.error('Error parsing token:', error);
            return null;
        }
    }

    async fetchWithAuth(url, options = {}) {
        const token = this.getToken();
        
        if (!token) {
            throw new Error('No authentication token available');
        }

        const headers = {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
            ...options.headers
        };

        try {
            const response = await fetch(url, {
                ...options,
                headers
            });

            const newToken = response.headers.get('X-New-Token');
            if (newToken && newToken !== token) {
                console.log('🔄 Token refreshed automatically');
                this.setToken(newToken);
            }

            return response;
        } catch (error) {
            console.error('Fetch error:', error);
            throw error;
        }
    }

    async refreshToken() {
        if (this.isRefreshing) {
            return new Promise((resolve) => {
                this.refreshQueue.push(resolve);
            });
        }

        this.isRefreshing = true;

        try {
            const response = await this.fetchWithAuth('/api/v1/auth/me');
            
            if (response.ok) {
                const newToken = response.headers.get('X-New-Token');
                if (newToken) {
                    this.setToken(newToken);
                    console.log('✅ Token refreshed successfully');
                    
                    this.refreshQueue.forEach(resolve => resolve());
                    this.refreshQueue = [];
                    
                    return newToken;
                } else {
                    console.log('ℹ️ No new token received (refresh not needed)');
                    return this.getToken();
                }
            } else {
                throw new Error(`Token refresh failed: ${response.status}`);
            }
        } catch (error) {
            console.error('❌ Token refresh failed:', error);
            this.removeToken();
            throw error;
        } finally {
            this.isRefreshing = false;
        }
    }
}

// Create singleton instance
const tokenManager = new TokenManager();

// Utility functions
async function getCurrentUser() {
    try {
        const response = await tokenManager.fetchWithAuth('/api/v1/auth/me');
        
        if (!response.ok) {
            if (response.status === 401) {
                console.log('🔑 Token invalid, refreshing...');
                await tokenManager.refreshToken();
                return getCurrentUser();
            }
            throw new Error(`Request failed: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('Failed to get current user:', error);
        throw error;
    }
}

async function updateUserProfile(userData) {
    try {
        const response = await tokenManager.fetchWithAuth('/api/v1/auth/me', {
            method: 'PUT',
            body: JSON.stringify(userData)
        });
        
        if (!response.ok) {
            if (response.status === 401) {
                console.log('🔑 Token invalid, refreshing...');
                await tokenManager.refreshToken();
                return updateUserProfile(userData);
            }
            throw new Error(`Request failed: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('Failed to update profile:', error);
        throw error;
    }
}