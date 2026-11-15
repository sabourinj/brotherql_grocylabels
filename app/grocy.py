import json
from urllib.parse import quote
from urllib.request import Request, urlopen

def text(value) -> str:
    """Webhook values can be strings, numbers or null (JSON), normalise to a string."""
    return "" if value is None else str(value).strip()

def stockEntryFromRequest(source) -> dict:
    """
    Grocy includes the stock entry in stock label webhooks: as a nested object when
    LABEL_PRINTER_HOOK_JSON is true, or as stock_entry[field] keys when sent as a form.
    """
    entry = source.get("stock_entry")
    if isinstance(entry, dict):
        return entry
    prefix = "stock_entry["
    return {key[len(prefix):-1]: value for (key, value) in source.items() if key.startswith(prefix) and key.endswith("]")}

def stockIdFromGrocycode(grocycode: str):
    """Stock entry grocycodes look like grcy:p:<product id>:<stock id>, returns (product id, stock id) or None."""
    parts = grocycode.split(":")
    if len(parts) == 4 and parts[0] == "grcy" and parts[1] == "p" and parts[2] and parts[3]:
        return (parts[2], parts[3])
    return None

def canLookup(stockEntry: dict, grocycode: str) -> bool:
    return bool(text(stockEntry.get("id")) or stockIdFromGrocycode(grocycode))

def _get(baseUrl: str, apiKey: str, apiPath: str, timeout: float):
    req = Request(baseUrl.rstrip("/") + "/api/" + apiPath, headers = {"GROCY-API-KEY": apiKey, "Accept": "application/json"})
    with urlopen(req, timeout = timeout) as response:
        return json.load(response)

def fetchStockEntry(baseUrl: str, apiKey: str, stockEntry: dict, grocycode: str, timeout: float = 5):
    """
    Read the stock entry fresh from the Grocy API.
    Uses the entry id from the webhook when there is one, which is exact even when Grocy has split an
    entry on opening (the original id is the opened part), otherwise the stock id from the grocycode.
    Returns None if there's nothing to look up.
    """
    entryId = text(stockEntry.get("id"))
    if entryId:
        return _get(baseUrl, apiKey, "stock/entry/" + quote(entryId), timeout)

    ids = stockIdFromGrocycode(grocycode)
    if ids:
        (productId, stockId) = ids
        entries = _get(baseUrl, apiKey, "stock/products/" + quote(productId) + "/entries", timeout)
        matches = [e for e in entries if text(e.get("stock_id")) == stockId]
        # a transfer can leave several entries with the same stock id, prefer an opened one
        matches.sort(key = lambda e: text(e.get("open")) == "1", reverse = True)
        return matches[0] if matches else None

    return None
