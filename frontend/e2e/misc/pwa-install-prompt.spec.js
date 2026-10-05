import { test, expect } from "../helpers/test.js";
import { setAuthLocalStorage } from "../helpers/auth.js";
import { installDashboardNavApiMocks } from "../helpers/dashboardNavMocks.js";
import { viewportUse } from "../helpers/viewports.js";
import { freezeAnimationClock, showInstallationAlert } from "../helpers/animationFrameGate.js";

// These tests catch disabled alert actions, the wrong install path, or a banner
// incorrectly displayed to a user who already installed the application.
async function installDashMocks(page, { userId, role = "lawyer", installed = false }) {
  await freezeAnimationClock(page);
  await installDashboardNavApiMocks(page, { userId, role, isGymLawyer: role === "lawyer" });
  await setAuthLocalStorage(page, {
    token: "e2e-token",
    userAuth: { id: userId, role, is_gym_lawyer: role === "lawyer", is_profile_completed: true },
  });
  await page.addInitScript((wasInstalled) => {
    if (wasInstalled) {
      localStorage.setItem("pwa-installed", "true");
    } else {
      localStorage.removeItem("pwa-installed");
    }
  }, installed);
}

for (const alias of ["portrait", "compact", "landscape", "desktop", "wide"]) {
  test.describe(`PWA alert fallback (${alias})`, () => {
    test.use(viewportUse(alias));

    test("alert action opens manual installation instructions", {
      tag: ['@flow:misc-pwa-install', '@module:misc', '@priority:P4', '@role:shared', '@outcome:success'],
    }, async ({ page }) => {
      // quality: allow-duplicate (per-viewport contract: misc-pwa-install at the shared viewport matrix)
      await installDashMocks(page, { userId: 3300 });
      await page.goto("/dashboard");
      await expect(page.getByTestId("pwa-install-alert")).toHaveCount(1);
      await showInstallationAlert(page);
      await expect(page.getByTestId("pwa-install-alert")).toHaveCSS("opacity", "1");

      await page.getByTestId("pwa-install-alert-button").click();

      await expect(page.getByRole("heading", { name: "Instalar Aplicación", exact: true }))
        .toHaveText("Instalar Aplicación");
      await expect(page.getByText("Para instalar la aplicación en tu dispositivo, sigue estos pasos:"))
        .toBeVisible();
    });
  });
}

test.describe("PWA Install - manual instructions fallback", { tag: ['@flow:misc-pwa-install', '@module:misc', '@priority:P4', '@role:shared'] }, () => {
  test("client closes the install instructions modal", { tag: ['@flow:misc-pwa-install', '@module:misc', '@priority:P4', '@role:shared'] }, async ({ page }) => {
    await installDashMocks(page, { userId: 3301, role: "client" });
    await page.goto("/dashboard");

    const installEntry = page.getByTestId("pwa-install-button");
    await expect(installEntry).toBeVisible({ timeout: 15_000 });
    await installEntry.click();

    const instructionsTitle = page.getByRole("heading", { name: "Instalar Aplicación" });
    await expect(instructionsTitle).toBeVisible({ timeout: 10_000 });

    await page.getByRole("button", { name: "Cerrar" }).click();

    await expect(instructionsTitle).toBeHidden({ timeout: 10_000 });
  });
});

test.describe("PWA Install - native browser prompt", { tag: ['@flow:misc-pwa-install', '@module:misc', '@priority:P4', '@role:shared'] }, () => {
  test("alert action triggers the deferred native installation prompt", { tag: ['@flow:misc-pwa-install', '@module:misc', '@priority:P4', '@role:shared', '@outcome:success'] }, async ({ page }) => {
    await installDashMocks(page, { userId: 3310 });
    await page.goto("/dashboard");

    const installEntry = page.getByTestId("pwa-install-alert-button");
    await expect(page.getByTestId("pwa-install-alert")).toHaveCount(1);
    await showInstallationAlert(page);
    await expect(page.getByTestId("pwa-install-alert")).toHaveCSS("opacity", "1");

    // Replay the browser event the composable listens for at module load.
    await page.evaluate(() => {
      window.__e2eNativePromptCalled = false;
      const deferred = new Event("beforeinstallprompt");
      deferred.prompt = () => {
        window.__e2eNativePromptCalled = true;
      };
      deferred.userChoice = Promise.resolve({ outcome: "dismissed" });
      window.dispatchEvent(deferred);
    });

    await installEntry.click();

    await expect
      .poll(() => page.evaluate(() => window.__e2eNativePromptCalled), { timeout: 10_000 })
      .toBe(true);
    await expect(page.getByRole("heading", { name: "Instalar Aplicación" })).toBeHidden();
  });
});

// Catches a stale installation banner obstructing an already-installed session.
test("installed session omits the first-visit installation banner", {
  tag: ['@flow:misc-pwa-install', '@module:misc', '@priority:P4', '@role:shared', '@outcome:display'],
}, async ({ page }) => {
  await installDashMocks(page, { userId: 3320, installed: true });
  await page.goto("/dashboard");

  await page.getByRole("link", { name: "Procesos", exact: true }).click();

  await expect(page).toHaveURL(/\/process_list$/);
  await expect(page.getByTestId("pwa-install-alert")).toHaveCount(0);
});
