import os
import shutil
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlparse

from flask import Flask, abort, flash, redirect, render_template, request, url_for

from config import Config
from database import Database, utcnow
from services import OpportunityService, RemotiveSource
from recommended_roles import RECOMMENDED_ROLES, VERIFIED_ON


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    db = Database(app.config["DATABASE"])
    db.initialize()
    app.extensions["database"] = db

    @app.context_processor
    def shared_template_values():
        return {"today": date.today().strftime("%A, %B %d, %Y")}

    @app.template_filter("money")
    def money(value):
        return "Unknown" if value is None or value == "" else "${:,.2f}".format(float(value))

    @app.template_filter("datefmt")
    def datefmt(value):
        if not value:
            return "Unknown"
        return str(value)[:10]

    @app.route("/")
    def dashboard():
        metrics = db.one("""SELECT COUNT(*) total, SUM(CASE WHEN date(discovered_at)=date('now') THEN 1 ELSE 0 END) new_count,
          SUM(CASE WHEN m.score>=85 THEN 1 ELSE 0 END) high_match,
          SUM(CASE WHEN status NOT IN ('Discovered','Expired','Rejected','Withdrawn') THEN 1 ELSE 0 END) active_applications
          FROM opportunities o LEFT JOIN opportunity_matches m ON m.opportunity_id=o.id""")
        recommended = db.all("""SELECT o.*,p.name platform,m.score,m.recommendation FROM opportunities o
          JOIN platforms p ON p.id=o.platform_id LEFT JOIN opportunity_matches m ON m.opportunity_id=o.id
          WHERE o.is_available=1 ORDER BY m.score DESC,o.discovered_at DESC LIMIT 6""")
        logs = db.all("SELECT * FROM search_executions ORDER BY started_at DESC LIMIT 4")
        profile = db.one("SELECT * FROM user_profile WHERE id=1")
        return render_template("dashboard.html", metrics=metrics, recommended=recommended, logs=logs, profile=profile,
                               current_recommendations=RECOMMENDED_ROLES[:5], recommendations_verified=VERIFIED_ON,
                               recommendation_count=len(RECOMMENDED_ROLES))

    @app.route("/recommended")
    def recommended_jobs():
        platform = request.args.get("platform", "").strip()
        category = request.args.get("category", "").strip()
        query = request.args.get("q", "").strip().lower()
        minimum_fit = request.args.get("min_fit", type=int) or 0
        roles = [role for role in RECOMMENDED_ROLES
                 if (not platform or role["platform"] == platform)
                 and (not category or role["category"] == category)
                 and role["fit"] >= minimum_fit
                 and (not query or query in (role["title"] + " " + role["why"] + " " + role["category"]).lower())]
        return render_template("recommended.html", roles=roles, verified_on=VERIFIED_ON,
                               platforms=sorted({r["platform"] for r in RECOMMENDED_ROLES}),
                               categories=sorted({r["category"] for r in RECOMMENDED_ROLES}))

    @app.route("/opportunities")
    def opportunities():
        clauses, params = [], []
        if request.args.get("q"):
            clauses.append("(o.title LIKE ? OR o.company LIKE ? OR o.description LIKE ?)")
            token = "%" + request.args["q"] + "%"; params.extend([token]*3)
        if request.args.get("platform"):
            clauses.append("p.id=?"); params.append(request.args["platform"])
        if request.args.get("min_score"):
            clauses.append("m.score>=?"); params.append(request.args["min_score"])
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        items = db.all("""SELECT o.*,p.name platform,m.score,m.recommendation,m.explanation FROM opportunities o
          JOIN platforms p ON p.id=o.platform_id LEFT JOIN opportunity_matches m ON m.opportunity_id=o.id""" + where + " ORDER BY m.score DESC,o.discovered_at DESC", params)
        return render_template("opportunities.html", opportunities=items, platforms=db.all("SELECT * FROM platforms ORDER BY name"))

    @app.route("/opportunities/new", methods=["GET","POST"])
    def new_opportunity():
        if request.method == "POST":
            def decimal(name):
                value = request.form.get(name, "").strip()
                try: return float(Decimal(value)) if value else None
                except InvalidOperation: raise ValueError("Compensation must be numeric.")
            try:
                data = {key: request.form.get(key, "").strip() or None for key in ("company","title","description","required_skills","preferred_skills","compensation_period","currency","remote_eligibility","geographic_restrictions","contract_type","application_url","source_url","posting_date","application_deadline","application_requirements","screening_requirements","payment_arrangements")}
                data.update(platform_id=int(request.form["platform_id"]), compensation_min=decimal("compensation_min"), compensation_max=decimal("compensation_max"))
                if not all(data.get(k) for k in ("company","title","description","application_url","source_url")): raise ValueError("Company, title, description, application URL, and source URL are required.")
                for name in ("application_url", "source_url"):
                    parsed = urlparse(data[name])
                    if parsed.scheme not in ("http", "https") or not parsed.netloc:
                        raise ValueError("Application and source URLs must use http or https.")
                _, created = OpportunityService(db).save(data)
                flash("Opportunity added and scored." if created else "Duplicate found; the existing listing was refreshed.", "success")
                return redirect(url_for("opportunities"))
            except (ValueError, KeyError) as exc:
                flash(str(exc), "error")
        return render_template("opportunity_form.html", platforms=db.all("SELECT * FROM platforms WHERE enabled=1 ORDER BY name"))

    @app.route("/opportunities/<int:item_id>")
    def opportunity_detail(item_id):
        item = db.one("""SELECT o.*,p.name platform,p.official_url,m.* FROM opportunities o JOIN platforms p ON p.id=o.platform_id LEFT JOIN opportunity_matches m ON m.opportunity_id=o.id WHERE o.id=?""", (item_id,))
        if not item: abort(404)
        return render_template("opportunity_detail.html", item=item, sources=db.all("SELECT * FROM opportunity_sources WHERE opportunity_id=?", (item_id,)))

    @app.post("/search/remotive")
    def search_remotive():
        keyword = request.form.get("keyword", "AI Python").strip()[:100]
        try:
            result = RemotiveSource(db, app.config["REQUEST_TIMEOUT"]).search(keyword)
            flash(f"Remotive search completed: {result['new']} new, {result['duplicates']} duplicates.", "success")
        except Exception as exc:
            app.logger.exception("Remotive search failed")
            flash(f"Remotive could not be searched: {exc}", "error")
        return redirect(url_for("opportunities"))

    @app.route("/profile", methods=["GET","POST"])
    def profile():
        if request.method == "POST":
            fields = ["full_name","headline","education","experience","skills","work_location","contract_types","minimum_hourly_rate","preferred_hourly_rate_min","preferred_hourly_rate_max","weekly_hours_min","weekly_hours_max","monthly_income_goal"]
            db.execute("UPDATE user_profile SET " + ",".join(f+"=?" for f in fields) + ",updated_at=? WHERE id=1", tuple(request.form.get(f, "").strip() for f in fields) + (utcnow(),))
            OpportunityService(db).rescore()
            flash("Profile saved and all opportunities rescored.", "success")
            return redirect(url_for("profile"))
        return render_template("profile.html", profile=db.one("SELECT * FROM user_profile WHERE id=1"))

    @app.route("/platforms")
    def platforms():
        return render_template("platforms.html", platforms=db.all("SELECT * FROM platforms ORDER BY CASE priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END,name"))

    @app.route("/search-history")
    def search_history():
        return render_template("search_history.html", logs=db.all("SELECT * FROM search_executions ORDER BY started_at DESC"))

    @app.post("/backup")
    def backup():
        backup_dir = Path(app.root_path) / "backups"; backup_dir.mkdir(exist_ok=True)
        target = backup_dir / ("incomegen-" + date.today().isoformat() + ".db")
        shutil.copy2(app.config["DATABASE"], target)
        flash(f"Database backup created: {target.name}", "success")
        return redirect(request.referrer or url_for("dashboard"))

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5051, debug=os.getenv("FLASK_DEBUG") == "1")

