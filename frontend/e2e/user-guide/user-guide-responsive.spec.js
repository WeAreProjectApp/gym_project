import { test, expect } from '../helpers/test.js';
import { setAuthLocalStorage } from '../helpers/auth.js';
import { mockApi } from '../helpers/api.js';
import { viewportUse } from '../helpers/viewports.js';

// Catches the zoomed guide regression where mobile controls render below a
// 44 px physical target, the menu cannot reach Procesos, or the example title
// sits below its close button and creates horizontal overflow.
async function openMobileGuide(page) {
  const user = {
    id: 9200,
    first_name: 'Guía',
    last_name: 'Responsiva',
    email: 'responsive-guide@example.com',
    role: 'lawyer',
    is_gym_lawyer: true,
    is_profile_completed: true,
  };

  await mockApi(page, async ({ apiPath }) => {
    const responses = {
      'validate_token/': {},
      'users/': [user],
      'users/9200/': user,
      'users/9200/signature/': { has_signature: false },
      'google-captcha/site-key/': { site_key: 'e2e-site-key' },
      'dynamic-documents/pending-signatures-count/': { count: 0 },
      'notifications/': { results: [], count: 0 },
    };
    return { status: 200, contentType: 'application/json', body: JSON.stringify(responses[apiPath] ?? {}) };
  });
  await setAuthLocalStorage(page, { token: 'e2e-token', userAuth: user });
  await page.goto('/user_guide');
  await expect(page.getByRole('heading', { name: 'Bienvenido al Manual de Usuario' })).toHaveText('Bienvenido al Manual de Usuario');
}

async function openProcessesGuide(page) {
  await openMobileGuide(page);
  await page.getByTestId('guide-mobile-navigation-toggle').click();
  await page.getByTestId('guide-mobile-navigation').getByRole('button', {
    name: 'Procesos',
    exact: true,
  }).click();
  await expect(page.getByRole('heading', { name: 'Procesos', exact: true })).toHaveText('Procesos');
}

async function expectPhysicalTarget(locator) {
  const box = await locator.boundingBox();
  expect(box?.width).toBeGreaterThanOrEqual(43.5);
  expect(box?.height).toBeGreaterThanOrEqual(43.5);
}

async function expectTitleClearOfClose(title, close) {
  const closeBox = await close.boundingBox();
  const titleLineBoxes = await title.evaluate((element) => {
    const range = document.createRange();
    range.selectNodeContents(element);
    return Array.from(range.getClientRects(), ({ left, right, top, bottom }) => ({ left, right, top, bottom }));
  });
  expect(closeBox).not.toBeNull();
  const overlappingTitleLines = titleLineBoxes.filter(({ top, bottom }) => (
    top < closeBox.y + closeBox.height && bottom > closeBox.y
  ));
  expect(overlappingTitleLines.length).toBeGreaterThan(0);
  expect(Math.max(...overlappingTitleLines.map(({ right }) => right))).toBeLessThanOrEqual(closeBox.x + 0.5);
}

for (const viewport of ['compact', 'portrait']) {
  test.describe(`mobile manual at ${viewport}`, () => {
    test.use(viewportUse(viewport));

    test(`opens Procesos from the mobile menu with reachable controls at ${viewport}`, {
      tag: ['@flow:user-guide-navigation', '@outcome:display', `@viewport:${viewport}`],
    }, async ({ page }) => {
      // quality: allow-duplicate (per-viewport contract — same behavior at standard widths)
      await openMobileGuide(page);
      const toggle = page.getByTestId('guide-mobile-navigation-toggle');
      await expectPhysicalTarget(toggle);
      await expect(toggle).toHaveAttribute('aria-expanded', 'false');
      await toggle.click();
      await expect(toggle).toHaveAttribute('aria-expanded', 'true');
      await page.getByTestId('guide-mobile-navigation').getByRole('button', { name: 'Procesos', exact: true }).click();

      await expect(page.getByRole('heading', { name: 'Procesos', exact: true })).toHaveText('Procesos');
      await expect(toggle).toHaveAttribute('aria-expanded', 'false');
      const fits = await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth);
      expect(fits).toBe(true);
    });

    test(`clears the guide search at ${viewport}`, {
      tag: ['@flow:user-guide-navigation', '@outcome:success', `@viewport:${viewport}`],
    }, async ({ page }) => {
      // quality: allow-duplicate (per-viewport contract — same behavior at standard widths)
      await openProcessesGuide(page);

      const search = page.getByTestId('guide-search-input');
      await expectPhysicalTarget(search);
      await search.fill('proceso');
      await expect(page.getByText(/resultado\(s\) encontrado\(s\)/)).toContainText('resultado(s) encontrado(s)');
      const clear = page.getByTestId('guide-search-clear');
      await expectPhysicalTarget(clear);
      await clear.click();
      await expect(search).toHaveValue('');
      await expect(page.getByText(/resultado\(s\) encontrado\(s\)/)).toHaveCount(0);

      const fits = await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth);
      expect(fits).toBe(true);
    });

    test(`closes a Procesos example without title overlap at ${viewport}`, {
      tag: ['@flow:user-guide-navigation', '@outcome:display', `@viewport:${viewport}`],
    }, async ({ page }) => {
      // quality: allow-duplicate (per-viewport contract — same behavior at standard widths)
      await openProcessesGuide(page);

      await page.getByRole('button', { name: 'Radicar Proceso (Solo Abogados)' }).click();
      await expect(page.getByRole('heading', { name: 'Radicar Proceso (Solo Abogados)' })).toHaveText('Radicar Proceso (Solo Abogados)');
      await page.getByRole('button', { name: 'Ver Ejemplo Completo' }).click();
      const dialog = page.getByTestId('guide-example-dialog');
      const title = dialog.getByRole('heading', {
        name: 'Ejemplo: Radicar un Proceso de Tutela',
        exact: true,
        level: 3,
      });
      await expect(title).toHaveText('Ejemplo: Radicar un Proceso de Tutela');
      const close = page.getByTestId('guide-example-close');
      await expectPhysicalTarget(close);
      await expectTitleClearOfClose(title, close);
      await close.click();

      await expect(dialog).toHaveCount(0);
      const fits = await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth);
      expect(fits).toBe(true);
    });
  });
}
