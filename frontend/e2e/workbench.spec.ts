import { test, expect } from "@playwright/test";
const password = "DemoOnly!2026";
async function login(page: any) {
  await page.goto("/");
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in to workspace" }).click();
  await expect(
    page.getByRole("heading", { name: "Control tower", exact: false }),
  ).toBeVisible();
}
test("connected control tower, filters, investigation edits, evidence, model, exports and logout", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await login(page);
  await expect(
    page.locator(".kpi-grid").getByText("50,000", { exact: true }),
  ).toBeVisible();
  await expect(page.getByLabel("Database storage")).toContainText("SQLite");
  await expect(page.getByLabel("Database storage")).toContainText("demo.db");
  await page.screenshot({
    path: "test-results/control-tower-desktop.png",
    fullPage: true,
  });
  await page.getByLabel("Filter by site").selectOption("1");
  await expect(page.locator("tbody tr").first()).toBeVisible();
  await expect(page.locator("tbody tr").first()).toContainText("DQ-001");
  await page.getByLabel("Filter exception type").selectOption("OOS");
  await expect(page.locator("tbody tr").first()).toContainText("OOS");
  await page.getByLabel("Search investigations").fill("NO_SUCH_CASE");
  await expect(page.getByText("No records match these filters.")).toBeVisible();
  await page.getByLabel("Search investigations").fill("");
  await page.getByLabel("Filter investigation status").selectOption("DETECTED");
  await page.locator(".case-link").first().click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.getByRole("button", { name: "Lineage", exact: true }).click();
  await expect(
    page.getByText("Source fingerprint", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Intelligence", exact: true }).click();
  await expect(
    page.getByText("Source-linked investigation checklist"),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Investigation", exact: true })
    .click();
  await page
    .getByLabel("Summary", { exact: true })
    .fill(
      "Synthetic browser verification: laboratory evidence requires independent review.",
    );
  await page
    .getByLabel("Impact assessment", { exact: true })
    .fill(
      "Synthetic impact assessment: assess related analytical runs and batches.",
    );
  await page
    .getByLabel("CAPA rationale", { exact: true })
    .fill(
      "Synthetic CAPA rationale: determine corrective actions after evidence review.",
    );
  await page.getByRole("button", { name: "Save investigation draft" }).click();
  await expect(page.getByRole("status")).toHaveText(
    "Investigation draft saved.",
  );
  await page.getByLabel("Next workflow state").selectOption("TRIAGED");
  await page
    .getByLabel("Reason", { exact: true })
    .fill("Synthetic triage for browser workflow verification.");
  await page
    .getByRole("button", { name: "Record workflow transition" })
    .click();
  await expect(page.getByRole("status")).toHaveText(
    "Workflow transition recorded.",
  );
  await page.getByLabel("Close investigation").click();
  await page.getByRole("button", { name: "Site network", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Synthetic Plant 001" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "CAPA worklist", exact: true })
    .click();
  await expect(page.getByRole("heading", { name: /Corrective/ })).toBeVisible();
  await page
    .getByRole("button", { name: "Controlled documents", exact: true })
    .click();
  await expect(
    page.getByText("OOS Investigation Workflow", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: /QualisIQ intelligence/ }).click();
  await expect(page.getByText("NOT APPROVED FOR PRODUCTION")).toBeVisible();
  await page
    .getByRole("button", { name: "Source library", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Public source register" }),
  ).toBeVisible();
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export summary" }).click();
  await expect((await download).suggestedFilename()).toBe(
    "qualisiq-quality-summary.json",
  );
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(
    page.getByRole("heading", { name: "Welcome to QualisIQ" }),
  ).toBeVisible();
  expect(errors).toEqual([]);
});
test("responsive mobile UI and failed login", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.getByLabel("Password", { exact: true }).fill("wrong-password");
  await page.getByRole("button", { name: "Sign in to workspace" }).click();
  await expect(page.getByRole("alert")).toContainText("Invalid");
  await login(page);
  await expect(
    page.locator(".kpi-grid").getByText("50,000", { exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "test-results/control-tower-mobile.png",
    fullPage: true,
  });
  await page.locator(".case-link").first().click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).not.toBeVisible();
});

test("record a synthetic OOS result, replay it idempotently, and open the generated investigation", async ({
  page,
}) => {
  await login(page);
  await page
    .getByRole("button", { name: "Result intake", exact: true })
    .click();
  await page.getByLabel("Authorized inspection lot").selectOption({ index: 1 });
  await page.getByLabel("Measured value").fill("93.5");
  await page
    .getByLabel("Source record ID", { exact: true })
    .fill("BROWSER-SYNTHETIC-RESULT-001");
  await page
    .getByRole("button", { name: "Validate and record result" })
    .click();
  await expect(page.getByRole("status")).toContainText(
    "Laboratory result recorded",
  );
  await expect(page.getByRole("status")).toContainText("Outcome: OOS");
  await page
    .getByRole("button", { name: "Validate and record result" })
    .click();
  await expect(page.getByRole("status")).toContainText(
    "Original result replayed",
  );
  await page
    .getByRole("button", { name: "Open generated investigation" })
    .click();
  await expect(page.getByRole("dialog")).toContainText("93.500");
  await page.getByRole("button", { name: "Lineage", exact: true }).click();
  await expect(page.getByRole("dialog")).toContainText(
    "BROWSER-SYNTHETIC-RESULT-001",
  );
  await page.getByLabel("Close investigation").click();
});
