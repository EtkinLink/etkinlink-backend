import os
from flask import Flask, jsonify
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
        with engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM users"))
            rows = [dict(r._mapping) for r in result]
        return jsonify(rows)
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
