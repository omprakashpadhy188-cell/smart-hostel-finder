"""Recommendation engine: hard filters + weighted scoring with a feature matrix.

How it works
1. Hard filters remove hostels that cannot work (wrong city/gender, Veg/Non-Veg mismatch,
   no available room option that matches sharing + AC choice within budget).
2. Every remaining hostel becomes one row of a feature matrix X (n_hostels x 4):
       [price_score, distance_score, amenity_score, rating_score]   each between 0 and 1
3. Final score = X @ w, where w is the user's weight vector (normalised to sum to 1).
4. Hostels are sorted by score and the top N are returned.
"""
import numpy as np

GENDERS = {"Boys", "Girls", "Co-ed"}
FOODS = {"Veg", "Non-Veg", "Both", "Any"}
AC_PREFS = {"AC", "Non-AC", "Any"}
FEATURES = ["price", "distance", "amenities", "rating"]
DEFAULT_WEIGHTS = {"w_price": 0.30, "w_distance": 0.20, "w_amenities": 0.30, "w_rating": 0.20}
DEFAULT_MAX_DISTANCE = 10.0


# ---------------------------------------------------------------- validation
def validate_prefs(data):
    """Check and clean the user's preferences. Raises ValueError with a clear message."""
    p = {}
    city = str(data.get("city", "")).strip()
    if not city:
        raise ValueError("'city' is required")
    p["city"] = city

    try:
        budget = float(data.get("max_budget"))
    except (TypeError, ValueError):
        raise ValueError("'max_budget' is required and must be a number")
    if budget <= 0:
        raise ValueError("'max_budget' must be greater than 0")
    p["max_budget"] = budget

    sharing = data.get("sharing_capacity")
    if sharing in (None, ""):
        p["sharing_capacity"] = None
    else:
        try:
            sharing = int(sharing)
        except (TypeError, ValueError):
            raise ValueError("'sharing_capacity' must be a whole number from 1 to 5")
        if not 1 <= sharing <= 5:
            raise ValueError("'sharing_capacity' must be between 1 and 5")
        p["sharing_capacity"] = sharing

    ac = data.get("ac_preference") or "Any"
    if ac not in AC_PREFS:
        raise ValueError(f"'ac_preference' must be one of {sorted(AC_PREFS)}")
    p["ac_preference"] = ac

    gender = data.get("gender") or None
    if gender is not None and gender not in GENDERS:
        raise ValueError(f"'gender' must be one of {sorted(GENDERS)}")
    p["gender"] = gender

    food = data.get("food_pref") or "Any"
    if food not in FOODS:
        raise ValueError(f"'food_pref' must be one of {sorted(FOODS)}")
    p["food_pref"] = food

    dist = data.get("max_distance_km")
    if dist in (None, ""):
        p["max_distance_km"] = None
    else:
        try:
            dist = float(dist)
        except (TypeError, ValueError):
            raise ValueError("'max_distance_km' must be a number")
        if dist <= 0:
            raise ValueError("'max_distance_km' must be greater than 0")
        p["max_distance_km"] = dist

    amenities = data.get("must_have_amenities") or []
    if isinstance(amenities, str):                      # allow "WiFi;Mess/Meals"
        amenities = [a for a in amenities.split(";") if a.strip()]
    if not isinstance(amenities, list):
        raise ValueError("'must_have_amenities' must be a list of names")
    p["must_have_amenities"] = [str(a).strip() for a in amenities]

    weights = {}
    for key, default in DEFAULT_WEIGHTS.items():
        try:
            w = float(data.get(key, default))
        except (TypeError, ValueError):
            raise ValueError(f"'{key}' must be a number")
        if w < 0:
            raise ValueError(f"'{key}' cannot be negative")
        weights[key] = w
    if sum(weights.values()) == 0:
        raise ValueError("At least one weight must be greater than 0")
    p["weights"] = weights

    try:
        top_n = int(data.get("top_n", 10))
    except (TypeError, ValueError):
        raise ValueError("'top_n' must be a whole number")
    if not 1 <= top_n <= 20:
        raise ValueError("'top_n' must be between 1 and 20")
    p["top_n"] = top_n
    return p


