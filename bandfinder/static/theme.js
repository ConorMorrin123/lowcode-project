// Dark / light mode toggle for Band Finder.
// The choice is saved in the browser (localStorage), so it is remembered next visit.
// This is only a display preference: no app data is stored here.
(function () {
  var saved = null;
  try { saved = localStorage.getItem("bandfinder-theme"); } catch (e) { /* storage blocked */ }
  var theme = saved === "light" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", theme);

  function updateButton(button) {
    var current = document.documentElement.getAttribute("data-theme");
    button.querySelector(".theme-label").textContent = current === "dark" ? "Light mode" : "Dark mode";
    button.setAttribute("aria-pressed", current === "light" ? "true" : "false");
  }

  document.addEventListener("DOMContentLoaded", function () {
    var button = document.getElementById("theme-toggle");
    if (!button) { return; }
    updateButton(button);
    button.addEventListener("click", function () {
      var next = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      try { localStorage.setItem("bandfinder-theme", next); } catch (e) { /* storage blocked */ }
      updateButton(button);
    });
  });
})();
