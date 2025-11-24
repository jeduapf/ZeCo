/**
 * Vitest Setup File
 * 
 * This file runs before all tests to set up the testing environment.
 */
import { expect, afterEach, vi } from 'vitest'
import { cleanup } from '@testing-library/react'
import '@testing-library/jest-dom/vitest'

// Cleanup after each test
afterEach(() => {
    cleanup()
})

// Mock window.matchMedia (used by some components)
Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation(query => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
    })),
})

// Mock window.location for HTTP/HTTPS testing
delete window.location
window.location = {
    protocol: 'http:',
    hostname: 'localhost',
    href: 'http://localhost:5173',
    origin: 'http://localhost:5173',
    pathname: '/',
    search: '',
    hash: '',
    reload: vi.fn(),
    replace: vi.fn(),
    assign: vi.fn(),
}

// Mock console methods to reduce noise in tests
global.console = {
    ...console,
    error: vi.fn(),
    warn: vi.fn(),
}
