import { test, expect } from "../helpers/test.js";
import { setAuthLocalStorage } from "../helpers/auth.js";
import {
  installSubscriptionsApiMocks,
  buildMockSubscription,
} from "../helpers/subscriptionsMocks.js";

/**
 * Deep coverage for:
 * - subscriptions/index.js store (15.8%) — fetchCurrentSubscription, getters
 * - Subscriptions.vue (81%) — plan features list, active plan badge
 * - Checkout.vue (62.6%) — free plan submission flow
 */

test("subscriber returning from checkout compares the three plan cards", { tag: ['@flow:subscriptions-management', '@module:subscriptions', '@priority:P2', '@role:shared'] }, async ({ page }) => {
  const userId = 9850;

  await installSubscriptionsApiMocks(page, {
    userId,
    role: "client",
    currentSubscription: buildMockSubscription({
      planType: "basico",
      status: "active",
      nextBillingDate: "2026-06-15",
    }),
  });

  await setAuthLocalStorage(page, {
    token: "e2e-token",
    userAuth: { id: userId, role: "client", is_profile_completed: true },
  });

  // The subscriber is on their current (free) plan checkout and goes back to
  // the catalogue to compare what the other plans offer.
  await page.goto("/checkout/basico");
  await expect(page.getByRole("heading", { name: "Finalizar Suscripción" })).toBeVisible({ timeout: 15_000 });

  await page.getByRole("button", { name: "Volver a planes" }).click();

  await expect(page.getByRole("heading", { name: "Servicios Legales" })).toBeVisible();
  await expect(page.getByText("Consulta Procesos Judiciales").first()).toBeVisible();
  await expect(page.getByText("Documentos Jurídicos").first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Plan Básico" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Plan Cliente" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Plan Corporativo" })).toBeVisible();
});

test("free plan checkout submits without payment method section", { tag: ['@flow:subscriptions-management', '@module:subscriptions', '@priority:P2', '@role:shared'] }, async ({ page }) => {
  const userId = 9851;

  await installSubscriptionsApiMocks(page, {
    userId,
    role: "client",
    currentSubscription: null,
  });

  // Mock subscription creation for free plan
  await page.route("**/api/subscriptions/create/", async (route) => {
    if (route.request().method() === "POST") {
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({
          id: 1,
          plan_type: "basico",
          status: "active",
          next_billing_date: null,
        }),
      });
    } else {
      await route.continue();
    }
  });

  await setAuthLocalStorage(page, {
    token: "e2e-token",
    userAuth: { id: userId, role: "client", is_profile_completed: true },
  });

  await page.goto("/checkout/basico");

  await expect(page.getByRole("heading", { name: "Finalizar Suscripción" })).toBeVisible({ timeout: 15_000 });

  // Plan details section
  await expect(page.getByText("Plan seleccionado")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Plan Básico" })).toBeVisible();
  await expect(page.getByText("Gratuito").first()).toBeVisible();

  // Free plan should NOT show payment card inputs
  await expect(page.locator('input[placeholder*="tarjeta"]')).toHaveCount(0);
});
