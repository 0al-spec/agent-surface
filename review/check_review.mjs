#!/usr/bin/env node

import { readFileSync } from "node:fs";

const dashboardPath = new URL("./agent-surface-rfc-review.html", import.meta.url);
const dashboard = readFileSync(dashboardPath, "utf8");
const scripts = [...dashboard.matchAll(/<script>([\s\S]*?)<\/script>/g)];

if (scripts.length !== 1) {
  throw new Error(`Expected one inline script, found ${scripts.length}`);
}

const requiredPlanningMarkers = [
  'data-review-filter="profile"',
  'data-review-filter="readiness"',
  'data-review-count="ready"',
  "data-review-jump",
  "data-review-pin",
  "aria-pressed",
  "AspReviewState",
  "visibleReviews"
];
for (const marker of requiredPlanningMarkers) {
  if (!dashboard.includes(marker)) {
    throw new Error(`Dashboard is missing planning marker: ${marker}`);
  }
}
new Function(scripts[0][1]);
console.log("Dashboard JavaScript syntax is valid");
