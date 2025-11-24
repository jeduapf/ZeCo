import { test, expect } from '@playwright/test';

/**
 * End-to-End Authentication Flow Tests
 * 
 * These tests verify the complete authentication workflow:
 * - Login process
 * - Logout process
 * - Protected route access
 * - Session persistence
 */

// Test credentials (ensure these exist in your test database)
const TEST_USER = {
    username: 'admin',
    password: 'admin123'
};

test.describe('Authentication Flow (HTTPS)', () => {
    test.use({ baseURL: 'https://localhost' });

    test('should show login page on HTTPS', async ({ page }) => {
        // Accept self-signed certificate
        await page.goto('/login');

        // Login page should be visible
        await expect(page).toHaveURL(/.*login/);
    });

    test('should login successfully with valid credentials', async ({ page }) => {
        await page.goto('/login');

        // Fill login form
        await page.fill('input[name="username"]', TEST_USER.username);
        await page.fill('input[name="password"]', TEST_USER.password);

        // Submit form
        await page.click('button[type="submit"]');

        // Should redirect to dashboard/home after login
        await expect(page).not.toHaveURL(/.*login/);
    });

    test('should reject invalid credentials', async ({ page }) => {
        await page.goto('/login');

        // Fill with invalid credentials
        await page.fill('input[name="username"]', 'invalid');
        await page.fill('input[name="password"]', 'wrongpass');

        // Submit form
        await page.click('button[type="submit"]');

        // Should show error message or stay on login page
        await expect(page).toHaveURL(/.*login/);
    });

    test('should access protected routes after login', async ({ page }) => {
        // Login first
        await page.goto('/login');
        await page.fill('input[name="username"]', TEST_USER.username);
        await page.fill('input[name="password"]', TEST_USER.password);
        await page.click('button[type="submit"]');

        // Wait for login to complete
        await page.waitForURL(/(?!.*login)/);

        // Try to access admin page
        await page.goto('/admin');

        // Should be accessible (not redirected)
        await expect(page).toHaveURL(/.*admin/);
    });

    test('should logout successfully', async ({ page }) => {
        // Login first
        await page.goto('/login');
        await page.fill('input[name="username"]', TEST_USER.username);
        await page.fill('input[name="password"]', TEST_USER.password);
        await page.click('button[type="submit"]');

        await page.waitForURL(/(?!.*login)/);

        // Find and click logout button (adjust selector as needed)
        await page.click('button:has-text("Logout"), a:has-text("Logout")');

        // Should redirect to landing or login
        await expect(page).toHaveURL(/.*\/(|login)/);
    });
});

test.describe('Multiple Login Sessions', () => {
    test.use({ baseURL: 'https://localhost' });

    test('should handle multiple login/logout cycles', async ({ page }) => {
        for (let i = 0; i < 3; i++) {
            // Login
            await page.goto('/login');
            await page.fill('input[name="username"]', TEST_USER.username);
            await page.fill('input[name="password"]', TEST_USER.password);
            await page.click('button[type="submit"]');

            await page.waitForURL(/(?!.*login)/);

            // Verify logged in
            await page.goto('/admin');
            await expect(page).toHaveURL(/.*admin/);

            // Logout
            await page.click('button:has-text("Logout"), a:has-text("Logout")');

            console.log(`✅ Cycle ${i + 1}/3 completed`);
        }
    });
});
