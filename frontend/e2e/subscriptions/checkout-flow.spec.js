import { test, expect } from "../helpers/test.js";
import { setAuthLocalStorage } from "../helpers/auth.js";
import { mockApi } from "../helpers/api.js";

const buildCheckoutEmail = (userId) => `checkout-user-${userId}@example.test`;

/**
 * Mock installer for subscription checkout page.
 */
async function installCheckoutMocks(page, { userId, planType = "basico", createSubscriptionStatus = 201 }) {
  const userEmail = buildCheckoutEmail(userId);
  const user = {
    id: userId,
    first_name: "Test",
    last_name: "User",
    email: userEmail,
    role: "client",
    contact: "",
    birthday: "",
    identification: "",
    document_type: "",
    photo_profile: "",
    is_profile_completed: true,
    is_gym_lawyer: false,
    has_signature: false,
  };

  const nowIso = new Date().toISOString();

  await mockApi(page, async ({ route, apiPath }) => {
    if (apiPath === "validate_token/") return { status: 200, contentType: "application/json", body: "{}" };
    if (apiPath === "users/") return { status: 200, contentType: "application/json", body: JSON.stringify([user]) };
    if (apiPath === `users/${userId}/`) return { status: 200, contentType: "application/json", body: JSON.stringify(user) };
    if (apiPath === `users/${userId}/signature/`) return { status: 200, contentType: "application/json", body: JSON.stringify({ has_signature: false }) };
    if (apiPath === "google-captcha/site-key/") return { status: 200, contentType: "application/json", body: JSON.stringify({ site_key: "e2e-site-key" }) };

    // Subscription endpoints
    if (apiPath === "subscriptions/current/") return { status: 404, contentType: "application/json", body: JSON.stringify({ detail: "not_found" }) };
    if (apiPath === "subscriptions/wompi-config/") return { status: 200, contentType: "application/json", body: JSON.stringify({ public_key: "pub_test_e2e_key" }) };

    // Create subscription (free plan)
    if (apiPath === "subscriptions/create/" && route.request().method() === "POST") {
      if (createSubscriptionStatus >= 400) {
        // No `.error` field: Checkout.vue's free-plan catch block reads
        // error.response?.data?.error first and only falls back to its own
        // generic message when that's absent — this fixture needs the
        // fallback path, unlike checkout-payment-flow.spec.js's paid-plan
        // failure test, which asserts the literal `.error` text instead.
        return {
          status: createSubscriptionStatus,
          contentType: "application/json",
          body: JSON.stringify({ detail: "Internal Server Error" }),
        };
      }
      return {
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({
          id: 1,
          plan_type: planType,
          status: "active",
          created_at: nowIso,
        }),
      };
    }

    // Activity, misc
    if (apiPath === "user-activities/") return { status: 200, contentType: "application/json", body: "[]" };
    if (apiPath === "create-activity/") return { status: 201, contentType: "application/json", body: JSON.stringify({ id: 1, action_type: "view", description: "", created_at: nowIso }) };
    if (apiPath === "recent-processes/") return { status: 200, contentType: "application/json", body: "[]" };
    if (apiPath === "dynamic-documents/recent/") return { status: 200, contentType: "application/json", body: "[]" };
    if (apiPath === "legal-updates/active/") return { status: 200, contentType: "application/json", body: "[]" };
    if (apiPath === "dynamic-documents/") return { status: 200, contentType: "application/json", body: "[]" };
    if (apiPath === "dynamic-documents/tags/") return { status: 200, contentType: "application/json", body: "[]" };
    if (apiPath === "dynamic-documents/folders/") return { status: 200, contentType: "application/json", body: "[]" };

    return null;
  });
}

test("selecting the free plan opens its checkout with the buyer's own data", { tag: ['@flow:subscriptions-checkout-free', '@module:subscriptions', '@priority:P1', '@role:shared'] }, async ({ page }) => {
  const userId = 9100;
  const userEmail = buildCheckoutEmail(userId);

  await installCheckoutMocks(page, { userId, planType: "basico" });

  await setAuthLocalStorage(page, {
    token: "e2e-token",
    userAuth: { id: userId, role: "client", is_profile_completed: true, first_name: "Test", last_name: "User", email: userEmail },
  });

  await page.goto("/subscriptions");
  await expect(page.getByRole("heading", { name: "Servicios Legales" })).toBeVisible({ timeout: 15_000 });

  // quality: allow-fragile-selector (positional access: first plan card is Plan Básico)
  await page.getByRole("button", { name: "Elegir plan" }).first().click();

  await expect(page).toHaveURL(/\/checkout\/basico/, { timeout: 15_000 });
  await expect(page.getByRole("heading", { name: "Plan Básico" })).toBeVisible();
  await expect(page.getByText("Resumen del pedido")).toBeVisible();

  // The checkout is filled with the signed-in buyer, not a placeholder
  await expect(page.getByText("Test User")).toBeVisible();
  await expect(page.getByText(userEmail)).toBeVisible();
  await expect(page.getByRole("button", { name: /Activar Plan Gratuito/i })).toBeVisible();
});

