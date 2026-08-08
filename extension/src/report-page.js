/**
 * Glue for the report viewer. Reads a file, validates it is a SaysWho report, hands it to render.js.
 *
 * The validation is not politeness. Rendering an arbitrary JSON file would produce a page with empty
 * verdicts and no marks, which looks like an audit that found nothing rather than a file that was never an
 * audit.
 */

(function () {
  "use strict";

  const loader = document.getElementById("sayswho-loader");
  const target = document.getElementById("sayswho-report");
  const error = document.getElementById("sw-err");
  const drop = document.getElementById("sw-drop");

  function fail(message) {
    error.hidden = false;
    error.textContent = message;
  }

  function show(payload) {
    if (!payload || payload.generated_by !== "SaysWho" || !Array.isArray(payload.claims)) {
      return fail("That file is not a SaysWho report. Expected the JSON written by --report-json.");
    }
    error.hidden = true;
    loader.hidden = true;
    window.saysWhoRender(target, payload);
    document.title = "SaysWho: " + (payload.meta && payload.meta.product) + " answer";
  }

  function read(file) {
    if (!file) return;
    const reader = new FileReader();
    reader.onerror = function () { fail("Could not read that file."); };
    reader.onload = function () {
      let payload;
      try {
        payload = JSON.parse(reader.result);
      } catch (exc) {
        return fail("That file is not valid JSON: " + exc.message);
      }
      show(payload);
    };
    reader.readAsText(file);
  }

  document.getElementById("sw-file").addEventListener("change", function (event) {
    read(event.target.files && event.target.files[0]);
  });

  ["dragenter", "dragover"].forEach(function (name) {
    drop.addEventListener(name, function (event) {
      event.preventDefault();
      drop.classList.add("sw-over");
    });
  });
  ["dragleave", "drop"].forEach(function (name) {
    drop.addEventListener(name, function (event) {
      event.preventDefault();
      drop.classList.remove("sw-over");
    });
  });
  drop.addEventListener("drop", function (event) {
    read(event.dataTransfer && event.dataTransfer.files && event.dataTransfer.files[0]);
  });
})();
