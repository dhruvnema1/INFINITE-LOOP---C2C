// Background Relay: Event-driven Service Worker
const lastResultByTab = {};

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === "scanText") {
    fetch("http://127.0.0.1:5000/analyze", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        url: message.url,
        text: message.text,
        timestamp: message.timestamp
      })
    })
      .then((response) => response.json())
      .then((data) => {
        if (sender.tab && sender.tab.id != null) {
          lastResultByTab[sender.tab.id] = data;
        }
        console.log("Threat analysis received:", data);
        sendResponse({ status: "success", data });
      })
      .catch((error) => {
        console.error("Error connecting to Guardian backend:", error);
        sendResponse({ status: "error", message: error.message });
      });

    return true; // Keeps the message channel open for the asynchronous response
  }

  if (message.action === "GET_SCAN_RESULTS") {
    const tabId = message.tabId ?? sender.tab?.id;
    sendResponse(lastResultByTab[tabId] || null);
    return true;
  }
});

// Clean up cached results when a tab closes
chrome.tabs.onRemoved.addListener((tabId) => {
  delete lastResultByTab[tabId];
});
