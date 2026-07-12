(function (root) {
  "use strict";

  const FILTER_FIELDS = [
    "profile",
    "priority",
    "status",
    "maturity",
    "target",
    "readiness"
  ];
  const INACTIVE_FILTER_VALUES = new Set(["", "all", "__all__"]);
  const UNASSIGNED_TARGET = "__unassigned__";

  function idKey(id) {
    return String(id);
  }

  function compareIds(left, right) {
    if (typeof left === "number" && typeof right === "number") {
      return left - right;
    }
    const leftKey = idKey(left);
    const rightKey = idKey(right);
    if (leftKey < rightKey) return -1;
    if (leftKey > rightKey) return 1;
    return 0;
  }

  function isSet(value) {
    return Object.prototype.toString.call(value) === "[object Set]";
  }

  function selections(value) {
    let values;
    if (Array.isArray(value)) values = value;
    else if (isSet(value)) values = Array.from(value);
    else values = [value];

    return values
      .filter((item) => item !== null && item !== undefined)
      .map((item) => String(item))
      .filter((item) => !INACTIVE_FILTER_VALUES.has(item));
  }

  function filterEntry(filters, field) {
    if (!filters || typeof filters !== "object") return { key: field, value: undefined };
    if (field === "target" && !Object.prototype.hasOwnProperty.call(filters, "target")) {
      return { key: "target_release", value: filters.target_release };
    }
    return { key: field, value: filters[field] };
  }

  function reviewValue(review, field) {
    if (field === "target") {
      return review.target_release === null || review.target_release === undefined
        ? UNASSIGNED_TARGET
        : String(review.target_release);
    }
    const value = review[field];
    return value === null || value === undefined ? undefined : String(value);
  }

  function fieldMatches(review, filters, field) {
    const selected = selections(filterEntry(filters, field).value);
    if (selected.length === 0) return true;
    return selected.includes(reviewValue(review, field));
  }

  function derivePlanningState(reviews, maturityOrder) {
    if (!Array.isArray(reviews)) throw new TypeError("reviews must be an array");
    if (!Array.isArray(maturityOrder)) {
      throw new TypeError("maturityOrder must be an array");
    }

    const orderedReviews = reviews
      .map((review, index) => ({ review, index }))
      .sort((left, right) => compareIds(left.review.id, right.review.id) || left.index - right.index)
      .map((item) => item.review);
    const reviewsById = new Map(orderedReviews.map((review) => [idKey(review.id), review]));
    const blocksById = new Map(
      orderedReviews.map((review) => [idKey(review.id), new Set()])
    );

    for (const review of orderedReviews) {
      const dependencies = Array.isArray(review.depends_on) ? review.depends_on : [];
      for (const dependencyId of dependencies) {
        const blockedReviews = blocksById.get(idKey(dependencyId));
        if (blockedReviews) blockedReviews.add(review.id);
      }
    }

    const maturityRanks = new Map(
      maturityOrder.map((maturity, index) => [String(maturity), index])
    );
    const specifiedRank = maturityRanks.get("specified");

    return orderedReviews.map((review) => {
      const dependencies = Array.isArray(review.depends_on) ? review.depends_on.slice() : [];
      const dependenciesReady = dependencies.every((dependencyId) => {
        const dependency = reviewsById.get(idKey(dependencyId));
        if (!dependency || dependency.status !== "present" || specifiedRank === undefined) {
          return false;
        }
        const dependencyRank = maturityRanks.get(String(dependency.maturity));
        return dependencyRank !== undefined && dependencyRank >= specifiedRank;
      });
      const blocks = Array.from(blocksById.get(idKey(review.id)) || []).sort(compareIds);

      return {
        ...review,
        depends_on: dependencies,
        blocks,
        readiness: dependenciesReady ? "ready" : "blocked"
      };
    });
  }

  function matchesFilters(review, filters) {
    if (!review || typeof review !== "object") return false;
    return FILTER_FIELDS.every((field) => fieldMatches(review, filters, field));
  }

  function filterReviews(reviews, filters) {
    if (!Array.isArray(reviews)) throw new TypeError("reviews must be an array");
    return reviews.filter((review) => matchesFilters(review, filters));
  }

  function nextReviewId(filtered, currentId, direction) {
    if (!Array.isArray(filtered)) throw new TypeError("filtered must be an array");
    if (filtered.length === 0) return null;

    const step = direction < 0 ? -1 : 1;
    const currentIndex = filtered.findIndex((review) => idKey(review.id) === idKey(currentId));
    if (currentIndex < 0) {
      return filtered[step < 0 ? filtered.length - 1 : 0].id;
    }
    const nextIndex = (currentIndex + step + filtered.length) % filtered.length;
    return filtered[nextIndex].id;
  }

  function cloneFilterValue(value) {
    if (Array.isArray(value)) return value.slice();
    if (isSet(value)) return new Set(value);
    return value;
  }

  function relaxedFilterValue(value) {
    if (Array.isArray(value)) return [];
    if (isSet(value)) return new Set();
    return null;
  }

  function relaxFiltersForReview(review, filters) {
    const source = filters && typeof filters === "object" ? filters : {};
    const relaxed = {};
    for (const key of Object.keys(source)) relaxed[key] = cloneFilterValue(source[key]);

    for (const field of FILTER_FIELDS) {
      const entry = filterEntry(source, field);
      if (selections(entry.value).length > 0 && !fieldMatches(review, source, field)) {
        relaxed[entry.key] = relaxedFilterValue(entry.value);
      }
    }
    return relaxed;
  }

  root.AspReviewState = Object.freeze({
    derivePlanningState,
    matchesFilters,
    filterReviews,
    nextReviewId,
    relaxFiltersForReview
  });
})(globalThis);
