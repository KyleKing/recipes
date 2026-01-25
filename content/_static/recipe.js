(function () {
  "use strict";

  var SCROLL_PAUSE_MS = 800;
  var SCROLL_MIN_DISTANCE = 100;
  var BACK_BUTTON_FADE_MS = 5000;

  var scrollStack = [];
  var scrollTimer = null;
  var fadeTimer = null;
  var lastScrollY = 0;

  function getStorageKey() {
    return "recipe-progress-" + window.location.pathname;
  }

  function loadState() {
    try {
      var data = localStorage.getItem(getStorageKey());
      return data ? JSON.parse(data) : {};
    } catch (e) {
      return {};
    }
  }

  function saveState(state) {
    try {
      localStorage.setItem(getStorageKey(), JSON.stringify(state));
    } catch (e) {
      // Storage unavailable
    }
  }

  function setupIngredientCheckboxes() {
    var state = loadState();
    var taskLists = document.querySelectorAll(".task-list");

    taskLists.forEach(function (list) {
      var items = list.querySelectorAll(":scope > li");
      items.forEach(function (li, index) {
        var cb = li.querySelector("input[type='checkbox']");
        if (!cb) return;

        var key = "ingredient-" + index;
        if (state[key]) {
          cb.checked = true;
          li.classList.add("completed");
        }

        li.style.cursor = "pointer";
        li.addEventListener("click", function (e) {
          if (e.target.tagName === "A") return;
          cb.checked = !cb.checked;
          li.classList.toggle("completed", cb.checked);
          var currentState = loadState();
          currentState[key] = cb.checked;
          saveState(currentState);
          updateSectionSummaries();
          updateButtonVisibility();
        });
      });
    });
  }

  function setupStepToggles() {
    var state = loadState();
    var allStepSections = document.querySelectorAll("section");
    var stepIndex = 0;
    var stepMap = new Map();

    allStepSections.forEach(function (section) {
      var orderedLists = section.querySelectorAll("ol");
      orderedLists.forEach(function (ol) {
        ol.classList.add("recipe-steps");
        var items = ol.querySelectorAll(":scope > li");
        items.forEach(function (li) {
          var key = "step-" + stepIndex;
          stepIndex++;
          stepMap.set(li, key);

          if (state[key]) {
            li.classList.add("completed");
          }
        });
      });

      function toggleLi(li) {
        li.classList.toggle("completed");
        var key = stepMap.get(li);
        var currentState = loadState();
        currentState[key] = li.classList.contains("completed");
        saveState(currentState);
        updateSectionSummaries();
        updateButtonVisibility();
      }

      section.addEventListener("click", function (e) {
        var allItems = section.querySelectorAll("ol.recipe-steps > li");
        for (var i = 0; i < allItems.length; i++) {
          var li = allItems[i];
          var rect = li.getBoundingClientRect();
          var clickX = e.clientX - rect.left;
          if (
            e.clientY >= rect.top &&
            e.clientY <= rect.bottom &&
            clickX < 30
          ) {
            toggleLi(li);
            break;
          }
        }
      });

      section.addEventListener("dblclick", function (e) {
        var li = e.target.closest("ol.recipe-steps > li");
        if (li && stepMap.has(li)) {
          toggleLi(li);
        }
      });
    });
  }

  function trackScroll() {
    var backBtn = document.getElementById("back-btn");
    if (!backBtn) return;

    window.addEventListener("scroll", function () {
      clearTimeout(scrollTimer);
      scrollTimer = setTimeout(function () {
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
    fadeTimer = setTimeout(function () {
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
    var sections = document.querySelectorAll("section");

    sections.forEach(function (section) {
      var h2 = section.querySelector("h2");
      var h3 = section.querySelector("h3");
      var heading = h2 || h3;
      if (!heading) return;

      if (!hasCompletableContent(section)) return;

      var sectionId =
        section.id ||
        heading.textContent.trim().toLowerCase().replace(/\s+/g, "-");
      section.classList.add("collapsible");

      var toggle = document.createElement("span");
      toggle.className = "collapse-toggle";
      toggle.textContent = "-";
      toggle.setAttribute("aria-label", "Toggle section");
      heading.appendChild(toggle);

      if (state["collapsed-" + sectionId]) {
        section.classList.add("collapsed");
        toggle.textContent = "+";
      }

      toggle.addEventListener("click", function (e) {
        e.stopPropagation();
        var isCollapsing = !section.classList.contains("collapsed");

        if (isCollapsing) {
          var completedItems = section.querySelectorAll("li.completed");
          completedItems.forEach(function (li) {
            li.classList.add("hiding");
          });
          setTimeout(function () {
            section.classList.add("collapsed");
            toggle.textContent = "+";
            completedItems.forEach(function (li) {
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
        currentState["collapsed-" + sectionId] = isCollapsing;
        saveState(currentState);
        updateButtonVisibility();
      });
    });

    updateSectionSummaries();
  }

  function updateSectionSummaries() {
    var sections = document.querySelectorAll("section.collapsible");

    sections.forEach(function (section) {
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

      var completedCheckboxes = Array.from(checkboxes).filter(function (cb) {
        return cb.checked;
      }).length;
      var completedSteps = Array.from(steps).filter(function (li) {
        return li.classList.contains("completed");
      }).length;
      var completed = completedCheckboxes + completedSteps;

      var summary = document.createElement("span");
      summary.className = "section-summary";
      summary.textContent = " (" + completed + "/" + total + ")";

      var toggle = heading.querySelector(".collapse-toggle");
      if (toggle) {
        heading.insertBefore(summary, toggle);
      } else {
        heading.appendChild(summary);
      }
    });
  }

  function setupHeaderAnchors() {
    var sections = document.querySelectorAll("section[id]");

    sections.forEach(function (section) {
      var heading = section.querySelector("h2, h3");
      if (!heading) return;

      var anchor = document.createElement("a");
      anchor.className = "header-anchor";
      anchor.href = "#" + section.id;
      anchor.textContent = "#";
      anchor.setAttribute("aria-label", "Link to this section");
      heading.appendChild(anchor);

      anchor.addEventListener("click", function (e) {
        e.preventDefault();
        history.pushState(null, "", "#" + section.id);
        section.scrollIntoView({ behavior: "smooth" });
      });
    });
  }

  function updateButtonVisibility() {
    var toggleCollapseBtn = document.getElementById("toggle-collapse-btn");
    var resetBtn = document.getElementById("reset-btn");

    var collapsibleSections = document.querySelectorAll("section.collapsible");
    var collapsedSections = document.querySelectorAll("section.collapsed");
    var allCollapsed = collapsedSections.length === collapsibleSections.length;
    var hasCheckedBoxes =
      document.querySelectorAll("input[type='checkbox']:checked").length > 0;
    var hasCompletedSteps =
      document.querySelectorAll("ol.recipe-steps li.completed").length > 0;

    if (toggleCollapseBtn && collapsibleSections.length > 0) {
      toggleCollapseBtn.style.display = "inline-block";
      // Update button text based on current state
      if (allCollapsed) {
        toggleCollapseBtn.textContent = "Expand All";
        toggleCollapseBtn.title = "Expand all collapsed sections";
      } else {
        toggleCollapseBtn.textContent = "Collapse All";
        toggleCollapseBtn.title = "Collapse all sections";
      }
    }
    if (resetBtn) {
      resetBtn.style.display =
        hasCheckedBoxes || hasCompletedSteps ? "inline-block" : "none";
    }
  }

  function expandAll() {
    document.querySelectorAll("section.collapsed").forEach(function (section) {
      section.classList.remove("collapsed");
      var toggle = section.querySelector(".collapse-toggle");
      if (toggle) toggle.textContent = "-";
    });

    var state = loadState();
    Object.keys(state).forEach(function (key) {
      if (key.startsWith("collapsed-")) {
        delete state[key];
      }
    });
    saveState(state);

    updateSectionSummaries();
    updateButtonVisibility();
  }

  function collapseAll() {
    var sections = document.querySelectorAll(
      "section.collapsible:not(.collapsed)",
    );
    var allCompletedItems = [];
    var state = loadState();

    sections.forEach(function (section) {
      // Add collapsed class immediately to fix double-click issue
      section.classList.add("collapsed");
      var toggle = section.querySelector(".collapse-toggle");
      if (toggle) toggle.textContent = "+";

      var sectionId =
        section.id ||
        section
          .querySelector("h2, h3")
          .textContent.trim()
          .toLowerCase()
          .replace(/\s+/g, "-");
      state["collapsed-" + sectionId] = true;

      var completedItems = section.querySelectorAll("li.completed");
      completedItems.forEach(function (li) {
        li.classList.add("hiding");
        allCompletedItems.push(li);
      });
    });

    // Save state immediately
    saveState(state);

    setTimeout(function () {
      allCompletedItems.forEach(function (li) {
        li.classList.remove("hiding");
      });
      updateSectionSummaries();
      updateButtonVisibility();
    }, 400);
  }

  function resetProgress() {
    var state = loadState();

    document.querySelectorAll("input[type='checkbox']").forEach(function (cb) {
      cb.checked = false;
      var li = cb.closest("li");
      if (li) li.classList.remove("completed");
    });

    document
      .querySelectorAll("ol.recipe-steps li.completed")
      .forEach(function (li) {
        li.classList.remove("completed");
      });

    Object.keys(state).forEach(function (key) {
      if (key.startsWith("ingredient-") || key.startsWith("step-")) {
        delete state[key];
      }
    });
    saveState(state);

    updateSectionSummaries();
    updateButtonVisibility();
  }

  function toggleCollapseAll() {
    var collapsibleSections = document.querySelectorAll("section.collapsible");
    var collapsedSections = document.querySelectorAll("section.collapsed");
    
    // Only proceed if there are collapsible sections
    if (collapsibleSections.length === 0) return;
    
    var allCollapsed = collapsedSections.length === collapsibleSections.length;

    if (allCollapsed) {
      expandAll();
    } else {
      collapseAll();
    }
  }

  function init() {
    if (document.body.classList.contains("trmnl-mode")) return;

    setupIngredientCheckboxes();
    setupStepToggles();
    trackScroll();
    setupSectionFolding();
    setupHeaderAnchors();

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

    updateButtonVisibility();
    lastScrollY = window.scrollY;
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
