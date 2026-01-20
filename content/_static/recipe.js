(function () {
  "use strict";

  var SCROLL_PAUSE_MS = 2000;
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
    var checkboxes = document.querySelectorAll(
      ".task-list input[type='checkbox']",
    );
    checkboxes.forEach(function (cb, index) {
      var key = "ingredient-" + index;
      if (state[key]) {
        cb.checked = true;
        cb.closest("li").classList.add("completed");
      }
      cb.addEventListener("change", function () {
        var currentState = loadState();
        currentState[key] = cb.checked;
        saveState(currentState);
        if (cb.checked) {
          cb.closest("li").classList.add("completed");
        } else {
          cb.closest("li").classList.remove("completed");
        }
        updateSectionSummaries();
      });
    });
  }

  function injectStepCheckboxes() {
    var state = loadState();
    var recipeSection = null;
    var notesSection = null;
    var sections = document.querySelectorAll("section");

    sections.forEach(function (section) {
      var h2 = section.querySelector("h2");
      if (h2) {
        var text = h2.textContent.trim().toLowerCase();
        if (text === "recipe") {
          recipeSection = section;
        } else if (text === "notes") {
          notesSection = section;
        }
      }
    });

    if (!recipeSection) return;

    var orderedLists = recipeSection.querySelectorAll("ol");
    orderedLists.forEach(function (ol) {
      ol.classList.add("recipe-steps");
      var items = ol.querySelectorAll(":scope > li");
      items.forEach(function (li, index) {
        var key = "step-" + ol.id + "-" + index;
        var checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.className = "step-checkbox";
        checkbox.setAttribute("aria-label", "Mark step complete");
        if (state[key]) {
          checkbox.checked = true;
          li.classList.add("completed");
        }
        checkbox.addEventListener("change", function () {
          var currentState = loadState();
          currentState[key] = checkbox.checked;
          saveState(currentState);
          if (checkbox.checked) {
            li.classList.add("completed");
          } else {
            li.classList.remove("completed");
          }
          updateSectionSummaries();
        });
        li.insertBefore(checkbox, li.firstChild);
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

  function setupSectionFolding() {
    var state = loadState();
    var sections = document.querySelectorAll("section");

    sections.forEach(function (section) {
      var h2 = section.querySelector("h2");
      var h3 = section.querySelector("h3");
      var heading = h2 || h3;
      if (!heading) return;

      var sectionId =
        section.id ||
        heading.textContent.trim().toLowerCase().replace(/\s+/g, "-");
      section.classList.add("collapsible");

      if (state["collapsed-" + sectionId]) {
        section.classList.add("collapsed");
      }

      heading.addEventListener("click", function () {
        section.classList.toggle("collapsed");
        var currentState = loadState();
        currentState["collapsed-" + sectionId] =
          section.classList.contains("collapsed");
        saveState(currentState);
      });
    });

    updateSectionSummaries();
  }

  function updateSectionSummaries() {
    var sections = document.querySelectorAll("section.collapsible");

    sections.forEach(function (section) {
      var existing = section.querySelector(".section-summary");
      if (existing) {
        existing.remove();
      }

      var checkboxes = section.querySelectorAll("input[type='checkbox']");
      if (checkboxes.length === 0) return;

      var completed = Array.from(checkboxes).filter(function (cb) {
        return cb.checked;
      }).length;

      var summary = document.createElement("div");
      summary.className = "section-summary";
      summary.textContent = completed + "/" + checkboxes.length + " complete";

      var heading = section.querySelector("h2, h3");
      if (heading && heading.nextSibling) {
        heading.parentNode.insertBefore(summary, heading.nextSibling);
      }
    });
  }

  function setupHeaderAnchors() {
    var sections = document.querySelectorAll("section[id]");

    sections.forEach(function (section) {
      var heading = section.querySelector("h2, h3");
      if (!heading) return;

      heading.classList.add("has-anchor");
      heading.addEventListener("click", function (e) {
        if (e.target.tagName === "INPUT") return;

        var url =
          window.location.origin + window.location.pathname + "#" + section.id;
        navigator.clipboard.writeText(url).then(function () {
          heading.classList.add("anchor-copied");
          setTimeout(function () {
            heading.classList.remove("anchor-copied");
          }, 1500);
        });
      });
    });
  }

  function resetProgress() {
    localStorage.removeItem(getStorageKey());

    document.querySelectorAll("input[type='checkbox']").forEach(function (cb) {
      cb.checked = false;
      var li = cb.closest("li");
      if (li) li.classList.remove("completed");
    });

    document.querySelectorAll("section.collapsed").forEach(function (section) {
      section.classList.remove("collapsed");
    });

    updateSectionSummaries();

    scrollStack = [];
    var backBtn = document.getElementById("back-btn");
    if (backBtn) backBtn.style.display = "none";
  }

  function init() {
    if (document.body.classList.contains("trmnl-mode")) return;

    setupIngredientCheckboxes();
    injectStepCheckboxes();
    trackScroll();
    setupSectionFolding();
    setupHeaderAnchors();

    var backBtn = document.getElementById("back-btn");
    if (backBtn) {
      backBtn.addEventListener("click", goBack);
    }

    var resetBtn = document.getElementById("reset-btn");
    if (resetBtn) {
      resetBtn.addEventListener("click", resetProgress);
    }

    lastScrollY = window.scrollY;
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
