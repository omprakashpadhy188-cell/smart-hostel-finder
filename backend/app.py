"""Smart Hostel Finder - Flask API (step 1: search + details).
Run:  python app.py      then open  http://127.0.0.1:5000/api/hostels
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
import mysql.connector
from db import query
from recommend import validate_prefs, rank_hostels
from admin import admin_bp

app = Flask(__name__)
CORS(app)
app.register_blueprint(admin_bp)

GENDERS = {"Boys", "Girls", "Co-ed"}
FOODS = {"Veg", "Non-Veg", "Both"}


class BadRequest(Exception):
    pass


def int_arg(name, lo=None, hi=None):
    """Read an optional integer query parameter with range validation."""
    raw = request.args.get(name)
    if raw in (None, ""):
        return None
    try:
        val = int(raw)
    except ValueError:
        raise BadRequest(f"'{name}' must be a whole number")
    if (lo is not None and val < lo) or (hi is not None and val > hi):
        raise BadRequest(f"'{name}' must be between {lo} and {hi}")
    return val


@app.get("/api/health")
def health():
    return jsonify(status="ok")


@app.get("/api/hostels")
def list_hostels():
    """Filters (all optional): city, gender, food, max_budget, sharing (1-5), ac (yes|no), limit"""
    where, params = [], []

    city = request.args.get("city")
    if city:
        where.append("h.city = %s"); params.append(city)

    gender = request.args.get("gender")
    if gender:
        if gender not in GENDERS:
            raise BadRequest(f"gender must be one of {sorted(GENDERS)}")
        where.append("h.gender_type = %s"); params.append(gender)

    food = request.args.get("food")
    if food:
        if food not in FOODS:
            raise BadRequest(f"food must be one of {sorted(FOODS)}")
        where.append("h.food_type = %s"); params.append(food)

    max_budget = int_arg("max_budget", lo=1)
    if max_budget is not None:
        where.append("ro.monthly_rent <= %s"); params.append(max_budget)

    sharing = int_arg("sharing", lo=1, hi=5)
    if sharing is not None:
        where.append("ro.sharing_capacity = %s"); params.append(sharing)

    ac = request.args.get("ac")
    if ac:
        if ac.lower() not in ("yes", "no"):
            raise BadRequest("ac must be 'yes' or 'no'")
        where.append("ro.ac_type = %s"); params.append("AC" if ac.lower() == "yes" else "Non-AC")

    limit = int_arg("limit", lo=1, hi=100) or 50

    sql = """
        SELECT h.hostel_id, h.name, h.city, h.area, h.nearest_institution, h.gender_type,
               h.food_type, h.rating, h.review_count, h.distance_to_campus_km,
               h.mess_price, h.laundry_price,
               MIN(ro.monthly_rent) AS min_rent,
               COUNT(ro.option_id)  AS matching_room_options
        FROM hostels h
        JOIN room_options ro ON ro.hostel_id = h.hostel_id
    """
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " GROUP BY h.hostel_id ORDER BY h.rating DESC, min_rent ASC LIMIT %s"
    params.append(limit)

    rows = query(sql, params)
    return jsonify(count=len(rows), hostels=rows)


@app.get("/api/hostels/<int:hostel_id>")
def hostel_detail(hostel_id):
    hostel = query("SELECT * FROM hostels WHERE hostel_id = %s", (hostel_id,))
    if not hostel:
        return jsonify(error=f"Hostel {hostel_id} not found"), 404
    rooms = query(
        "SELECT sharing_capacity, ac_type, attached_bathroom, monthly_rent, security_deposit, total_rooms, rooms_available "
        "FROM room_options WHERE hostel_id = %s ORDER BY ac_type, sharing_capacity", (hostel_id,))
    amenities = query(
        "SELECT a.amenity_name FROM hostel_amenities ha "
        "JOIN amenities a ON a.amenity_id = ha.amenity_id WHERE ha.hostel_id = %s", (hostel_id,))
    result = hostel[0]
    result["ac_available"] = any(r["ac_type"] == "AC" for r in rooms)
    result["rooms"] = rooms
    result["amenities"] = [a["amenity_name"] for a in amenities]
    return jsonify(result)


def attach_details(hostels):
    """Add 'rooms' and 'amenities' lists to each hostel dict (2 queries for all hostels)."""
    if not hostels:
        return hostels
    ids = [h["hostel_id"] for h in hostels]
    marks = ",".join(["%s"] * len(ids))          # only %s placeholders are inserted, never user text
    rooms = query(f"SELECT * FROM room_options WHERE hostel_id IN ({marks})", ids)
    amens = query(
        f"SELECT ha.hostel_id, a.amenity_name FROM hostel_amenities ha "
        f"JOIN amenities a ON a.amenity_id = ha.amenity_id WHERE ha.hostel_id IN ({marks})", ids)
    for h in hostels:
        h["rooms"] = [r for r in rooms if r["hostel_id"] == h["hostel_id"]]
        h["amenities"] = [a["amenity_name"] for a in amens if a["hostel_id"] == h["hostel_id"]]
    return hostels


def load_candidates(city):
    """Every hostel in a city together with its rooms and amenities."""
    return attach_details(query("SELECT * FROM hostels WHERE city = %s", (city,)))


@app.post("/api/recommend")
def recommend():
    """Body (JSON): city, max_budget (required); sharing_capacity, ac_preference, gender,
    food_pref, max_distance_km, must_have_amenities, w_price, w_distance, w_amenities, w_rating, top_n"""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise BadRequest("Send a JSON body with at least 'city' and 'max_budget'")
    try:
        prefs = validate_prefs(payload)
    except ValueError as e:
        raise BadRequest(str(e))
    results = rank_hostels(load_candidates(prefs["city"]), prefs)
    message = None if results else "No hostel matches all your requirements. Try a higher budget, another sharing type, or a larger distance."
    return jsonify(count=len(results), message=message, results=results)


@app.get("/api/compare")
def compare_hostels():
    """GET /api/compare?ids=81,82,85  - side-by-side comparison of 2 to 4 hostels."""
    raw = request.args.get("ids", "")
    try:
        ids = [int(x) for x in raw.split(",") if x.strip()]
    except ValueError:
        raise BadRequest("'ids' must be comma-separated hostel numbers, e.g. ids=81,82,85")
    ids = list(dict.fromkeys(ids))                       # remove duplicates, keep order
    if not 2 <= len(ids) <= 4:
        raise BadRequest("Give between 2 and 4 different hostel ids, e.g. ids=81,82,85")

    marks = ",".join(["%s"] * len(ids))
    found = attach_details(query(f"SELECT * FROM hostels WHERE hostel_id IN ({marks})", ids))
    by_id = {h["hostel_id"]: h for h in found}
    missing = [i for i in ids if i not in by_id]
    if missing:
        return jsonify(error=f"Hostel id(s) not found: {missing}"), 404

    def options(h, ac_type):
        return [{"sharing_capacity": r["sharing_capacity"], "monthly_rent": r["monthly_rent"]}
                for r in sorted(h["rooms"], key=lambda r: r["sharing_capacity"]) if r["ac_type"] == ac_type]

    items = []
    for i in ids:                                         # keep the order the user asked for
        h = by_id[i]
        rents = [r["monthly_rent"] for r in h["rooms"]]
        items.append({
            "hostel_id": h["hostel_id"], "name": h["name"], "city": h["city"], "area": h["area"],
            "nearest_institution": h["nearest_institution"], "gender_type": h["gender_type"],
            "food_type": h["food_type"], "rating": h["rating"], "review_count": h["review_count"],
            "distance_to_campus_km": h["distance_to_campus_km"],
            "ac_available": any(r["ac_type"] == "AC" for r in h["rooms"]),
            "ac_options": options(h, "AC"), "non_ac_options": options(h, "Non-AC"),
            "min_rent": min(rents) if rents else None,
            "mess_price": h["mess_price"], "laundry_price": h["laundry_price"],
            "amenities": sorted(h["amenities"]),
        })

    common = set(items[0]["amenities"])
    for it in items[1:]:
        common &= set(it["amenities"])
    priced = [it for it in items if it["min_rent"] is not None]
    highlights = {
        "cheapest_rent": min(priced, key=lambda x: x["min_rent"])["hostel_id"] if priced else None,
        "best_rated": max(items, key=lambda x: x["rating"])["hostel_id"],
        "nearest_to_campus": min(items, key=lambda x: x["distance_to_campus_km"])["hostel_id"],
        "most_amenities": max(items, key=lambda x: len(x["amenities"]))["hostel_id"],
    }
    return jsonify(count=len(items), highlights=highlights, common_amenities=sorted(common), hostels=items)


@app.errorhandler(BadRequest)
def handle_bad_request(e):
    return jsonify(error=str(e)), 400


@app.errorhandler(mysql.connector.Error)
def handle_db_error(e):
    app.logger.exception(e)
    return jsonify(error="Database error - check MySQL is running and the password in db.py"), 500


@app.errorhandler(404)
def handle_404(e):
    return jsonify(error="Route not found"), 404


if __name__ == "__main__":
    app.run(debug=True)