// Hotfix 2026-10-07: online payment is not available. The paid plan cards read «Próximamente» and
// no longer open a paid checkout.
test("the corporate plan card shows Próximamente instead of opening a paid checkout", { tag: ['@flow:subscriptions-checkout-paid', '@module:subscriptions', '@priority:P1', '@role:shared', '@outcome:display'] }, async ({ page }) => {
  const userId = 9101;
  const userEmail = buildCheckoutEmail(userId);

  await installCheckoutMocks(page, { userId, planType: "corporativo" });

  await setAuthLocalStorage(page, {
    token: "e2e-token",
    userAuth: { id: userId, role: "client", is_profile_completed: true, first_name: "Test", last_name: "User", email: userEmail },
  });

  await page.goto("/subscriptions");
  await expect(page.getByRole("heading", { name: "Servicios Legales" })).toBeVisible({ timeout: 15_000 });
  await expect(page.getByRole("heading", { name: "Plan Corporativo" })).toBeVisible();

  const corporate = page.getByTestId("plan-corporativo-coming-soon");
  await expect(corporate).toHaveText("Próximamente");
  await expect(corporate).toBeDisabled();
  await corporate.click({ force: true });

  await expect(page).toHaveURL(/\/subscriptions$/);
  await expect(page.getByRole("heading", { name: "Finalizar Suscripción" })).toHaveCount(0);
});

test("free plan checkout activates subscription successfully", { tag: ['@flow:subscriptions-checkout-free', '@module:subscriptions', '@priority:P1', '@role:shared', '@outcome:success'] }, async ({ page }) => {
  const userId = 9102;
  const userEmail = buildCheckoutEmail(userId);

  await installCheckoutMocks(page, { userId, planType: "basico" });

  await setAuthLocalStorage(page, {
    token: "e2e-token",
    userAuth: { id: userId, role: "client", is_profile_completed: true, first_name: "Test", last_name: "User", email: userEmail },
  });

  await page.goto("/checkout/basico");

  await expect(page.getByRole("button", { name: /Activar Plan Gratuito/i })).toBeVisible({ timeout: 15_000 });

  // Click to activate free plan
  await page.getByRole("button", { name: /Activar Plan Gratuito/i }).click();

  // Should show success notification
  const successDialog = page.locator('[class~="swal2-popup"]');
  await expect(successDialog).toBeVisible({ timeout: 15_000 });
  await expect(successDialog).toContainText("Activada");
  await page.locator('[class~="swal2-confirm"]').click();

  // Should redirect to dashboard
  await expect(page).toHaveURL(/dashboard/, { timeout: 15_000 });
});

test("free plan checkout shows an error and does not redirect when activation fails", { tag: ['@flow:subscriptions-checkout-free', '@module:subscriptions', '@priority:P1', '@role:shared', '@outcome:failure'] }, async ({ page }) => {
  const userId = 9103;
  const userEmail = buildCheckoutEmail(userId);

  await installCheckoutMocks(page, { userId, planType: "basico", createSubscriptionStatus: 500 });

  await setAuthLocalStorage(page, {
    token: "e2e-token",
    userAuth: { id: userId, role: "client", is_profile_completed: true, first_name: "Test", last_name: "User", email: userEmail },
  });

  await page.goto("/checkout/basico");

  await expect(page.getByRole("button", { name: /Activar Plan Gratuito/i })).toBeVisible({ timeout: 15_000 });
  await page.getByRole("button", { name: /Activar Plan Gratuito/i }).click();

  // Failure notification — the generic catch-block message, since the mock's
  // error body has no `.error` field that the frontend would surface instead.
  const errorDialog = page.locator('[class~="swal2-popup"]');
  await expect(errorDialog).toBeVisible({ timeout: 15_000 });
  await expect(errorDialog).toContainText("No se pudo activar tu suscripción. Por favor, intenta nuevamente.");
  await page.locator('[class~="swal2-confirm"]').click();

  // No redirect on failure — the buyer stays on the checkout to retry.
  expect(page.url()).toContain("/checkout/basico");
});
