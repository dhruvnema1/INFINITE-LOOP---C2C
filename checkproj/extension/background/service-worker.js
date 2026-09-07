const API = "http://127.0.0.1:8000";

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type !== "SCAN_PAGE") return;

  (async () => {
    try {
      const response = await fetch(`${API}/scan`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(message.payload)
      });

      const body = await response.json();

      if (!response.ok) {
        throw new Error(body.detail || `API error ${response.status}`);
      }

      sendResponse({ok: true, result: body});
    } catch (error) {
      sendResponse({
        ok: false,
        error: error?.message || "Unable to reach local AI service."
      });
    }
  })();

  return true;
});
