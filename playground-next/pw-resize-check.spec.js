const { test, expect } = require("@playwright/test");

test("docs↔code vertical resize handle drags", async ({ page }, testInfo) => {
  const url = "http://localhost:3002";

  const consoleMessages = [];
  const pageErrors = [];

  page.on("console", (msg) => {
    const type = msg.type();
    if (type === "error" || type === "warning") {
      consoleMessages.push({ type, text: msg.text() });
    }
  });
  page.on("pageerror", (err) => pageErrors.push(String(err)));

  await page.goto(url, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(1500);

  const handles = await page.$$(
    '[data-panel-resize-handle-id], [data-panel-resize-handle], [role="separator"]'
  );
  expect(handles.length).toBeGreaterThan(0);

  let bestHandle = null;
  let bestScore = -Infinity;
  for (const h of handles) {
    const box = await h.boundingBox();
    if (!box) continue;
    const score =
      (box.height > 200 ? 10 : 0) +
      (box.width < 25 ? 10 : 0) -
      Math.abs(box.width - 6);
    if (score > bestScore) {
      bestHandle = h;
      bestScore = score;
    }
  }
  expect(bestHandle).toBeTruthy();

  const before = await bestHandle.evaluate((handle) => {
    const r = handle.getBoundingClientRect();
    const x = r.left + r.width / 2;
    const y = r.top + r.height / 2;

    const leftEl = document.elementFromPoint(x - 50, y);
    const rightEl = document.elementFromPoint(x + 50, y);

    const leftPanel = leftEl?.closest?.("[data-panel-id]") ?? leftEl;
    const rightPanel = rightEl?.closest?.("[data-panel-id]") ?? rightEl;

    const leftRect = leftPanel?.getBoundingClientRect?.();
    const rightRect = rightPanel?.getBoundingClientRect?.();

    return {
      handle: { x, y, w: r.width, h: r.height },
      left: leftRect ? { w: leftRect.width, x: leftRect.x } : null,
      right: rightRect ? { w: rightRect.width, x: rightRect.x } : null,
      topStack: document.elementsFromPoint(x, y).slice(0, 8).map((e) => {
        const cs = getComputedStyle(e);
        return {
          tag: e.tagName,
          id: e.id || null,
          class: typeof e.className === "string" ? e.className : null,
          role: e.getAttribute("role"),
          cursor: cs.cursor,
          pointerEvents: cs.pointerEvents,
          zIndex: cs.zIndex,
        };
      }),
    };
  });

  await page.screenshot({ path: "pw-resize-before.png", fullPage: true });

  const dragOnce = async (dx) => {
    const { x, y } = before.handle;
    await page.mouse.move(x, y);
    await page.mouse.down();
    await page.mouse.move(x + dx, y, { steps: 12 });
    await page.mouse.up();
    await page.waitForTimeout(250);
  };

  // Try left drag, then right drag if no movement.
  await dragOnce(-180);
  await dragOnce(220);

  const after = await page.evaluate(({ x, y }) => {
    const leftEl = document.elementFromPoint(x - 50, y);
    const rightEl = document.elementFromPoint(x + 50, y);
    const leftPanel = leftEl?.closest?.("[data-panel-id]") ?? leftEl;
    const rightPanel = rightEl?.closest?.("[data-panel-id]") ?? rightEl;
    const leftRect = leftPanel?.getBoundingClientRect?.();
    const rightRect = rightPanel?.getBoundingClientRect?.();
    return {
      left: leftRect ? { w: leftRect.width, x: leftRect.x } : null,
      right: rightRect ? { w: rightRect.width, x: rightRect.x } : null,
      topStack: document.elementsFromPoint(x, y).slice(0, 8).map((e) => {
        const cs = getComputedStyle(e);
        return {
          tag: e.tagName,
          id: e.id || null,
          class: typeof e.className === "string" ? e.className : null,
          role: e.getAttribute("role"),
          cursor: cs.cursor,
          pointerEvents: cs.pointerEvents,
          zIndex: cs.zIndex,
        };
      }),
    };
  }, { x: before.handle.x, y: before.handle.y });

  await page.screenshot({ path: "pw-resize-after.png", fullPage: true });

  const deltaLeft =
    before.left && after.left ? after.left.w - before.left.w : null;
  const deltaRight =
    before.right && after.right ? after.right.w - before.right.w : null;
  const moved = [deltaLeft, deltaRight].some(
    (d) => typeof d === "number" && Math.abs(d) >= 20
  );

  testInfo.attach("resize-check.json", {
    body: Buffer.from(
      JSON.stringify(
        {
          url,
          before,
          after,
          deltaLeft,
          deltaRight,
          moved,
          consoleMessages,
          pageErrors,
        },
        null,
        2
      )
    ),
    contentType: "application/json",
  });

  expect(moved, "Expected panel widths to change after drag").toBeTruthy();
});

