import { test, expect } from "@playwright/test";

test("composition stage in pipeline", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("rail-composition")).toBeVisible();
  await expect(page.getByTestId("rail-segmentation")).toBeVisible();
});
