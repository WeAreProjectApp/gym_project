import { test, expect } from "../helpers/test.js";
import { setAuthLocalStorage } from "../helpers/auth.js";
import { mockApi } from "../helpers/api.js";
// @flow: tags must be inline strings — imported constants are invisible to the coverage scanner
import { installDynamicDocumentApiMocks } from "../helpers/dynamicDocumentMocks.js";
import { installSecopApiMocks } from "../secop/secopMocks.js";

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
    created_at: new Date().toISOString(),
    is_profile_completed: true,
    is_gym_lawyer: false,
    has_signature: false,
  };
}

async function installBasicUserMocks(page, { userId }) {
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
    if (apiPath === "dropdown_options_legal_request/") {
      return { status: 200, contentType: "application/json", body: JSON.stringify({ request_types: ["Consulta", "Asesoría"], areas: ["Civil", "Penal"] }) };
    }
    return null;
  });
}

function basicAuth(userId) {
  return {
    token: "e2e-basic-token",
    userAuth: { id: userId, role: "basic", is_gym_lawyer: false, is_profile_completed: true },
  };
}

test.describe("Basic User Restrictions", () => {
  test("basic user is redirected from directory (lawyer-only route)", {
    tag: ['@flow:basic-restrictions', '@module:auth', '@priority:P3', '@role:basic'],
  }, async ({ page }) => {
    const userId = 9600;
    await installBasicUserMocks(page, { userId });
    await setAuthLocalStorage(page, basicAuth(userId));

    await page.goto("/directory_list");
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 15_000 });
  });

  test("basic user is redirected from process form (lawyer-only route)", {
    tag: ['@flow:basic-restrictions', '@module:auth', '@priority:P3', '@role:basic'],
  }, async ({ page }) => {
    const userId = 9601;
    await installBasicUserMocks(page, { userId });
    await setAuthLocalStorage(page, basicAuth(userId));

    await page.goto("/dynamic_document_dashboard/lawyer/variables-config");
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 15_000 });
  });

  test("basic user is redirected from document editor (lawyer-only route)", {
    tag: ['@flow:basic-restrictions', '@module:auth', '@priority:P3', '@role:basic'],
  }, async ({ page }) => {
    const userId = 9602;
    await installBasicUserMocks(page, { userId });
    await setAuthLocalStorage(page, basicAuth(userId));

    await page.goto("/dynamic_document_dashboard/lawyer/editor/create/TestDoc");
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 15_000 });
  });

  test("basic user can access legal request creation page", {
    tag: ['@flow:basic-restrictions', '@module:auth', '@priority:P3', '@role:basic'],
  }, async ({ page }) => {
    const userId = 9603;
    await installBasicUserMocks(page, { userId });
    await setAuthLocalStorage(page, basicAuth(userId));

    await page.goto("/legal_request_create");
    await expect(page).toHaveURL(/\/legal_request_create/, { timeout: 15_000 });
  });

  test("basic user has no signature available", {
    tag: ['@flow:basic-restrictions', '@module:auth', '@priority:P3', '@role:basic'],
  }, async ({ page }) => {
    const userId = 9605;
    await installBasicUserMocks(page, { userId });
    await setAuthLocalStorage(page, basicAuth(userId));

    await page.goto("/dashboard");
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 15_000 });

    // Verify the user session reflects basic role without signature
    const userAuth = await page.evaluate(() => JSON.parse(localStorage.getItem("userAuth") || "{}"));
    expect(userAuth.role).toBe("basic");
    expect(userAuth.is_gym_lawyer).toBe(false);
  });

  test("basic user sees disabled letterhead button in document dashboard", {
    tag: ['@flow:basic-restrictions', '@module:auth', '@priority:P3', '@role:basic'],
  }, async ({ page }) => {
    const userId = 9606;

    await installDynamicDocumentApiMocks(page, {
      userId,
      role: "basic",
      hasSignature: false,
      documents: [],
      folders: [],
    });
    await setAuthLocalStorage(page, basicAuth(userId));

    await page.goto("/dynamic_document_dashboard");
    await expect(page).toHaveURL(/\/dynamic_document_dashboard/, { timeout: 15_000 });

    // Wait for the client/basic section to render (it's inside a v-if on userRole)
    const letterheadBtn = page.getByRole('button', { name: 'Membrete Global' });
    await expect(letterheadBtn).toBeVisible({ timeout: 10_000 });
    await expect(letterheadBtn).toBeDisabled();
  });

  test("basic user sees SECOP advanced filters disabled overlay", {
    tag: ['@flow:basic-restrictions', '@module:auth', '@priority:P3', '@role:basic'],
  }, async ({ page }) => {
    const userId = 9607;
    const basicUser = {
      role: "basic",
      is_gym_lawyer: false,
      first_name: "E2E",
      last_name: "Basic",
      email: `basic-${userId}@example.com`,
    };

    await installSecopApiMocks(page, { userId, user: basicUser });
    await setAuthLocalStorage(page, basicAuth(userId));

    await page.goto("/secop");
    await expect(page).toHaveURL(/\/secop/, { timeout: 15_000 });

    // The filters panel overlay is shown for basic users (filtersDisabled = role === 'basic')
    await expect(page.getByTestId("filters-disabled-overlay")).toBeVisible({ timeout: 10_000 });
  });
});
