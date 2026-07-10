#!/usr/bin/env node

import { readFileSync } from "node:fs";

const dashboardPath = new URL("./agent-surface-rfc-review.html", import.meta.url);
const dashboard = readFileSync(dashboardPath, "utf8");
const scripts = [...dashboard.matchAll(/<script>([\s\S]*?)<\/script>/g)];

if (scripts.length !== 1) {
  throw new Error(`Expected one inline script, found ${scripts.length}`);
}

new Function(scripts[0][1]);
console.log("Dashboard JavaScript syntax is valid");
