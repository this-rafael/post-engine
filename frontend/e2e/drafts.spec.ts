import { test, expect } from "@playwright/test";

test("drafts stage tab exists in rail when reachable", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("rail-drafts")).toBeVisible();
});
