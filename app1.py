from flask import Flask, request, jsonify
from flask_cors import CORS
import random
from datetime import datetime, timedelta

# ML model import
from model import civic_assistant

app = Flask(__name__)
CORS(app)

# =====================================================
# In-memory database
# =====================================================
issues = []

# =====================================================
# Action Guide
# =====================================================
action_guide = {
    "waste": [
        "Dry aur wet waste alag rakhein.",
        "Complaint ke saath photo upload karein.",
        "48 ghante me safai na ho to re-report karein."
    ],
    "water": [
        "Leak ya problem ki clear photo upload karein.",
        "Main valve check karein.",
        "Emergency me tanker request karein."
    ],
    "air": [
        "Pollution source ki exact location mention karein.",
        "Mask use karein aur polluted area se door rahein."
    ],
    "transport": [
        "Problem wali jagah ka landmark likhein.",
        "Peak time mention karein."
    ],
    "energy": [
        "Spark ya exposed wire se turant door rahein.",
        "Pole ya meter number mention karein."
    ],
    "sanitation": [
        "Blocked drain ki photo upload karein.",
        "Bachon ko us area se door rakhein."
    ],
    "noise": [
        "Noise ka time aur source clearly likhein.",
        "Night disturbance ho to urgent mark karein."
    ]
}

# =====================================================
# Priority Keywords
# =====================================================
HIGH_PRIORITY_KEYWORDS = [
    "spark", "fire", "short circuit", "blast",
    "gas leak", "exposed wire", "danger",
    "accident", "transformer", "electric shock",
    "sewer overflow", "open manhole"
]

MEDIUM_PRIORITY_KEYWORDS = [
    "overflow", "blocked", "jam",
    "not working", "broken",
    "garbage", "dustbin", "pothole",
    "leak", "bad smell"
]

# =====================================================
# Helper Functions
# =====================================================
def is_near(lat1, lon1, lat2, lon2, threshold=0.002):
    return abs(lat1 - lat2) < threshold and abs(lon1 - lon2) < threshold


def get_area_key(lat, lon):
    return f"{round(lat,2)}_{round(lon,2)}"


def priority_from_keywords(text):
    text = text.lower()
    for w in HIGH_PRIORITY_KEYWORDS:
        if w in text:
            return "high"
    for w in MEDIUM_PRIORITY_KEYWORDS:
        if w in text:
            return "medium"
    return "low"


def priority_from_count(count):
    if count >= 5:
        return "high"
    elif count >= 3:
        return "medium"
    return "low"


def priority_from_time(created_at):
    days = (datetime.now() - created_at).days
    if days >= 6:
        return "high"
    elif days >= 3:
        return "medium"
    return "low"


def trust_from_supporters(count):
    if count >= 5:
        return "high"
    elif count >= 3:
        return "medium"
    return "low"


def merge_priority(p1, p2):
    order = {"low": 1, "medium": 2, "high": 3}
    return p1 if order[p1] >= order[p2] else p2

# =====================================================
# USER ROUTES
# =====================================================
@app.route("/")
def home():
    return "Civic Sustainability Assistant Backend Running 🚀"


@app.route("/predict", methods=["POST"])
def predict():
    data = request.json
    text = data["text"]
    location = data.get("location", "0,0")

    lat, lon = map(float, location.split(","))

    category, authority = civic_assistant(text)
    actions = action_guide.get(category, [])

    keyword_priority = priority_from_keywords(text)

    # Duplicate detection
    for issue in issues:
        if issue["category"] == category and is_near(lat, lon, issue["lat"], issue["lon"]):
            issue["count"] += 1

            count_priority = priority_from_count(issue["count"])
            time_priority = priority_from_time(issue["created_at"])
            trust = trust_from_supporters(issue["count"])

            issue["priority"] = merge_priority(
                merge_priority(keyword_priority, count_priority),
                time_priority
            )

            return jsonify({
                "duplicate": True,
                "id": issue["id"],
                "category": category,
                "authority": authority,
                "priority": issue["priority"],
                "trust_level": trust,
                "supporters": issue["count"],
                "actions": actions,
                "message": "Same issue already reported. Trust & priority increased."
            })

    # New issue
    new_issue = {
        "id": random.randint(1000, 9999),
        "category": category,
        "lat": lat,
        "lon": lon,
        "count": 1,
        "priority": keyword_priority,
        "trust_level": "low",
        "status": "open",
        "created_at": datetime.now()
    }

    issues.append(new_issue)

    return jsonify({
        "duplicate": False,
        "id": new_issue["id"],
        "category": category,
        "authority": authority,
        "priority": new_issue["priority"],
        "trust_level": "low",
        "supporters": 1,
        "actions": actions,
        "message": "New issue created."
    })

# =====================================================
# ADMIN ROUTES
# =====================================================
@app.route("/admin/issues", methods=["GET"])
def admin_all_issues():
    return jsonify(issues)


@app.route("/admin/issues/high", methods=["GET"])
def admin_high_priority():
    return jsonify([
        i for i in issues
        if i["priority"] == "high" and i["status"] == "open"
    ])


@app.route("/admin/resolve/<int:issue_id>", methods=["POST"])
def admin_resolve(issue_id):
    for issue in issues:
        if issue["id"] == issue_id:
            issue["status"] = "resolved"
            return jsonify({"message": "Issue resolved by admin"})
    return jsonify({"error": "Issue not found"}), 404


@app.route("/admin/stats", methods=["GET"])
def admin_stats():
    total = len(issues)
    resolved = len([i for i in issues if i["status"] == "resolved"])
    open_issues = total - resolved
    high_priority = len([i for i in issues if i["priority"] == "high"])

    return jsonify({
        "total_issues": total,
        "open_issues": open_issues,
        "resolved_issues": resolved,
        "high_priority_issues": high_priority
    })


@app.route("/admin/areas/critical", methods=["GET"])
def admin_critical_areas():
    area_stats = {}

    for issue in issues:
        area = get_area_key(issue["lat"], issue["lon"])
        if area not in area_stats:
            area_stats[area] = {"total": 0, "resolved": 0}

        area_stats[area]["total"] += 1
        if issue["status"] == "resolved":
            area_stats[area]["resolved"] += 1

    critical = []
    for area, stats in area_stats.items():
        score = int((stats["resolved"] / stats["total"]) * 100) if stats["total"] else 0
        if score < 40:
            critical.append({
                "area": area,
                "health_score": score
            })

    return jsonify(critical)


@app.route("/area-health", methods=["GET"])
def area_health():
    area_stats = {}

    for issue in issues:
        if issue["status"] == "open":
            issue["priority"] = merge_priority(
                issue["priority"],
                priority_from_time(issue["created_at"])
            )

        area = get_area_key(issue["lat"], issue["lon"])
        if area not in area_stats:
            area_stats[area] = {"total": 0, "resolved": 0}

        area_stats[area]["total"] += 1
        if issue["status"] == "resolved":
            area_stats[area]["resolved"] += 1

    result = []
    for area, stats in area_stats.items():
        score = int((stats["resolved"] / stats["total"]) * 100) if stats["total"] else 0
        color = "green" if score >= 70 else "yellow" if score >= 40 else "red"

        result.append({
            "area": area,
            "health_score": score,
            "color": color,
            "total_issues": stats["total"],
            "resolved_issues": stats["resolved"]
        })

    return jsonify(result)

# =====================================================
# Run Server
# =====================================================
if __name__ == "__main__":
    app.run(debug=True)