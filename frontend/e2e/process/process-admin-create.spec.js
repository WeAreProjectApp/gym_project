import { test, expect } from "../helpers/test.js";
import { setAuthLocalStorage } from "../helpers/auth.js";
import { installProcessFormApiMocks, buildMockUser } from "../helpers/processFormMocks.js";

async function openAdminProcessForm(page) {
  const lawyer = buildMockUser({ id: 1500, role: "lawyer", firstName: "Laura", lastName: "Abogada" });
  const client = buildMockUser({ id: 1501, role: "client", firstName: "Client", lastName: "One" });
  const admin = buildMockUser({ id: 1502, role: "admin", firstName: "Admin", lastName: "Operaciones" });
  await installProcessFormApiMocks(page, { lawyer, client, currentUser: admin });
  await setAuthLocalStorage(page, { token: "e2e-token", userAuth: admin });
  await page.goto("/process_list");
  await page.getByRole("link", { name: "Nuevo proceso", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Información del proceso" })).toBeVisible();
  return { lawyer };
}

async function fillProcessFields(page) {
  await page.getByTestId("process-plaintiff").fill("Demandante");
  await page.getByTestId("process-defendant").fill("Demandado");
  await page.getByRole("button", { name: /Seleccionar/ }).click();
  await page.getByRole("option", { name: "Civil", exact: true }).click();
  await page.getByTestId("process-subcase").fill("Subcaso");
  await page.getByTestId("process-ref").fill("RAD-9002");
  await page.getByRole("textbox", { name: /^Autoridad/ }).fill("Juzgado 1");
  await page.getByPlaceholder("Buscar y agregar usuarios").fill("Client");
  await page.getByRole("option", { name: /One Client/i }).click();
  await page.locator('input[name="stage"]:visible').fill("Inicio");
  await page.locator("tbody input[type='file']:visible").setInputFiles({
    name: "case.pdf", mimeType: "application/pdf", buffer: Buffer.from("%PDF-1.4\n%PDF-MOCK\n"),
  });
}

for (const viewport of [{ width: 1440, height: 900 }, { width: 412, height: 915 }]) {
  test(`admin creates a process with the chosen lawyer at width ${viewport.width}`, {
    tag: ["@flow:process-create", "@module:processes", "@priority:P1", "@role:admin", "@outcome:success"],
  }, async ({ page }) => {
    await page.setViewportSize(viewport);
    const { lawyer } = await openAdminProcessForm(page);
    await expect(page.getByTestId("process-lawyer-input")).toHaveValue("");
    await fillProcessFields(page);
    await page.getByTestId("process-lawyer-input").fill("Laura");
    await page.getByTestId(`process-lawyer-option-${lawyer.id}`).click();
    const creation = page.waitForRequest(request => request.url().endsWith("/create_process/") && request.method() === "POST");

    await page.getByRole("button", { name: "Guardar Proceso", exact: true }).click();

    expect((await creation).postData()).toContain(`"lawyerId":${lawyer.id}`);
    await expect(page.getByRole("dialog")).toContainText("Exitoso");
    await page.getByRole("button", { name: "OK!", exact: true }).click();
    await expect(page).toHaveURL(/\/process_list/);
    await expect(page.getByRole("row", { name: /Client One.*Civil.*Demandante.*Demandado.*Inicio/ })).toBeVisible();
  });
}

test("admin cannot save without selecting a responsible lawyer", {
  tag: ["@flow:process-create", "@module:processes", "@priority:P1", "@role:admin", "@outcome:error"],
}, async ({ page }) => {
  await openAdminProcessForm(page);
  await fillProcessFields(page);
  const creationRequests = [];
  page.on("request", request => creationRequests.push(request.url()));

  await page.getByRole("button", { name: "Guardar Proceso", exact: true }).click();

  await expect(page.getByRole("dialog")).toContainText('El campo "Abogado" es obligatorio.');
  expect(creationRequests.filter(url => url.endsWith("/create_process/"))).toHaveLength(0);
  await expect(page).toHaveURL(/\/process_form\/create/);
});

test("admin receives an error when process creation fails", {
  tag: ["@flow:process-create", "@module:processes", "@priority:P1", "@role:admin", "@outcome:failure"],
}, async ({ page }) => {
  const { lawyer } = await openAdminProcessForm(page);
  await fillProcessFields(page);
  await page.getByTestId("process-lawyer-input").fill("Laura");
  await page.getByTestId(`process-lawyer-option-${lawyer.id}`).click();
  await page.route("**/api/create_process/", route => route.fulfill({
    status: 500, json: { detail: "No se pudo crear el proceso." },
  }));

  await page.getByRole("button", { name: "Guardar Proceso", exact: true }).click();

  await expect(page.getByRole("dialog")).toContainText("Oops...");
  await page.getByRole("button", { name: "OK", exact: true }).click();
  await expect(page).toHaveURL(/\/process_list/);
  await expect(page.getByRole("row", { name: /Demandante/ })).toHaveCount(0);
});
