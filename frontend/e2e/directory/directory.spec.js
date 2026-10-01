import { test, expect } from "../helpers/test.js";

import { setAuthLocalStorage } from "../helpers/auth.js";
import {
  installDirectoryApiMocks,
  buildMockUser,
  buildMockProcess,
} from "../helpers/directoryMocks.js";
import { viewportUse } from "../helpers/viewports.js";

async function expectPhysicalTarget(locator) {
  await expect.poll(async () => (await locator.boundingBox())?.width ?? 0).toBeGreaterThanOrEqual(43.5);
  await expect.poll(async () => (await locator.boundingBox())?.height ?? 0).toBeGreaterThanOrEqual(43.5);
}

async function expectNoHorizontalOverflow(locator) {
  await expect(locator).toBeVisible();
  const dimensions = await locator.evaluate(async (element) => {
    await document.fonts.ready;
    return {
      scrollWidth: element.scrollWidth,
      clientWidth: element.clientWidth,
    };
  });
  expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth);
}

async function openDirectoryFromDesktopSidebar(page) {
  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/dashboard/);
  await page.getByTestId("sidebar-nav").getByRole("link", { name: "Directorio", exact: true }).click();
  await expect(page).toHaveURL(/\/directory_list/);
}

async function openDirectoryFromMobileSidebar(page) {
  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/dashboard/);
  await page.getByRole("button", { name: "Open sidebar" }).click();
  await page.getByRole("dialog").getByRole("link", { name: "Directorio", exact: true }).click();
  await expect(page).toHaveURL(/\/directory_list/);
}

async function installAndOpenDirectory(page, fixture, navigateToDirectory) {
  await installDirectoryApiMocks(page, {
    currentUserId: fixture.lawyer.id,
    users: [fixture.lawyer, fixture.client],
    processes: fixture.processes,
  });
  await setAuthLocalStorage(page, {
    token: "e2e-token",
    userAuth: {
      id: fixture.lawyer.id,
      role: "lawyer",
      is_gym_lawyer: true,
      is_profile_completed: true,
    },
  });
  await navigateToDirectory(page);
}

async function openUserDetails(page, user) {
  const search = page.getByRole("searchbox", { name: "Buscar" });
  const userLabel = `${user.first_name} ${user.last_name} (Cliente)`;
  await search.fill(user.first_name);
  const userEntry = page.getByRole("main").getByText(userLabel, { exact: true });
  await expect(userEntry).toHaveText(userLabel);
  await userEntry.click();
  await expect(page.getByRole("heading", { name: `${user.first_name} ${user.last_name}`, exact: true })).toHaveText(`${user.first_name} ${user.last_name}`);
}

function buildDirectoryFixture({ lawyerId = 1900, clientId = 1901 } = {}) {
  const lawyer = buildMockUser({
    id: lawyerId,
    role: "lawyer",
    firstName: "E2E",
    lastName: "Lawyer",
    email: "lawyer@example.com",
    identification: "LAW-1",
  });
  const client = buildMockUser({
    id: clientId,
    role: "client",
    firstName: "Ana",
    lastName: "Client",
    email: "ana@example.com",
    identification: "CLI-1",
  });
  const processes = [buildMockProcess({ id: 501, lawyerId, clientId })];

  return { lawyer, client, processes };
}

function buildLongDirectoryFixture() {
  const fixture = buildDirectoryFixture({ lawyerId: 4100, clientId: 4101 });
  fixture.client.first_name = "NombreExtraordinariamenteExtensoSinEspaciosParaProbarElAjuste";
  fixture.client.last_name = "ApellidoMuyLargoQueDebeMantenerseVisibleEnLaFicha";
  fixture.client.email = "correo.con.identificador.demasiado.extenso.para.truncar@directorio-e2e.example.com";
  fixture.processes[0].case.type = "TipoDeProcesoExtremadamenteLargoQueDebeAjustarseSinRecorte";
  fixture.processes[0].subcase = "DescripciónMuyLargaQueDebeConservarCadaPalabraVisibleDentroDelContenedorResponsivo";
  fixture.processes[0].ref = "RADICADO-EXTENSO-2026-PRUEBA-DE-AJUSTE-SIN-TRUNCAMIENTO";
  fixture.processes[0].authority = "AutoridadJurisdiccionalConNombreExtensoQueDebeAjustarse";

  return fixture;
}

