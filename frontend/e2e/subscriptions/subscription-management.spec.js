import { test, expect } from "../helpers/test.js";
import { setAuthLocalStorage } from "../helpers/auth.js";
import {
  installSubscriptionsApiMocks,
  buildMockSubscription,
} from "../helpers/subscriptionsMocks.js";

test("subscriber with an active plan can still switch plan from the plans page", { tag: ['@flow:subscriptions-management', '@module:subscriptions', '@priority:P2', '@role:shared'] }, async ({ page }) => {
  const userId = 850;

  await installSubscriptionsApiMocks(page, {
    userId,
    role: "client",
    currentSubscription: buildMockSubscription({
      planType: "basico",
      status: "active",
      nextBillingDate: "2026-03-15",
    }),
  });

  await setAuthLocalStorage(page, {
    token: "e2e-token",
    userAuth: { id: userId, role: "client", is_profile_completed: true },
  });

  await page.goto("/subscriptions");
  await expect(page.getByRole("heading", { name: "Servicios Legales" })).toBeVisible({ timeout: 10_000 });

  // Holding an active plan does not lock the catalogue: the free plan card
  // still routes to its checkout.
  // quality: allow-fragile-selector (positional access: first plan card is Plan Básico)
  await page.getByRole("button", { name: "Elegir plan" }).first().click();

  await expect(page).toHaveURL(/\/checkout\/basico/, { timeout: 10_000 });
  await expect(page.getByRole("heading", { name: "Plan Básico" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Activar Plan Gratuito" })).toBeVisible();
});

// Hotfix 2026-10-07: online payment is not available, so the paid plans cannot be chosen.
test("authenticated user finds the paid plans marked Próximamente on the plans page", { tag: ['@flow:subscriptions-management', '@module:subscriptions', '@priority:P2', '@role:shared'] }, async ({ page }) => {
  const userId = 851;

  await installSubscriptionsApiMocks(page, {
    userId,
    role: "client",
    currentSubscription: null,
  });

  await setAuthLocalStorage(page, {
    token: "e2e-token",
    userAuth: { id: userId, role: "client", is_profile_completed: true },
  });

  await page.goto("/subscriptions");

  await expect(page.getByRole("heading", { name: "Servicios Legales" })).toBeVisible({ timeout: 10_000 });

  // Only the free plan keeps «Elegir plan»; Cliente and Corporativo read «Próximamente», disabled.
  await expect(page.getByRole("button", { name: "Elegir plan" })).toHaveCount(1);
  const cliente = page.getByTestId("plan-cliente-coming-soon");
  const corporativo = page.getByTestId("plan-corporativo-coming-soon");
  await expect(cliente).toHaveText("Próximamente");
  await expect(corporativo).toHaveText("Próximamente");
  await expect(cliente).toBeDisabled();
  await expect(corporativo).toBeDisabled();

  await cliente.click({ force: true });

  // The disabled button leads nowhere: the visitor stays on the plans page
  await expect(page).toHaveURL(/\/subscriptions$/);
  await expect(page.getByRole("heading", { name: "Finalizar Suscripción" })).toHaveCount(0);
});

test("plan selection carries the contact and plan sections into checkout", { tag: ['@flow:subscriptions-management', '@module:subscriptions', '@priority:P2', '@role:shared'] }, async ({ page }) => {
  const userId = 852;

  await installSubscriptionsApiMocks(page, {
    userId,
    role: "client",
    currentSubscription: null,
  });

  await setAuthLocalStorage(page, {
    token: "e2e-token",
    userAuth: { id: userId, role: "client", is_profile_completed: true },
  });

  await page.goto("/subscriptions");
  await expect(page.getByRole("heading", { name: "Servicios Legales" })).toBeVisible({ timeout: 10_000 });

  // quality: allow-fragile-selector (positional access: first plan card is Plan Básico)
  await page.getByRole("button", { name: "Elegir plan" }).first().click();

  await expect(page.getByRole("heading", { name: "Finalizar Suscripción" })).toBeVisible({ timeout: 10_000 });
  await expect(page.getByText("Información de contacto")).toBeVisible();
  await expect(page.getByText("Plan seleccionado")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Plan Básico" })).toBeVisible();
});

test("checkout back button returns to subscriptions page", { tag: ['@flow:subscriptions-management', '@module:subscriptions', '@priority:P2', '@role:shared'] }, async ({ page }) => {
  const userId = 853;

  await installSubscriptionsApiMocks(page, {
    userId,
    role: "client",
    currentSubscription: null,
  });

  await setAuthLocalStorage(page, {
    token: "e2e-token",
    userAuth: { id: userId, role: "client", is_profile_completed: true },
  });

  await page.goto("/checkout/basico");

  await expect(page.getByText("Volver a planes")).toBeVisible({ timeout: 10_000 });
  await page.getByText("Volver a planes").click();

  await expect(page).toHaveURL(/\/subscriptions/);
});
