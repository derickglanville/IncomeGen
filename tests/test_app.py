import os
import tempfile

from app import create_app


def make_client():
    handle, path = tempfile.mkstemp(suffix=".db"); os.close(handle)
    app = create_app({"TESTING":True,"DATABASE":path,"SECRET_KEY":"test"})
    return app.test_client(), path


def test_dashboard_and_empty_database():
    client, path = make_client()
    try:
        response = client.get("/")
        assert response.status_code == 200
        assert b"Build your next income stream" in response.data
        assert b"Unique listings" in response.data
    finally: os.unlink(path)


def test_manual_opportunity_is_saved_and_scored():
    client, path = make_client()
    try:
        response = client.post("/opportunities/new", data={"platform_id":"1","company":"Verified Co","title":"Python NLP Consultant","description":"Remote Python NLP and SQL Server contract","application_url":"https://example.test/apply/123","source_url":"https://example.test/jobs/123","compensation_min":"45","compensation_max":"60","compensation_period":"hour","currency":"USD","remote_eligibility":"Remote","geographic_restrictions":"United States","contract_type":"Contract","payment_arrangements":"$45-$60 hourly"}, follow_redirects=True)
        assert response.status_code == 200
        assert b"Verified Co" in response.data
        assert b"Opportunity added and scored" in response.data
    finally: os.unlink(path)


def test_duplicate_manual_opportunity_is_not_added_twice():
    client, path = make_client()
    payload={"platform_id":"1","company":"Verified Co","title":"Python Consultant","description":"Python","application_url":"https://example.test/jobs/1?ref=a","source_url":"https://example.test/jobs/1"}
    try:
        client.post("/opportunities/new",data=payload)
        payload["application_url"]="https://example.test/jobs/1?ref=b"
        response=client.post("/opportunities/new",data=payload,follow_redirects=True)
        assert b"Duplicate found" in response.data
        assert response.data.count(b"Verified Co") == 1
    finally: os.unlink(path)


def test_unsafe_source_url_is_rejected():
    client, path = make_client()
    try:
        response=client.post("/opportunities/new",data={"platform_id":"1","company":"Example","title":"Role","description":"Details","application_url":"javascript:alert(1)","source_url":"https://example.test/role"},follow_redirects=True)
        assert b"must use http or https" in response.data
        assert b"Example" not in client.get("/opportunities").data
    finally: os.unlink(path)


def test_all_phase_one_pages_render():
    client, path = make_client()
    try:
        for route in ("/opportunities", "/opportunities/new", "/profile", "/platforms", "/search-history", "/recommended"):
            assert client.get(route).status_code == 200
    finally: os.unlink(path)


def test_recommended_jobs_are_extensive_and_filterable():
    client, path = make_client()
    try:
        response = client.get("/recommended")
        assert response.data.count(b"recommended-card") >= 20
        filtered = client.get("/recommended?platform=Outlier&min_fit=90")
        assert b"OpenClaw Agent Builder" in filtered.data
        assert b"Legacy Codebase Migration" not in filtered.data
    finally: os.unlink(path)

