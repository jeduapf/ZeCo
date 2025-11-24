/**
 * LandingPage Component Tests
 * 
 * Tests the main landing page functionality including:
 * - Component rendering
 * - Guest button navigation
 * - Staff button HTTPS check
 * - Certificate instructions modal
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import LandingPage from '../pages/LandingPage'

// Mock useNavigate
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
    const actual = await vi.importActual('react-router-dom')
    return {
        ...actual,
        useNavigate: () => mockNavigate,
    }
})

// Mock fetch for HTTPS check
global.fetch = vi.fn()

describe('LandingPage', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        window.location.protocol = 'http:'
    })

    it('renders welcome message', () => {
        render(
            <BrowserRouter>
                <LandingPage />
            </BrowserRouter>
        )

        expect(screen.getByText('Welcome to ZeCo')).toBeInTheDocument()
    })

    it('renders guest and staff buttons', () => {
        render(
            <BrowserRouter>
                <LandingPage />
            </BrowserRouter>
        )

        expect(screen.getByText('I am a Guest')).toBeInTheDocument()
        expect(screen.getByText('I am Staff / Connected User')).toBeInTheDocument()
    })

    it('navigates to menu when guest button is clicked', () => {
        render(
            <BrowserRouter>
                <LandingPage />
            </BrowserRouter>
        )

        const guestButton = screen.getByText('I am a Guest')
        fireEvent.click(guestButton)

        expect(mockNavigate).toHaveBeenCalledWith('/menu')
    })

    it('navigates to login if already on HTTPS', () => {
        window.location.protocol = 'https:'

        render(
            <BrowserRouter>
                <LandingPage />
            </BrowserRouter>
        )

        const staffButton = screen.getByText('I am Staff / Connected User')
        fireEvent.click(staffButton)

        expect(mockNavigate).toHaveBeenCalledWith('/login')
    })

    it('checks HTTPS certificate when staff button clicked on HTTP', async () => {
        global.fetch.mockResolvedValueOnce({ ok: true })

        render(
            <BrowserRouter>
                <LandingPage />
            </BrowserRouter>
        )

        const staffButton = screen.getByText('I am Staff / Connected User')
        fireEvent.click(staffButton)

        // Should show "Checking Connection..." text
        await waitFor(() => {
            expect(screen.getByText('Checking Connection...')).toBeInTheDocument()
        })
    })

    it('shows certificate instructions when HTTPS check fails', async () => {
        global.fetch.mockRejectedValueOnce(new Error('Certificate error'))

        render(
            <BrowserRouter>
                <LandingPage />
            </BrowserRouter>
        )

        const staffButton = screen.getByText('I am Staff / Connected User')
        fireEvent.click(staffButton)

        // Wait for certificate instructions to appear
        await waitFor(() => {
            expect(screen.getByText('Security Certificate Required')).toBeInTheDocument()
        })

        expect(screen.getByText('1. Download Certificate')).toBeInTheDocument()
        expect(screen.getByText('2. I have installed it - Connect')).toBeInTheDocument()
    })

    it('allows user to go back from certificate instructions', async () => {
        global.fetch.mockRejectedValueOnce(new Error('Certificate error'))

        render(
            <BrowserRouter>
                <LandingPage />
            </BrowserRouter>
        )

        const staffButton = screen.getByText('I am Staff / Connected User')
        fireEvent.click(staffButton)

        await waitFor(() => {
            expect(screen.getByText('Security Certificate Required')).toBeInTheDocument()
        })

        const backButton = screen.getByText('Back')
        fireEvent.click(backButton)

        // Should show main buttons again
        await waitFor(() => {
            expect(screen.getByText('I am a Guest')).toBeInTheDocument()
        })
    })
})
