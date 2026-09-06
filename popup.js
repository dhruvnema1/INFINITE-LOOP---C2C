document.addEventListener('DOMContentLoaded', async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

  if (tab && tab.url) {
    document.getElementById('page-url').textContent = new URL(tab.url).hostname;
  }

  let pageText = '';
  try {
    const [{ result }] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => document.body.innerText
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
  } catch (err) {
    console.error('Backend offline:', err);
    showError('Could not reach the local analysis server on port 5000.');
  }
});

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
