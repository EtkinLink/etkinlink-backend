import os
from flask import request,Flask, jsonify
from flask_cors import CORS
from sqlalchemy import create_engine, text

app = Flask(__name__)
CORS(app)

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)

@app.get("/health")
def health():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"ok": True}
    except Exception as e:

        return {"ok": False, "error": str(e)}, 503
    

@app.get("/users")
def users():
    try:
        user_id = request.args.get("id")

        with engine.connect() as conn:
            if user_id:
                user_result = conn.execute(
                    text("SELECT * FROM users WHERE id = :id"),
                    {"id": user_id}
                ).fetchone()

                if not user_result:
                    return {"error": "User not found"}, 404

                user = dict(user_result._mapping)
                user.pop("password_hash", None)
                user.pop("photo_url", None)

                total_events = conn.execute(text("""
                    SELECT COUNT(*)
                    FROM participants
                    WHERE user_id = :id
                """), {"id": user_id}).scalar()

                attended_events = conn.execute(text("""
                    SELECT COUNT(*)
                    FROM participants
                    WHERE user_id = :id AND status = 'ATTENDED'
                """), {"id": user_id}).scalar()

                if total_events == 0:
                    attendance_rate = "No participation yet"
                else:
                    attendance_rate = f"{round((attended_events / total_events) * 100, 2)}%"

                user["attendance_rate"] = attendance_rate

                return jsonify(user)

            result = conn.execute(text("SELECT id, name, username, email FROM users"))
            users_list = [dict(r._mapping) for r in result]
            return jsonify(users_list)

    except Exception as e:
        return {"error": str(e)}, 503



@app.get("/universities")
def universities():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM universities"))
            rows = [dict(r._mapping) for r in result]
        return jsonify(rows)
    except Exception as e:
        return {"error": str(e)}, 503





@app.get("/event_types")
def event_types():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM event_types"))
            rows = [dict(r._mapping) for r in result]
        return jsonify(rows)
    except Exception as e:
        return {"error": str(e)}, 503


@app.get("/events")
def events():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM events"))
            rows = [dict(r._mapping) for r in result]
        return jsonify(rows)
    except Exception as e:
        return {"error": str(e)}, 503


@app.get("/applications")
def applications():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM applications"))
            rows = [dict(r._mapping) for r in result]
        return jsonify(rows)
    except Exception as e:
        return {"error": str(e)}, 503


@app.get("/participants")
def participants():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM participants"))
            rows = [dict(r._mapping) for r in result]
        return jsonify(rows)
    except Exception as e:
        return {"error": str(e)}, 503


@app.get("/ratings")
def ratings():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM ratings"))
            rows = [dict(r._mapping) for r in result]
        return jsonify(rows)
    except Exception as e:
        return {"error": str(e)}, 503


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
