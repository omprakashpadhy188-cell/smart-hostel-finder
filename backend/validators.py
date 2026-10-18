"""Input validation for the admin (create / update) endpoints."""
import re

GENDERS = ("Boys", "Girls", "Co-ed")
FOODS = ("Veg", "Non-Veg", "Both")
TIERS = ("budget", "standard", "premium")
AC_TYPES = ("AC", "Non-AC")


class ValidationError(ValueError):
    """Raised when the data sent by the client is invalid (becomes a 400 response)."""


def _text(data, key, max_len, required):
    val = data.get(key)
    if val is None or str(val).strip() == "":
        if required:
            raise ValidationError(f"'{key}' is required")
        return None
    val = str(val).strip()
    if len(val) > max_len:
        raise ValidationError(f"'{key}' must be at most {max_len} characters")
    return val


def _choice(data, key, options, required):
    val = data.get(key)
    if val is None or val == "":
        if required:
            raise ValidationError(f"'{key}' is required (one of {list(options)})")
        return None
    if val not in options:
        raise ValidationError(f"'{key}' must be one of {list(options)}")
    return val


def _number(data, key, lo, hi, required, integer=False, decimals=None):
    val = data.get(key)
    if val is None or val == "":
        if required:
            raise ValidationError(f"'{key}' is required")
        return None
    try:
        num = int(val) if integer else float(val)
        if integer and isinstance(val, float) and val != int(val):
            raise ValueError
    except (TypeError, ValueError):
        raise ValidationError(f"'{key}' must be a {'whole ' if integer else ''}number")
    if isinstance(val, bool) or not lo <= num <= hi:
        raise ValidationError(f"'{key}' must be between {lo} and {hi}")
    return round(num, decimals) if decimals is not None else num


# column -> function(data, partial) returning the cleaned value (None = not provided)
def validate_hostel(data, partial=False):
    """Return a dict of cleaned hostel columns.
    partial=False (create): required fields must be present and defaults are filled in.
    partial=True  (update): only the keys that were sent are validated and returned."""
    req = not partial
    specs = {
        "name":                  lambda: _text(data, "name", 100, req),
        "city":                  lambda: _text(data, "city", 50, req),
        "area":                  lambda: _text(data, "area", 80, req),
        "nearest_institution":   lambda: _text(data, "nearest_institution", 120, False),
        "gender_type":           lambda: _choice(data, "gender_type", GENDERS, req),
        "food_type":             lambda: _choice(data, "food_type", FOODS, req),
        "price_tier":            lambda: _choice(data, "price_tier", TIERS, req),
        "rating":                lambda: _number(data, "rating", 0, 5, False, decimals=1),
        "review_count":          lambda: _number(data, "review_count", 0, 10_000_000, False, integer=True),
        "distance_to_campus_km": lambda: _number(data, "distance_to_campus_km", 0, 99.9, req, decimals=1),
        "latitude":              lambda: _number(data, "latitude", -90, 90, False, decimals=5),
        "longitude":             lambda: _number(data, "longitude", -180, 180, False, decimals=5),
        "established_year":      lambda: _number(data, "established_year", 1900, 2026, False, integer=True),
        "mess_price":            lambda: _number(data, "mess_price", 0, 100000, False, integer=True),
        "laundry_price":         lambda: _number(data, "laundry_price", 0, 100000, False, integer=True),
    }
    out = {}
    for col, fn in specs.items():
        if partial and col not in data:
            continue
        val = fn()
        if val is not None:
            out[col] = val
        elif partial and col in data:
            out[col] = None if col in ("nearest_institution", "latitude", "longitude", "established_year") else _reject_blank(col)

    if "contact_phone" in data and (not partial or "contact_phone" in data):
        phone = str(data.get("contact_phone") or "").strip()
        if phone and not re.fullmatch(r"\d{10}", phone):
            raise ValidationError("'contact_phone' must be exactly 10 digits")
        if phone or partial:
            out["contact_phone"] = phone or None

    if not partial:                                   # defaults for NOT NULL columns
        out.setdefault("rating", 0.0)
        out.setdefault("review_count", 0)
        out.setdefault("mess_price", 0)
        out.setdefault("laundry_price", 0)
    return out


def _reject_blank(col):
    raise ValidationError(f"'{col}' cannot be empty")


def validate_rooms(rooms, required):
    """Validate a list of room options. Each: sharing_capacity (1-5), ac_type, monthly_rent, ..."""
    if rooms is None:
        if required:
            raise ValidationError("'rooms' is required: send at least one room option")
        return None
    if not isinstance(rooms, list) or (required and not rooms):
        raise ValidationError("'rooms' must be a non-empty list of room options")
    cleaned, seen = [], set()
    for i, r in enumerate(rooms, start=1):
        if not isinstance(r, dict):
            raise ValidationError(f"rooms[{i}] must be an object")
        try:
            sharing = _number(r, "sharing_capacity", 1, 5, True, integer=True)
            ac = _choice(r, "ac_type", AC_TYPES, True)
            rent = _number(r, "monthly_rent", 1, 1_000_000, True, integer=True)
            deposit = _number(r, "security_deposit", 0, 1_000_000, False, integer=True) or 0
            total = _number(r, "total_rooms", 1, 10_000, True, integer=True)
            avail = _number(r, "rooms_available", 0, 10_000, False, integer=True)
        except ValidationError as e:
            raise ValidationError(f"rooms[{i}]: {e}")
        avail = total if avail is None else avail
        if avail > total:
            raise ValidationError(f"rooms[{i}]: 'rooms_available' cannot be more than 'total_rooms'")
        bath = r.get("attached_bathroom", 0)
        if bath not in (0, 1, True, False):
            raise ValidationError(f"rooms[{i}]: 'attached_bathroom' must be 0 or 1")
        if (sharing, ac) in seen:
            raise ValidationError(f"rooms[{i}]: duplicate option ({sharing} sharing, {ac})")
        seen.add((sharing, ac))
        cleaned.append(dict(sharing_capacity=sharing, ac_type=ac, attached_bathroom=int(bool(bath)),
                            monthly_rent=rent, security_deposit=deposit, total_rooms=total, rooms_available=avail))
    return cleaned


def validate_amenity_names(names):
    if names is None:
        return None
    if not isinstance(names, list) or not all(isinstance(n, str) for n in names):
        raise ValidationError("'amenities' must be a list of amenity names")
    return list(dict.fromkeys(n.strip() for n in names if n.strip()))
