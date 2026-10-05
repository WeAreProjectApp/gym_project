import { test, expect } from "../helpers/test.js";

import { setAuthLocalStorage } from "../helpers/auth.js";
import { installDashboardNavApiMocks } from "../helpers/dashboardNavMocks.js";
import { VIEWPORTS, viewportUse } from "../helpers/viewports.js";
import { freezeAnimationClock, showInstallationAlert } from "../helpers/animationFrameGate.js";

async function openMobileSidebar(page) {
  await page.getByRole("button", { name: "Open sidebar", exact: true }).click();
}

async function useDesktopSidebar(page) {
  await expect(page.getByRole("link", { name: "Procesos", exact: true })).toBeVisible();
}

const sidebarActions = {
  compact: openMobileSidebar,
  portrait: openMobileSidebar,
  landscape: useDesktopSidebar,
  desktop: useDesktopSidebar,
  wide: useDesktopSidebar,
};

async function retainInvisibleAlert(page) {
  await page.getByTestId("pwa-install-alert").waitFor({ state: "attached" });
}

const alertPhases = {
  invisible: { advance: retainInvisibleAlert, opacity: "0" },
  visible: { advance: showInstallationAlert, opacity: "1" },
};

for (const alias of ["portrait", "compact", "landscape", "desktop", "wide"]) {
  test.describe(`First web visit navigation (${alias})`, () => {
    test.use(viewportUse(alias));

    for (const phase of ["invisible", "visible"]) {
      // Catches the global PWA banner intercepting normal sidebar navigation.
      test(`first-visit ${phase} banner permits navigation to processes`, {
        tag: ['@flow:dashboard-navigation', '@module:dashboard', '@priority:P2', '@role:lawyer', '@outcome:success'],
      }, async ({ page }) => {
        // quality: allow-duplicate (per-viewport contract: dashboard-navigation at the shared viewport matrix)
        const userId = 1320;
        await freezeAnimationClock(page);
        await installDashboardNavApiMocks(page, { userId, role: "lawyer", isGymLawyer: true });
        await setAuthLocalStorage(page, {
          token: "e2e-token",
          userAuth: { id: userId, role: "lawyer", is_gym_lawyer: true, is_profile_completed: true },
        });
        await page.addInitScript(() => localStorage.removeItem("pwa-installed"));
        await page.goto("/dashboard");

        const alert = page.getByTestId("pwa-install-alert");
        await expect(alert).toHaveCount(1);
        await alertPhases[phase].advance(page);
        await expect(alert).toHaveCSS("opacity", alertPhases[phase].opacity);
        await sidebarActions[alias](page);
        await page.getByRole("link", { name: "Procesos", exact: true }).click();

        await expect(page).toHaveURL(/\/process_list$/);
        await expect(page.getByPlaceholder("Buscar procesos...")).toBeVisible();
        await expect(page.getByRole("cell", { name: /Client One/ })).toBeVisible();
        const documentWidth = await page.evaluate(async () => {
          await document.fonts.ready;
          return document.documentElement.scrollWidth;
        });
        expect(documentWidth).toBeLessThanOrEqual(VIEWPORTS[alias].width);
      });
    }
  });
}

test("dashboard loads and sidebar navigation works (processes, legal requests, dynamic documents)", { tag: ['@flow:dashboard-navigation', '@module:dashboard', '@priority:P2', '@role:shared', '@outcome:display'] }, async ({ page }) => {
  const userId = 1300;

  await installDashboardNavApiMocks(page, {
    userId,
    role: "lawyer",
    isGymLawyer: true,
  });

  await setAuthLocalStorage(page, {
    token: "e2e-token",
    userAuth: {
      id: userId,
      role: "lawyer",
      is_gym_lawyer: true,
      is_profile_completed: true,
    },
  });

  await page.goto("/dashboard");
  await page.waitForLoadState("networkidle");

  // Smoke: dashboard should render welcome card
  await expect(page.getByText("Procesos activos")).toBeVisible();

  const sidebar = page.locator("div.lg\\:fixed.lg\\:inset-y-0");

  // Sidebar navigation items (desktop)
  await sidebar.getByRole("link", { name: "Procesos", exact: true }).click();
  await expect(page).toHaveURL(/\/process_list/);
  await expect(page.getByPlaceholder("Buscar procesos...")).toBeVisible();

  await sidebar.getByRole("link", { name: "Archivos Juridicos", exact: true }).click();
  await expect(page).toHaveURL(/\/dynamic_document_dashboard/);
  await expect(page.getByRole("button", { name: "Minutas" })).toBeVisible();
});

test("client dashboard loads and shows sidebar with correct navigation items", { tag: ['@flow:dashboard-navigation', '@module:dashboard', '@priority:P2', '@role:shared'] }, async ({ page }) => {
  const userId = 1301;

  await installDashboardNavApiMocks(page, {
    userId,
    role: "client",
    isGymLawyer: false,
  });

  await setAuthLocalStorage(page, {
    token: "e2e-token",
    userAuth: { id: userId, role: "client", is_profile_completed: true },
  });

  await page.goto("/dashboard");
  await page.waitForLoadState("networkidle");

  // Client dashboard should render
  await expect(page.locator("body")).toBeVisible();

  const sidebar = page.locator("div.lg\\:fixed.lg\\:inset-y-0");

  // Client should see Archivos Juridicos link
  await sidebar.getByRole("link", { name: "Archivos Juridicos", exact: true }).click();
  await expect(page).toHaveURL(/\/dynamic_document_dashboard/);
});
