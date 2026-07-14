import { test, expect } from "@playwright/test";

test("editorial pipeline rail order", async ({ page }) => {
  await page.goto("/");
  const rail = page.locator("nav");
  await expect(rail.getByText("Storyboard")).toBeVisible();
  await expect(rail.getByText("Rascunhos")).toBeVisible();
  await expect(rail.getByText("Composição")).toBeVisible();
  await expect(rail.getByText("Segmentação")).toBeVisible();
});
