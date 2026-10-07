import { test, expect } from "../helpers/test.js";
import { setAuthLocalStorage } from "../helpers/auth.js";
import { installDashboardNavApiMocks } from "../helpers/dashboardNavMocks.js";

/**
 * Deep coverage for dashboard widgets:
 * - UserWelcomeCard.vue
 * - QuickActionButtons.vue
 */

test("lawyer quick action Todos los Procesos opens the general process list", { tag: ['@flow:dashboard-quick-actions', '@module:dashboard', '@priority:P3', '@role:shared', '@outcome:display'] }, async ({ page }) => {
  const userId = 9830;

  await installDashboardNavApiMocks(page, { userId, role: "lawyer", isGymLawyer: true });

  await setAuthLocalStorage(page, {
    token: "e2e-token",
    userAuth: { id: userId, role: "lawyer", is_gym_lawyer: true, is_profile_completed: true },
  });

  await page.goto("/dashboard");

  // Wait for dashboard shell to render
  await expect(page.getByRole("button", { name: "Feed" })).toBeVisible({ timeout: 15_000 });

  // UserWelcomeCard should show active processes count
  await expect(page.getByText("Procesos activos")).toBeVisible({ timeout: 10_000 });

  // QuickActionButtons for lawyer
  await expect(page.getByText("Radicar Proceso")).toBeVisible({ timeout: 10_000 });
  await expect(page.getByText("Nueva Minuta")).toBeVisible();
  await expect(page.getByText("Radicar Informe")).toBeVisible();

  await page.getByRole("link", { name: /Todos los Procesos/ }).click();

  // Transition: the general process list replaces the dashboard
  await expect(page).toHaveURL(/\/process_list\?group=general/);
  await expect(page.getByPlaceholder("Buscar procesos...")).toBeVisible({ timeout: 10_000 });
  await expect(page.getByRole("button", { name: "Todos los Procesos" })).toBeVisible();
});

// The client «Agendar Cita» quick action (Calendly) was removed by the 2026-10-07 hotfix.
test("client quick action Radicar Solicitud opens the legal request form", { tag: ['@flow:dashboard-quick-actions', '@module:dashboard', '@priority:P3', '@role:shared'] }, async ({ page }) => {
  const userId = 9832;

  await installDashboardNavApiMocks(page, { userId, role: "client", isGymLawyer: false });

  await setAuthLocalStorage(page, {
    token: "e2e-token",
    userAuth: { id: userId, role: "client", is_profile_completed: true },
  });

  await page.goto("/dashboard");

  await expect(page.getByText("Procesos activos")).toBeVisible({ timeout: 15_000 });

  // Client quick actions — use first() since "Mis Procesos" may appear in sidebar too
  await expect(page.getByText("Mis Procesos").first()).toBeVisible({ timeout: 10_000 });
  await expect(page.getByRole("link", { name: /Agendar Cita/ })).toHaveCount(0);

  await page.getByRole("link", { name: /Radicar Solicitud/ }).first().click();

  // Transition: the legal request form replaces the dashboard
  await expect(page).toHaveURL(/\/legal_request/, { timeout: 10_000 });
  await expect(page.getByText("Procesos activos")).toHaveCount(0);
});
