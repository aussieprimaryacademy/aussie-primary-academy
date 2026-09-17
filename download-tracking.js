// APA Download Tracking + Email Gate
// Keeps worksheet PDF links tracked in GA4 and adds a soft email gate
// before the PDF is opened. The gate reuses the existing Brevo form on
// the APA homepage so there is only one email collection system.

(function () {
  "use strict";

  const SITE_HOME = "https://aussieprimaryacademy.github.io/aussie-primary-academy/index.html#newsletter";
  const UNLOCK_KEY = "apa_email_gate_unlocked";

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

  function injectStyles() {
    if (document.getElementById("apa-email-gate-styles")) return;

    const style = document.createElement("style");
    style.id = "apa-email-gate-styles";
    style.textContent = `
      .apa-email-gate-backdrop{position:fixed;inset:0;background:rgba(35,27,42,.48);display:flex;align-items:center;justify-content:center;padding:18px;z-index:99999}
      .apa-email-gate{position:relative;width:min(560px,100%);background:#fff;border:1px solid #eadff0;border-radius:18px;padding:26px;box-shadow:0 20px 60px rgba(35,27,42,.22)}
      .apa-email-gate h2{margin:0 36px 8px 0;color:#4A3358;font-size:1.35rem;line-height:1.3}
      .apa-email-gate p{margin:0 0 14px;color:#6b6070;line-height:1.5;font-size:.95rem}
      .apa-email-gate-close{position:absolute;top:12px;right:14px;border:0;background:transparent;color:#6b6070;font-size:24px;line-height:1;cursor:pointer;padding:5px}
      .apa-email-gate-status{min-height:22px;margin:8px 0 0;color:#6b6070;font-size:.85rem}
      .apa-email-gate-frame{position:absolute;width:1px;height:1px;left:-10000px;top:-10000px;border:0;opacity:0}
      .apa-email-gate-note{font-size:.78rem!important;color:#7b7180!important;margin-top:10px!important}
      @media(max-width:600px){.apa-email-gate{padding:22px 18px}.apa-email-gate h2{font-size:1.2rem}}
    `;
    document.head.appendChild(style);
  }

  function showGate(link) {
    injectStyles();

    const existing = document.getElementById("apa-email-gate-backdrop");
    if (existing) existing.remove();

    const backdrop = document.createElement("div");
    backdrop.id = "apa-email-gate-backdrop";
    backdrop.className = "apa-email-gate-backdrop";
    backdrop.setAttribute("role", "dialog");
    backdrop.setAttribute("aria-modal", "true");
    backdrop.setAttribute("aria-labelledby", "apa-email-gate-title");

    const gate = document.createElement("div");
    gate.className = "apa-email-gate";
    gate.innerHTML = `
      <button type="button" class="apa-email-gate-close" aria-label="Close">×</button>
      <h2 id="apa-email-gate-title">Download this free worksheet</h2>
      <p>Enter your email to get access to this printable PDF and occasional new resource updates from Aussie Primary Academy.</p>
      <div class="apa-email-gate-status" aria-live="polite">Loading secure signup…</div>
      <p class="apa-email-gate-note">Your email is used for APA resource updates. You can unsubscribe at any time.</p>
    `;

    const frame = document.createElement("iframe");
    frame.className = "apa-email-gate-frame";
    frame.title = "Aussie Primary Academy email signup";
    frame.src = SITE_HOME;

    gate.appendChild(frame);
    backdrop.appendChild(gate);
    document.body.appendChild(backdrop);

    let status = gate.querySelector(".apa-email-gate-status");
    const closeButton = gate.querySelector(".apa-email-gate-close");
    let submitted = false;
    let finished = false;
    let submitStartedAt = 0;
    let gateSubmitButton = null;
    let gateStatus = status;
    let pollTimer = null;
    let submitTimeoutTimer = null;
    const SUBMIT_TIMEOUT_MS = 20000;

    function setGateStatus(message) {
      if (gateStatus && gateStatus.isConnected) {
        gateStatus.textContent = message;
      }
    }

    function clearSubmitTimeout() {
      if (submitTimeoutTimer) {
        clearTimeout(submitTimeoutTimer);
        submitTimeoutTimer = null;
      }
    }

    function resetSubmission(message) {
      clearSubmitTimeout();
      submitted = false;
      submitStartedAt = 0;
      if (gateSubmitButton) {
        gateSubmitButton.disabled = false;
        gateSubmitButton.style.opacity = "1";
      }
      setGateStatus(message);
    }

    function isVisible(element, win) {
      if (!element || !element.textContent.trim()) return false;
      const style = win.getComputedStyle(element);
      return style.display !== "none" &&
        style.visibility !== "hidden" &&
        style.opacity !== "0" &&
        element.getClientRects().length > 0;
    }

    function closeGate() {
      clearSubmitTimeout();
      if (pollTimer) clearInterval(pollTimer);
      backdrop.remove();
    }

    closeButton.addEventListener("click", closeGate);
    backdrop.addEventListener("click", function (event) {
      if (event.target === backdrop) closeGate();
    });
    document.addEventListener("keydown", function onKey(event) {
      if (event.key === "Escape") {
        closeGate();
        document.removeEventListener("keydown", onKey);
      }
    });

    function unlockAndDownload() {
      if (finished) return;
      finished = true;
      clearSubmitTimeout();
      sessionStorage.setItem(UNLOCK_KEY, "true");

      if (typeof gtag === "function") {
        gtag("event", "email_signup", { method: "brevo_worksheet_gate" });
      }

      closeGate();
      link.dataset.apaGateUnlocked = "true";
      // The click handler below will record exactly one worksheet_download event.
      link.click();
    }

    function inspectForm() {
      let doc;
      try {
        doc = frame.contentDocument || frame.contentWindow.document;
      } catch (error) {
        if (submitted) {
          resetSubmission("We could not confirm the signup. Please try again.");
        }
        return false;
      }

      if (!doc) return false;

      // Check Brevo's result panels before looking for the form. Brevo may
      // replace or hide the form after a response, so requiring #sib-form
      // first can leave the gate stuck on “Submitting…”.
      if (submitted) {
        const success = doc.querySelector("#success-message, .sib-success-message, .success-message, .newsletter-success");
        const error = doc.querySelector("#error-message, .sib-error-message, .error-message, .newsletter-error");

        if (isVisible(success, frame.contentWindow)) {
          unlockAndDownload();
          return true;
        }

        if (isVisible(error, frame.contentWindow)) {
          resetSubmission(error.textContent.trim() || "Your subscription could not be saved. Please check the email and try again.");
          return true;
        }

        const fieldError = Array.from(doc.querySelectorAll(".entry__error, .sib-form-message-panel__inner-text"))
          .find(function (element) {
            return isVisible(element, frame.contentWindow) && /invalid|required|could not|error|try again/i.test(element.textContent);
          });

        if (fieldError) {
          resetSubmission(fieldError.textContent.trim());
          return true;
        }
      }

      const form = doc.querySelector("#sib-form");
      if (!form) return false;

      const emailInput = Array.from(form.querySelectorAll('input[type="email"], input[type="text"]')).find(function (input) {
        const style = frame.contentWindow.getComputedStyle(input);
        return style.display !== "none" && style.visibility !== "hidden" && !input.classList.contains("input--hidden");
      });
      const submitButton = form.querySelector('button[type="submit"], input[type="submit"], .sib-form-block__button');

      if (!emailInput || !submitButton) {
        if (!submitted) setGateStatus("The signup form is still loading…");
        return false;
      }

      if (!submitted) {
        setGateStatus("Enter your email below:");
        const cloned = document.createElement("div");
        cloned.style.marginTop = "8px";
        cloned.innerHTML = `
          <input type="email" id="apa-gate-email" autocomplete="email" placeholder="Your email address" style="width:100%;box-sizing:border-box;border:1px solid #d9cee0;border-radius:10px;padding:11px 12px;font:inherit;font-size:14px;background:#fff;color:#3A3040;">
          <button type="button" id="apa-gate-submit" style="width:100%;margin-top:8px;border:0;border-radius:10px;padding:11px 16px;background:#4A3358;color:#fff;font:inherit;font-weight:700;cursor:pointer;">Get the Worksheet</button>
        `;

        status.replaceWith(cloned);

        const gateEmail = cloned.querySelector("#apa-gate-email");
        const gateSubmit = cloned.querySelector("#apa-gate-submit");
        const newStatus = document.createElement("div");
        newStatus.className = "apa-email-gate-status";
        newStatus.setAttribute("aria-live", "polite");
        newStatus.style.marginTop = "8px";
        cloned.appendChild(newStatus);
        gateSubmitButton = gateSubmit;
        gateStatus = newStatus;
        status = newStatus;

        gateSubmit.addEventListener("click", function () {
          const value = gateEmail.value.trim();
          if (!/^\S+@\S+\.\S+$/.test(value)) {
            newStatus.textContent = "Please enter a valid email address.";
            gateEmail.focus();
            return;
          }

          submitted = true;
          submitStartedAt = Date.now();
          gateSubmit.disabled = true;
          gateSubmit.style.opacity = "0.65";
          newStatus.textContent = "Submitting…";

          // Independent watchdog: if Brevo never reports a result, do not
          // leave the visitor stuck on “Submitting…” and never unlock on timeout.
          clearSubmitTimeout();
          submitTimeoutTimer = setTimeout(function () {
            if (!finished && submitted) {
              resetSubmission("We could not confirm the signup. Please try again.");
            }
          }, SUBMIT_TIMEOUT_MS);

          emailInput.value = value;
          emailInput.dispatchEvent(new Event("input", { bubbles: true }));
          emailInput.dispatchEvent(new Event("change", { bubbles: true }));

          // Brevo's main.js normally intercepts this submission and handles
          // the response. If it is not ready, the watchdog will safely reset.
          if (typeof form.requestSubmit === "function") {
            form.requestSubmit(submitButton);
          } else {
            submitButton.click();
          }
        });
      }

      return true;
    }

    frame.addEventListener("load", function () {
      // Check immediately after every iframe load, then continue polling.
      inspectForm();
      if (pollTimer) clearInterval(pollTimer);
      let attempts = 0;
      pollTimer = setInterval(function () {
        attempts += 1;
        inspectForm();
        if (finished || !backdrop.isConnected) {
          clearInterval(pollTimer);
          pollTimer = null;
          return;
        }
        if (attempts >= 60 && !gateSubmitButton) {
          clearInterval(pollTimer);
          pollTimer = null;
          if (!finished) {
            setGateStatus("Signup form could not be loaded. Please try again.");
          }
        }
      }, 500);
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    const pdfLinks = document.querySelectorAll('a[href$=".pdf"], a[href$=".PDF"]');
    const alreadyUnlocked = sessionStorage.getItem(UNLOCK_KEY) === "true";

    pdfLinks.forEach(function (link) {
      if (link.dataset.apaDownloadTracked === "true") return;
      link.dataset.apaDownloadTracked = "true";

      if (!link.hasAttribute("download")) {
        link.setAttribute("download", "");
      }

      link.addEventListener("click", function (event) {
        if (link.dataset.apaGateUnlocked === "true" || alreadyUnlocked || sessionStorage.getItem(UNLOCK_KEY) === "true") {
          trackDownload(link);
          return;
        }

        event.preventDefault();
        showGate(link);
      });
    });
  });
})();
