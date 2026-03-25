/* eslint-disable no-console */

const fs = require("node:fs");
const path = require("node:path");

async function main() {
  // Provided by user.
  const url = "http://localhost:3002";

  const { chromium } = require("playwright");
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

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

  const handleSelectors =
    '[data-panel-resize-handle-id], [data-panel-resize-handle], [role="separator"]';
  const handles = await page.$$(handleSelectors);

  const handleBoxes = [];
  for (const h of handles) {
    const box = await h.boundingBox();
    if (!box) continue;
    handleBoxes.push({ h, box });
  }

  let best = null;
  let bestScore = -Infinity;
  for (const { h, box } of handleBoxes) {
    const score =
      (box.height > 200 ? 10 : 0) + (box.width < 25 ? 10 : 0) - Math.abs(box.width - 6);
    if (score > bestScore) {
      best = { h, box, score };
      bestScore = score;
    }
  }

  const result = {
    url,
    foundHandles: handleBoxes.map(({ box }) => box),
    chosenHandle: best ? best.box : null,
    before: null,
    after: null,
    deltaLeft: null,
    deltaRight: null,
    moved: false,
    consoleMessages,
    pageErrors,
  };

  const artifactsDir = path.join(process.cwd(), "pw-resize-artifacts");
  fs.mkdirSync(artifactsDir, { recursive: true });

  const beforePng = path.join(artifactsDir, "before.png");
  const afterPng = path.join(artifactsDir, "after.png");
  const jsonPath = path.join(artifactsDir, "result.json");

  await page.screenshot({ path: beforePng, fullPage: true });

  if (!best) {
    result.before = { error: `No handle found via selector: ${handleSelectors}` };
    fs.writeFileSync(jsonPath, JSON.stringify(result, null, 2));
    console.log(`NO_HANDLE: wrote ${jsonPath}`);
    await browser.close();
    process.exitCode = 2;
    return;
  }

  const before = await best.h.evaluate((handle) => {
    const r = handle.getBoundingClientRect();
    const x = r.left + r.width / 2;
    const y = r.top + r.height / 2;

    const leftEl = document.elementFromPoint(x - 50, y);
    const rightEl = document.elementFromPoint(x + 50, y);

    const leftPanel = leftEl?.closest?.("[data-panel-id]") ?? leftEl;
    const rightPanel = rightEl?.closest?.("[data-panel-id]") ?? rightEl;

    const leftRect = leftPanel?.getBoundingClientRect?.();
    const rightRect = rightPanel?.getBoundingClientRect?.();

    const stack = document.elementsFromPoint(x, y).slice(0, 10).map((e) => {
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
    });

    return {
      handle: { x, y, w: r.width, h: r.height },
      left: leftRect ? { w: leftRect.width, x: leftRect.x } : null,
      right: rightRect ? { w: rightRect.width, x: rightRect.x } : null,
      topStack: stack,
    };
  });
  result.before = before;

  const drag = async (dx) => {
    const { x, y } = before.handle;
    await page.mouse.move(x, y);
    await page.mouse.down();
    await page.mouse.move(x + dx, y, { steps: 12 });
    await page.mouse.up();
    await page.waitForTimeout(250);
  };

  // Try both directions, some layouts enforce min sizes.
  await drag(-180);
  await drag(220);

  const after = await page.evaluate(({ x, y }) => {
    const leftEl = document.elementFromPoint(x - 50, y);
    const rightEl = document.elementFromPoint(x + 50, y);
    const leftPanel = leftEl?.closest?.("[data-panel-id]") ?? leftEl;
    const rightPanel = rightEl?.closest?.("[data-panel-id]") ?? rightEl;
    const leftRect = leftPanel?.getBoundingClientRect?.();
    const rightRect = rightPanel?.getBoundingClientRect?.();

    const stack = document.elementsFromPoint(x, y).slice(0, 10).map((e) => {
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
    });

    return {
      left: leftRect ? { w: leftRect.width, x: leftRect.x } : null,
      right: rightRect ? { w: rightRect.width, x: rightRect.x } : null,
      topStack: stack,
    };
  }, { x: before.handle.x, y: before.handle.y });
  result.after = after;

  await page.screenshot({ path: afterPng, fullPage: true });

  if (before.left && after.left) result.deltaLeft = after.left.w - before.left.w;
  if (before.right && after.right) result.deltaRight = after.right.w - before.right.w;

  result.moved = [result.deltaLeft, result.deltaRight].some(
    (d) => typeof d === "number" && Math.abs(d) >= 20
  );

  fs.writeFileSync(jsonPath, JSON.stringify(result, null, 2));

  console.log(
    [
      `moved=${result.moved}`,
      `deltaLeft=${result.deltaLeft}`,
      `deltaRight=${result.deltaRight}`,
      `consoleErrors=${consoleMessages.length}`,
      `pageErrors=${pageErrors.length}`,
      `artifacts=${artifactsDir}`,
    ].join(" ")
  );

  await browser.close();
}

main().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});

