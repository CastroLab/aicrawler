import hashlib
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "ref", "source", "mc_cid", "mc_eid",
}


def normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())

    scheme = parsed.scheme.lower() or "https"
    host = parsed.hostname or ""
    if host.startswith("www."):
        host = host[4:]
    host = host.lower()

    port = ""
    if parsed.port and parsed.port not in (80, 443):
        port = f":{parsed.port}"

    path = parsed.path.rstrip("/") or "/"

    params = parse_qs(parsed.query, keep_blank_values=False)
    filtered = {k: v for k, v in sorted(params.items()) if k.lower() not in TRACKING_PARAMS}
    query = urlencode(filtered, doseq=True)

    return urlunparse((scheme, f"{host}{port}", path, "", query, ""))


def url_hash(url: str) -> str:
    normalized = normalize_url(url)
    return hashlib.sha256(normalized.encode()).hexdigest()