# ---------------------------------------------------------------- core logic
def _best_room(hostel, prefs):
    """Cheapest room option that fits the sharing / AC / budget / availability needs."""
    fits = []
    for r in hostel["rooms"]:
        if r["rooms_available"] <= 0:
            continue
        if prefs["sharing_capacity"] and r["sharing_capacity"] != prefs["sharing_capacity"]:
            continue
        if prefs["ac_preference"] != "Any" and r["ac_type"] != prefs["ac_preference"]:
            continue
        if r["monthly_rent"] > prefs["max_budget"]:
            continue
        fits.append(r)
    return min(fits, key=lambda r: r["monthly_rent"]) if fits else None


def _passes_basic_filters(h, prefs):
    if prefs["gender"] and h["gender_type"] not in (prefs["gender"], "Co-ed"):
        return False
    food = prefs["food_pref"]
    if food in ("Veg", "Non-Veg") and h["food_type"] not in (food, "Both"):
        return False          # 'Both' or 'Any' means the student has no food restriction
    return True               # distance is NOT a hard filter: far hostels just score lower


def rank_hostels(hostels, prefs):
    """hostels: list of dicts, each with keys
         hostel_id, name, city, area, nearest_institution, gender_type, food_type,
         rating, distance_to_campus_km, mess_price, laundry_price,
         amenities (list of names), rooms (list of room-option dicts)
       prefs: output of validate_prefs()."""
    required = prefs["must_have_amenities"]
    required_lower = {a.lower() for a in required}
    max_d = prefs["max_distance_km"] or DEFAULT_MAX_DISTANCE

    candidates = []
    for h in hostels:
        if not _passes_basic_filters(h, prefs):
            continue
        room = _best_room(h, prefs)
        if room is None:
            continue
        # monthly cost = rent + the paid facilities the student asked for
        cost = room["monthly_rent"]
        if "mess/meals" in required_lower:
            cost += h.get("mess_price") or 0
        if "laundry" in required_lower:
            cost += h.get("laundry_price") or 0
        have = {a.lower() for a in h["amenities"]}
        matched = [a for a in required if a.lower() in have]
        candidates.append((h, room, cost, matched))

    if not candidates:
        return []

    # ---- build the feature matrix X (one row per hostel, one column per feature)
    costs = np.array([c[2] for c in candidates], dtype=float)
    span = costs.max() - costs.min()
    price_score = np.ones(len(costs)) if span == 0 else 1 - (costs - costs.min()) / span   # cheapest = 1

    dist = np.array([c[0]["distance_to_campus_km"] for c in candidates], dtype=float)
    distance_score = np.clip(1 - dist / max_d, 0, 1)                                         # closer = higher

    if required:
        amenity_score = np.array([len(c[3]) / len(required) for c in candidates])           # share of wishes met
    else:
        amenity_score = np.array([min(len(c[0]["amenities"]) / 12, 1) for c in candidates])  # general richness

    rating = np.array([c[0]["rating"] for c in candidates], dtype=float)
    rating_score = np.clip((rating - 2.5) / 2.5, 0, 1)                                       # 2.5 -> 0, 5.0 -> 1

    X = np.column_stack([price_score, distance_score, amenity_score, rating_score])

    # ---- weighted score: X @ w
    w = np.array([prefs["weights"][k] for k in ("w_price", "w_distance", "w_amenities", "w_rating")], dtype=float)
    w = w / w.sum()
    scores = X @ w

    results = []
    for i in np.argsort(-scores, kind="stable")[: prefs["top_n"]]:
        h, room, cost, matched = candidates[i]
        results.append({
            "hostel_id": h["hostel_id"], "name": h["name"], "city": h["city"], "area": h["area"],
            "nearest_institution": h["nearest_institution"], "gender_type": h["gender_type"],
            "food_type": h["food_type"], "rating": h["rating"],
            "distance_to_campus_km": h["distance_to_campus_km"],
            "within_preferred_distance": h["distance_to_campus_km"] <= max_d,
            "match_score": round(float(scores[i]) * 100, 1),
            "best_room": {k: room[k] for k in ("sharing_capacity", "ac_type", "monthly_rent", "security_deposit", "rooms_available")},
            "mess_price": h.get("mess_price") or 0, "laundry_price": h.get("laundry_price") or 0,
            "total_monthly_cost": int(cost),
            "matched_amenities": matched,
            "missing_amenities": [a for a in required if a not in matched],
            "score_breakdown": {f: round(float(X[i, j]), 2) for j, f in enumerate(FEATURES)},
        })
    return results
