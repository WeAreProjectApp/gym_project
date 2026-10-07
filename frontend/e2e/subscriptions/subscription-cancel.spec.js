import { test, expect } from "../helpers/test.js";
import { setAuthLocalStorage } from "../helpers/auth.js";
import {
  installSubscriptionsApiMocks,
  buildMockSubscription,
} from "../helpers/subscriptionsMocks.js";

/**
 * E2E tests for the subscriptions-cancel flow surface.
 *
 * NOTE: there is currently NO cancel-subscription UI in the frontend (no
 * component calls `subscriptions/cancel/`). The observable "cancel" surface
 * for an active subscriber is the plans page, which advertises the
 * cancel-anytime policy and lets the user switch plans through checkout.
 */

test("active subscriber leaving checkout finds the cancel-anytime policy", { tag: ['@flow:subscriptions-cancel', '@module:subscriptions', '@priority:P2', '@role:shared'] }, async ({ page }) => {
  const userId = 9100;
  const sub = buildMockSubscription({ planType: "cliente", status: "active" });

  await installSubscriptionsApiMocks(page, {
    userId,
    role: "client",
    currentSubscription: sub,
  });

  await setAuthLocalStorage(page, {
    token: "e2e-token",
    userAuth: { id: userId, role: "client", is_gym_lawyer: false, is_profile_completed: true },
  });

  // The subscriber is mid-checkout and backs out of the purchase
  await page.goto("/checkout/cliente");
  await expect(page.getByRole("heading", { name: "Finalizar Suscripción" })).toBeVisible({ timeout: 15_000 });

  await page.getByRole("button", { name: "Volver a planes" }).click();

  // The plans page is where the cancellation policy is stated
  await expect(page).toHaveURL(/\/subscriptions/);
  await expect(page.getByText("Cancela en cualquier momento")).toBeVisible();
  await expect(page.getByText("30 días de garantía de reembolso")).toBeVisible();
});

test("user navigates to checkout from subscriptions page for plan upgrade", { tag: ['@flow:subscriptions-cancel', '@module:subscriptions', '@priority:P2', '@role:shared'] }, async ({ page }) => {
  const userId = 9101;

  await installSubscriptionsApiMocks(page, {
    userId,
    role: "client",
    currentSubscription: null,
  });

  await setAuthLocalStorage(page, {
    token: "e2e-token",
    userAuth: { id: userId, role: "client", is_gym_lawyer: false, is_profile_completed: true },
  });

  await page.goto("/subscriptions");
  await expect(page.getByRole("heading", { name: "Servicios Legales" })).toBeVisible({ timeout: 15_000 });

  // Only the free plan can be chosen since the 2026-10-07 hotfix (the paid plans show «Próximamente»).
  await page.getByRole("button", { name: "Elegir plan" }).first().click();

  await expect(page).toHaveURL(/\/checkout\/basico/, { timeout: 10_000 });
  await expect(page.getByRole("heading", { name: "Finalizar Suscripción" })).toBeVisible();
});
