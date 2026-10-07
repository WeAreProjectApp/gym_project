import { test, expect } from "../helpers/test.js";
import { setAuthLocalStorage } from "../helpers/auth.js";
import { mockApi } from "../helpers/api.js";

// quality: allow-fragile-test-data (seeded fake data from generate_fake_data command)

function buildBasicUser(id) {
  return {
    id,
    first_name: "E2E",
    last_name: "Basic",
    email: `basic-${id}@example.com`,
    role: "basic",
    contact: "",
    birthday: "",
    identification: "",
    document_type: "",
    photo_profile: "",
    is_profile_completed: true,
    is_gym_lawyer: false,
    has_signature: false,
  };
}

async function installBasicUserDashboardMocks(page, { userId }) {
  const user = buildBasicUser(userId);
  const nowIso = new Date().toISOString();

  await mockApi(page, async ({ route, apiPath }) => {
    if (apiPath === "validate_token/") {
      return { status: 200, contentType: "application/json", body: "{}" };
    }

    if (apiPath === "google-captcha/site-key/") {
      return { status: 200, contentType: "application/json", body: JSON.stringify({ site_key: "e2e-site-key" }) };
    }

    if (apiPath === "users/") {
      return { status: 200, contentType: "application/json", body: JSON.stringify([user]) };
    }

    if (apiPath === `users/${userId}/`) {
      return { status: 200, contentType: "application/json", body: JSON.stringify(user) };
    }

    if (apiPath === `users/${userId}/signature/`) {
      return { status: 200, contentType: "application/json", body: JSON.stringify({ has_signature: false }) };
    }

    if (apiPath === "user-activities/") {
      return { status: 200, contentType: "application/json", body: "[]" };
    }

    if (apiPath === "create-activity/") {
      return { status: 201, contentType: "application/json", body: JSON.stringify({ id: 1, action_type: "other", description: "", created_at: nowIso }) };
    }

    if (apiPath === "recent-processes/") {
      return { status: 200, contentType: "application/json", body: "[]" };
    }

    if (apiPath === "dynamic-documents/recent/") {
      return { status: 200, contentType: "application/json", body: "[]" };
    }

    if (apiPath === "legal-updates/active/") {
      return { status: 200, contentType: "application/json", body: "[]" };
    }

    if (apiPath === "processes/") {
      return { status: 200, contentType: "application/json", body: "[]" };
    }

    return null;
  });
}

test("basic user can access dashboard and sees welcome content", { tag: ['@flow:basic-restrictions', '@module:auth', '@priority:P3', '@role:basic'] }, async ({ page }) => {
  const userId = 9500;

  await installBasicUserDashboardMocks(page, { userId });

  await setAuthLocalStorage(page, {
    token: "e2e-token",
    userAuth: { id: userId, role: "basic", is_gym_lawyer: false, is_profile_completed: true },
  });

  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/dashboard/, { timeout: 15_000 });

  // Dashboard welcome card and the non-lawyer quick actions render
  await expect(page.getByText("Procesos activos")).toBeVisible({ timeout: 10_000 });
  await expect(page.getByText("Radicar Solicitud")).toBeVisible();
  await expect(page.getByText("Mis Procesos").first()).toBeVisible();

  // Verify role is basic in session
  const userAuth = await page.evaluate(() => JSON.parse(localStorage.getItem("userAuth") || "{}"));
  expect(userAuth.role).toBe("basic");
});

test("basic user sidebar does not show lawyer-only navigation items", { tag: ['@flow:basic-restrictions', '@module:auth', '@priority:P3', '@role:basic'] }, async ({ page }) => {
  const userId = 9501;

  await installBasicUserDashboardMocks(page, { userId });

  await setAuthLocalStorage(page, {
    token: "e2e-token",
    userAuth: { id: userId, role: "basic", is_gym_lawyer: false, is_profile_completed: true },
  });

  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/dashboard/, { timeout: 15_000 });

  // Positive anchors first: sidebar and quick actions rendered for basic user
  const sidebar = page.getByTestId("sidebar-nav");
  await expect(sidebar.getByText("Inicio", { exact: true })).toBeVisible({ timeout: 10_000 });
  await expect(page.getByText("Mis Procesos", { exact: true })).toBeVisible();

  // Lawyer-only quick action "Radicar Proceso" must NOT render for basic users
  await expect(page.getByText("Radicar Proceso")).toHaveCount(0);

  // "Directorio" is filtered out of the sidebar for basic users
  await expect(sidebar.getByText("Directorio", { exact: true })).toHaveCount(0);
});

test("basic user can see common navigation items like Procesos and Servicios", { tag: ['@flow:basic-restrictions', '@module:auth', '@priority:P3', '@role:basic'] }, async ({ page }) => {
  const userId = 9502;

  await installBasicUserDashboardMocks(page, { userId });

  await setAuthLocalStorage(page, {
    token: "e2e-token",
    userAuth: { id: userId, role: "basic", is_gym_lawyer: false, is_profile_completed: true },
  });

  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/dashboard/, { timeout: 15_000 });

  // Basic users keep the common nav items in the sidebar. Note: the legacy
  // "Solicitudes" entry was replaced by "Servicios y Solicitudes".
  const sidebar = page.getByTestId("sidebar-nav");
  await expect(sidebar.getByText("Procesos", { exact: true })).toBeVisible({ timeout: 10_000 });
  await expect(sidebar.getByText("Servicios y Solicitudes", { exact: true })).toBeVisible();
  await expect(sidebar.getByText("Organizaciones", { exact: true })).toBeVisible();
});