// Catches the regression where directory search no longer filters users, the
// modal hides its data, or its accessible close action disappears.
test("directory list renders, can search, and shows user modal", {
  tag: ['@flow:directory-search', '@outcome:success', '@outcome:display', '@module:directory', '@priority:P2', '@role:lawyer'],
}, async ({ page }) => {
  const fixture = buildDirectoryFixture();
  const secondClient = buildMockUser({
    id: 1902,
    role: "client",
    firstName: "E2E",
    lastName: "Client",
    email: "second-client@example.com",
    identification: "CLI-2",
  });

  await installDirectoryApiMocks(page, {
    currentUserId: fixture.lawyer.id,
    users: [fixture.lawyer, fixture.client, secondClient],
    processes: [
      buildMockProcess({ id: 501, lawyerId: fixture.lawyer.id, clientId: fixture.client.id }),
      buildMockProcess({ id: 502, lawyerId: fixture.lawyer.id, clientId: fixture.client.id }),
    ],
  });
  await setAuthLocalStorage(page, {
    token: "e2e-token",
    userAuth: { id: fixture.lawyer.id, role: "lawyer", is_gym_lawyer: true, is_profile_completed: true },
  });
  await openDirectoryFromDesktopSidebar(page);

  const list = page.getByRole("main").getByRole("list");
  await expect(list.getByText("E2E Lawyer (Abogado)", { exact: true })).toHaveText("E2E Lawyer (Abogado)");
  await expect(list.getByText("Ana Client (Cliente)", { exact: true })).toHaveText("Ana Client (Cliente)");

  await page.getByRole("searchbox", { name: "Buscar" }).fill("ana");
  await expect(list.getByText("Ana Client (Cliente)", { exact: true })).toHaveText("Ana Client (Cliente)");
  await expect(list.getByText("E2E Lawyer (Abogado)", { exact: true })).toHaveCount(0);

  await list.getByText("Ana Client (Cliente)", { exact: true }).click();
  await expect(page.getByRole("heading", { name: "Ana Client", exact: true })).toHaveText("Ana Client");
  await expect(page.getByRole("heading", { name: "Información del usuario", exact: true })).toHaveText("Información del usuario");
  await expect(page.getByRole("heading", { name: "Procesos del usuario", exact: true })).toHaveText("Procesos del usuario");
  await expect(page.getByText("Se encontraron 2 proceso(s) asociados", { exact: true })).toHaveText("Se encontraron 2 proceso(s) asociados");

  await page.getByRole("button", { name: "Cerrar detalle de usuario" }).click();
  await expect(page.getByRole("heading", { name: "Ana Client", exact: true })).toHaveCount(0);
});

// Catches the regression where clearing the directory search leaves users hidden.
test("directory search clears when input is emptied", {
  tag: ['@flow:directory-search', '@outcome:success', '@module:directory', '@priority:P2', '@role:lawyer'],
}, async ({ page }) => {
  const lawyerId = 1910;
  const clientId = 1911;
  const users = [
    buildMockUser({ id: lawyerId, role: "lawyer", firstName: "Carlos", lastName: "Abogado", email: "carlos@example.com", identification: "LAW-10" }),
    buildMockUser({ id: clientId, role: "client", firstName: "María", lastName: "Cliente", email: "maria@example.com", identification: "CLI-10" }),
  ];

  await installDirectoryApiMocks(page, { currentUserId: lawyerId, users, processes: [] });
  await setAuthLocalStorage(page, {
    token: "e2e-token",
    userAuth: { id: lawyerId, role: "lawyer", is_gym_lawyer: true, is_profile_completed: true },
  });
  await page.goto("/directory_list");

  const list = page.getByRole("main").getByRole("list");
  await expect(list.getByText("Carlos Abogado (Abogado)", { exact: true })).toHaveText("Carlos Abogado (Abogado)");
  await expect(list.getByText("María Cliente (Cliente)", { exact: true })).toHaveText("María Cliente (Cliente)");

  const search = page.getByRole("searchbox", { name: "Buscar" });
  await search.fill("María");
  await expect(list.getByText("María Cliente (Cliente)", { exact: true })).toHaveText("María Cliente (Cliente)");
  await expect(list.getByText("Carlos Abogado (Abogado)", { exact: true })).toHaveCount(0);

  await search.clear();
  await expect(list.getByText("Carlos Abogado (Abogado)", { exact: true })).toHaveText("Carlos Abogado (Abogado)");
  await expect(list.getByText("María Cliente (Cliente)", { exact: true })).toHaveText("María Cliente (Cliente)");
});

// Catches the regression where either directory process action no longer reaches
// its destination after a user opens the details modal.
test("user modal navigates to a process detail and to the full process list", {
  tag: ['@flow:directory-navigate-to-process', '@outcome:success', '@outcome:display', '@module:directory', '@priority:P4', '@role:lawyer'],
}, async ({ page }) => {
  const fixture = buildDirectoryFixture();
  await installAndOpenDirectory(page, fixture, openDirectoryFromDesktopSidebar);
  await openUserDetails(page, fixture.client);

  await page.getByRole("button", { name: "Ver proceso" }).click();
  await expect(page).toHaveURL(/\/process_detail\/501/);

  await openDirectoryFromDesktopSidebar(page);
  await openUserDetails(page, fixture.client);
  await page.getByRole("button", { name: "Ver todos en Procesos" }).click();
  await expect(page).toHaveURL(new RegExp(`/process_list/${fixture.client.id}`));
});

