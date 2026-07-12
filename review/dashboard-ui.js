(() => {
  "use strict";

  const root = document.getElementById("asp-review-019f48fb");
  if (!root) return;

  const state = globalThis.AspReviewState;
  if (!state) throw new Error("ASP review state helpers are unavailable");

  const stage = root.querySelector("[data-review-stage]");
  const documentColumn = root.querySelector("[data-rfc-document]");
  const svg = root.querySelector("[data-review-threads]");
  const previousButton = root.querySelector("[data-review-prev]");
  const nextButton = root.querySelector("[data-review-next]");
  const reviewPosition = root.querySelector("[data-review-position]");
  const filterStatus = root.querySelector("[data-review-filter-status]");
  const resetFiltersButton = root.querySelector("[data-review-filter-reset]");
  const filterElements = Object.fromEntries(
    [...root.querySelectorAll("[data-review-filter]")].map((element) => [
      element.dataset.reviewFilter,
      element
    ])
  );
  const countElements = Object.fromEntries(
    [...root.querySelectorAll("[data-review-count]")].map((element) => [
      element.dataset.reviewCount,
      element
    ])
  );
  const rails = {
    left: root.querySelector('[data-review-rail="left"]'),
    right: root.querySelector('[data-review-rail="right"]')
  };
  const statusLabels = {
    missing: "Пробел",
    partial: "Частично",
    present: "Уже есть"
  };
  const maturityLabels = {
    proposal: "Proposal",
    specified: "Specified",
    machine_validated: "Machine validated",
    implementation_tested: "Implementation tested",
    interop_tested: "Interop tested",
    stable: "Stable"
  };
  const readinessLabels = {
    ready: "Ready",
    blocked: "Blocked"
  };
  const filterLabels = {
    profile: "Profile",
    priority: "Priority",
    status: "Coverage",
    maturity: "Maturity",
    target: "Target",
    readiness: "Readiness"
  };
  const unassignedTarget = "__unassigned__";
  const profileById = new Map(
    dashboardData.profiles.map((profile) => [String(profile.id), profile])
  );
  const releaseById = new Map(
    dashboardData.releases.map((release) => [String(release.id), release])
  );
  const preparedReviews = dashboardData.reviews.map((review) => ({
    ...review,
    anchorIds: review.anchors.map((anchor) => anchor.anchorId)
  }));
  const reviews = state.derivePlanningState(
    preparedReviews,
    dashboardData.maturity_order
  );
  const byId = new Map(reviews.map((review) => [String(review.id), review]));
  const cards = new Map();
  let visibleReviews = reviews.slice();
  let visibleIds = new Set(visibleReviews.map((review) => String(review.id)));
  let narrow = null;
  let activeReview = null;
  let pinnedReview = null;
  let pendingScrollReview = null;
  let pendingFocus = false;
  let scheduled = 0;

  const escapeHtml = (value) => String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

  function appendOptions(select, options) {
    for (const [value, label] of options) {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = label;
      select.append(option);
    }
  }

  function populateFilters() {
    appendOptions(
      filterElements.profile,
      dashboardData.profiles.map((profile) => [profile.id, profile.title])
    );
    appendOptions(
      filterElements.priority,
      ["P0", "P1", "P2", "P3"].map((priority) => [priority, priority])
    );
    appendOptions(
      filterElements.status,
      Object.entries(statusLabels).map(([value, label]) => [value, label])
    );
    appendOptions(
      filterElements.maturity,
      dashboardData.maturity_order.map((maturity) => [
        maturity,
        maturityLabels[maturity] ?? maturity
      ])
    );
    appendOptions(filterElements.target, [
      [unassignedTarget, "Unassigned"],
      ...dashboardData.releases.map((release) => [
        release.id,
        release.title ?? release.id
      ])
    ]);
    appendOptions(
      filterElements.readiness,
      Object.entries(readinessLabels).map(([value, label]) => [value, label])
    );
  }

  function propertyMarkup(label, value, property, extra = "") {
    return `
      <div class="asp-comment-property">
        <dt>${escapeHtml(label)}</dt>
        <dd data-review-property="${escapeHtml(property)}" ${extra}>${escapeHtml(value)}</dd>
      </div>
    `;
  }

  function dependencyMarkup(label, relation, ids) {
    const content = ids.length > 0
      ? ids.map((id) => {
          const target = byId.get(String(id));
          const title = target ? ` — ${target.title}` : "";
          return `<button class="asp-dependency-chip" type="button" data-review-jump="${escapeHtml(id)}" aria-label="Перейти к карточке #${escapeHtml(id)}${escapeHtml(title)}">#${escapeHtml(id)}</button>`;
        }).join("")
      : '<span class="asp-dependency-empty">—</span>';
    return `
      <div class="asp-dependency-row" data-review-${relation}>
        <span class="asp-dependency-label">${escapeHtml(label)}</span>
        ${content}
      </div>
    `;
  }

  function createCard(review) {
    const card = document.createElement("article");
    const profile = profileById.get(String(review.profile));
    const release = review.target_release === null
      ? null
      : releaseById.get(String(review.target_release));
    const targetLabel = review.target_release === null
      ? "Unassigned"
      : (release?.title ?? release?.id ?? review.target_release);
    card.className = "card asp-comment";
    card.id = `review-${review.id}`;
    card.tabIndex = -1;
    card.dataset.reviewId = review.id;
    card.dataset.status = review.status;
    card.dataset.priority = review.priority;
    card.dataset.side = review.side;
    card.dataset.profile = review.profile;
    card.dataset.maturity = review.maturity;
    card.dataset.target = review.target_release ?? unassignedTarget;
    card.dataset.readiness = review.readiness;
    const primaryId = review.anchorIds[0];
    card.innerHTML = `
      <div class="asp-comment-meta">
        <span class="asp-comment-id">#${String(review.id).padStart(2, "0")}</span>
        <span class="asp-comment-flags">
          <span class="asp-priority-label" data-priority="${escapeHtml(review.priority)}"><span class="asp-priority-mark"></span><strong>${escapeHtml(review.priority)}</strong></span>
          <span class="asp-comment-status"><span class="asp-status-dot"></span>${statusLabels[review.status]}</span>
        </span>
      </div>
      <a class="asp-comment-title" href="#${escapeHtml(primaryId)}">${escapeHtml(review.title)}</a>
      <div class="asp-comment-category">${escapeHtml(review.category)}</div>
      <p class="asp-comment-description">${escapeHtml(review.description)}</p>
      <p class="asp-comment-rationale"><strong>Сейчас:</strong> ${escapeHtml(review.rationale)}</p>
      <div class="asp-comment-actions">
        <div class="asp-comment-links">${review.anchorIds.length} ${review.anchorIds.length === 1 ? "связь" : "связи"}</div>
        <button class="asp-pin-button" type="button" data-review-pin aria-pressed="false" aria-label="Закрепить подсветку карточки #${escapeHtml(review.id)}: ${escapeHtml(review.title)}">Закрепить</button>
      </div>
      <footer class="asp-comment-footer">
        <dl class="asp-comment-properties">
          ${propertyMarkup("Profile", profile?.title ?? review.profile, "profile")}
          ${propertyMarkup("Maturity", maturityLabels[review.maturity] ?? review.maturity, "maturity")}
          ${propertyMarkup("Target", targetLabel, "target")}
          ${propertyMarkup("Readiness", readinessLabels[review.readiness] ?? review.readiness, "readiness", `class="asp-readiness-value" data-readiness="${escapeHtml(review.readiness)}"`)}
        </dl>
        ${dependencyMarkup("Depends on", "depends", review.depends_on)}
        ${dependencyMarkup("Blocks", "blocks", review.blocks)}
      </footer>
    `;
    card.addEventListener("pointerenter", () => {
      if (!pinnedReview) setActive(review.id);
    });
    card.addEventListener("pointerleave", () => {
      if (!pinnedReview) clearActive(review.id);
    });
    card.addEventListener("focusin", () => {
      if (!pinnedReview) setActive(review.id);
    });
    card.addEventListener("focusout", (event) => {
      if (!pinnedReview && !card.contains(event.relatedTarget)) clearActive(review.id);
    });
    card.addEventListener("click", (event) => {
      if (event.target.closest("[data-review-jump], [data-review-pin], a")) return;
      togglePinned(review.id);
    });
    const pinButton = card.querySelector("[data-review-pin]");
    pinButton.addEventListener("click", (event) => {
      event.stopPropagation();
      togglePinned(review.id);
    });
    for (const button of card.querySelectorAll("[data-review-jump]")) {
      button.addEventListener("click", (event) => {
        event.stopPropagation();
        jumpToReview(button.dataset.reviewJump);
      });
    }
    cards.set(String(review.id), card);
    return card;
  }

  function updatePinnedControls() {
    for (const [reviewId, card] of cards) {
      const button = card.querySelector("[data-review-pin]");
      const pressed = reviewId === pinnedReview;
      const review = byId.get(reviewId);
      button.setAttribute("aria-pressed", String(pressed));
      button.setAttribute(
        "aria-label",
        `Закрепить подсветку карточки #${reviewId}: ${review?.title ?? ""}`
      );
    }
  }

  function setActive(id, persist = false) {
    activeReview = String(id);
    if (persist) pinnedReview = activeReview;
    root.dataset.activeReview = activeReview;
    for (const [cardId, card] of cards) {
      card.classList.toggle("is-active", cardId === activeReview);
    }
    for (const heading of documentColumn.querySelectorAll(".asp-anchor-active")) {
      heading.classList.remove("asp-anchor-active");
    }
    const review = byId.get(activeReview);
    if (review) {
      for (const anchorId of review.anchorIds) {
        document.getElementById(anchorId)?.classList.add("asp-anchor-active");
      }
    }
    for (const group of svg.querySelectorAll(".asp-thread-group")) {
      group.classList.toggle("is-active", group.dataset.reviewId === activeReview);
    }
    updatePinnedControls();
    updateNavigation();
  }

  function clearActive(id, force = false) {
    if (id !== null && id !== undefined && activeReview !== String(id)) return;
    if (!force && pinnedReview) {
      setActive(pinnedReview);
      return;
    }
    activeReview = null;
    root.removeAttribute("data-active-review");
    for (const card of cards.values()) card.classList.remove("is-active");
    for (const heading of documentColumn.querySelectorAll(".asp-anchor-active")) {
      heading.classList.remove("asp-anchor-active");
    }
    for (const group of svg.querySelectorAll(".asp-thread-group")) {
      group.classList.remove("is-active");
    }
    updatePinnedControls();
    updateNavigation();
  }

  function resetSelection() {
    const selected = activeReview;
    pinnedReview = null;
    clearActive(selected, true);
  }

  function togglePinned(id) {
    const reviewId = String(id);
    if (pinnedReview === reviewId) {
      resetSelection();
      return;
    }
    setActive(reviewId, true);
  }

  function currentFilters() {
    return Object.fromEntries(
      Object.entries(filterElements).map(([field, element]) => [field, element.value])
    );
  }

  function setFilters(filters) {
    for (const [field, element] of Object.entries(filterElements)) {
      element.value = filters[field] ?? "";
    }
  }

  function updateNavigation() {
    const currentId = pinnedReview ?? activeReview;
    const index = visibleReviews.findIndex((review) => String(review.id) === currentId);
    if (visibleReviews.length === 0) {
      reviewPosition.textContent = "0 / 0";
    } else if (index < 0) {
      reviewPosition.textContent = `— / ${visibleReviews.length}`;
    } else {
      reviewPosition.textContent = `#${String(visibleReviews[index].id).padStart(2, "0")} · ${index + 1} / ${visibleReviews.length}`;
    }
    const navigationDisabled = visibleReviews.length === 0;
    previousButton.disabled = navigationDisabled;
    nextButton.disabled = navigationDisabled;
  }

  function updateCounters() {
    const readyCount = visibleReviews.filter((review) => review.readiness === "ready").length;
    countElements.visible.textContent = visibleReviews.length;
    countElements.total.textContent = reviews.length;
    countElements.ready.textContent = readyCount;
    countElements.blocked.textContent = visibleReviews.length - readyCount;

    const priorityCounts = visibleReviews.reduce((counts, review) => {
      counts[review.priority] = (counts[review.priority] ?? 0) + 1;
      return counts;
    }, {});
    for (const counter of root.querySelectorAll("[data-priority-count]")) {
      counter.textContent = `(${priorityCounts[counter.dataset.priorityCount] ?? 0})`;
    }
  }

  function applyFilters(message = "") {
    visibleReviews = state.filterReviews(reviews, currentFilters());
    visibleIds = new Set(visibleReviews.map((review) => String(review.id)));
    for (const [reviewId, card] of cards) card.hidden = !visibleIds.has(reviewId);
    if (activeReview && !visibleIds.has(activeReview)) resetSelection();
    updateCounters();
    updateNavigation();
    const summary = `Показано ${visibleReviews.length} из ${reviews.length} карточек.`;
    filterStatus.textContent = message ? `${message} ${summary}` : summary;
    scheduleLayout();
  }

  function selectAndScroll(id, focus = false) {
    if (!visibleIds.has(String(id))) return;
    setActive(id, true);
    pendingScrollReview = String(id);
    pendingFocus = focus;
    scheduleLayout();
  }

  function navigateReviews(direction) {
    const currentId = pinnedReview ?? activeReview;
    const nextId = state.nextReviewId(visibleReviews, currentId, direction);
    if (nextId !== null) selectAndScroll(nextId);
  }

  function jumpToReview(id) {
    const review = byId.get(String(id));
    if (!review) return;
    const before = currentFilters();
    const relaxed = state.relaxFiltersForReview(review, before);
    const relaxedFields = Object.keys(filterElements).filter(
      (field) => String(before[field] ?? "") !== String(relaxed[field] ?? "")
    );
    setFilters(relaxed);
    const message = relaxedFields.length > 0
      ? `Ослаблены фильтры: ${relaxedFields.map((field) => filterLabels[field] ?? field).join(", ")}.`
      : "";
    applyFilters(message);
    selectAndScroll(review.id, true);
  }

  function enterNarrowMode() {
    if (narrow === true) return;
    narrow = true;
    svg.replaceChildren();
    const grouped = new Map();
    for (const review of reviews) {
      const anchorId = review.anchorIds[0];
      if (!grouped.has(anchorId)) grouped.set(anchorId, []);
      grouped.get(anchorId).push(review);
    }
    for (const [anchorId, anchorReviews] of grouped) {
      const anchor = document.getElementById(anchorId);
      if (!anchor) continue;
      let insertionPoint = anchor;
      for (const review of anchorReviews) {
        const card = cards.get(String(review.id));
        card.style.removeProperty("top");
        card.classList.add("is-inline");
        insertionPoint.insertAdjacentElement("afterend", card);
        insertionPoint = card;
      }
    }
    stage.style.minHeight = "";
  }

  function solveRail(items, stageHeight, gap = 14, padding = 0) {
    items.sort((a, b) => a.preferredTop - b.preferredTop || a.id - b.id);
    let packedHeight = 0;
    items.forEach((item, index) => {
      item.offset = packedHeight;
      packedHeight += item.height + (index === items.length - 1 ? 0 : gap);
    });
    stageHeight = Math.max(stageHeight, packedHeight + 2 * padding);
    const blocks = [];
    items.forEach((item, index) => {
      blocks.push({ first: index, last: index, weight: 1, weightedSum: item.preferredTop - item.offset });
      while (blocks.length > 1) {
        const right = blocks[blocks.length - 1];
        const left = blocks[blocks.length - 2];
        if (left.weightedSum / left.weight <= right.weightedSum / right.weight) break;
        blocks.splice(-2, 2, {
          first: left.first,
          last: right.last,
          weight: left.weight + right.weight,
          weightedSum: left.weightedSum + right.weightedSum
        });
      }
    });
    const maxX = Math.max(padding, stageHeight - padding - packedHeight);
    for (const block of blocks) {
      const x = Math.max(padding, Math.min(maxX, block.weightedSum / block.weight));
      for (let index = block.first; index <= block.last; index += 1) {
        items[index].top = Math.round(x + items[index].offset);
      }
    }
    return { items, stageHeight };
  }

  function enterWideMode() {
    if (narrow !== false) {
      narrow = false;
      for (const review of reviews) {
        const card = cards.get(String(review.id));
        card.classList.remove("is-inline");
        rails[review.side].append(card);
      }
    }

    for (const [reviewId, card] of cards) {
      if (!visibleIds.has(reviewId)) card.style.removeProperty("top");
    }
    stage.style.minHeight = `${documentColumn.offsetHeight}px`;
    const stageRect = stage.getBoundingClientRect();
    const railItems = { left: [], right: [] };
    for (const review of visibleReviews) {
      const anchor = document.getElementById(review.anchorIds[0]);
      const card = cards.get(String(review.id));
      if (!anchor || !card) continue;
      const anchorRect = anchor.getBoundingClientRect();
      const height = card.offsetHeight;
      railItems[review.side].push({
        id: review.id,
        card,
        height,
        preferredTop: anchorRect.top - stageRect.top + Math.min(anchorRect.height / 2, 18) - height / 2
      });
    }

    const baseHeight = Math.max(documentColumn.offsetHeight, 1);
    const left = solveRail(railItems.left, baseHeight);
    const right = solveRail(railItems.right, baseHeight);
    const solvedHeight = Math.max(baseHeight, left.stageHeight, right.stageHeight);
    stage.style.minHeight = `${solvedHeight}px`;
    for (const item of [...left.items, ...right.items]) {
      item.card.style.top = `${item.top}px`;
    }
    requestAnimationFrame(drawThreads);
  }

  function svgElement(name, attributes) {
    const element = document.createElementNS("http://www.w3.org/2000/svg", name);
    for (const [key, value] of Object.entries(attributes)) element.setAttribute(key, value);
    return element;
  }

  function drawThreads() {
    if (narrow) return;
    const stageRect = stage.getBoundingClientRect();
    const documentRect = documentColumn.getBoundingClientRect();
    svg.setAttribute("viewBox", `0 0 ${stageRect.width} ${stageRect.height}`);
    svg.replaceChildren();

    for (const review of visibleReviews) {
      const card = cards.get(String(review.id));
      if (!card) continue;
      const cardRect = card.getBoundingClientRect();
      const group = svgElement("g", { class: "asp-thread-group", "data-review-id": review.id });
      const startX = review.side === "left"
        ? cardRect.right - stageRect.left
        : cardRect.left - stageRect.left;
      const startYBase = cardRect.top - stageRect.top + Math.min(42, cardRect.height / 2);
      const laneX = review.side === "left"
        ? documentRect.left - stageRect.left - 14
        : documentRect.right - stageRect.left + 14;

      review.anchorIds.forEach((anchorId, index) => {
        const anchor = document.getElementById(anchorId);
        if (!anchor) return;
        const anchorRect = anchor.getBoundingClientRect();
        const endX = review.side === "left"
          ? documentRect.left - stageRect.left
          : documentRect.right - stageRect.left;
        const endY = anchorRect.top - stageRect.top + Math.min(anchorRect.height / 2, 18);
        const startY = startYBase + index * 5;
        const path = svgElement("path", {
          class: `asp-thread${index === 0 ? "" : " asp-thread-secondary"}`,
          d: `M ${startX} ${startY} C ${laneX} ${startY}, ${laneX} ${endY}, ${endX} ${endY}`
        });
        const dot = svgElement("circle", {
          class: "asp-thread-endpoint",
          cx: endX,
          cy: endY,
          r: index === 0 ? 3 : 2.25
        });
        group.append(path, dot);
      });
      if (activeReview === String(review.id)) group.classList.add("is-active");
      svg.append(group);
    }
  }

  function scrollSelectedAfterLayout() {
    if (pendingScrollReview === null) return;
    const reviewId = pendingScrollReview;
    const shouldFocus = pendingFocus;
    pendingScrollReview = null;
    pendingFocus = false;
    requestAnimationFrame(() => {
      const card = cards.get(reviewId);
      if (!card || card.hidden) return;
      card.scrollIntoView({
        block: "center",
        inline: "nearest",
        behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth"
      });
      if (shouldFocus) card.focus({ preventScroll: true });
    });
  }

  function layout() {
    scheduled = 0;
    if (root.clientWidth < 1200) enterNarrowMode();
    else enterWideMode();
    scrollSelectedAfterLayout();
  }

  function scheduleLayout() {
    if (scheduled) cancelAnimationFrame(scheduled);
    scheduled = requestAnimationFrame(layout);
  }

  populateFilters();
  for (const review of reviews) createCard(review);
  previousButton.addEventListener("click", () => navigateReviews(-1));
  nextButton.addEventListener("click", () => navigateReviews(1));
  for (const element of Object.values(filterElements)) {
    element.addEventListener("change", () => applyFilters());
  }
  resetFiltersButton.addEventListener("click", () => {
    setFilters({});
    applyFilters("Фильтры сброшены.");
  });

  const resizeObserver = new ResizeObserver(scheduleLayout);
  resizeObserver.observe(root);
  resizeObserver.observe(documentColumn);
  window.addEventListener("load", scheduleLayout, { once: true });
  window.addEventListener("resize", scheduleLayout);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") resetSelection();
  });
  applyFilters();
})();
