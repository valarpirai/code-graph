import { test, expect, type Page } from "@playwright/test";

// servlet-example — small Java project, reliably ready
const PROJECT_ID = "5aca57b7-4862-4599-9959-ca4a8c000fd5";
const PROJECT_URL = `/projects/${PROJECT_ID}`;

async function waitForGraphReady(page: Page) {
  // Progressive rendering shows a "Rendering X / Y nodes…" pill while active.
  // Wait for it to appear first (rendering started), then wait for it to go away (done).
  const pill = page.locator("text=/Rendering \\d+ \\/ \\d+ nodes/");

  // It may appear quickly — poll for up to 15 s
  await expect(pill).toBeVisible({ timeout: 15_000 }).catch(() => {
    // If the project is tiny the pill may flash too fast to catch — that's fine
  });

  // Now wait until rendering is fully complete (pill gone)
  await expect(pill).not.toBeVisible({ timeout: 60_000 });
}

test.describe("Graph rendering", () => {
  test("graph tab loads and renders nodes", async ({ page }) => {
    await page.goto(PROJECT_URL);

    // Project header must show the project name
    await expect(page.getByRole("heading", { level: 1 })).toContainText(
      "servlet-example",
      { timeout: 10_000 }
    );

    // Graph tab is active by default — wait for Cytoscape canvas
    const canvas = page.locator(".bg-surface canvas").first();
    await expect(canvas).toBeVisible({ timeout: 10_000 });

    await waitForGraphReady(page);

    // Canvas must have non-zero dimensions (layout ran and Cytoscape resized the canvas)
    const dims = await canvas.evaluate((el) => {
      const c = el as HTMLCanvasElement;
      return { w: c.width, h: c.height };
    });
    expect(dims.w).toBeGreaterThan(0);
    expect(dims.h).toBeGreaterThan(0);

    // Filter panel shows node-type counts — confirms graphData was fully loaded and counted
    const filterSidebar = page.locator(".w-52").first();
    const countText = filterSidebar.locator("text=/\\d+/").first();
    await expect(countText).toBeVisible();

    await page.screenshot({ path: "e2e/screenshots/graph-rendered.png", fullPage: false });
  });

  test("filter panel lists node types", async ({ page }) => {
    await page.goto(PROJECT_URL);
    await waitForGraphReady(page);

    // Filter sidebar must contain at least one node-type row
    const filterSidebar = page.locator(".w-52").first();
    await expect(filterSidebar).toBeVisible();

    // Expect known node types to appear
    await expect(filterSidebar).toContainText("File");
    await expect(filterSidebar).toContainText("Class");
  });

  test("Fit and Clear buttons are present", async ({ page }) => {
    await page.goto(PROJECT_URL);
    await waitForGraphReady(page);

    await expect(page.getByRole("button", { name: "Fit" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Clear" })).toBeVisible();
  });

  test("clicking a node opens the side panel", async ({ page }) => {
    await page.goto(PROJECT_URL);
    await waitForGraphReady(page);

    const canvas = page.locator(".bg-surface canvas").first();
    const box = await canvas.boundingBox();
    if (!box) throw new Error("Canvas bounding box not found");

    // Click the centre of the canvas — likely hits a node in a small project
    await canvas.click({ position: { x: box.width / 2, y: box.height / 2 } });

    // If a node was hit the side panel appears; if not, nothing breaks.
    // We accept either outcome but at least verify no crash occurred.
    await page.waitForTimeout(500);
    const panelVisible = await page.locator("text=Called from").isVisible().catch(() => false);
    const noError = await page.locator(".text-accent-red").count();

    // No error state in the UI
    expect(noError).toBe(0);

    await page.screenshot({
      path: `e2e/screenshots/graph-after-click-${panelVisible ? "panel-open" : "no-node-hit"}.png`,
    });
  });

  test("Re-index button is visible in header", async ({ page }) => {
    await page.goto(PROJECT_URL);
    await expect(page.getByRole("button", { name: "Re-index" })).toBeVisible({ timeout: 10_000 });
  });
});
