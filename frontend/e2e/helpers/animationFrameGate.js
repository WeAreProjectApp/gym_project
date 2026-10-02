// Control only the browser's Date.now clock. Native animation frames and timers
// stay active so sidebar transitions retain their real browser behavior.
export async function freezeAnimationClock(page) {
  await page.addInitScript(() => {
    let currentTime = Date.now();
    Date.now = () => currentTime;
    window.__e2eAdvanceAnimationClock = (milliseconds) => {
      currentTime += milliseconds;
    };
  });
}

export async function showInstallationAlert(page) {
  // Small clock steps preserve the animation's ordinary lag-smoothing rules.
  await page.evaluate(async () => {
    for (const milliseconds of [250, 250, 250, 250, 100]) {
      window.__e2eAdvanceAnimationClock(milliseconds);
      await new Promise((resolve) => requestAnimationFrame(resolve));
    }
  });
}
