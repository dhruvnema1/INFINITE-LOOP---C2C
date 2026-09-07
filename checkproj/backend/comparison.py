import re
from urllib.parse import quote, urlparse

import requests
from bs4 import BeautifulSoup

PRICE_RE = re.compile(r"(?:₹|Rs\.?|INR|\$|€|£)\s?\d[\d,]*(?:\.\d{1,2})?", re.I)
STOP = {"the","and","for","with","from","this","that","new","sale","official","buy","online","price"}


def _tokens(value: str):
    words = re.findall(r"[a-z0-9]{3,}", (value or "").lower())
    return {w for w in words if w not in STOP}


def _money(s: str):
    m = PRICE_RE.search(s or "")
    if not m:
        return None, None
    raw = m.group(0)
    symbol = "₹" if "₹" in raw or re.search(r"\brs\.?|\binr\b", raw, re.I) else ("$" if "$" in raw else ("€" if "€" in raw else "£"))
    digits = re.sub(r"[^0-9.]", "", raw.replace(",", ""))
    try:
        return float(digits), symbol
    except ValueError:
        return None, symbol


def _search_duckduckgo(query: str):
    url = "https://html.duckduckgo.com/html/?q=" + quote(query)
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"}
    r = requests.get(url, headers=headers, timeout=7)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    results = []
    for item in soup.select(".result")[:10]:
        a = item.select_one(".result__a")
        snippet = item.select_one(".result__snippet")
        if not a:
            continue
        href = a.get("href", "")
        title = a.get_text(" ", strip=True)
        text = " ".join(x for x in [title, snippet.get_text(" ", strip=True) if snippet else ""] if x)
        price, currency = _money(text)
        results.append({"title": title, "url": href, "snippet": text, "price": price, "currency": currency})
    return results


def compare_product(product_name: str, brand: str, current_url: str, current_price=None, claimed_old_price=None):
    """Best-effort cross-site evidence. Search results are supporting evidence, not proof."""
    name = (product_name or "").strip()
    if len(name) < 4:
        return {"available": False, "reason": "Product name could not be identified reliably."}

    query_parts = [brand, name] if brand else [name]
    query = " ".join(x for x in query_parts if x)
    try:
        raw = _search_duckduckgo(query + " price")
    except Exception as exc:
        return {"available": False, "reason": f"Cross-site search unavailable: {type(exc).__name__}."}

    current_domain = urlparse(current_url or "").netloc.lower().replace("www.", "")
    target_tokens = _tokens(name)
    if brand:
        target_tokens |= _tokens(brand)

    matches = []
    for r in raw:
        domain = urlparse(r["url"]).netloc.lower().replace("www.", "")
        if not domain or domain == current_domain:
            continue
        result_tokens = _tokens(r["title"] + " " + r["snippet"])
        overlap = len(target_tokens & result_tokens) / max(1, min(len(target_tokens), 8))
        if overlap >= 0.45 and r["price"] is not None:
            r["domain"] = domain
            r["match_score"] = round(overlap, 2)
            matches.append(r)

    # Keep one result per domain and at most five comparators.
    unique = {}
    for r in matches:
        unique.setdefault(r["domain"], r)
    matches = list(unique.values())[:5]

    prices = [m["price"] for m in matches if m.get("price") is not None]
    if not prices:
        return {"available": False, "reason": "No reliable same-product prices were found in search results.", "matches": []}

    prices_sorted = sorted(prices)
    mid = len(prices_sorted) // 2
    median = prices_sorted[mid] if len(prices_sorted) % 2 else (prices_sorted[mid-1] + prices_sorted[mid]) / 2

    evidence = []
    comparison_conf = 0.0
    if claimed_old_price and median and claimed_old_price > median * 1.25:
        ratio = claimed_old_price / median
        comparison_conf = min(1.0, 0.55 + min(0.35, (ratio - 1.25) * 0.5))
        evidence.append(f"Claimed reference price is about {ratio:.1f}× the cross-site median.")
    if current_price and median:
        diff = abs(current_price - median) / median
        if diff <= 0.15:
            evidence.append("Current price is within 15% of the observed cross-site median.")
            comparison_conf = max(comparison_conf, 0.25)

    return {
        "available": True,
        "product": name,
        "brand": brand or "",
        "median_price": round(median, 2),
        "currency": matches[0].get("currency") or "",
        "matches": [{k: r.get(k) for k in ["domain","title","url","price","currency","match_score"]} for r in matches],
        "confidence": round(comparison_conf, 2),
        "evidence": evidence,
        "disclaimer": "Cross-site prices are supporting evidence only; sellers, regions, taxes, shipping and variants can differ.",
    }
