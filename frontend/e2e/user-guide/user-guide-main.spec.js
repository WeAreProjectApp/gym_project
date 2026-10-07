import { test, expect } from "../helpers/test.js";
import { setAuthLocalStorage } from "../helpers/auth.js";
import { mockApi } from "../helpers/api.js";

/**
 * E2E tests for the user guide (UserGuideMain.vue + components).
 *
 * The manual is a client-side wizard: the sidebar picks a module, the module
 * overview lists its sections, a section renders its steps/example, and the
 * search box jumps straight to a section. Every test below drives one of those
 * transitions instead of asserting the landing screen.
 */

function buildMockUser({ id, role }) {
  return {
    id,
    first_name: "E2E",
    last_name: role === "lawyer" ? "Lawyer" : "Client",
    email: "e2e@example.com",
    role,
    is_profile_completed: true,
    is_gym_lawyer: role === "lawyer",
  };
}

async function installUserGuideMocks(page, { userId, role }) {
  const user = buildMockUser({ id: userId, role });

  await mockApi(page, async ({ route, apiPath }) => {
    if (apiPath === "validate_token/") return { status: 200, contentType: "application/json", body: "{}" };
    if (apiPath === "users/") return { status: 200, contentType: "application/json", body: JSON.stringify([user]) };
    if (apiPath === `users/${userId}/`) return { status: 200, contentType: "application/json", body: JSON.stringify(user) };
    if (apiPath === `users/${userId}/signature/`) return { status: 200, contentType: "application/json", body: JSON.stringify({ has_signature: false }) };

    // Standard endpoints
    if (apiPath === "google-captcha/site-key/") return { status: 200, contentType: "application/json", body: JSON.stringify({ site_key: "e2e-site-key" }) };

    return null;
  });
}

async function openGuide(page, { userId, role }) {
  await installUserGuideMocks(page, { userId, role });

  await setAuthLocalStorage(page, {
    token: "e2e-token",
    userAuth: {
      id: userId,
      role,
      is_gym_lawyer: role === "lawyer",
      is_profile_completed: true,
    },
  });

  await page.goto("/user_guide");
  await expect(page.getByRole("heading", { name: "Bienvenido al Manual de Usuario" })).toBeVisible({ timeout: 15_000 });
}

