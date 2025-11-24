import { test, expect } from '@playwright/test';

/**
 * End-to-End Staff User Flow Tests
 * 
 * These tests verify the staff user journey including:
 * - Certificate check on HTTP
 * - HTTPS redirect
 * - Certificate installation instructions
 */

test.describe('Staff User Flow (HTTP)', () => {
    test.use({ baseURL: 'http://localhost:5173' });

    test('should show certificate instructions when staff button clicked', async ({ page }) => {
        await page.goto('/');

        // Click staff button
        await page.getByText('I am Staff / Connected User').click();

        // Should show "Checking Connection..." while checking
        await expect(page.getByText(/Checking Connection/)).toBeVisible();

        // Wait for certificate instructions to appear
        // (This assumes the HTTPS check will fail on HTTP)
        await expect(page.getByText('Security Certificate Required')).toBeVisible({ timeout: 5000 });
    });

    test('should display download certificate button', async ({ page }) => {
        await page.goto('/');

        await page.getByText('I am Staff / Connected User').click();

        // Wait for instructions
        await page.waitForSelector('text=Security Certificate Required');

        // Verify download button exists
        await expect(page.getByText('1. Download Certificate')).toBeVisible();
    });

    test('should allow going back from certificate instructions', async ({ page }) => {
        await page.goto('/');

        await page.getByText('I am Staff / Connected User').click();

        // Wait for instructions
        await page.waitForSelector('text=Security Certificate Required');

        // Click back button
        await page.getByText('Back').click();

        // Should return to main landing page
        await expect(page.getByText('I am a Guest')).toBeVisible();
    });
});

test.describe('Staff User Flow (HTTPS)', () => {
    test.use({ baseURL: 'https://localhost' });

    test('should redirect to login on HTTPS when staff button clicked', async ({ page }) => {
        await page.goto('/');

        // Click staff button
        await page.getByText('I am Staff / Connected User').click();

        // Should navigate to login page
        await expect(page).toHaveURL(/.*login/);
    });
});
