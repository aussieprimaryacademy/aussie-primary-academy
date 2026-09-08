// APA Download Tracking
// Adds the browser download attribute to PDF links and records a custom
// worksheet_download event in Google Analytics 4 for every worksheet PDF click.

document.addEventListener("DOMContentLoaded", function () {
  const pdfLinks = document.querySelectorAll('a[href$=".pdf"], a[href$=".PDF"]');

  pdfLinks.forEach(function (link) {
    if (link.dataset.apaDownloadTracked === "true") return;
    link.dataset.apaDownloadTracked = "true";

    if (!link.hasAttribute("download")) {
      link.setAttribute("download", "");
    }

    link.addEventListener("click", function () {
      if (typeof gtag === "function") {
        const href = link.getAttribute("href") || "";
        gtag("event", "worksheet_download", {
          file_name: href.split("/").pop().split("?")[0],
          link_url: link.href,
          link_text: link.textContent.trim(),
          file_extension: "pdf"
        });
      }
    });
  });
});
