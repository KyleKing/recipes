(() => {
	var SCROLL_PAUSE_MS = 800;
	var SCROLL_MIN_DISTANCE = 100;
	var BACK_BUTTON_FADE_MS = 5000;
	var PROGRESS_MAX_AGE_MS = 48 * 60 * 60 * 1000;
	var STORAGE_PREFIX = "recipe-progress-";
	var COPY_FEEDBACK_MS = 1500;
	var SUBSTITUTIONS_URL = "/_static/substitutions.json";
	var INGREDIENT_INDEX_URL = "/_static/ingredient-index.json";
	var SPLIT_QUERY =
		"(pointer: coarse) and (orientation: landscape) and (min-width: 900px) and (max-height: 900px)";
	var SPLIT_DISABLED_KEY = "recipe-split-disabled";

	var scrollStack = [];
	var scrollTimer = null;
	var fadeTimer = null;
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

	var ingredientRows = [];
	var stepRows = [];
	var rowsByKey = new Map();
	var selectedRow = null;

	// Info mode is deliberately not persisted: it changes what a tap does, so a page must
	// always open in the state where tapping a row checks it off
	function infoMode() {
		return document.body.classList.contains("info-mode");
	}

	function keysOf(label) {
		var keys = [];
		label.querySelectorAll(".ing-ref").forEach((span) => {
			span.dataset.ing.split(/\s+/).forEach((key) => {
				if (key !== "" && !keys.includes(key)) keys.push(key);
			});
		});
		return keys;
	}

	function registerRow(row) {
		(row.kind === "ingredient" ? ingredientRows : stepRows).push(row);
		row.keys.forEach((key) => {
			if (!rowsByKey.has(key)) rowsByKey.set(key, { ingredient: [], step: [] });
			rowsByKey.get(key)[row.kind].push(row);
		});
	}

	// Every row carries the same two controls: the label toggles it done, the trailing
	// button selects it. No row responds to a click anywhere else.
	function buildRow(li, kind, key) {
		wrapOwnLabel(li);
		var label = li.querySelector(":scope > .item-label");
		var row = { li: li, label: label, kind: kind, storageKey: key, keys: keysOf(label) };
		li.classList.add("recipe-row");

		label.addEventListener("click", (e) => {
			if (e.target.closest("a")) return;
			if (hasTextSelection()) return;
			if (infoMode() && row.keys.length > 0) {
				selectRow(selectedRow === row ? null : row);
				return;
			}
			toggleRow(row);
		});

		// The underline on an `.ing-ref` is a hint, never its own target: on an ingredient
		// row it covers most of the label, so making it tappable would leave the row with
		// no reliable place to check off
		if (row.keys.length > 0) li.classList.add("has-info");

		registerRow(row);
		return row;
	}

	function isDone(row) {
		return row.li.classList.contains("completed");
	}

	function toggleRow(row) {
		var done = !isDone(row);
		row.li.classList.toggle("completed", done);
		if (row.kind === "ingredient") {
			var cb = row.li.querySelector(":scope > input[type='checkbox']");
			if (cb) cb.checked = done;
		}

		var state = loadState();
		state[row.storageKey] = done;
		saveState(state, true);

		applyRetirement();
		updateSectionSummaries();
		updateButtonVisibility();
	}

	// A step consumes its ingredients: completing it spends them, and an ingredient stays
	// spent only while some completed step still claims it
	function applyRetirement() {
		var spent = new Set();
		stepRows.forEach((row) => {
			if (isDone(row)) {
				row.keys.forEach((key) => {
					spent.add(key);
				});
			}
		});
		ingredientRows.forEach((row) => {
			row.li.classList.toggle(
				"spent",
				row.keys.some((key) => spent.has(key)),
			);
		});
	}

	function setupIngredientRows() {
		var state = loadState();
		var index = 0;

		document.querySelectorAll("ul.task-list").forEach((list) => {
			list.querySelectorAll(":scope > li").forEach((li) => {
				var cb = li.querySelector(":scope > input[type='checkbox']");
				if (!cb) return;

				var key = `ingredient-${index}`;
				index++;
				cb.dataset.storageKey = key;
				if (state[key]) {
					cb.checked = true;
					li.classList.add("completed");
				}
				buildRow(li, "ingredient", key);
			});
		});
	}

	function setupStepRows() {
		var state = loadState();
		var index = 0;

		document.querySelectorAll("section ol").forEach((ol) => {
			ol.classList.add("recipe-steps");
			ol.querySelectorAll(":scope > li").forEach((li) => {
				var key = `step-${index}`;
				index++;
				if (state[key]) li.classList.add("completed");
				var row = buildRow(li, "step", key);
				row.number = Array.from(ol.children).indexOf(li) + 1;
			});
		});
	}

	var referenceData = null;

	// Both tables are static build output, so one fetch per page load serves every dossier
	function loadReferenceData() {
		if (referenceData) return referenceData;
		referenceData = Promise.all([
			fetch(SUBSTITUTIONS_URL).then((r) => r.json()),
			fetch(INGREDIENT_INDEX_URL).then((r) => r.json()),
		])
			.then(([substitutions, index]) => ({ substitutions: substitutions, index: index }))
			.catch(() => ({ substitutions: {}, index: {} }));
		return referenceData;
	}

	function panelElement() {
		var panel = document.getElementById("recipe-panel");
		if (panel) return panel;
		panel = document.createElement("aside");
		panel.id = "recipe-panel";
		panel.className = "recipe-panel";
		panel.hidden = true;
		var close = document.createElement("button");
		close.type = "button";
		close.className = "panel-close";
		close.setAttribute("aria-label", "Close");
		close.textContent = "\u00d7";
		close.addEventListener("click", () => {
			selectRow(null);
		});
		var body = document.createElement("div");
		body.className = "panel-body";
		panel.append(close, body);
		document.body.appendChild(panel);
		return panel;
	}

	function heading(body, text) {
		var el = document.createElement("h2");
		el.className = "panel-title";
		el.textContent = text;
		body.appendChild(el);
	}

	function paragraph(body, text, className) {
		var el = document.createElement("p");
		if (className) el.className = className;
		el.textContent = text;
		body.appendChild(el);
	}

	function jumpButton(body, row, text) {
		var btn = document.createElement("button");
		btn.type = "button";
		btn.className = "panel-jump";
		btn.textContent = text;
		btn.addEventListener("click", () => {
			selectRow(row);
			row.li.scrollIntoView({ behavior: "smooth", block: "center" });
		});
		body.appendChild(btn);
	}

	function renderStepPanel(body, row) {
		heading(body, `Step ${row.number} needs`);
		row.keys.forEach((key) => {
			(rowsByKey.get(key)?.ingredient || []).forEach((ingredient) => {
				jumpButton(body, ingredient, ownText(ingredient.li));
			});
		});
	}

	function renderSubstitution(body, entry) {
		var block = document.createElement("div");
		block.className = "panel-substitution";
		var title = document.createElement("h3");
		title.textContent = entry.use
			? `${entry.amount} ${entry.name} (${entry.use})`
			: `${entry.amount} ${entry.name}`;
		block.appendChild(title);
		var list = document.createElement("ul");
		entry.items.forEach((item) => {
			var li = document.createElement("li");
			li.textContent = item;
			list.appendChild(li);
		});
		block.appendChild(list);
		if (entry.note) {
			var note = document.createElement("p");
			note.className = "panel-note";
			note.textContent = entry.note;
			block.appendChild(note);
		}
		var link = document.createElement("a");
		link.href = entry.href;
		link.textContent = "Full entry";
		block.appendChild(link);
		body.appendChild(block);
	}

	function renderIngredientPanel(body, row, data) {
		heading(body, ownText(row.li));

		var entries = row.keys.flatMap((key) => data.substitutions[key] || []);
		if (entries.length > 0) {
			entries.forEach((entry) => {
				renderSubstitution(body, entry);
			});
		} else {
			paragraph(body, "No substitute recorded for this ingredient.", "panel-empty");
		}

		var steps = row.keys.flatMap((key) => rowsByKey.get(key)?.step || []);
		if (steps.length > 0) {
			paragraph(body, "Used in", "panel-label");
			steps.forEach((step) => {
				jumpButton(body, step, `Step ${step.number}: ${ownText(step.li)}`);
			});
		}

		var elsewhere = row.keys
			.flatMap((key) => data.index[key] || [])
			.filter((use) => use.url !== window.location.pathname);
		if (elsewhere.length > 0) {
			paragraph(body, "Also used in", "panel-label");
			var list = document.createElement("ul");
			list.className = "panel-recipes";
			elsewhere.forEach((use) => {
				var li = document.createElement("li");
				var link = document.createElement("a");
				link.href = use.url;
				link.textContent = use.name;
				li.appendChild(link);
				list.appendChild(li);
			});
			body.appendChild(list);
		}
	}

	// One selection at a time and mutual: a selected step lights its ingredients, a selected
	// ingredient lights the steps that use it, and the panel shows the other side's detail
	function selectRow(row) {
		selectedRow = row;
		document.querySelectorAll(".recipe-row.selected, .recipe-row.lit").forEach((li) => {
			li.classList.remove("selected", "lit");
		});
		document.body.classList.toggle("has-selection", Boolean(row));

		var panel = panelElement();
		if (!row) {
			panel.hidden = true;
			return;
		}

		row.li.classList.add("selected");
		var counterpart = row.kind === "ingredient" ? "step" : "ingredient";
		row.keys.forEach((key) => {
			(rowsByKey.get(key)?.[counterpart] || []).forEach((other) => {
				other.li.classList.add("lit");
			});
		});

		var body = panel.querySelector(".panel-body");
		body.textContent = "";
		panel.hidden = false;

		if (row.kind === "step") {
			renderStepPanel(body, row);
			return;
		}
		paragraph(body, "Loading\u2026", "panel-empty");
		loadReferenceData().then((data) => {
			if (selectedRow !== row) return;
			body.textContent = "";
			renderIngredientPanel(body, row, data);
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

		var stepsPane = document.createElement("div");
		stepsPane.className = "split-pane split-pane-body";
		var ingredientsPane = document.createElement("div");
		ingredientsPane.className = "split-pane split-pane-ingredients";

		function enterSplit() {
			if (main.classList.contains("split-layout")) return;
			sourceOrder.forEach((el) => {
				(ingredients.includes(el) ? ingredientsPane : stepsPane).appendChild(el);
			});
			main.append(stepsPane, ingredientsPane);
			main.classList.add("split-layout");
		}

		function exitSplit() {
			if (!main.classList.contains("split-layout")) return;
			sourceOrder.forEach((el) => {
				main.appendChild(el);
			});
			stepsPane.remove();
			ingredientsPane.remove();
			main.classList.remove("split-layout");
		}

		var query = window.matchMedia(SPLIT_QUERY);
		var toggleBtn = document.getElementById("split-toggle-btn");

		function userDisabled() {
			return localStorage.getItem(SPLIT_DISABLED_KEY) === "1";
		}

		function updateToggleBtn() {
			if (!toggleBtn) return;
			toggleBtn.style.display = query.matches ? "inline-block" : "none";
			toggleBtn.textContent = userDisabled() ? "Split View: Off" : "Split View: On";
		}

		function apply() {
			if (query.matches && !userDisabled()) enterSplit();
			else exitSplit();
			updateToggleBtn();
		}

		query.addEventListener("change", apply);
		if (toggleBtn) {
			toggleBtn.addEventListener("click", () => {
				if (userDisabled()) localStorage.removeItem(SPLIT_DISABLED_KEY);
				else localStorage.setItem(SPLIT_DISABLED_KEY, "1");
				apply();
			});
		}
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

		selectRow(null);
		applyRetirement();

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

	function setupInfoMode() {
		var btn = document.getElementById("info-btn");
		if (!btn) return;
		if (document.querySelectorAll(".recipe-row.has-info").length === 0) return;

		function paint() {
			var on = infoMode();
			btn.textContent = on ? "Info: On" : "Info: Off";
			btn.setAttribute("aria-pressed", String(on));
		}

		btn.style.display = "inline-block";
		paint();
		btn.addEventListener("click", () => {
			document.body.classList.toggle("info-mode");
			if (!infoMode()) selectRow(null);
			paint();
		});
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
		setupIngredientRows();
		setupStepRows();
		applyRetirement();
		setupSplitLayout();
		setupSectionFolding();
		setupHeaderAnchors();
		setupInfoMode();
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
