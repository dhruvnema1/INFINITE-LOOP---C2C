const APIS = ["http://127.0.0.1:8000", "http://localhost:8000"];

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type !== "SCAN_PAGE") return;

  (async () => {
    let lastError = null;
    for (const api of APIS) {
      try {
        const response = await fetch(`${api}/scan`, {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify(message.payload)
        });
        const body = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(body.detail || `API returned HTTP ${response.status}`);
        }
        sendResponse({ok: true, result: body});
        return;
      } catch (error) {
        lastError = error;
      }
    }
    sendResponse({
      ok: false,
      error: `Cannot reach the AI backend. Start FastAPI at 127.0.0.1:8000. Details: ${lastError?.message || "connection failed"}`
    });
  })();

  return true;
});
