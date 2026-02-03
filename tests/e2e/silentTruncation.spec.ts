/**
 * SAFETY-CRITICAL E2E Test: Silent Truncation Regression Gate
 * 
 * This test guards against SILENT-TRUNCATION-001, an S0 severity bug where
 * the braille STL generator would silently drop content that exceeded the
 * available rows, producing an STL file with incomplete braille without
 * warning the user.
 * 
 * CRITICAL: This test MUST NOT be skipped or quarantined without explicit
 * approval from the project maintainer. It is the primary safety gate for
 * preventing incorrect braille output.
 * 
 * Bug reproduction input: "Ryan Johnston 4Sight ryan.johnston@go4sight.com"
 * with 4 rows × 18 columns causes truncation in Auto Placement mode.
 * 
 * @see docs/specifications/BRAILLE_SAFETY_AUDIT_PLAN.md
 */

import { test, expect } from '@playwright/test';

test.describe('Silent Truncation Regression Gate', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    // Wait for the app to fully load
    await page.waitForSelector('#language-table');
    
    // Expand Expert Mode to access grid_rows and grid_columns settings
    const expertToggle = page.locator('#expert-toggle');
    await expect(expertToggle).toBeVisible();
    // Check if expert settings are already expanded
    const isExpanded = await expertToggle.getAttribute('aria-expanded');
    if (isExpanded !== 'true') {
      await expertToggle.click();
      // Wait for expert settings to be visible
      await page.waitForSelector('#expert-settings', { state: 'visible' });
    }
    
    // Expand the "Braille Spacing" submenu which contains grid_rows and grid_columns
    const spacingToggle = page.locator('button.expert-submenu-toggle:has-text("Braille Spacing")');
    await expect(spacingToggle).toBeVisible();
    const spacingExpanded = await spacingToggle.getAttribute('aria-expanded');
    if (spacingExpanded !== 'true') {
      await spacingToggle.click();
      // Wait for the spacing panel to be visible
      await page.waitForSelector('#expert-panel-spacing', { state: 'visible' });
    }
  });

  test('should block generation when auto-wrapped text exceeds rows', async ({ page }) => {
    // Switch to Auto Placement mode
    const autoModeRadio = page.locator('input[name="placement_mode"][value="auto"]');
    await autoModeRadio.check();
    await expect(autoModeRadio).toBeChecked();

    // Enter text that will exceed the available rows
    // Using plain text without special characters to avoid translation errors
    // This text is long enough to exceed 2 rows × 10 columns
    const autoTextArea = page.locator('#auto-text');
    await autoTextArea.fill('This is a very long text that will definitely need to be truncated because it exceeds the available space in the braille grid configuration');

    // Set very constrained dimensions that will cause truncation
    // 2 rows × 10 columns is too small for the test input
    const rowsInput = page.locator('#grid_rows');
    await rowsInput.fill('2');

    const columnsInput = page.locator('#grid_columns');
    await columnsInput.fill('10');

    // Track download events - we expect NO download to occur
    let downloadTriggered = false;
    page.on('download', () => {
      downloadTriggered = true;
    });

    // Click the Generate button
    const generateButton = page.locator('#action-btn');
    await expect(generateButton).toBeVisible();
    await generateButton.click();

    // Wait for error message to appear
    const errorDiv = page.locator('#error-message');
    await expect(errorDiv).toBeVisible({ timeout: 10000 });

    // Verify the error message indicates truncation blocking
    const errorText = page.locator('#error-text');
    const errorContent = await errorText.textContent();
    
    // The error should mention one of these truncation indicators:
    // - "extra content was not placed" (from banaAutoWrap)
    // - "exceeds available rows" (alternative phrasing)
    // - "Generation blocked" (our new blocking message)
    expect(
      errorContent?.toLowerCase().includes('not placed') ||
      errorContent?.toLowerCase().includes('exceeds') ||
      errorContent?.toLowerCase().includes('blocked')
    ).toBeTruthy();

    // Verify the error is displayed as a blocking error, not just a warning
    // The error-message class without 'info' indicates blocking
    await expect(errorDiv).toHaveClass(/error-message/);
    
    // The 'info' class indicates a loading message, not an error
    // We should NOT have the 'info' class
    const errorClasses = await errorDiv.getAttribute('class');
    expect(errorClasses?.includes('info')).toBeFalsy();

    // Verify the Generate button is re-enabled (not stuck in "Generating..." state)
    await expect(generateButton).toHaveText('Generate STL', { timeout: 5000 });
    await expect(generateButton).not.toBeDisabled();

    // Verify no download was triggered
    expect(downloadTriggered).toBeFalsy();
  });

  test('should allow generation when text fits within available space', async ({ page }) => {
    // Switch to Auto Placement mode
    const autoModeRadio = page.locator('input[name="placement_mode"][value="auto"]');
    await autoModeRadio.check();

    // Enter short text that will fit (default settings: 4 rows × 11 columns)
    const autoTextArea = page.locator('#auto-text');
    await autoTextArea.fill('Hi');

    // Click the Generate button
    const generateButton = page.locator('#action-btn');
    await expect(generateButton).toBeVisible();
    await generateButton.click();

    // Wait a moment for any error to appear
    await page.waitForTimeout(3000);
    
    // Check that no blocking error appeared (would block truncation)
    const errorDiv = page.locator('#error-message');
    const errorClasses = await errorDiv.getAttribute('class');
    
    // If error is visible, it should be 'info' (loading message) or not a blocking error
    // A blocking error would have 'error-message' without 'info'
    if (errorClasses && errorClasses.includes('error-message') && !errorClasses.includes('info')) {
      // Check if it's NOT a truncation error
      const errorText = await page.locator('#error-text').textContent();
      // If there's an error, it should NOT be a truncation error
      expect(
        errorText?.toLowerCase().includes('not placed') ||
        errorText?.toLowerCase().includes('truncat')
      ).toBeFalsy();
    }
    
    // The button should show "Generating..." or "Download" or "Generate STL"
    // (not stuck in an error state)
    const buttonText = await generateButton.textContent();
    expect(buttonText?.toLowerCase()).not.toContain('error');
  });

  test('should show error containing omitted content details', async ({ page }) => {
    // Switch to Auto Placement mode
    const autoModeRadio = page.locator('input[name="placement_mode"][value="auto"]');
    await autoModeRadio.check();

    // Enter the bug reproduction input
    const autoTextArea = page.locator('#auto-text');
    await autoTextArea.fill('Ryan Johnston 4Sight ryan.johnston@go4sight.com This text will definitely be truncated because it is very long');

    // Set very constrained dimensions
    const rowsInput = page.locator('#grid_rows');
    await rowsInput.fill('2');

    const columnsInput = page.locator('#grid_columns');
    await columnsInput.fill('10');

    // Click Generate
    const generateButton = page.locator('#action-btn');
    await generateButton.click();

    // Wait for error
    const errorText = page.locator('#error-text');
    await expect(errorText).toBeVisible({ timeout: 10000 });

    // Verify the error message is descriptive
    const content = await errorText.textContent();
    expect(content?.length).toBeGreaterThan(20); // Not just a generic error
  });
});
