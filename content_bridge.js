// Client Bridge: extracts page text and relays it to the background service worker
let lastScannedText = null;
let debounceTimer = null;
const DEBOUNCE_MS = 800;

// "Recommended for you" / "customers also bought" / sponsored-product
// carousels live INSIDE the same product-page container as the actual
// product on most sites (Amazon included), so picking a bigger container
// doesn't separate them. Instead, walk the live page and skip any element
// whose id/class matches a known recommendation/carousel/sponsored pattern,
// wherever it sits in the DOM.
const EXCLUDE_SELECTOR = [
  '[id*="sims" i]', '[id*="similar" i]', '[id*="related" i]',
  '[id*="recommend" i]', '[class*="recommend" i]',
  '[id*="also-bought" i]', '[id*="also_bought" i]',
  '[id*="cross-sell" i]', '[id*="crosssell" i]',
  '[id*="upsell" i]', '[class*="carousel" i]', '[id*="carousel" i]',
  '[class*="sponsored" i]', '[id*="sponsored" i]', '[id*="sp_detail" i]',
  '[class*="p13n" i]', '[id*="p13n" i]',
  'script', 'style', 'noscript'
].join(',');

function getProductText() {
  if (!document.body) return "";

  const excluded = new Set(document.body.querySelectorAll(EXCLUDE_SELECTOR));

  function isExcluded(el) {
    while (el) {
      if (excluded.has(el)) return true;
      el = el.parentElement;
    }
    return false;
  }

  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {
    acceptNode(node) {
      const parent = node.parentElement;
      if (!parent || isExcluded(parent)) return NodeFilter.FILTER_REJECT;
      return NodeFilter.FILTER_ACCEPT;
    }
  });

  let text = "";
  let node;
  while ((node = walker.nextNode())) {
    text += node.nodeValue + " ";
  }
  return text.replace(/\s+/g, " ").trim();
}

function scanPage() {
  const pageText = getProductText();
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
