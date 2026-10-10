document.addEventListener("DOMContentLoaded", function () {
  const toggle = document.querySelector(".nav-toggle");
  const nav = document.querySelector(".nav-links");
  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      const opened = nav.classList.toggle("nav-open");
      toggle.setAttribute("aria-expanded", String(opened));
    });
  }

  const checklist = document.querySelector("#checklist-items");
  if (checklist) {
    const storageKey = "safetrip-checklist-v1";
    let saved = {};
    try { saved = JSON.parse(localStorage.getItem(storageKey) || "{}"); } catch (_) { saved = {}; }
    const boxes = Array.from(checklist.querySelectorAll("input[type=checkbox]"));
    const progress = document.querySelector("#check-progress");
    const count = document.querySelector("#check-count");
    const complete = document.querySelector("#check-complete");

    function update() {
      const done = boxes.filter(box => box.checked).length;
      if (progress) progress.style.width = (done / boxes.length * 100) + "%";
      if (count) count.textContent = done + " of " + boxes.length + " completed";
      if (complete) complete.hidden = done !== boxes.length;
      const state = {};
      boxes.forEach(box => state[box.dataset.check] = box.checked);
      try { localStorage.setItem(storageKey, JSON.stringify(state)); } catch (_) {}
    }
    boxes.forEach(box => {
      box.checked = Boolean(saved[box.dataset.check]);
      box.addEventListener("change", update);
    });
    const reset = document.querySelector("#reset-checklist");
    if (reset) reset.addEventListener("click", function () {
      boxes.forEach(box => box.checked = false);
      update();
    });
    update();
  }
});
