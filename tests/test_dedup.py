from app.services.dedup import normalize_url, url_hash


def test_normalize_strips_tracking():
    url = "https://example.com/article?utm_source=twitter&id=123"
    result = normalize_url(url)
    assert "utm_source" not in result
    assert "id=123" in result


def test_normalize_strips_www():
    assert normalize_url("https://www.example.com/page") == "https://example.com/page"


def test_normalize_strips_fragment():
    assert normalize_url("https://example.com/page#section") == "https://example.com/page"


def test_normalize_trailing_slash():
    assert normalize_url("https://example.com/page/") == "https://example.com/page"


def test_url_hash_deterministic():
    url = "https://example.com/article"
    assert url_hash(url) == url_hash(url)


def test_url_hash_same_for_variants():
    h1 = url_hash("https://www.example.com/article?utm_source=fb")
    h2 = url_hash("https://example.com/article")
    assert h1 == h2


def test_url_hash_different_for_different_urls():
    h1 = url_hash("https://example.com/article-1")
    h2 = url_hash("https://example.com/article-2")
    assert h1 != h2
