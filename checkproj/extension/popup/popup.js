const button = document.getElementById("scanButton");
const scoreEl = document.getElementById("score");
const badge = document.getElementById("riskBadge");
const riskTitle = document.getElementById("riskTitle");
const status = document.getElementById("status");
const ring = document.getElementById("ring");
const list = document.getElementById("threatList");
const count = document.getElementById("count");
const comparisonEl = document.getElementById("comparison");

const ICONS = {
  "Fake urgency": "◷",
  "Misleading discount": "%",
  "Hidden fees": "₹",
  "Scarcity": "◇",
  "Forced continuity": "↻"
};

function colorFor(score) {
  if (score <= 29) return "#4cffad";
  if (score <= 59) return "#ffd45c";
  return "#ff5f73";
}
function classFor(score) {
  if (score <= 29) return "safe";
  if (score <= 59) return "medium";
  return "high";
}
function titleFor(score) {
  if (score <= 29) return "Looks safe";
  if (score <= 59) return "Proceed carefully";
  return "High-risk page";
}
function renderThreats(threats) {
  count.textContent = String(threats.length);
  if (!threats.length) {
    list.innerHTML = `<div class="empty"><div class="empty-orbit"><span>✓</span></div>
      <p>No dark patterns detected</p><small>The current scan did not meet the configured evidence threshold.</small></div>`;
    return;
  }
  list.innerHTML = threats.map(threat => {
    const c = colorFor(threat.score);
    const cls = threat.score > 59 ? "redd" : threat.score > 29 ? "yell" : "greenn";
    const icon = ICONS[threat.label] || "!";
    const reasonItems = threat.reasons.map(r => `<li>${escapeHtml(r)}</li>`).join("");
    return `<article class="threat ${cls}" style="color:${c}">
      <div class="threat-top"><div class="threat-left"><span class="threat-icon">${icon}</span>
      <span class="threat-name">${escapeHtml(threat.label)}</span></div>
      <span class="threat-score">${threat.score}/100</span></div>
      <div class="bar"><div style="width:${Math.max(0, Math.min(100, threat.score))}%;"></div></div>
      <ul class="reasons">${reasonItems}</ul>
    </article>`;
  }).join("");
}
function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[ch]));
}
function renderComparison(cmp) {
  if (!cmp?.available || !cmp.matches?.length) {
    comparisonEl.classList.add("hidden");
    comparisonEl.innerHTML = "";
    return;
  }
  const rows = cmp.matches.map(m => `<div class="market-row">
    <div class="market-site"><strong>${escapeHtml(m.domain || m.title || "Retailer")}</strong><small>${escapeHtml((m.title || "Same-product result").slice(0,80))}</small></div>
    <div class="market-price">${escapeHtml(m.currency || "")}${m.price != null ? Number(m.price).toLocaleString() : "—"}</div>
  </div>`).join("");
  const evidence = (cmp.evidence || []).map(x => `• ${escapeHtml(x)}`).join("<br>");
  comparisonEl.classList.remove("hidden");
  comparisonEl.innerHTML = `<div class="compare-head"><h3>Cross-site evidence</h3><span class="compare-tag">SUPPORTING SIGNAL</span></div>
    <p class="compare-copy">Matched <b>${escapeHtml(cmp.product || "this product")}</b> against prices found on other sites.</p>
    ${rows}
    ${evidence ? `<div class="evidence"><b>Why it matters</b><br>${evidence}</div>` : ""}
    <p class="disclaimer">${escapeHtml(cmp.disclaimer || "Prices can differ by seller, region, tax, shipping and variant.")}</p>`;
}

function render(result) {
  const score = Math.max(0, Math.min(100, Number(result.score) || 0));
  const c = colorFor(score);
  scoreEl.textContent = score;
  badge.textContent = result.risk.label;
  badge.className = `risk-badge ${classFor(score)}`;
  riskTitle.textContent = titleFor(score);
  status.textContent = result.threats.length
    ? `${result.threats.length} threat type(s) supported by AI and heuristic evidence.`
    : "No configured threat reached the evidence threshold.";
  ring.style.background = `conic-gradient(${c} ${score * 3.6}deg, #161a20 ${score * 3.6}deg)`;
  ring.style.boxShadow = `0 0 28px ${c}18`;
  renderThreats(result.threats);
  renderComparison(result.comparison);
}
button.addEventListener("click", async () => {
  button.disabled = true;
  button.classList.add("scanning");
  button.querySelector("span:nth-child(2)").textContent = "Analyzing page…";
  status.textContent = "Extracting visible content and running AI analysis…";
  try {
    const [tab] = await chrome.tabs.query({active:true,currentWindow:true});
    if (!tab?.id) throw new Error("No active tab.");
    let payload = await chrome.tabs.sendMessage(tab.id,{type:"COLLECT_PAGE"}).catch(()=>null);
    if (!payload?.ok) {
      await chrome.scripting.executeScript({target:{tabId:tab.id},files:["content/content.js"]});
      payload = await chrome.tabs.sendMessage(tab.id,{type:"COLLECT_PAGE"});
    }
    const response = await chrome.runtime.sendMessage({
      type:"SCAN_PAGE", payload: payload?.data || payload
    });
    if (!response?.ok) throw new Error(response?.error || "Scan failed.");
    render(response.result);
  } catch (error) {
    scoreEl.textContent = "!";
    badge.textContent = "SCAN ERROR";
    badge.className = "risk-badge high";
    riskTitle.textContent = "Could not scan";
    ring.style.background = "conic-gradient(#ff5f73 360deg,#161a20 0deg)";
    status.textContent = error.message || "Unable to scan this page.";
    list.innerHTML = `<div class="empty"><div class="empty-orbit"><span>!</span></div>
      <p>Scan could not be completed</p><small>Make sure the local AI API is running and the page allows content scripts.</small></div>`;
  } finally {
    button.disabled = false;
    button.classList.remove("scanning");
    button.querySelector("span:nth-child(2)").textContent = "Scan this page";
  }
});