test.describe("user guide: main page", { tag: ['@flow:user-guide-navigation', '@module:user-guide', '@priority:P3', '@role:shared'] }, () => {
  test("lawyer opens the Directorio module from the sidebar", { tag: ['@flow:user-guide-navigation', '@module:user-guide', '@priority:P3', '@role:shared'] }, async ({ page }) => {
    await openGuide(page, { userId: 6000, role: "lawyer" });

    const sidebar = page.locator("aside");
    await sidebar.getByRole("button", { name: "Directorio", exact: true }).click();

    // The welcome screen is replaced by the module content
    await expect(page.getByRole("heading", { name: "Directorio", exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Bienvenido al Manual de Usuario" })).toBeHidden();
  });

  test("client opens the Procesos module from the sidebar", { tag: ['@flow:user-guide-navigation', '@module:user-guide', '@priority:P3', '@role:shared'] }, async ({ page }) => {
    await openGuide(page, { userId: 6001, role: "client" });

    const sidebar = page.locator("aside");
    await sidebar.getByRole("button", { name: "Procesos", exact: true }).click();

    await expect(page.getByRole("heading", { name: "Procesos", exact: true })).toBeVisible();
    await expect(page.getByText("Gestión y consulta de procesos judiciales")).toBeVisible();
  });

  test("client sidebar omits the lawyer-only Directorio module", { tag: ['@flow:user-guide-navigation', '@module:user-guide', '@priority:P3', '@role:shared'] }, async ({ page }) => {
    await openGuide(page, { userId: 6002, role: "client" });

    const sidebar = page.locator("aside");
    await sidebar.getByRole("button", { name: "Procesos", exact: true }).click();

    // Selecting a module never reveals modules outside the role's catalogue
    await expect(sidebar.getByRole("button", { name: "Directorio", exact: true })).toHaveCount(0);
    await expect(sidebar.getByRole("button", { name: "Organizaciones", exact: true })).toBeVisible();
  });
});

test.describe("user guide: navigation component", { tag: ['@flow:user-guide-navigation', '@module:user-guide', '@priority:P3', '@role:shared'] }, () => {
  test("user can navigate between guide sections", { tag: ['@flow:user-guide-navigation', '@module:user-guide', '@priority:P3', '@role:shared'] }, async ({ page }) => {
    await openGuide(page, { userId: 6010, role: "lawyer" });

    const sidebar = page.locator("aside");
    await sidebar.getByRole("button", { name: "Procesos", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Procesos", exact: true })).toBeVisible();

    // Switching module swaps the whole content pane
    await sidebar.getByRole("button", { name: "Archivos Jurídicos", exact: true }).click();

    await expect(page.getByRole("heading", { name: "Archivos Jurídicos", exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Procesos", exact: true })).toBeHidden();
  });

  test("navigation highlights current section", { tag: ['@flow:user-guide-navigation', '@module:user-guide', '@priority:P3', '@role:shared'] }, async ({ page }) => {
    await openGuide(page, { userId: 6011, role: "lawyer" });

    const sidebar = page.locator("aside");
    const procesos = sidebar.getByRole("button", { name: "Procesos", exact: true });
    const directorio = sidebar.getByRole("button", { name: "Directorio", exact: true });

    await procesos.click();
    await expect(procesos).toHaveAttribute("aria-current", "true");
    await expect(directorio).toHaveAttribute("aria-current", "false");

    await directorio.click();
    await expect(directorio).toHaveAttribute("aria-current", "true");
    await expect(procesos).toHaveAttribute("aria-current", "false");
  });
});

test.describe("user guide: search component", { tag: ['@flow:user-guide-navigation', '@module:user-guide', '@priority:P3', '@role:shared'] }, () => {
  test("user guide has search functionality", { tag: ['@flow:user-guide-navigation', '@module:user-guide', '@priority:P3', '@role:shared'] }, async ({ page }) => {
    const userId = 6020;

    await installUserGuideMocks(page, { userId, role: "lawyer" });

    await setAuthLocalStorage(page, {
      token: "e2e-token",
      userAuth: { id: userId, role: "lawyer", is_gym_lawyer: true, is_profile_completed: true },
    });

    await page.goto("/user_guide");

    // Typing 3+ characters triggers the guide search and opens the results dropdown
    const searchInput = page.getByPlaceholder("Buscar en el manual...");
    await expect(searchInput).toBeVisible({ timeout: 10_000 });
    await searchInput.fill("documento");

    await expect(page.getByText(/resultado\(s\) encontrado\(s\)/)).toBeVisible({ timeout: 5_000 });
  });

  test("search filters guide content", { tag: ['@flow:user-guide-navigation', '@module:user-guide', '@priority:P3', '@role:shared'] }, async ({ page }) => {
    const userId = 6021;

    await installUserGuideMocks(page, { userId, role: "lawyer" });

    await setAuthLocalStorage(page, {
      token: "e2e-token",
      userAuth: { id: userId, role: "lawyer", is_gym_lawyer: true, is_profile_completed: true },
    });

    await page.goto("/user_guide");

    const searchInput = page.getByPlaceholder("Buscar en el manual...");
    await expect(searchInput).toBeVisible({ timeout: 10_000 });

    // Searching shows the results dropdown
    await searchInput.fill("proceso");
    await expect(page.getByText(/resultado\(s\) encontrado\(s\)/)).toBeVisible({ timeout: 5_000 });

    // Clearing the input (below the 3-char threshold) closes the dropdown
    await searchInput.clear();
    await expect(page.getByText(/resultado\(s\) encontrado\(s\)/)).toBeHidden();
  });
});

test.describe("user guide: module guide component", { tag: ['@flow:user-guide-navigation', '@module:user-guide', '@priority:P3', '@role:shared'] }, () => {
  test("module guide displays content sections", { tag: ['@flow:user-guide-navigation', '@module:user-guide', '@priority:P3', '@role:shared'] }, async ({ page }) => {
    await openGuide(page, { userId: 6030, role: "lawyer" });

    const sidebar = page.locator("aside");
    await sidebar.getByRole("button", { name: "Procesos", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Secciones Disponibles:" })).toBeVisible();

    // Opening a section card swaps the overview for the section detail
    await page.getByRole("button", { name: "Filtros y Búsqueda" }).click();

    await expect(page.getByRole("heading", { name: "Filtros y Búsqueda" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Paso a Paso:" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Secciones Disponibles:" })).toBeHidden();
  });

  test("back button returns from a section to the module overview", { tag: ['@flow:user-guide-navigation', '@module:user-guide', '@priority:P3', '@role:shared'] }, async ({ page }) => {
    await openGuide(page, { userId: 6031, role: "lawyer" });

    const sidebar = page.locator("aside");
    await sidebar.getByRole("button", { name: "Procesos", exact: true }).click();
    await page.getByRole("button", { name: "Filtros y Búsqueda" }).click();
    await expect(page.getByRole("heading", { name: "Filtros y Búsqueda" })).toBeVisible();

    await page.getByRole("button", { name: "Volver al módulo" }).click();

    await expect(page.getByRole("heading", { name: "Secciones Disponibles:" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Volver al módulo" })).toBeHidden();
    await expect(page.getByRole("heading", { name: "Paso a Paso:" })).toBeHidden();
  });
});

test.describe("user guide: example modal component", { tag: ['@flow:user-guide-navigation', '@module:user-guide', '@priority:P3', '@role:shared'] }, () => {
  test("user can view examples in modal", { tag: ['@flow:user-guide-navigation', '@module:user-guide', '@priority:P3', '@role:shared'] }, async ({ page }) => {
    const userId = 6040;

    await installUserGuideMocks(page, { userId, role: "lawyer" });

    await setAuthLocalStorage(page, {
      token: "e2e-token",
      userAuth: { id: userId, role: "lawyer", is_gym_lawyer: true, is_profile_completed: true },
    });

    await page.goto("/user_guide");

    // Navigate: sidebar module "Procesos" → section card in the module overview
    const sidebar = page.locator("aside");
    await expect(sidebar.getByRole("button", { name: "Procesos", exact: true })).toBeVisible({ timeout: 10_000 });
    await sidebar.getByRole("button", { name: "Procesos", exact: true }).click();
    await page.getByRole("button", { name: "Radicar Proceso (Solo Abogados)" }).click();

    // The section exposes the example trigger
    await page.getByRole("button", { name: "Ver Ejemplo Completo" }).click();

    // ExampleModal opens with the example content
    await expect(page.getByRole("heading", { name: "Ejemplo: Radicar un Proceso de Tutela" })).toBeVisible({ timeout: 5_000 });
    await expect(page.getByText("Paso a paso para crear un nuevo proceso de tutela en el sistema.")).toBeVisible();

    // Closing the modal removes the example content
    await page.getByRole("button", { name: "Entendido" }).click();
    await expect(page.getByRole("heading", { name: "Ejemplo: Radicar un Proceso de Tutela" })).toBeHidden();
  });
});

test.describe("user guide: role info card component", { tag: ['@flow:user-guide-navigation', '@module:user-guide', '@priority:P3', '@role:shared'] }, () => {
  test("selecting a search result opens the matching module section", { tag: ['@flow:user-guide-navigation', '@module:user-guide', '@priority:P3', '@role:shared'] }, async ({ page }) => {
    await openGuide(page, { userId: 6050, role: "lawyer" });

    // The welcome screen introduces the role before the user searches
    await expect(page.getByText("10 módulos disponibles")).toBeVisible();

    const searchInput = page.getByPlaceholder("Buscar en el manual...");
    await searchInput.fill("Alertas Personalizadas");
    await page.getByRole("button", { name: /Alertas Personalizadas/ }).first().click();

    // The picked result navigates straight into the SECOP section
    await expect(page.getByRole("heading", { name: "Alertas Personalizadas" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Volver al módulo" })).toBeVisible();
    await expect(page.getByText("10 módulos disponibles")).toBeHidden();
  });
});

test.describe("user guide: quick links card component", { tag: ['@flow:user-guide-navigation', '@module:user-guide', '@priority:P3', '@role:shared'] }, () => {
  test("quick links provide shortcuts", { tag: ['@flow:user-guide-navigation', '@module:user-guide', '@priority:P3', '@role:shared'] }, async ({ page }) => {
    await openGuide(page, { userId: 6060, role: "lawyer" });

    const quickLinks = page.getByRole("heading", { name: "Enlaces Rápidos" }).locator("..");
    await quickLinks.getByRole("button", { name: "Directorio" }).click();

    // The shortcut opens the module without touching the sidebar
    await expect(page.getByRole("heading", { name: "Directorio", exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Enlaces Rápidos" })).toBeHidden();
  });
});

test.describe("user guide: SECOP module", { tag: ['@flow:user-guide-navigation', '@module:user-guide', '@priority:P3', '@role:shared'] }, () => {
  test("lawyer opens the SECOP module from navigation", { tag: ['@flow:user-guide-navigation', '@module:user-guide', '@priority:P3', '@role:shared'] }, async ({ page }) => {
    await openGuide(page, { userId: 6070, role: "lawyer" });

    const sidebar = page.locator("aside");
    await sidebar.getByRole("button", { name: "SECOP — Contratación Estatal" }).click();

    await expect(page.getByRole("heading", { name: "SECOP — Contratación Estatal" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Pestañas de SECOP" })).toBeVisible();
  });

  test("basic role opens the SECOP module and sees its plan restriction", { tag: ['@flow:user-guide-navigation', '@module:user-guide', '@priority:P3', '@role:shared'] }, async ({ page }) => {
    await openGuide(page, { userId: 6071, role: "basic" });

    const sidebar = page.locator("aside");
    await sidebar.getByRole("button", { name: "SECOP — Contratación Estatal" }).click();
    await page.getByRole("button", { name: "Pestañas de SECOP" }).click();

    await expect(page.getByRole("heading", { name: "Restricciones:" })).toBeVisible();
    await expect(page.getByText(/El rol básico ve el módulo con un overlay/)).toBeVisible();
  });

  test("search surfaces SECOP content for UNSPSC query", { tag: ['@flow:user-guide-navigation', '@module:user-guide', '@priority:P3', '@role:shared'] }, async ({ page }) => {
    const userId = 6072;

    await installUserGuideMocks(page, { userId, role: "lawyer" });

    await setAuthLocalStorage(page, {
      token: "e2e-token",
      userAuth: { id: userId, role: "lawyer", is_gym_lawyer: true, is_profile_completed: true },
    });

    await page.goto("/user_guide");
    await page.waitForLoadState("domcontentloaded");

    const searchInput = page.getByPlaceholder(/buscar|search/i).first();
    await expect(searchInput).toBeVisible({ timeout: 10000 });
    await searchInput.fill("UNSPSC");
    await expect(page.getByText(/SECOP/i).first()).toBeVisible({ timeout: 5000 });
  });
});

test.describe("user guide: Servicios y Trámites module", { tag: ['@flow:user-guide-navigation', '@module:user-guide', '@priority:P3', '@role:shared'] }, () => {
  test("client opens the Servicios y Trámites module from navigation", { tag: ['@flow:user-guide-navigation', '@module:user-guide', '@priority:P3', '@role:shared'] }, async ({ page }) => {
    await openGuide(page, { userId: 6080, role: "client" });

    const sidebar = page.locator("aside");
    await sidebar.getByRole("button", { name: "Servicios y Trámites" }).click();

    await expect(page.getByRole("heading", { name: "Servicios y Trámites" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Catálogo de Servicios" })).toBeVisible();
  });

  test("lawyer opens the Servicios inbox section reserved for lawyers", { tag: ['@flow:user-guide-navigation', '@module:user-guide', '@priority:P3', '@role:shared'] }, async ({ page }) => {
    await openGuide(page, { userId: 6081, role: "lawyer" });

    const sidebar = page.locator("aside");
    await sidebar.getByRole("button", { name: "Servicios y Trámites" }).click();
    await page.getByRole("button", { name: "Bandeja de Solicitudes (Abogados)" }).click();

    await expect(page.getByRole("heading", { name: "Bandeja de Solicitudes (Abogados)" })).toBeVisible();
    await expect(page.getByText("Gestionar las solicitudes recibidas")).toBeVisible();
  });

  test("search surfaces Servicios content for radicado query", { tag: ['@flow:user-guide-navigation', '@module:user-guide', '@priority:P3', '@role:shared'] }, async ({ page }) => {
    const userId = 6082;

    await installUserGuideMocks(page, { userId, role: "client" });

    await setAuthLocalStorage(page, {
      token: "e2e-token",
      userAuth: { id: userId, role: "client", is_profile_completed: true },
    });

    await page.goto("/user_guide");
    await page.waitForLoadState("domcontentloaded");

    const searchInput = page.getByPlaceholder(/buscar|search/i).first();
    await expect(searchInput).toBeVisible({ timeout: 10000 });
    await searchInput.fill("radicado");
    await expect(page.getByText(/Servicios/i).first()).toBeVisible({ timeout: 5000 });
  });
});
