import hashlib
import html
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from database import utcnow


def clean_text(value):
    text = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def normalize(value):
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()


def fingerprint(company, title, url=""):
    canonical_url = (url or "").split("?")[0].rstrip("/").lower()
    value = "|".join((normalize(company), normalize(title), canonical_url))
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def parse_skills(value):
    return [part.strip() for part in (value or "").split(",") if part.strip()]


def infer_skills(text, profile_skills):
    haystack = normalize(text)
    aliases = {".net": ["net", "dotnet", "asp net"], "c#": ["c#", "c sharp"], "sql server": ["sql server", "t sql"]}
    found = []
    for skill in profile_skills:
        terms = aliases.get(skill.lower(), [normalize(skill)])
        if any(term and term in haystack for term in terms):
            found.append(skill)
    return found


def score_opportunity(opportunity, profile):
    profile_skills = parse_skills(profile["skills"])
    text = " ".join(str(opportunity.get(k) or "") for k in ("title", "description", "required_skills", "preferred_skills"))
    matched = infer_skills(text, profile_skills)
    tech = min(100, 25 + len(matched) * 15) if matched else 15
    experience_terms = ["healthcare", "enterprise", "integration", "automation", "ai", "nlp", "database", "etl"]
    exp_hits = [term for term in experience_terms if term in normalize(text)]
    experience = min(100, 25 + len(exp_hits) * 15)
    rate = opportunity.get("compensation_max") or opportunity.get("compensation_min")
    period = (opportunity.get("compensation_period") or "").lower()
    compensation = 50
    if rate is not None and period == "hour":
        minimum = float(profile["minimum_hourly_rate"])
        preferred = float(profile["preferred_hourly_rate_min"])
        compensation = 100 if float(rate) >= preferred else (65 if float(rate) >= minimum else 20)
    contract = normalize(opportunity.get("contract_type"))
    flexibility = 90 if any(x in contract for x in ("contract", "freelance", "part time")) else 55
    remote_value = normalize(opportunity.get("remote_eligibility"))
    geo = normalize(opportunity.get("geographic_restrictions"))
    hard_pass = not any(x in geo for x in ("europe only", "uk only", "canada only", "india only"))
    remote = 100 if any(x in remote_value + " " + geo for x in ("remote", "worldwide", "usa", "united states")) else 35
    effort = 65
    score = round(tech * .30 + experience * .20 + compensation * .20 + flexibility * .15 + remote * .10 + effort * .05)
    if not hard_pass:
        score = min(score, 35)
    if score >= 85:
        recommendation = "Apply immediately"
    elif score >= 70:
        recommendation = "Strong candidate — review requirements"
    elif score >= 50:
        recommendation = "Possible candidate — additional skills needed"
    elif score >= 35:
        recommendation = "Low priority"
    else:
        recommendation = "Not recommended"
    reasons = []
    if matched:
        reasons.append("Matched skills: " + ", ".join(matched[:8]))
    else:
        reasons.append("No explicit profile skill match was found; review transferable experience.")
    if exp_hits:
        reasons.append("Relevant experience signals: " + ", ".join(exp_hits))
    reasons.append("Compensation is " + ("unknown and scored neutrally." if rate is None else "included using the stated rate."))
    if not hard_pass:
        reasons.append("Geographic eligibility appears incompatible and caps the score.")
    return {"score": score, "recommendation": recommendation, "explanation": " ".join(reasons),
            "skill_score": tech, "experience_score": experience, "compensation_score": compensation,
            "flexibility_score": flexibility, "remote_score": remote, "effort_score": effort,
            "hard_requirement_passed": int(hard_pass), "matched_skills": matched}


