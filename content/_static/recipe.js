(() => {
	var SCROLL_PAUSE_MS = 800;
	var SCROLL_MIN_DISTANCE = 100;
	var BACK_BUTTON_FADE_MS = 5000;
	var PROGRESS_MAX_AGE_MS = 48 * 60 * 60 * 1000;
	var STORAGE_PREFIX = "recipe-progress-";
	var STEP_ZONE_PX = 30;
	var STEP_ZONE_TOUCH_PX = 44;
	var ZONE_HINT_MS = 2000;
	var COPY_FEEDBACK_MS = 1500;
	var SPLIT_QUERY =
		"(pointer: coarse) and (orientation: landscape) and (min-width: 900px) and (max-height: 900px)";

	var scrollStack = [];
	var scrollTimer = null;
	var fadeTimer = null;
	var zoneHintTimer = null;
	var copyTimer = null;
	var lastScrollY = 0;
	var cachedContentHash = null;

	function getStorageKey() {
		return STORAGE_PREFIX + window.location.pathname;
	}

	// Must be primed before any script-injected DOM (toggles, anchors, split panes) exists,
	// otherwise the stored hash never matches the hash recomputed on the next page load.
	function computeContentHash() {
		if (cachedContentHash !== null) return cachedContentHash;
		var main = document.querySelector("main") || document.body;
		var text = main.textContent || "";
		var hash = 5381;
		for (var i = 0; i < text.length; i++) {
			hash = ((hash << 5) + hash) ^ text.charCodeAt(i);
			hash = hash & hash;
		}
		cachedContentHash = hash.toString(36);
		return cachedContentHash;
	}

	function isProgressKey(key) {
		return key.startsWith("ingredient-") || key.startsWith("step-");
	}

	function clearProgressKeys(state) {
		var cleaned = {};
		Object.keys(state).forEach((key) => {
			if (!isProgressKey(key) && key !== "_progressAt") {
				cleaned[key] = state[key];
			}
		});
		return cleaned;
	}

	function readState(key) {
		try {
			var data = localStorage.getItem(key);
			if (!data) return null;
			return JSON.parse(data);
		} catch (_e) {
			return null;
		}
	}

	function writeState(key, state) {
		try {
			localStorage.setItem(key, JSON.stringify(state));
		} catch (_e) {
			// Storage unavailable
		}
	}

	function isExpired(state) {
		var stamp = state._progressAt;
		return Boolean(stamp) && Date.now() - stamp > PROGRESS_MAX_AGE_MS;
	}

	function loadState() {
		var key = getStorageKey();
		var parsed = readState(key);
		if (!parsed) return {};

		if (parsed._contentHash && parsed._contentHash !== computeContentHash()) {
			try {
				localStorage.removeItem(key);
			} catch (_e) {
				// Storage unavailable
			}
			return {};
		}

		if (isExpired(parsed)) {
			var cleaned = clearProgressKeys(parsed);
			writeState(key, cleaned);
			return cleaned;
		}

		return parsed;
	}

	// `touchedProgress` marks a save that changed a checkbox or step, which is the only
	// kind of save that restarts the expiry window
	function saveState(state, touchedProgress) {
		if (touchedProgress) {
			state._progressAt = Date.now();
		}
		if (!Object.keys(state).some(isProgressKey)) {
			delete state._progressAt;
		}
		state._savedAt = Date.now();
		state._contentHash = computeContentHash();
		writeState(getStorageKey(), state);
	}

	function purgeExpiredRecipes() {
		var keys = [];
		try {
			for (var i = 0; i < localStorage.length; i++) {
				var key = localStorage.key(i);
				if (key?.startsWith(STORAGE_PREFIX)) keys.push(key);
			}
		} catch (_e) {
			return;
		}

		keys.forEach((key) => {
			var state = readState(key);
			if (!state || !isExpired(state)) return;
			var cleaned = clearProgressKeys(state);
			if (Object.keys(cleaned).some((k) => !k.startsWith("_"))) {
				writeState(key, cleaned);
			} else {
				try {
					localStorage.removeItem(key);
				} catch (_e) {
					// Storage unavailable
				}
			}
		});
	}

	function hasTextSelection() {
		var selection = window.getSelection();
		return Boolean(selection) && !selection.isCollapsed && selection.toString().trim() !== "";
	}

	// A completed item paints its line-through across every in-flow descendant, which would
	// falsely strike unchecked children. Giving an item's own content its own box keeps
	// nested lists outside the decorated subtree.
	function wrapOwnLabel(li) {
		if (li.querySelector(":scope > .item-label")) return;
		var nested = li.querySelector(":scope > ul, :scope > ol");
		var label = document.createElement("span");
		label.className = "item-label";
		Array.from(li.childNodes).forEach((node) => {
			if (node === nested) return;
			if (node.nodeType === Node.ELEMENT_NODE && node.tagName === "INPUT") return;
			label.appendChild(node);
		});
		li.insertBefore(label, nested);
	}

	function ownText(li) {
		var clone = li.cloneNode(true);
		clone.querySelectorAll("ul, ol, input").forEach((node) => {
			node.remove();
		});
		return clone.textContent.replace(/\s+/g, " ").trim();
	}

	function setupIngredientCheckboxes() {
		var state = loadState();
		var globalIndex = 0;

		document.querySelectorAll("ul.task-list").forEach((list) => {
			list.querySelectorAll(":scope > li").forEach((li) => {
				var cb = li.querySelector(":scope > input[type='checkbox']");
				if (!cb) return;

				var key = `ingredient-${globalIndex}`;
				globalIndex++;
				cb.dataset.storageKey = key;
				wrapOwnLabel(li);

				if (state[key]) {
					cb.checked = true;
					li.classList.add("completed");
				}

				li.style.cursor = "pointer";
				li.addEventListener("click", (e) => {
					if (e.target.closest("a")) return;
					// A nested item handles its own click; the parent never cascades to children
					if (e.target.closest("li") !== li) return;
					if (hasTextSelection()) return;

					cb.checked = !cb.checked;
					li.classList.toggle("completed", cb.checked);

					var currentState = loadState();
					currentState[key] = cb.checked;
					saveState(currentState, true);
					updateSectionSummaries();
					updateButtonVisibility();
				});
			});
		});
	}

	function stepZoneWidth() {
		return window.matchMedia("(pointer: coarse)").matches ? STEP_ZONE_TOUCH_PX : STEP_ZONE_PX;
	}

	// A step owns only the rows it renders itself: the rows below a nested list belong to
	// the sub-steps drawn there, so the parent's clickable band stops where that list starts
	function ownExtent(li) {
		var rect = li.getBoundingClientRect();
		var nested = li.querySelector(":scope > ol");
		return {
			top: rect.top,
			bottom: nested ? nested.getBoundingClientRect().top : rect.bottom,
			left: rect.left,
		};
	}

	function stepAtClick(section, e) {
		var zone = stepZoneWidth();
		var match = null;
		section.querySelectorAll("ol.recipe-steps > li").forEach((li) => {
			var extent = ownExtent(li);
			if (e.clientY < extent.top || e.clientY > extent.bottom) return;
			if (e.clientX >= extent.left + zone) return;
			if (e.clientX < li.parentElement.getBoundingClientRect().left) return;
			if (!match || extent.left > match.left) match = { li: li, left: extent.left };
		});
		return match?.li;
	}

	// Sizes each tint to the band that actually responds to a click, then reveals them all
	function flashStepZones() {
		document.querySelectorAll("ol.recipe-steps > li").forEach((li) => {
			var extent = ownExtent(li);
			li.style.setProperty("--zone-height", `${extent.bottom - extent.top}px`);
		});
		document.body.classList.add("show-step-zones");
		clearTimeout(zoneHintTimer);
		zoneHintTimer = setTimeout(() => {
			document.body.classList.remove("show-step-zones");
		}, ZONE_HINT_MS);
	}

	function setupStepToggles() {
		var state = loadState();
		var stepIndex = 0;
		var stepMap = new Map();

		document.querySelectorAll("section").forEach((section) => {
			section.querySelectorAll("ol").forEach((ol) => {
				ol.classList.add("recipe-steps");
				ol.querySelectorAll(":scope > li").forEach((li) => {
					var key = `step-${stepIndex}`;
					stepIndex++;
					stepMap.set(li, key);
					wrapOwnLabel(li);
					if (state[key]) {
						li.classList.add("completed");
					}
				});
			});

			function toggleLi(li) {
				li.classList.toggle("completed");
				var currentState = loadState();
				currentState[stepMap.get(li)] = li.classList.contains("completed");
				saveState(currentState, true);
				flashStepZones();
				updateSectionSummaries();
				updateButtonVisibility();
			}

			section.addEventListener("click", (e) => {
				if (e.target.closest("a")) return;
				if (hasTextSelection()) return;
				var li = stepAtClick(section, e);
				if (li && stepMap.has(li)) {
					toggleLi(li);
				}
			});

			section.addEventListener("dblclick", (e) => {
				if (e.target.closest("a")) return;
				var li = e.target.closest("ol.recipe-steps > li");
				if (li && stepMap.has(li)) {
					toggleLi(li);
				}
			});
		});

		document.addEventListener("selectionchange", () => {
			if (hasTextSelection()) {
				clearTimeout(zoneHintTimer);
				document.body.classList.remove("show-step-zones");
			}
		});
	}

	// Ingredient sections are the `Ingredients` h2 section plus the h3 sub-group sections
	// that follow it, which djot emits as siblings rather than as children
	function ingredientSections(main) {
		var collected = [];
		var inRun = false;
		Array.from(main.children).forEach((el) => {
			if (el.tagName !== "SECTION") return;
			var h2 = el.querySelector(":scope > h2");
			if (h2) {
				inRun = /ingredient/i.test(h2.textContent);
			}
			if (inRun) collected.push(el);
		});
		return collected;
	}

	function setupSplitLayout() {
		var main = document.querySelector("main");
		if (!main) return;

		var sourceOrder = Array.from(main.children);
		var ingredients = ingredientSections(main);
		if (ingredients.length === 0 || ingredients.length === sourceOrder.length) return;

		var left = document.createElement("div");
		left.className = "split-pane split-pane-ingredients";
		var right = document.createElement("div");
		right.className = "split-pane split-pane-body";

		function enterSplit() {
			if (main.classList.contains("split-layout")) return;
			sourceOrder.forEach((el) => {
				(ingredients.includes(el) ? left : right).appendChild(el);
			});
			main.append(left, right);
			main.classList.add("split-layout");
		}

		function exitSplit() {
			if (!main.classList.contains("split-layout")) return;
			sourceOrder.forEach((el) => {
				main.appendChild(el);
			});
			left.remove();
			right.remove();
			main.classList.remove("split-layout");
		}

		var query = window.matchMedia(SPLIT_QUERY);
		function apply() {
			if (query.matches) enterSplit();
			else exitSplit();
		}
		query.addEventListener("change", apply);
		apply();
	}

	function trackScroll() {
		var backBtn = document.getElementById("back-btn");
		if (!backBtn) return;

		window.addEventListener("scroll", () => {
			clearTimeout(scrollTimer);
			scrollTimer = setTimeout(() => {
				var currentY = window.scrollY;
				var distance = Math.abs(currentY - lastScrollY);
				if (distance >= SCROLL_MIN_DISTANCE) {
					scrollStack.push(lastScrollY);
					if (scrollStack.length > 20) {
						scrollStack.shift();
					}
					lastScrollY = currentY;
					showBackButton();
				}
			}, SCROLL_PAUSE_MS);
		});
	}

	function showBackButton() {
		var backBtn = document.getElementById("back-btn");
		if (!backBtn || scrollStack.length === 0) return;

		backBtn.style.display = "inline-block";
		backBtn.classList.remove("fading");

		clearTimeout(fadeTimer);
		fadeTimer = setTimeout(() => {
			backBtn.classList.add("fading");
		}, BACK_BUTTON_FADE_MS);
	}

	function goBack() {
		if (scrollStack.length === 0) return;
		var position = scrollStack.pop();
		window.scrollTo({ top: position, behavior: "smooth" });

		var backBtn = document.getElementById("back-btn");
		if (backBtn && scrollStack.length === 0) {
			backBtn.style.display = "none";
		} else {
			showBackButton();
		}
	}

	function hasCompletableContent(section) {
		var checkboxes = section.querySelectorAll("input[type='checkbox']");
		var steps = section.querySelectorAll("ol.recipe-steps li");
		return checkboxes.length > 0 || steps.length > 0;
	}

	function setupSectionFolding() {
		var state = loadState();

		document.querySelectorAll("section").forEach((section) => {
			var heading = section.querySelector("h2") || section.querySelector("h3");
			if (!heading) return;
			if (!hasCompletableContent(section)) return;

			var sectionId = section.id || heading.textContent.trim().toLowerCase().replace(/\s+/g, "-");
			section.classList.add("collapsible");

			var toggle = document.createElement("span");
			toggle.className = "collapse-toggle";
			toggle.textContent = "-";
			toggle.setAttribute("aria-label", "Toggle section");
			heading.appendChild(toggle);

			if (state[`collapsed-${sectionId}`] === true) {
				section.classList.add("collapsed");
				toggle.textContent = "+";
			}

			toggle.addEventListener("click", (e) => {
				e.stopPropagation();
				var isCollapsing = !section.classList.contains("collapsed");

				if (isCollapsing) {
					var completedItems = section.querySelectorAll("li.completed");
					completedItems.forEach((li) => {
						li.classList.add("hiding");
					});
					setTimeout(() => {
						section.classList.add("collapsed");
						toggle.textContent = "+";
						completedItems.forEach((li) => {
							li.classList.remove("hiding");
						});
						updateSectionSummaries();
					}, 400);
				} else {
					section.classList.remove("collapsed");
					toggle.textContent = "-";
					updateSectionSummaries();
				}

				var currentState = loadState();
				currentState[`collapsed-${sectionId}`] = isCollapsing;
				saveState(currentState, false);
				updateButtonVisibility();
			});
		});

		updateSectionSummaries();
	}

	function updateSectionSummaries() {
		document.querySelectorAll("section.collapsible").forEach((section) => {
			var heading = section.querySelector("h2, h3");
			if (!heading) return;

			var existing = heading.querySelector(".section-summary");
			if (existing) {
				existing.remove();
			}

			if (!section.classList.contains("collapsed")) return;

			var checkboxes = section.querySelectorAll("input[type='checkbox']");
			var steps = section.querySelectorAll("ol.recipe-steps li");
			var total = checkboxes.length + steps.length;
			if (total === 0) return;

			var completedCheckboxes = Array.from(checkboxes).filter((cb) => cb.checked).length;
			var completedSteps = Array.from(steps).filter((li) =>
				li.classList.contains("completed"),
			).length;

			var summary = document.createElement("span");
			summary.className = "section-summary";
			summary.textContent = ` (${completedCheckboxes + completedSteps}/${total})`;

			var toggle = heading.querySelector(".collapse-toggle");
			if (toggle) {
				heading.insertBefore(summary, toggle);
			} else {
				heading.appendChild(summary);
			}
		});
	}

	function setupHeaderAnchors() {
		document.querySelectorAll("section[id]").forEach((section) => {
			var heading = section.querySelector("h2, h3");
			if (!heading) return;

			var anchor = document.createElement("a");
			anchor.className = "header-anchor";
			anchor.href = `#${section.id}`;
			anchor.textContent = "#";
			anchor.setAttribute("aria-label", "Link to this section");
			heading.appendChild(anchor);

			anchor.addEventListener("click", (e) => {
				e.preventDefault();
				history.pushState(null, "", `#${section.id}`);
				section.scrollIntoView({ behavior: "smooth" });
			});
		});
	}

	function updateButtonVisibility() {
		var toggleCollapseBtn = document.getElementById("toggle-collapse-btn");
		var resetBtn = document.getElementById("reset-btn");
		var copyBtn = document.getElementById("copy-ingredients-btn");

		var collapsibleSections = document.querySelectorAll("section.collapsible");
		var collapsedSections = document.querySelectorAll("section.collapsed");
		var allCollapsed = collapsedSections.length === collapsibleSections.length;
		var hasCheckedBoxes = document.querySelectorAll("input[type='checkbox']:checked").length > 0;
		var hasCompletedSteps = document.querySelectorAll("ol.recipe-steps li.completed").length > 0;

		if (toggleCollapseBtn && collapsibleSections.length > 0) {
			toggleCollapseBtn.style.display = "inline-block";
			if (allCollapsed) {
				toggleCollapseBtn.textContent = "Expand All";
				toggleCollapseBtn.title = "Expand all collapsed sections";
			} else {
				toggleCollapseBtn.textContent = "Collapse All";
				toggleCollapseBtn.title = "Collapse all sections";
			}
		}
		if (resetBtn) {
			resetBtn.style.display = hasCheckedBoxes || hasCompletedSteps ? "inline-block" : "none";
		}
		if (copyBtn) {
			var hasIngredients = document.querySelectorAll("ul.task-list li").length > 0;
			copyBtn.style.display = hasIngredients ? "inline-block" : "none";
		}
	}

	function expandAll() {
		document.querySelectorAll("section.collapsed").forEach((section) => {
			section.classList.remove("collapsed");
			var toggle = section.querySelector(".collapse-toggle");
			if (toggle) toggle.textContent = "-";
		});

		var state = loadState();
		Object.keys(state).forEach((key) => {
			if (key.startsWith("collapsed-")) {
				delete state[key];
			}
		});
		saveState(state, false);

		updateSectionSummaries();
		updateButtonVisibility();
	}

	function collapseAll() {
		var allCompletedItems = [];
		var state = loadState();

		document.querySelectorAll("section.collapsible:not(.collapsed)").forEach((section) => {
			section.classList.add("collapsed");
			var toggle = section.querySelector(".collapse-toggle");
			if (toggle) toggle.textContent = "+";

			var sectionId =
				section.id ||
				section.querySelector("h2, h3").textContent.trim().toLowerCase().replace(/\s+/g, "-");
			state[`collapsed-${sectionId}`] = true;

			section.querySelectorAll("li.completed").forEach((li) => {
				li.classList.add("hiding");
				allCompletedItems.push(li);
			});
		});

		saveState(state, false);

		setTimeout(() => {
			allCompletedItems.forEach((li) => {
				li.classList.remove("hiding");
			});
			updateSectionSummaries();
			updateButtonVisibility();
		}, 400);
	}

	function resetProgress() {
		var state = loadState();

		document.querySelectorAll("input[type='checkbox']").forEach((cb) => {
			cb.checked = false;
			var li = cb.closest("li");
			if (li) li.classList.remove("completed");
		});

		document.querySelectorAll("ol.recipe-steps li.completed").forEach((li) => {
			li.classList.remove("completed");
		});

		saveState(clearProgressKeys(state), false);

		updateSectionSummaries();
		updateButtonVisibility();
	}

	function toggleCollapseAll() {
		var collapsibleSections = document.querySelectorAll("section.collapsible");
		if (collapsibleSections.length === 0) return;

		var collapsedSections = document.querySelectorAll("section.collapsed");
		if (collapsedSections.length === collapsibleSections.length) {
			expandAll();
		} else {
			collapseAll();
		}
	}

	function uncheckedIngredientsAsDjot() {
		var lines = [];
		document.querySelectorAll("ul.task-list li").forEach((li) => {
			var cb = li.querySelector(":scope > input[type='checkbox']");
			if (!cb || cb.checked) return;
			var text = ownText(li);
			if (text !== "") lines.push(`- ${text}`);
		});
		return lines.join("\n");
	}

	function copyIngredients() {
		var btn = document.getElementById("copy-ingredients-btn");
		var djot = uncheckedIngredientsAsDjot();

		function report(label) {
			if (!btn) return;
			btn.textContent = label;
			clearTimeout(copyTimer);
			copyTimer = setTimeout(() => {
				btn.textContent = "Copy Ingredients";
			}, COPY_FEEDBACK_MS);
		}

		navigator.clipboard.writeText(djot).then(
			() => {
				report(djot === "" ? "Nothing to copy" : "Copied");
			},
			() => {
				// The clipboard is refused when the document is not focused; say so rather
				// than leaving the button looking as though nothing was asked of it
				report("Copy failed");
			},
		);
	}

	function setupToolbarToggle() {
		var toolbar = document.getElementById("recipe-toolbar");
		var toggleBtn = document.getElementById("toolbar-toggle");
		if (!toolbar || !toggleBtn) return;

		var state = loadState();
		if (state["toolbar-hidden"] === false) {
			toolbar.classList.remove("hidden");
		}

		toggleBtn.addEventListener("click", () => {
			toolbar.classList.toggle("hidden");
			var currentState = loadState();
			currentState["toolbar-hidden"] = toolbar.classList.contains("hidden");
			saveState(currentState, false);
		});
	}

	function init() {
		computeContentHash();
		purgeExpiredRecipes();
		setupIngredientCheckboxes();
		setupStepToggles();
		setupSplitLayout();
		setupSectionFolding();
		setupHeaderAnchors();
		setupToolbarToggle();
		trackScroll();

		var backBtn = document.getElementById("back-btn");
		if (backBtn) {
			backBtn.addEventListener("click", goBack);
		}

		var toggleCollapseBtn = document.getElementById("toggle-collapse-btn");
		if (toggleCollapseBtn) {
			toggleCollapseBtn.addEventListener("click", toggleCollapseAll);
		}

		var resetBtn = document.getElementById("reset-btn");
		if (resetBtn) {
			resetBtn.addEventListener("click", resetProgress);
		}

		var copyBtn = document.getElementById("copy-ingredients-btn");
		if (copyBtn) {
			copyBtn.addEventListener("click", copyIngredients);
		}

		updateButtonVisibility();
		lastScrollY = window.scrollY;
	}

	if (document.readyState === "loading") {
		document.addEventListener("DOMContentLoaded", init);
	} else {
		init();
	}
})();
