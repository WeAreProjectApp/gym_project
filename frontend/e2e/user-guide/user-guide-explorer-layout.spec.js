import { test, expect } from '../helpers/test.js';
import { setAuthLocalStorage } from '../helpers/auth.js';
import { mockApi } from '../helpers/api.js';
import { viewportUse } from '../helpers/viewports.js';

// Catches a responsive explorer regression that makes a capability unreachable,
// overflows its container, or derives its mode from the viewport instead of the
// measured explorer container.
const STANDARD_VIEWPORTS = ['compact', 'portrait', 'landscape', 'desktop', 'wide'];

async function openExplorerGuide(page) {
  const user = {
    id: 9100,
    role: 'client',
    first_name: 'Usuario',
    last_name: 'Explorador',
    email: 'explorer@example.com',
    is_profile_completed: true,
  };
  await mockApi(page, async ({ apiPath }) => {
    const responses = {
      'validate_token/': {},
      'users/': [user],
      'users/9100/': user,
      'users/9100/signature/': { has_signature: false },
      'google-captcha/site-key/': { site_key: 'e2e-site-key' },
      'dynamic-documents/pending-signatures-count/': { count: 0 },
      'notifications/': { results: [], count: 0 },
    };
    return { status: 200, contentType: 'application/json', body: JSON.stringify(responses[apiPath] ?? {}) };
  });
  await setAuthLocalStorage(page, { token: 'e2e-token', userAuth: user });
  await page.goto('/user_guide', { waitUntil: 'domcontentloaded' });
  const openExplorer = page.getByTestId('open-guide-explorer');
  await expect(openExplorer).toBeVisible();
  await openExplorer.scrollIntoViewIfNeeded();
  await openExplorer.click();
  await expect(page.getByTestId('guide-explorer').getByRole('heading', { name: 'Explorador de la plataforma' })).toHaveText('Explorador de la plataforma');
}

for (const viewport of STANDARD_VIEWPORTS) {
  test.describe(`explorer at ${viewport}`, () => {
    test.use(viewportUse(viewport));

    test(`users open collaboration content without horizontal overflow at ${viewport}`, {
      tag: ['@flow:user-guide-explorer-responsive', '@outcome:display', `@viewport:${viewport}`],
    }, async ({ page }) => {
      // quality: allow-duplicate (per-viewport contract — same behavior at standard widths)
      await page.emulateMedia({ reducedMotion: 'reduce' });
      await openExplorerGuide(page);
      await page.getByTestId('explorer-node-collaboration').click();
      await expect(page.getByTestId('explorer-detail-title')).toHaveText('Seguimiento y colaboración');
      await page.getByTestId('explorer-node-notifications').click();

      await expect(page.getByTestId('explorer-detail-title')).toHaveText('Notificaciones');
      const layout = await page.getByTestId('explorer-stage').getAttribute('data-layout');
      expect(['cards', 'orbit']).toContain(layout);
      const fits = await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth);
      expect(fits).toBe(true);
    });
  });
}

test.describe('explorer orbit controls', () => {
  test.use(viewportUse('wide'));

  test('wide-screen users rotate the measured orbital explorer', {
    tag: ['@flow:user-guide-explorer-orbit', '@outcome:success', '@viewport:wide'],
  }, async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await openExplorerGuide(page);
    await expect(page.getByTestId('explorer-stage')).toHaveAttribute('data-layout', 'orbit');
    const node = page.getByTestId('explorer-node-legal');
    const before = await node.boundingBox();
    await page.getByRole('button', { name: 'Girar a la derecha' }).click();

    await expect.poll(async () => (await node.boundingBox())?.x).toBeGreaterThan((before?.x ?? 0) + 5);
  });
});

test.describe('explorer keyboard return', () => {
  test.use(viewportUse('landscape'));

  test('keyboard users return with Escape after opening a capability', {
    tag: ['@flow:user-guide-explorer-responsive', '@outcome:success', '@viewport:landscape'],
  }, async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await openExplorerGuide(page);
    await page.getByTestId('explorer-node-legal').focus();
    await page.keyboard.press('Enter');
    await page.keyboard.press('Escape');

    await expect(page.getByTestId('explorer-detail-title')).toHaveText('G&M Consultores Jurídicos');
    await expect(page.getByText('El giro automático está desactivado por tu preferencia de movimiento reducido.')).toBeVisible();
  });
});