class OpportunityService:
    def __init__(self, db):
        self.db = db

    def save(self, data, source_platform=None):
        now = utcnow()
        fp = fingerprint(data.get("company"), data.get("title"), data.get("application_url"))
        existing = self.db.one("SELECT id FROM opportunities WHERE fingerprint=?", (fp,))
        if not existing and data.get("external_id"):
            existing = self.db.one("SELECT id FROM opportunities WHERE platform_id=? AND external_id=?", (data["platform_id"], str(data["external_id"])))
        if existing:
            self.db.execute("INSERT OR IGNORE INTO opportunity_sources(opportunity_id,platform_id,source_url,external_id,discovered_at) VALUES(?,?,?,?,?)",
                            (existing["id"], data["platform_id"], data["source_url"], data.get("external_id"), now))
            self.db.execute("UPDATE opportunities SET last_verified_at=?,is_available=1,updated_at=? WHERE id=?", (now, now, existing["id"]))
            return existing["id"], False
        fields = ["external_id","platform_id","company","title","description","required_skills","preferred_skills","compensation_min","compensation_max","compensation_period","currency","estimated_hours","remote_eligibility","geographic_restrictions","contract_type","application_url","source_url","posting_date","application_deadline","status","application_requirements","screening_requirements","payment_arrangements"]
        values = [data.get(f) for f in fields]
        defaults = {"required_skills":"", "preferred_skills":"", "currency":"USD", "remote_eligibility":"Unknown", "geographic_restrictions":"Unknown", "contract_type":"Unknown", "status":"Discovered", "application_requirements":"", "screening_requirements":"", "payment_arrangements":"Unknown"}
        values = [defaults.get(f) if value is None and f in defaults else value for f, value in zip(fields, values)]
        marks = ",".join("?" for _ in fields)
        opportunity_id = self.db.execute(f"INSERT INTO opportunities({','.join(fields)},discovered_at,last_verified_at,fingerprint,created_at,updated_at) VALUES({marks},?,?,?,?,?)", (*values, now, now, fp, now, now))
        self.db.execute("INSERT INTO opportunity_sources(opportunity_id,platform_id,source_url,external_id,discovered_at) VALUES(?,?,?,?,?)", (opportunity_id, data["platform_id"], data["source_url"], data.get("external_id"), now))
        self.rescore(opportunity_id)
        return opportunity_id, True

    def rescore(self, opportunity_id=None):
        profile = self.db.one("SELECT * FROM user_profile WHERE id=1")
        query = "SELECT * FROM opportunities" + (" WHERE id=?" if opportunity_id else "")
        for item in self.db.all(query, (opportunity_id,) if opportunity_id else ()):
            result = score_opportunity(item, profile)
            self.db.execute("""INSERT INTO opportunity_matches(opportunity_id,score,recommendation,explanation,skill_score,experience_score,compensation_score,flexibility_score,remote_score,effort_score,hard_requirement_passed,evaluated_at)
              VALUES(?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(opportunity_id) DO UPDATE SET score=excluded.score,recommendation=excluded.recommendation,explanation=excluded.explanation,skill_score=excluded.skill_score,experience_score=excluded.experience_score,compensation_score=excluded.compensation_score,flexibility_score=excluded.flexibility_score,remote_score=excluded.remote_score,effort_score=excluded.effort_score,hard_requirement_passed=excluded.hard_requirement_passed,evaluated_at=excluded.evaluated_at""",
              (item["id"], result["score"], result["recommendation"], result["explanation"], result["skill_score"], result["experience_score"], result["compensation_score"], result["flexibility_score"], result["remote_score"], result["effort_score"], result["hard_requirement_passed"], utcnow()))


class RemotiveSource:
    endpoint = "https://remotive.com/api/remote-jobs"

    def __init__(self, db, timeout=20):
        self.db, self.timeout = db, timeout

    def search(self, keyword):
        started, started_clock = utcnow(), time.monotonic()
        execution_id = self.db.execute("INSERT INTO search_executions(source,started_at,status) VALUES(?,?,?)", ("Remotive", started, "Running"))
        new_count = duplicate_count = 0
        try:
            url = self.endpoint + "?" + urllib.parse.urlencode({"search": keyword})
            request = urllib.request.Request(url, headers={"User-Agent":"IncomeGen/1.0 personal job-search application"})
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
            platform = self.db.one("SELECT id FROM platforms WHERE name='Remotive'")
            service = OpportunityService(self.db)
            for job in payload.get("jobs", []):
                salary = clean_text(job.get("salary")) or None
                data = {"external_id":str(job.get("id")), "platform_id":platform["id"], "company":clean_text(job.get("company_name")) or "Unknown",
                        "title":clean_text(job.get("title")) or "Untitled opportunity", "description":clean_text(job.get("description")),
                        "required_skills":",".join(job.get("tags") or []), "compensation_min":None, "compensation_max":None,
                        "compensation_period":None, "remote_eligibility":"Remote", "geographic_restrictions":clean_text(job.get("candidate_required_location")) or "Unknown",
                        "contract_type":clean_text(job.get("job_type")) or "Unknown", "application_url":job.get("url"), "source_url":job.get("url"),
                        "posting_date":job.get("publication_date"), "payment_arrangements":salary or "Unknown"}
                _, created = service.save(data)
                new_count += int(created); duplicate_count += int(not created)
            duration = round((time.monotonic() - started_clock) * 1000)
            self.db.execute("UPDATE search_executions SET completed_at=?,status='Success',found_count=?,new_count=?,duplicate_count=?,duration_ms=? WHERE id=?", (utcnow(), new_count+duplicate_count, new_count, duplicate_count, duration, execution_id))
            return {"found":new_count+duplicate_count,"new":new_count,"duplicates":duplicate_count}
        except Exception as exc:
            duration = round((time.monotonic() - started_clock) * 1000)
            self.db.execute("UPDATE search_executions SET completed_at=?,status='Failed',error_message=?,duration_ms=? WHERE id=?", (utcnow(), str(exc)[:500], duration, execution_id))
            raise

