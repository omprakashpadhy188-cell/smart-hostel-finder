"""Admin CRUD endpoints (create / update / delete hostels).
Every admin route needs the header   X-Admin-Key: <your key>
Set your own key with the ADMIN_KEY environment variable, or change the default below."""
import hmac
import os
from functools import wraps
from flask import Blueprint, jsonify, request
import db
from validators import ValidationError, validate_hostel, validate_rooms, validate_amenity_names

ADMIN_KEY = os.getenv("ADMIN_KEY", "admin123")      # <-- change this before sharing the project
admin_bp = Blueprint("admin", __name__)


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        sent = request.headers.get("X-Admin-Key", "")
        if not hmac.compare_digest(sent.encode(), ADMIN_KEY.encode()):
            return jsonify(error="Admin key missing or wrong. Send the header X-Admin-Key."), 401
        return fn(*args, **kwargs)
    return wrapper


def _body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError("Send a JSON body")
    return data


def _amenity_ids(cur, names):
    cur.execute("SELECT amenity_id, amenity_name FROM amenities")
    rows = cur.fetchall()
    known = {r["amenity_name"].lower(): r["amenity_id"] for r in rows}
    unknown = [n for n in names if n.lower() not in known]
    if unknown:
        raise ValidationError(f"Unknown amenities: {unknown}. Valid names: {sorted(r['amenity_name'] for r in rows)}")
    return [known[n.lower()] for n in names]


def _save_rooms(cur, hostel_id, rooms):
    cur.execute("DELETE FROM room_options WHERE hostel_id = %s", (hostel_id,))
    for r in rooms:
        cur.execute(
            "INSERT INTO room_options (hostel_id, sharing_capacity, ac_type, attached_bathroom, monthly_rent, "
            "security_deposit, total_rooms, rooms_available) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            (hostel_id, r["sharing_capacity"], r["ac_type"], r["attached_bathroom"], r["monthly_rent"],
             r["security_deposit"], r["total_rooms"], r["rooms_available"]))


def _save_amenities(cur, hostel_id, amenity_ids):
    cur.execute("DELETE FROM hostel_amenities WHERE hostel_id = %s", (hostel_id,))
    for aid in amenity_ids:
        cur.execute("INSERT INTO hostel_amenities (hostel_id, amenity_id) VALUES (%s, %s)", (hostel_id, aid))


@admin_bp.errorhandler(ValidationError)
def handle_validation(e):
    return jsonify(error=str(e)), 400


@admin_bp.get("/api/amenities")
def list_amenities():
    """Public helper: the valid amenity names (useful for the admin form)."""
    return jsonify(amenities=[r["amenity_name"] for r in db.query("SELECT amenity_name FROM amenities ORDER BY amenity_id")])


@admin_bp.post("/api/admin/hostels")
@admin_required
def create_hostel():
    data = _body()
    hostel = validate_hostel(data, partial=False)
    rooms = validate_rooms(data.get("rooms"), required=True)
    names = validate_amenity_names(data.get("amenities")) or []

    conn = db.get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        amenity_ids = _amenity_ids(cur, names)
        cols = list(hostel)                          # column names come from our whitelist, never from the client
        cur.execute(f"INSERT INTO hostels ({', '.join(cols)}) VALUES ({', '.join(['%s'] * len(cols))})",
                    [hostel[c] for c in cols])
        hostel_id = cur.lastrowid
        _save_rooms(cur, hostel_id, rooms)
        _save_amenities(cur, hostel_id, amenity_ids)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return jsonify(message="Hostel created", hostel_id=hostel_id), 201


@admin_bp.put("/api/admin/hostels/<int:hostel_id>")
@admin_required
def update_hostel(hostel_id):
    """Send only the fields you want to change. If you send 'rooms' or 'amenities',
    the old list is replaced completely by the new one."""
    data = _body()
    hostel = validate_hostel(data, partial=True)
    rooms = validate_rooms(data["rooms"], required=True) if "rooms" in data else None
    names = validate_amenity_names(data["amenities"]) if "amenities" in data else None
    if not hostel and rooms is None and names is None:
        raise ValidationError("Nothing to update. Send at least one hostel field, 'rooms' or 'amenities'.")

    conn = db.get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT hostel_id FROM hostels WHERE hostel_id = %s", (hostel_id,))
        if not cur.fetchall():
            return jsonify(error=f"Hostel {hostel_id} not found"), 404
        amenity_ids = _amenity_ids(cur, names) if names is not None else None
        if hostel:
            cols = list(hostel)
            cur.execute(f"UPDATE hostels SET {', '.join(c + ' = %s' for c in cols)} WHERE hostel_id = %s",
                        [hostel[c] for c in cols] + [hostel_id])
        if rooms is not None:
            _save_rooms(cur, hostel_id, rooms)
        if amenity_ids is not None:
            _save_amenities(cur, hostel_id, amenity_ids)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return jsonify(message="Hostel updated", hostel_id=hostel_id)


@admin_bp.delete("/api/admin/hostels/<int:hostel_id>")
@admin_required
def delete_hostel(hostel_id):
    conn = db.get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("DELETE FROM hostels WHERE hostel_id = %s", (hostel_id,))   # rooms + amenity links cascade
        deleted = cur.rowcount
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    if not deleted:
        return jsonify(error=f"Hostel {hostel_id} not found"), 404
    return jsonify(message="Hostel deleted", hostel_id=hostel_id)
