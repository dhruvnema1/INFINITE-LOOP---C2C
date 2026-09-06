// Client Bridge: extracts page text and relays it to the background service worker
let lastScannedText = null;
let debounceTimer = null;
const DEBOUNCE_MS = 800;

function scanPage() {
  const pageText = document.body ? document.body.innerText.trim() : "";
  if (!pageText || pageText === lastScannedText) return;
  lastScannedText = pageText;

  chrome.runtime.sendMessage({
    action: "scanText",
    url: window.location.href,
    text: pageText,
    timestamp: Date.now()
  });
}

function scheduleScan() {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(scanPage, DEBOUNCE_MS);
}

// Initial scan
scheduleScan();

// Re-scan on dynamic content changes (SPAs, lazy-loaded content), debounced
if (document.body) {
  const observer = new MutationObserver(scheduleScan);
  observer.observe(document.body, { childList: true, subtree: true, characterData: true });
}
