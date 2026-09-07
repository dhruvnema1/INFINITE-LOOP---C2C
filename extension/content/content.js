(() => {
  if (window.__darkPatternDetectorInstalled) return;
  window.__darkPatternDetectorInstalled = true;

  const MAX_TEXT = 80000;
  const NOISE_RE = /(?:^|[-_\s])(featured|recommended|recommendations|related|similar|you may also like|customers also|frequently bought|sponsored products|more like this|trending|popular picks|top picks)(?:$|[-_\s])/i;

  function isVisible(el) {
    if (!el || !el.getBoundingClientRect) return false;
    const s = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    return s.display !== "none" && s.visibility !== "hidden" && r.width > 0 && r.height > 0;
  }

  function isRecommendationContainer(el) {
    if (!el || el.nodeType !== 1) return false;
    const attrs = [el.id, el.className, el.getAttribute("aria-label"), el.getAttribute("data-testid"), el.getAttribute("data-section-id")]
      .filter(v => typeof v === "string").join(" ");
    if (NOISE_RE.test(attrs)) return true;
    const heading = el.querySelector("h1,h2,h3,h4,h5,[role='heading']");
    const headingText = heading?.textContent?.replace(/\s+/g, " ").trim() || "";
    return NOISE_RE.test(headingText);
  }

  function findMainProductRoot() {
    // Prefer structured product markup when the site provides it.
    const name = document.querySelector("[itemprop='name']");
    if (name && isVisible(name)) {
      let node = name;
      for (let i = 0; i < 7 && node.parentElement; i++) {
        const parent = node.parentElement;
        const text = parent.innerText || "";
        const hasPrice = /(?:₹|rs\.?|\$|€|£)\s*[\d,]+|\b\d[\d,]+\s*(?:₹|rs\.?|usd|eur|gbp)\b/i.test(text);
        if (hasPrice && text.length >= 80 && text.length <= 30000) node = parent;
      }
      return node;
    }

    // Common product-detail containers. Avoid generic .product-card selectors.
    const candidates = [
      "main",
      "[role='main']",
      "article",
      "[itemtype*='Product']",
      "[data-testid*='product-detail']",
      "[data-testid*='product-page']",
      "[class*='product-detail']",
      "[class*='product-page']"
    ];
    for (const selector of candidates) {
      const els = [...document.querySelectorAll(selector)].filter(isVisible);
      const useful = els.find(el => {
        const text = el.innerText || "";
        return text.length > 100 && text.length < 50000 && /(?:₹|rs\.?|\$|€|£)\s*[\d,]+/i.test(text);
      });
      if (useful) return useful;
    }
    return document.body;
  }

  function cloneWithoutRecommendations(root) {
    const clone = root.cloneNode(true);
    clone.querySelectorAll("script,style,noscript,template,svg,canvas,iframe,video,audio")
      .forEach(el => el.remove());

    [...clone.querySelectorAll("*")].forEach(el => {
      if (isRecommendationContainer(el)) el.remove();
    });

    return clone;
  }

  function visibleText() {
    const root = findMainProductRoot();
    const clone = cloneWithoutRecommendations(root);
    const walker = document.createTreeWalker(clone, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        const parent = node.parentElement;
        if (!parent) return NodeFilter.FILTER_REJECT;
        return node.textContent.trim()
          ? NodeFilter.FILTER_ACCEPT
          : NodeFilter.FILTER_REJECT;
      }
    });

    const chunks = [];
    let node;
    while ((node = walker.nextNode()) && chunks.join(" ").length < MAX_TEXT) {
      chunks.push(node.textContent.replace(/\s+/g, " ").trim());
    }
    return chunks.join(" ").slice(0, MAX_TEXT);
  }

  function prices() {
    const root = findMainProductRoot();
    const selectors = "[itemprop='price'],[data-price],.price,.sale-price,.current-price,.original-price,.old-price";
    const result = [];
    root.querySelectorAll(selectors).forEach(el => {
      if (!isVisible(el)) return;
      const raw = el.getAttribute("content") || el.getAttribute("data-price") || el.textContent || "";
      const nums = raw.replace(/,/g, "").match(/\d+(?:\.\d{1,2})?/g);
      if (nums) result.push({value: Number(nums[nums.length - 1]), text: raw.trim().slice(0, 120)});
    });
    return result.slice(0, 40);
  }

  function collect() {
    const root = findMainProductRoot();
    const body = root?.innerText?.toLowerCase() || "";
    const current = root.querySelector(".sale-price,.current-price,[itemprop='price'],[data-price]");
    const old = root.querySelector(".original-price,.old-price,.was-price,[data-old-price]");

    const parse = el => {
      if (!el) return null;
      const raw = el.getAttribute("content") || el.getAttribute("data-price") || el.getAttribute("data-old-price") || el.textContent || "";
      const m = raw.replace(/,/g, "").match(/\d+(?:\.\d{1,2})?/);
      return m ? Number(m[0]) : null;
    };

    return {
      url: location.href,
      title: document.title,
      text: visibleText(),
      prices: prices(),
      dom_signals: {
        checkout_fee_hint: /\b(service|processing|handling|platform|convenience)\s+fee\b/i.test(body) || /\badditional charges?\b/i.test(body) || /\bcalculated at checkout\b/i.test(body),
        current_price: parse(current),
        old_price: parse(old),
        scan_scope: "primary product area; recommendation/featured sections excluded"
      }
    };
  }

  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message?.type === "COLLECT_PAGE") sendResponse({ok: true, data: collect()});
  });
})();
