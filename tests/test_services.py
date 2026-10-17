from services import clean_text, fingerprint, score_opportunity


PROFILE = {"skills":"Python,SQL Server,NLP,Healthcare IT,ETL", "minimum_hourly_rate":25, "preferred_hourly_rate_min":40}


def test_clean_text_removes_external_html():
    assert clean_text("<p>Python &amp; SQL</p><script>bad</script>") == "Python & SQL bad"


def test_fingerprint_ignores_tracking_query():
    assert fingerprint("Acme", "AI Engineer", "https://x.test/job/1?a=1") == fingerprint("ACME", "AI Engineer", "https://x.test/job/1?b=2")


def test_matching_is_explainable_and_high_for_relevant_role():
    result = score_opportunity({"title":"Python NLP Healthcare AI Consultant","description":"SQL Server ETL automation", "required_skills":"Python,NLP,SQL Server", "compensation_max":60, "compensation_period":"hour", "contract_type":"contract part time", "remote_eligibility":"remote USA", "geographic_restrictions":"United States"}, PROFILE)
    assert result["score"] >= 85
    assert "Matched skills" in result["explanation"]


def test_ineligible_geography_caps_score():
    result = score_opportunity({"title":"Python NLP Engineer","description":"Python NLP healthcare ETL SQL Server", "compensation_max":80, "compensation_period":"hour", "contract_type":"contract", "remote_eligibility":"remote", "geographic_restrictions":"Europe only"}, PROFILE)
    assert result["score"] <= 35
    assert not result["hard_requirement_passed"]

