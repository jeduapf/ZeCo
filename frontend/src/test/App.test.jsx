/**
 * App Component Tests
 * 
 * Tests the main App component including:
 * - License checking on mount
 * - Route rendering
 * - HTTP/HTTPS conditional routing
 * - License activation modal
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import App from '../App'

// Mock the API service
vi.mock('../services/api', () => ({
    default: {
        get: vi.fn(),
        post: vi.fn(),
    }
}))

import api from '../services/api'

describe('App Component', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        window.location.protocol = 'http:'
    })

    it('renders without crashing', () => {
        api.get.mockResolvedValueOnce({ data: { status: 'active' } })

        render(
            <MemoryRouter initialEntries={['/']}>
                <App />
            </MemoryRouter>
        )

        // App should render (NavBar should be present)
        expect(document.querySelector('.main-content')).toBeInTheDocument()
    })

    it('checks license status on mount', async () => {
        api.get.mockResolvedValueOnce({ data: { status: 'active' } })

        render(
            <MemoryRouter initialEntries={['/']}>
                <App />
            </MemoryRouter>
        )

        await waitFor(() => {
            expect(api.get).toHaveBeenCalledWith('/license/status')
        })
    })

    it('shows license activation modal when license is invalid', async () => {
        const error = new Error('License invalid')
        error.status = 402
        api.get.mockRejectedValueOnce(error)

        render(
            <MemoryRouter initialEntries={['/']}>
                <App />
            </MemoryRouter>
        )

        await waitFor(() => {
            expect(screen.getByText('Application Locked')).toBeInTheDocument()
        })
    })

    it('renders landing page on root route', () => {
        api.get.mockResolvedValueOnce({ data: { status: 'active' } })

        render(
            <MemoryRouter initialEntries={['/']}>
                <App />
            </MemoryRouter>
        )

        expect(screen.getByText('Welcome to ZeCo')).toBeInTheDocument()
    })

    it('allows access to login on HTTPS', () => {
        window.location.protocol = 'https:'
        api.get.mockResolvedValueOnce({ data: { status: 'active' } })

        render(
            <MemoryRouter initialEntries={['/login']}>
                <App />
            </MemoryRouter>
        )

        // Login page should render (not redirect to landing)
        // This test verifies HTTPS routes are accessible
        expect(screen.queryByText('Welcome to ZeCo')).not.toBeInTheDocument()
    })

    it('redirects login to landing page on HTTP', () => {
        window.location.protocol = 'http:'
        api.get.mockResolvedValueOnce({ data: { status: 'active' } })

        render(
            <MemoryRouter initialEntries={['/login']}>
                <App />
            </MemoryRouter>
        )

        // Should show landing page instead of login
        expect(screen.getByText('Welcome to ZeCo')).toBeInTheDocument()
    })
})
