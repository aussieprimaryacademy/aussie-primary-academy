// APA Download Tracking — keeps worksheet_download event name stable.
(function () {
  "use strict";
  function contextFor(link, href) {
    const path = location.pathname;
    const combined = path + " " + href;
    const yearMatch = combined.match(/(?:foundation|year[-_ ]?([1-6]))/i);
    const yearLevel = /foundation/i.test(combined) ? "Foundation" :
      (yearMatch && yearMatch[1] ? "Year " + yearMatch[1] : "unknown");
    const subjectMatch = combined.match(/(?:^|[/_-])(maths?|english|science|phonics|reading|writing)(?:[/_-]|$)/i);
    return {
      year_level: yearLevel,
      subject: subjectMatch ? subjectMatch[1].replace(/s$/i, "").toLowerCase() : "unknown",
      page_path: path
    };
  }
  function trackDownload(link) {
    if (typeof gtag !== "function") return;
    const href = link.getAttribute("href") || "";
    const fileName = href.split("/").pop().split("?")[0];
    gtag("event", "worksheet_download", Object.assign({
      file_name: fileName, link_url: link.href,
      link_text: link.textContent.trim(), file_extension: "pdf"
    }, contextFor(link, href)));
  }
  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("a[href]").forEach(function (link) {
      try {
        if (!new URL(link.href, document.baseURI).pathname.toLowerCase().endsWith(".pdf")) return;
      } catch (_) { return; }
      if (link.dataset.apaDownloadTracked === "true") return;
      link.dataset.apaDownloadTracked = "true";
      link.addEventListener("click", function () { trackDownload(link); });
    });
  });
})();
