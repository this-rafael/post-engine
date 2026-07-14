import { test, expect } from "@playwright/test";

test("pipeline rail shows storyboard stage", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("rail-storyboard")).toBeVisible();
  await expect(page.getByTestId("rail-composition")).toBeVisible();
  await expect(page.getByTestId("rail-prompt")).toHaveCount(0);
});
