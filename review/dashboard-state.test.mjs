import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import vm from "node:vm";

const source = await readFile(new URL("./dashboard-state.js", import.meta.url), "utf8");
const context = vm.createContext({});
vm.runInContext(source, context, { filename: "dashboard-state.js" });
const state = context.AspReviewState;

const maturityOrder = [
  "proposal",
  "specified",
  "machine_validated",
  "implementation_tested",
  "interop_tested",
  "stable"
];

function plain(value) {
  return JSON.parse(JSON.stringify(value));
}

test("derivePlanningState derives deterministic inverse edges and direct readiness", () => {
  const reviews = [
    { id: 3, status: "present", maturity: "stable", depends_on: [2] },
    { id: 1, status: "missing", maturity: "proposal", depends_on: [] },
    { id: 4, status: "present", maturity: "specified", depends_on: [999] },
    { id: 2, status: "present", maturity: "specified", depends_on: [1] },
    { id: 5, status: "present", maturity: "machine_validated", depends_on: [2, 1] }
  ];

  const derived = plain(state.derivePlanningState(reviews, maturityOrder));

  assert.deepEqual(derived.map(({ id, blocks, readiness }) => ({ id, blocks, readiness })), [
    { id: 1, blocks: [2, 5], readiness: "ready" },
    { id: 2, blocks: [3, 5], readiness: "blocked" },
    { id: 3, blocks: [], readiness: "ready" },
    { id: 4, blocks: [], readiness: "blocked" },
    { id: 5, blocks: [], readiness: "blocked" }
  ]);
  assert.equal(reviews[0].blocks, undefined, "input reviews are not mutated");
});

test("matchesFilters applies AND across fields and OR within a field", () => {
  const review = {
    id: 8,
    profile: "manifest",
    priority: "P1",
    status: "present",
    maturity: "specified",
    target_release: "0.2",
    readiness: "ready"
  };
  const filters = {
    profile: ["core", "manifest"],
    priority: "P1",
    status: new Set(["partial", "present"]),
    maturity: "specified",
    target: "0.2",
    readiness: "ready"
  };

  assert.equal(state.matchesFilters(review, filters), true);
  assert.equal(state.matchesFilters(review, { ...filters, priority: "P0" }), false);
  assert.equal(state.matchesFilters(review, { ...filters, status: ["missing", "partial"] }), false);
  assert.deepEqual(
    plain(state.filterReviews([review, { ...review, id: 9, profile: "receipts" }], filters)).map(
      (item) => item.id
    ),
    [8]
  );
});

test("target filter distinguishes unassigned cards and supports target_release alias", () => {
  const unassigned = { target_release: null };
  const assigned = { target_release: "0.2" };

  assert.equal(state.matchesFilters(unassigned, { target: "__unassigned__" }), true);
  assert.equal(state.matchesFilters(assigned, { target: "__unassigned__" }), false);
  assert.equal(state.matchesFilters(assigned, { target_release: "0.2" }), true);
  assert.equal(state.matchesFilters(unassigned, { target_release: "0.2" }), false);
  assert.equal(state.matchesFilters(assigned, { target: "all" }), true);
});

test("nextReviewId handles empty, one-item, missing-current, and wrapping lists", () => {
  assert.equal(state.nextReviewId([], 1, 1), null);
  assert.equal(state.nextReviewId([{ id: 7 }], 7, 1), 7);
  assert.equal(state.nextReviewId([{ id: 7 }], null, -1), 7);

  const reviews = [{ id: 2 }, { id: 4 }, { id: 9 }];
  assert.equal(state.nextReviewId(reviews, 9, 1), 2);
  assert.equal(state.nextReviewId(reviews, 2, -1), 9);
  assert.equal(state.nextReviewId(reviews, 4, 1), 9);
  assert.equal(state.nextReviewId(reviews, 404, 1), 2);
  assert.equal(state.nextReviewId(reviews, 404, -1), 9);
});

test("relaxFiltersForReview clears only filters that exclude the card", () => {
  const review = {
    profile: "oauth-grants",
    priority: "P1",
    status: "present",
    maturity: "proposal",
    target_release: null,
    readiness: "blocked"
  };
  const filters = {
    profile: "manifest",
    priority: "P1",
    status: ["present", "partial"],
    maturity: new Set(["specified"]),
    target: "0.2",
    readiness: "ready",
    query: "binding"
  };

  const relaxed = state.relaxFiltersForReview(review, filters);

  assert.equal(relaxed.profile, null);
  assert.equal(relaxed.priority, "P1");
  assert.deepEqual(plain(relaxed.status), ["present", "partial"]);
  assert.equal(Object.prototype.toString.call(relaxed.maturity), "[object Set]");
  assert.equal(relaxed.maturity.size, 0);
  assert.equal(relaxed.target, null);
  assert.equal(relaxed.readiness, null);
  assert.equal(relaxed.query, "binding");
  assert.equal(filters.profile, "manifest", "source filters are not mutated");
  assert.deepEqual(filters.status, ["present", "partial"]);
  assert.deepEqual([...filters.maturity], ["specified"]);
  assert.equal(state.matchesFilters(review, relaxed), true);
});

test("relaxFiltersForReview preserves a matching unassigned target filter", () => {
  const filters = { target: "__unassigned__", profile: "core" };
  const relaxed = state.relaxFiltersForReview(
    { target_release: null, profile: "oauth-grants" },
    filters
  );

  assert.equal(relaxed.target, "__unassigned__");
  assert.equal(relaxed.profile, null);
});
