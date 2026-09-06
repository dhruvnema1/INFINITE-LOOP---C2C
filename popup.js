document.addEventListener('DOMContentLoaded', async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

  if (tab && tab.url) {
    document.getElementById('page-url').textContent = new URL(tab.url).hostname;
  }

  // Ask the background service worker if it already has a fresh result cached
  // (populated by content_bridge.js when the page first loaded).
  const cached = await chrome.runtime.sendMessage({
    action: 'GET_SCAN_RESULTS',
    tabId: tab.id
  });

  if (cached && cached.url === tab.url) {
    renderResults(cached.data);
    return;
  }

  // No usable cache (extension just installed, page hasn't finished its own
  // scan yet, or it's a restricted page content scripts can't run on) —
  // fall back to scanning right now from the popup.
  await runFreshScan(tab);
});

async function runFreshScan(tab) {
  let pageText = '';
  try {
    const [{ result }] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => {
        // Kept in sync with content_bridge.js's getProductText() — excludes
        // recommendation/carousel/sponsored sections wherever they sit in
        // the DOM, since they live INSIDE the same container as the actual
        // product on most sites (a container whitelist alone doesn't work).
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

        if (!document.body) return '';

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

        let text = '';
        let node;
        while ((node = walker.nextNode())) {
          text += node.nodeValue + ' ';
        }
        return text.replace(/\s+/g, ' ').trim();
      }
    });
    pageText = result || '';
  } catch (err) {
    console.error('Could not read page content:', err);
    showError('Could not read this page (restricted tab?).');
    return;
  }

  try {
    const response = await fetch('http://127.0.0.1:5000/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: tab.url, text: pageText })
    });
    const data = await response.json();
    renderResults(data);

    // Let background cache this too, so the next popup-open on this tab
    // (same page) can skip straight to the cache.
    chrome.runtime.sendMessage({
      action: 'scanText',
      url: tab.url,
      text: pageText,
      timestamp: Date.now(),
      tabId: tab.id
    });
  } catch (err) {
    console.error('Backend offline:', err);
    showError('Could not reach the local analysis server on port 5000.');
  }
}

function showError(message) {
  document.getElementById('risk-status').textContent = 'Backend unreachable';
  document.getElementById('risk-desc').textContent = message;
}

function renderResults(data) {
  const score = data.risk_score ?? Math.round((data.threat_score || 0) * 100);
  document.getElementById('score-val').textContent = score;

  const statusEl = document.getElementById('risk-status');
  const descEl = document.getElementById('risk-desc');
  const circle = document.querySelector('.score-circle');

  if (score >= 60) {
    statusEl.textContent = 'Critical Risk Detected';
    descEl.textContent = 'Multiple manipulative UI tactics found on this page.';
    if (circle) circle.style.borderColor = '#ef4444';
  } else if (score >= 30) {
    statusEl.textContent = 'Moderate Risk Detected';
    descEl.textContent = 'Some manipulative patterns found on this page.';
    if (circle) circle.style.borderColor = '#f59e0b';
  } else {
    statusEl.textContent = 'Verified Safe';
    descEl.textContent = 'No deceptive patterns found on this page.';
    if (circle) circle.style.borderColor = '#10b981';
  }

  const list = document.getElementById('threats-list');
  list.innerHTML = '';

  const findings = data.findings || [];
  if (findings.length === 0) {
    list.innerHTML = '<p class="action">No dark patterns detected.</p>';
    return;
  }

  const categoryClass = {
    'Fake Urgency': 'urgency',
    'Fake Scarcity': 'urgency',
    'Hidden Fees': 'hiddenfee',
    'Confirmshaming': 'confirmshaming',
    'Social Proof': 'discount'
  };

  for (const finding of findings) {
    const card = document.createElement('div');
    card.className = `threat-card ${categoryClass[finding.category] || ''}`;
    card.innerHTML = `
      <div class="threat-header">
        <span class="threat-title">${escapeHtml(finding.category)}</span>
        <span class="threat-tag">+${finding.points}</span>
      </div>
      <div class="snippet">"${escapeHtml(finding.evidence)}"</div>
      <div class="action">${escapeHtml(finding.reason)}</div>
    `;
    list.appendChild(card);
  }
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}