const standardViewportNavigation = {
  compact: openDirectoryFromMobileSidebar,
  portrait: openDirectoryFromMobileSidebar,
  landscape: openDirectoryFromDesktopSidebar,
  desktop: openDirectoryFromDesktopSidebar,
  wide: openDirectoryFromDesktopSidebar,
};

for (const viewport of ['compact', 'portrait', 'landscape', 'desktop', 'wide']) {
  test.describe(`directory detail at ${viewport}`, () => {
    test.use(viewportUse(viewport));

    // I-R-95087cafa8da catches the regression where long detail values are
    // truncated or widen the page beyond the standard viewport.
    test(`shows complete long directory details without horizontal overflow at ${viewport}`, {
      tag: ['@flow:directory-search', '@outcome:display', '@module:directory', '@priority:P2', '@role:lawyer', `@viewport:${viewport}`],
    }, async ({ page }) => {
      const fixture = buildLongDirectoryFixture();
      await installAndOpenDirectory(page, fixture, standardViewportNavigation[viewport]);
      await openUserDetails(page, fixture.client);

      const fullName = `${fixture.client.first_name} ${fixture.client.last_name}`;
      const process = fixture.processes[0];
      const name = page.getByRole("heading", { name: fullName, exact: true });
      const email = page.getByRole("definition").filter({ hasText: fixture.client.email });
      const processType = page.getByRole("heading", { name: process.case.type, exact: true });
      const description = page.getByText(process.subcase, { exact: true });
      const reference = page.getByText(process.ref, { exact: true });
      const authority = page.getByText(process.authority, { exact: true });
      const caseMetadata = reference.locator("..");

      await expect(name).toHaveText(fullName);
      await expect(email).toHaveText(fixture.client.email);
      await expect(processType).toHaveText(process.case.type);
      await expect(description).toHaveText(process.subcase);
      await expect(reference).toHaveText(process.ref);
      await expect(authority).toHaveText(process.authority);

      await expectNoHorizontalOverflow(name);
      await expectNoHorizontalOverflow(email);
      await expectNoHorizontalOverflow(processType);
      await expectNoHorizontalOverflow(description);
      await expectNoHorizontalOverflow(caseMetadata);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    });
  });
}

for (const viewport of ['compact', 'portrait']) {
  test.describe(`directory detail controls at ${viewport}`, () => {
    test.use(viewportUse(viewport));

    // I-R-f6f4bc737914 catches the regression where the global zoom makes the
    // modal close target too small or the accessible close action fails.
    test(`closes the directory detail with a physical target at ${viewport}`, {
      tag: ['@flow:directory-search', '@outcome:display', '@module:directory', '@priority:P2', '@role:lawyer', `@viewport:${viewport}`],
    }, async ({ page }) => {
      const fixture = buildDirectoryFixture({ lawyerId: 5000, clientId: 5001 });
      await installAndOpenDirectory(page, fixture, standardViewportNavigation[viewport]);
      await openUserDetails(page, fixture.client);

      const close = page.getByRole("button", { name: "Cerrar detalle de usuario" });
      await expectPhysicalTarget(close);
      await close.click();
      await expect(page.getByRole("heading", { name: "Ana Client", exact: true })).toHaveCount(0);
      await expect(page.getByRole("main").getByText("Ana Client (Cliente)", { exact: true })).toHaveText("Ana Client (Cliente)");
    });

    // I-R-f6f4bc737914 catches the regression where the compact process-detail
    // target is too small to use or no longer routes to its process.
    test(`opens the process detail with a physical target at ${viewport}`, {
      tag: ['@flow:directory-navigate-to-process', '@outcome:display', '@module:directory', '@priority:P4', '@role:lawyer', `@viewport:${viewport}`],
    }, async ({ page }) => {
      const fixture = buildDirectoryFixture({ lawyerId: 5100, clientId: 5101 });
      await installAndOpenDirectory(page, fixture, standardViewportNavigation[viewport]);
      await openUserDetails(page, fixture.client);

      const processDetail = page.getByRole("button", { name: "Ver proceso" });
      await expectPhysicalTarget(processDetail);
      await processDetail.click();
      await expect(page).toHaveURL(/\/process_detail\/501/);
    });

    // I-R-f6f4bc737914 catches the regression where the compact user-process
    // list target is too small to use or drops the selected user from its route.
    test(`opens the user's process list with a physical target at ${viewport}`, {
      tag: ['@flow:directory-navigate-to-process', '@outcome:display', '@module:directory', '@priority:P4', '@role:lawyer', `@viewport:${viewport}`],
    }, async ({ page }) => {
      const fixture = buildDirectoryFixture({ lawyerId: 5200, clientId: 5201 });
      await installAndOpenDirectory(page, fixture, standardViewportNavigation[viewport]);
      await openUserDetails(page, fixture.client);

      const processList = page.getByRole("button", { name: "Ver todos en Procesos" });
      await expectPhysicalTarget(processList);
      await processList.click();
      await expect(page).toHaveURL(new RegExp(`/process_list/${fixture.client.id}`));
    });
  });
}
