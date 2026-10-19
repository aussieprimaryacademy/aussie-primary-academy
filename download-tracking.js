// APA Download Tracking
// Tracks worksheet PDF clicks without forcing browser downloads.

(function () {
  "use strict";

  function trackDownload(link) {
    if (typeof gtag !== "function") return;

    const href = link.getAttribute("href") || "";
    gtag("event", "worksheet_download", {
      file_name: href.split("/").pop().split("?")[0],
      link_url: link.href,
      link_text: link.textContent.trim(),
      file_extension: "pdf"
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    const pdfLinks = document.querySelectorAll('a[href$=".pdf"], a[href$=".PDF"]');

    pdfLinks.forEach(function (link) {
      if (link.dataset.apaDownloadTracked === "true") return;
      link.dataset.apaDownloadTracked = "true";


      link.addEventListener("click", function () {
        trackDownload(link);
      });
    });
  });
})();
