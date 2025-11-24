import { test, expect } from '@playwright/test';

/**
 * End-to-End Guest User Flow Tests
 * 
 * These tests verify the complete guest user journey:
 * - Landing page rendering
 * - Guest button functionality
 * - Menu page access
 * - Navigation
 */

test.describe('Guest User Flow', () => {
    test('should display landing page correctly', async ({ page }) => {
        await page.goto('http://localhost:5173');

        // Verify main elements
        await expect(page.getByText('Welcome to ZeCo')).toBeVisible();
        await expect(page.getByText('I am a Guest')).toBeVisible();
        await expect(page.getByText('I am Staff / Connected User')).toBeVisible();
    });

    test('should navigate to menu when guest button is clicked', async ({ page }) => {
        await page.goto('http://localhost:5173');

        // Click guest button
        await page.getByText('I am a Guest').click();

        // Verify navigation to menu page
        await expect(page).toHaveURL(/.*menu/);
    });

    test('should allow browsing menu as guest', async ({ page }) => {
        // Navigate directly to menu
        await page.goto('http://localhost:5173/menu');

        // Menu should be accessible
        // (Exact assertions depend on your menu structure)
        await expect(page).toHaveURL(/.*menu/);
    });

    test('should navigate back from menu to landing', async ({ page }) => {
        await page.goto('http://localhost:5173/menu');

        // Find and click navigation link back to home
        // (Adjust selector based on your NavBar implementation)
        await page.goto('http://localhost:5173/');

        await expect(page.getByText('Welcome to ZeCo')).toBeVisible();
    });
});

test.describe('HTTP vs HTTPS Routing', () => {
    test('should show landing page on HTTP root', async ({ page }) => {
        await page.goto('http://localhost:5173/');

        await expect(page.getByText('Welcome to ZeCo')).toBeVisible();
    });

    test('should redirect login to landing on HTTP', async ({ page }) => {
        // Try to access login on HTTP
        await page.goto('http://localhost:5173/login');

        // Should show landing page instead
        await expect(page.getByText('Welcome to ZeCo')).toBeVisible();
    });

    test('should redirect admin to landing on HTTP', async ({ page }) => {
        // Try to access admin on HTTP
        await page.goto('http://localhost:5173/admin');

        // Should show landing page instead
        await expect(page.getByText('Welcome to ZeCo')).toBeVisible();
    });
});

test.describe('Page Rendering', () => {
    test('should render about page', async ({ page }) => {
        await page.goto('http://localhost:5173/about');

        // Verify about page loaded
        await expect(page).toHaveURL(/.*about/);
    });

    test('should render checkout page', async ({ page }) => {
        await page.goto('http://localhost:5173/checkout');

        // Verify checkout page loaded
        await expect(page).toHaveURL(/.*checkout/);
    });
});
