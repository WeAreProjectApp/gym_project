import { test, expect } from "../helpers/test.js";
import { setAuthLocalStorage } from "../helpers/auth.js";
import { mockApi } from "../helpers/api.js";

/**
 * E2E tests for Checkout subscription flows with behavior-first assertions.
 *
 * Hotfix 2026-10-07: online payment is not available. The paid checkout no longer renders the Wompi
 * card form nor loads any third-party script; it shows a «Próximamente» notice and a disabled button.
 * docs/hotfixes/2026-10-07-remove-unused-third-party-loaders.md explains why and how to reactivate it.
 */

function buildMockUser({ id, role }) {
  return {
    id,
    first_name: "E2E",
    last_name: "User",
    email: "e2e@example.com",
    role,
    has_signature: role === "lawyer",
    is_profile_completed: true,
    is_gym_lawyer: role === "lawyer",
    contact: "",
    birthday: "",
    identification: "",
    document_type: "",
    photo_profile: "",
  };
}

function buildAuthPayload(user) {
  return {
    token: "e2e-token",
    userAuth: {
      id: user.id,
      role: user.role,
      email: user.email,
      first_name: user.first_name,
      last_name: user.last_name,
      is_profile_completed: true,
      is_gym_lawyer: user.is_gym_lawyer,
    },
  };
}

async function installCheckoutMocks(
  page,
  {
    user,
    currentSubscription = null,
    createSubscriptionStatus = 201,
    subscriptionRequests = [],
    apiCalls = [],
  }
) {
  const nowIso = new Date().toISOString();

  await mockApi(page, async ({ route, apiPath }) => {
    apiCalls.push(apiPath);
    if (apiPath === "validate_token/") return { status: 200, contentType: "application/json", body: "{}" };
    if (apiPath === "users/") return { status: 200, contentType: "application/json", body: JSON.stringify([user]) };
    if (apiPath === `users/${user.id}/`) return { status: 200, contentType: "application/json", body: JSON.stringify(user) };
    if (apiPath === `users/${user.id}/signature/`) {
      return {
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ has_signature: user.has_signature }),
      };
    }

    if (apiPath === "subscriptions/current/") {
      if (currentSubscription) {
        return { status: 200, contentType: "application/json", body: JSON.stringify(currentSubscription) };
      }
      return { status: 404, contentType: "application/json", body: JSON.stringify({ detail: "not_found" }) };
    }

    if (apiPath === "subscriptions/create/" && route.request().method() === "POST") {
      const payload = route.request().postDataJSON?.() || {};
      subscriptionRequests.push(payload);

      if (createSubscriptionStatus >= 400) {
        return {
          status: createSubscriptionStatus,
          contentType: "application/json",
          body: JSON.stringify({ error: "subscription_create_failed" }),
        };
      }

      const newSub = {
        id: 5001,
        plan_type: payload.plan_type,
        status: "active",
        next_billing_date: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
      };
      return { status: 201, contentType: "application/json", body: JSON.stringify(newSub) };
    }

    if (apiPath === "user-activities/") return { status: 200, contentType: "application/json", body: "[]" };
    if (apiPath === "create-activity/") {
      return {
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({ id: 1, action_type: "view", description: "", created_at: nowIso }),
      };
    }
    if (apiPath === "recent-processes/") return { status: 200, contentType: "application/json", body: "[]" };
    if (apiPath === "processes/") return { status: 200, contentType: "application/json", body: "[]" };
    if (apiPath === "dynamic-documents/recent/") return { status: 200, contentType: "application/json", body: "[]" };
    if (apiPath === "legal-updates/active/") return { status: 200, contentType: "application/json", body: "[]" };

    return null;
  });
}

test.describe.configure({ timeout: 90_000 });

test("paid checkout from an old link shows the unavailable notice and never charges", { tag: ['@flow:subscriptions-checkout-paid', '@module:subscriptions', '@priority:P1', '@role:shared', '@outcome:display'] }, async ({ page }) => {
  // quality: allow-deep-link (since the 2026-10-07 hotfix the paid plan buttons are disabled, so an old link or bookmark is the only way into a paid checkout)
  const user = buildMockUser({ id: 5400, role: "client" });
  const subscriptionRequests = [];
  const apiCalls = [];
  const paymentScripts = [];
  page.on("request", (request) => {
    if (/wompi|calendly/i.test(new URL(request.url()).hostname)) paymentScripts.push(request.url());
  });

  await installCheckoutMocks(page, { user, subscriptionRequests, apiCalls });
  await setAuthLocalStorage(page, buildAuthPayload(user));

  await page.goto("/checkout/cliente");

  await expect(page.getByRole("heading", { name: "Finalizar Suscripción" })).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText("Plan Cliente").first()).toBeVisible();
  await expect(page.getByTestId("checkout-paid-unavailable")).toContainText("El pago en línea no está disponible por ahora");
  await expect(page.getByPlaceholder("0000 0000 0000 0000")).toHaveCount(0);

  const soon = page.getByRole("button", { name: "Próximamente" });
  await expect(soon).toBeDisabled();
  await soon.click({ force: true });

  await expect(page).toHaveURL(/\/checkout\/cliente/);
  expect(subscriptionRequests).toHaveLength(0);
  expect(apiCalls).not.toContain("subscriptions/wompi-config/");
  expect(paymentScripts).toEqual([]);
});

test("free checkout creates subscription without payment tokenization", { tag: ['@flow:subscriptions-checkout-paid','@module:subscriptions', '@priority:P1', '@role:shared'] }, async ({ page }) => {
  const user = buildMockUser({ id: 5403, role: "client" });
  const subscriptionRequests = [];

  await installCheckoutMocks(page, { user, subscriptionRequests });
  await setAuthLocalStorage(page, buildAuthPayload(user));

  await page.goto("/checkout/basico");

  await expect(page.getByText("Plan Básico").first()).toBeVisible({ timeout: 15_000 });
  await expect(page.getByRole("heading", { name: "Método de pago" })).toHaveCount(0);

  await page.getByRole("button", { name: "Activar Plan Gratuito" }).click();

  const successDialog = page.locator('[role="dialog"], [role="alertdialog"]');
  await expect(successDialog).toBeVisible({ timeout: 15_000 });
  await expect(successDialog).toContainText("Suscripción Activada");
  await successDialog.getByRole("button", { name: /ok|aceptar/i }).click();

  await expect(page).toHaveURL(/\/dashboard/, { timeout: 15_000 });
  expect(subscriptionRequests).toHaveLength(1);
  expect(subscriptionRequests[0]).toMatchObject({ plan_type: "basico" });
  expect(subscriptionRequests[0].token).toBeUndefined();
  expect(subscriptionRequests[0].session_id).toBeUndefined();
});
