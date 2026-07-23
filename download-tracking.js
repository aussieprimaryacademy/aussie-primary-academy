// APA Download Tracking
// Automatically adds the "download" attribute to every PDF link on the page
// and fires a Google Analytics 4 event each time someone clicks a worksheet download.
// Add this file to your repo, then add this line before </body> on any page with PDF links:
// <script src="download-tracking.js"></script>

document.addEventListener("DOMContentLoaded", function () {
  const pdfLinks = document.querySelectorAll('a[href$=".pdf"]');

  pdfLinks.forEach(function (link) {
    if (!link.hasAttribute("download")) {
      link.setAttribute("download", "");
    }

    link.addEventListener("click", function () {
      if (typeof gtag === "function") {
        gtag("event", "worksheet_download", {
          file_name: link.getAttribute("href"),
          link_text: link.textContent.trim()
        });
      }
    });
  });
});
