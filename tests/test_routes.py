def test_login_page(client):
    resp = client.get("/login")
    assert resp.status_code == 200
    assert "Login" in resp.text


def test_login_redirect_unauthed(client):
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/login"


def test_login_success(authed_client):
    resp = authed_client.get("/")
    assert resp.status_code == 200
    assert "Dashboard" in resp.text


def test_login_wrong_password(client, db_session):
    from passlib.hash import bcrypt
    from app.models.user import User

    user = User(username="badlogin", password_hash=bcrypt.hash("correct"), role="member")
    db_session.add(user)
    db_session.commit()

    resp = client.post("/login", data={"username": "badlogin", "password": "wrong"})
    assert resp.status_code == 401


def test_add_article(authed_client):
    resp = authed_client.post(
        "/articles/add",
        data={
            "url": "https://example.com/test-article",
            "title": "Test Article Title",
            "source": "Test",
            "content_type": "article",
            "authors": "Author One",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert "/articles/" in resp.headers["location"]


def test_add_duplicate_article(authed_client):
    data = {
        "url": "https://example.com/dup-test",
        "title": "Dup Test",
        "source": "Test",
        "content_type": "article",
        "authors": "",
    }
    authed_client.post("/articles/add", data=data)
    resp = authed_client.post("/articles/add", data=data)
    assert resp.status_code == 409


def test_article_list(authed_client):
    authed_client.post(
        "/articles/add",
        data={
            "url": "https://example.com/list-test",
            "title": "List Test Article",
            "source": "Test",
            "content_type": "article",
            "authors": "",
        },
    )
    resp = authed_client.get("/articles")
    assert resp.status_code == 200
    assert "List Test Article" in resp.text


def test_article_fts_search(authed_client):
    authed_client.post(
        "/articles/add",
        data={
            "url": "https://example.com/fts-search-test",
            "title": "Quantum Computing in Education Policy",
            "source": "Test",
            "content_type": "article",
            "authors": "",
        },
    )
    resp = authed_client.get("/articles?q=quantum")
    assert "Quantum Computing" in resp.text


def test_article_detail(authed_client):
    resp = authed_client.post(
        "/articles/add",
        data={
            "url": "https://example.com/detail-test",
            "title": "Detail Test Article",
            "source": "Test",
            "content_type": "article",
            "authors": "Author A, Author B",
        },
        follow_redirects=False,
    )
    location = resp.headers["location"]
    resp = authed_client.get(location)
    assert resp.status_code == 200
    assert "Detail Test Article" in resp.text
    assert "Author A" in resp.text


def test_admin_page(authed_client):
    resp = authed_client.get("/admin")
    assert resp.status_code == 200
    assert "Admin" in resp.text


def test_search_jobs_page(authed_client):
    resp = authed_client.get("/search-jobs")
    assert resp.status_code == 200


def test_add_search_job(authed_client):
    resp = authed_client.post(
        "/search-jobs/add",
        data={"name": "Test Job", "query": "AI policy", "schedule": "daily"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    resp = authed_client.get("/search-jobs")
    assert "Test Job" in resp.text


def test_interrogation_page(authed_client):
    resp = authed_client.get("/interrogation")
    assert resp.status_code == 200
    assert "Ask" in resp.text


def test_reading_lists_page(authed_client):
    resp = authed_client.get("/reading-lists")
    assert resp.status_code == 200
