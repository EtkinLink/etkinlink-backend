


from flask import Blueprint, request, jsonify, current_app
from sqlalchemy import text
from backend.utils.auth_utils import verify_jwt, check_event_ownership, check_organization_permission, AuthError
from backend.utils.pagination import paginate_query
from datetime import datetime
import uuid

events_bp = Blueprint('events', __name__, url_prefix='/events')

# Register directly for an event without application
@events_bp.post("/<int:event_id>/register")
def register_for_event(event_id):
    """
    Allows an authenticated user to register directly for an event
    that does not require an application.
    - Sadece status = FUTURE olan
    - ve allow_direct_registration = 1 olan event'ler için çalışır.
    """
    try:
        user_id = verify_jwt()

        with current_app.engine.connect() as conn:
            # allow_direct_registration'ı da çek
            event = conn.execute(
                text("""
                    SELECT id, status, user_limit, has_register
                    FROM events
                    WHERE id = :eid
                """),
                {"eid": event_id}
            ).fetchone()
            
            if not event:
                return {"error": "Event not found"}, 404
            
            # Event aktif mi?
            if event.status != 'FUTURE':
                return {
                    "error": "This event is not active or has already been completed"
                }, 400

            # Bu event direct register'a izin veriyor mu?
            if event.has_register:
                return {
                    "error": "This event does not allow direct registration. Please apply instead."
                }, 400

            # Zaten katılımcı mı?
            is_participant = conn.execute(
                text("""
                    SELECT id 
                    FROM participants 
                    WHERE event_id = :eid AND user_id = :uid
                """),
                {"eid": event_id, "uid": user_id}
            ).fetchone()
            
            if is_participant:
                return {"error": "You are already registered for this event"}, 409
            
            # Daha önce application yapmış mı?
            has_application = conn.execute(
                text("""
                    SELECT id 
                    FROM applications 
                    WHERE event_id = :eid AND user_id = :uid
                """),
                {"eid": event_id, "uid": user_id}
            ).fetchone()

            if has_application:
                 return {
                     "error": "You have a pending or processed application for this event. Cannot register directly."
                 }, 409

            # Kayıt kısmı transaction içinde
            with conn.begin() as trans:
                user_limit = event.user_limit
                
                if user_limit is not None:
                    current_participant_count = conn.execute(
                        text("SELECT COUNT(*) FROM participants WHERE event_id = :eid"),
                        {"eid": event_id}
                    ).scalar()
                    
                    if current_participant_count >= user_limit:
                        # trans.rollback() demene gerek yok aslında,
                        # context manager exception olmadığı için commit etmeyecek
                        return {
                            "error": "Event user limit reached. Cannot register."
                        }, 409

                ticket_code = str(uuid.uuid4())
                
                conn.execute(
                    text("""
                        INSERT INTO participants (event_id, user_id, application_id, status, ticket_code)
                        VALUES (:eid, :uid, NULL, 'NO_SHOW', :ticket)
                    """),
                    {
                        "eid": event_id,
                        "uid": user_id,
                        "ticket": ticket_code
                    }
                )

        return {"message": "Registration successful", "ticket_code": ticket_code}, 201

    except AuthError as e:
        return {"error": e.args[0]}, e.code
    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}, 503

# Apply to an event with application
@events_bp.post("/<int:event_id>/apply")
def apply_to_event(event_id):
    """
    Allows an authenticated user to apply for an event.
    """
    try:
        user_id = verify_jwt()

        data = request.get_json(silent=True)
        why_me_text = data.get("why_me") if data else None

        with current_app.engine.connect() as conn:
            
            # Güncellenen kısım: Etkinliğin durumunu (status) kontrol et
            event = conn.execute(
                text("SELECT id, status FROM events WHERE id = :eid"),
                {"eid": event_id}
            ).fetchone()
            
            if not event:
                return {"error": "Event not found"}, 404
            
            if event.status != 'FUTURE':
                return {"error": "This event is not active or has already been completed"}, 400

            # Mevcut katılımcı kontrolü
            is_participant = conn.execute(
                text("SELECT id FROM participants WHERE event_id = :eid AND user_id = :uid"),
                {"eid": event_id, "uid": user_id}
            ).fetchone()
            
            if is_participant:
                return {"error": "You are already a participant in this event"}, 409

            try:
                conn.execute(
                    text("""
                        INSERT INTO applications (event_id, user_id, why_me, status)
                        VALUES (:eid, :uid, :why_me, 'PENDING')
                    """),
                    {
                        "eid": event_id,
                        "uid": user_id,
                        "why_me": why_me_text
                    }
                )
                conn.commit()
            
            except Exception as db_error:
                conn.rollback()
                error_str = str(db_error).lower()
                if "duplicate entry" in error_str or "unique constraint failed" in error_str:
                    return {"error": "You have already applied to this event"}, 409
                
                raise db_error

        return {"message": "Application submitted successfully"}, 201

    except AuthError as e:
        return {"error": e.args[0]}, e.code
    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}, 503


@events_bp.delete("/<int:event_id>/participants/<int:target_user_id>")
def manage_event_participation(event_id, target_user_id):
    """
    Allows:
    - Participants to leave an event.
    - Applicants to withdraw their application.
    - Event owners (or org admins) to remove participants.
    """
    try:
        user_id = verify_jwt()

        with current_app.engine.connect() as conn:
            
            participant = conn.execute(text("""
                SELECT id, status FROM participants
                WHERE event_id = :eid AND user_id = :uid
            """), {"eid": event_id, "uid": target_user_id}).fetchone()

            application = conn.execute(text("""
                SELECT id, status FROM applications
                WHERE event_id = :eid AND user_id = :uid
            """), {"eid": event_id, "uid": target_user_id}).fetchone()

            
            if not participant and not application:
                return {"error": "User is neither a participant nor an applicant for this event."}, 404

            
            if user_id == target_user_id:
                if participant:
                    conn.execute(text("""
                        DELETE FROM participants
                        WHERE event_id = :eid AND user_id = :uid
                    """), {"eid": event_id, "uid": target_user_id})
                    conn.commit()
                    return {"message": "You have successfully left the event."}, 200

                if application and application.status == "PENDING":
                    conn.execute(text("""
                        DELETE FROM applications
                        WHERE event_id = :eid AND user_id = :uid
                    """), {"eid": event_id, "uid": target_user_id})
                    conn.commit()
                    return {"message": "Application withdrawn successfully."}, 200

                return {"error": "You cannot withdraw after being accepted or rejected."}, 403

            
            else:
                try:
                    check_event_ownership(conn, event_id, user_id)
                except AuthError as auth_err:
                    return {"error": auth_err.args[0]}, auth_err.code

                if participant:
                    conn.execute(text("""
                        DELETE FROM participants
                        WHERE event_id = :eid AND user_id = :uid
                    """), {"eid": event_id, "uid": target_user_id})
                    conn.commit()
                    return {"message": "Participant removed successfully."}, 200

                if application:
                    conn.execute(text("""
                        DELETE FROM applications
                        WHERE event_id = :eid AND user_id = :uid
                    """), {"eid": event_id, "uid": target_user_id})
                    conn.commit()
                    return {"message": "Application deleted successfully."}, 200

        return {"error": "No action performed."}, 400

    except AuthError as e:
        return {"error": e.args[0]}, e.code
    except Exception as e:
        return {"error": f"Internal error: {str(e)}"}, 503


@events_bp.get("/<int:event_id>/applications")
def get_event_applications(event_id):
    """
    Lists all applications for a specific event.
    Only the event owner (user or org admin/rep) can access this.
    Supports pagination with ?page=1&per_page=20 parameters.
    """
    try:
        user_id = verify_jwt()

        with current_app.engine.connect() as conn:
            
            try:
                check_event_ownership(conn, event_id, user_id)
            except AuthError as auth_err:
                return {"error": auth_err.args[0]}, auth_err.code

            base_query = """
                SELECT 
                    a.id AS application_id,
                    a.user_id,
                    u.username,
                    u.name AS user_name,
                    a.why_me,
                    a.status
                FROM applications a
                JOIN users u ON a.user_id = u.id
                WHERE a.event_id = :eid
                ORDER BY a.status ASC, a.id DESC
            """
            
            count_query = """
                SELECT COUNT(*) 
                FROM applications a
                WHERE a.event_id = :eid
            """
            
            params = {"eid": event_id}
            result = paginate_query(conn, base_query, count_query, params)
            return jsonify(result)

    except AuthError as e:
        return {"error": e.args[0]}, e.code
    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}, 503


@events_bp.post("/<int:event_id>/ratings")
def rate_event(event_id):
    """
    Kullanıcı bir etkinliği 1-5 arası puanlar, opsiyonel yorum bırakır.
    - Sadece etkinliğe KATILMIŞ (ATTENDED) kullanıcı puan verebilir.
    - Daha önce rating varsa UPDATE, yoksa INSERT yapılır.
    """
    try:
        user_id = verify_jwt()

        data = request.get_json(silent=True) or {}
        rating = data.get("rating")
        comment = data.get("comment", "")

        # Rating doğrulama
        if rating is None:
            return {"error": "rating field is required"}, 400

        try:
            rating = int(rating)
        except (TypeError, ValueError):
            return {"error": "rating must be an integer between 1 and 5"}, 400

        if rating < 1 or rating > 5:
            return {"error": "rating must be between 1 and 5"}, 400

        with current_app.engine.connect() as conn:
            # 1) Kullanıcı bu etkinliğin katılımcısı mı ve ATTENDED mı?
            participant = conn.execute(
                text("""
                    SELECT status 
                    FROM participants
                    WHERE event_id = :eid AND user_id = :uid
                """),
                {"eid": event_id, "uid": user_id}
            ).fetchone()

            if not participant:
                return {"error": "You can only rate events you participated in."}, 403

            if participant.status != "ATTENDED":
                return {"error": "You can only rate events you have attended."}, 403

            # 2) Daha önce rating var mı?
            existing = conn.execute(
                text("""
                    SELECT id 
                    FROM ratings
                    WHERE event_id = :eid AND user_id = :uid
                """),
                {"eid": event_id, "uid": user_id}
            ).fetchone()

            if existing:
                # UPDATE
                conn.execute(
                    text("""
                        UPDATE ratings
                        SET rating = :rating,
                            comment = :comment
                        WHERE event_id = :eid AND user_id = :uid
                    """),
                    {
                        "rating": rating,
                        "comment": comment,
                        "eid": event_id,
                        "uid": user_id
                    }
                )
                conn.commit()
                return {
                    "message": "Rating updated successfully",
                    "rating": rating,
                    "comment": comment
                }, 200
            else:
                # INSERT
                conn.execute(
                    text("""
                        INSERT INTO ratings (event_id, user_id, rating, comment)
                        VALUES (:eid, :uid, :rating, :comment)
                    """),
                    {
                        "eid": event_id,
                        "uid": user_id,
                        "rating": rating,
                        "comment": comment
                    }
                )
                conn.commit()
                return {
                    "message": "Rating created successfully",
                    "rating": rating,
                    "comment": comment
                }, 201

    except AuthError as e:
        return {"error": e.args[0]}, e.code
    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}, 503


@events_bp.get("/<int:event_id>/ratings")
def get_event_ratings(event_id):
    """
    Belirli bir etkinlik için:
      - ortalama puan
      - toplam rating sayısı
      - rating listesi (kullanıcı + yorumlar)
    döndürür.

    Auth ZORUNLU (verify_jwt).
    """
    try:
        # Sadece login kullanıcılar görebilsin diye
        user_id = verify_jwt()  # şu an sadece doğrulama için, kullanmak zorunda değiliz

        with current_app.engine.connect() as conn:
            # Event var mı kontrol et
            event = conn.execute(
                text("SELECT id FROM events WHERE id = :eid"),
                {"eid": event_id}
            ).fetchone()

            if not event:
                return {"error": "Event not found"}, 404

            # Ortalama ve toplam rating
            agg_row = conn.execute(
                text("""
                    SELECT 
                        AVG(rating) AS avg_rating,
                        COUNT(*) AS rating_count
                    FROM ratings
                    WHERE event_id = :eid
                """),
                {"eid": event_id}
            ).fetchone()

            avg_rating = agg_row.avg_rating
            rating_count = agg_row.rating_count

            avg_rating = float(avg_rating) if avg_rating is not None else None
            rating_count = int(rating_count) if rating_count is not None else 0

            # Bütün rating kayıtları (username ile birlikte)
            ratings_rows = conn.execute(
                text("""
                    SELECT 
                        r.id,
                        u.username,
                        r.rating,
                        r.comment
                    FROM ratings r
                    JOIN users u ON u.id = r.user_id
                    WHERE r.event_id = :eid
                    ORDER BY r.id ASC
                """),
                {"eid": event_id}
            ).fetchall()

        ratings = [dict(row._mapping) for row in ratings_rows]

        return jsonify({
            "event_id": event_id,
            "average_rating": avg_rating,
            "rating_count": rating_count,
            "ratings": ratings
        })

    except AuthError as e:
        return {"error": e.args[0]}, e.code
    except Exception as e:
        return {"error": str(e)}, 503



@events_bp.post("/")
def create_event():
    """
    Create a new event (owned by a user or an organization).
    Requires a valid JWT token.
    """
    try:
        user_id = verify_jwt()

        data = request.get_json()
        required_fields = ["title", "explanation", "type_id", "starts_at", "ends_at", "owner_type","has_register"]
        missing = [f for f in required_fields if f not in data]
        if missing:
            return {"error": f"Missing required fields: {', '.join(missing)}"}, 400

        owner_type = data.get("owner_type", "USER").upper()
        org_id = data.get("organization_id") if owner_type == "ORGANIZATION" else None
        
        # get privacy settings -> default False/Public
        is_participants_private = data.get("is_participants_private", False)

        # If organization, check if user is admin/member of it
        if owner_type == "ORGANIZATION":
            with current_app.engine.connect() as conn:
                check_organization_permission(conn, org_id, user_id, ["ADMIN", "REPRESENTATIVE"])

        with current_app.engine.connect() as conn:
            query = text("""
                INSERT INTO events (
                    owner_user_id, owner_type, owner_organization_id,
                    title, explanation, type_id, price, has_register,
                    starts_at, ends_at, location_name, photo_url,
                    status, user_limit, latitude, longitude, 
                    is_participants_private, -- YENİ SÜTUN
                    created_at, updated_at
                )
                VALUES (
                    :owner_user_id, :owner_type, :owner_organization_id,
                    :title, :explanation, :type_id, :price, :has_register,
                    :starts_at, :ends_at, :location_name, :photo_url,
                    'FUTURE', :user_limit, :latitude, :longitude, 
                    :is_participants_private, -- YENİ DEĞER
                    NOW(), NOW()
                )
            """)

            conn.execute(query, {
                "owner_user_id": user_id,
                "owner_type": owner_type,
                "owner_organization_id": org_id,
                "title": data.get("title"),
                "explanation": data.get("explanation"),
                "type_id": data.get("type_id"),
                "price": data.get("price", 0),
                "has_register": data.get("has_register"),
                "starts_at": data.get("starts_at"),
                "ends_at": data.get("ends_at"),
                "location_name": data.get("location_name"),
                "photo_url": data.get("photo_url"),
                "user_limit": data.get("user_limit"),
                "latitude": data.get("latitude"),
                "longitude": data.get("longitude"),
                "is_participants_private": is_participants_private 
            })
            conn.commit()

        return {"message": "Event created successfully"}, 201

    except AuthError as e:
        return {"error": e.args[0]}, e.code
    except Exception as e:
        return {"error": str(e)}, 503



@events_bp.post("/<int:event_id>/check-in")
def check_in_participant(event_id):
    """
    Performs check-in for a participant by scanning their ticket_code.
    Only event owners or organization admins/representatives can perform this.
    """
    try:
        admin_user_id = verify_jwt()
        
        data = request.get_json()
        if not data or "ticket_code" not in data:
            return {"error": "ticket_code is required"}, 400
        
        ticket_code = data.get("ticket_code")

        with current_app.engine.connect() as conn:
            
            try:
                check_event_ownership(conn, event_id, admin_user_id)
            except AuthError as auth_err:
                return {"error": auth_err.args[0]}, auth_err.code

            with conn.begin() as trans:
            
                query = text("""
                    SELECT 
                        p.status,
                        u.username,
                        u.name
                    FROM participants p
                    JOIN users u ON p.user_id = u.id
                    WHERE p.ticket_code = :ticket_code AND p.event_id = :event_id
                    FOR UPDATE
                """)
                
                participant = conn.execute(query, {
                    "ticket_code": ticket_code, 
                    "event_id": event_id
                }).fetchone()

                if not participant:
                    return {"error": "Invalid ticket or not for this event"}, 404
                
                if participant.status == 'ATTENDED':
                    return {"error": f"Ticket already used by {participant.username}"}, 409
                
                update_query = text("""
                    UPDATE participants 
                    SET status = 'ATTENDED' 
                    WHERE ticket_code = :ticket_code
                """)
                
                conn.execute(update_query, {"ticket_code": ticket_code})


        return {
            "message": "Check-in successful", 
            "username": participant.username,
            "name": participant.name
        }, 200

    except AuthError as e:
        return {"error": e.args[0]}, e.code
    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}, 503


@events_bp.get("/")
def get_events():
    """
    Returns all events (user or organization owned) with type, owner info, and participant count.
    Supports pagination with ?page=1&per_page=20 parameters.
    """
    try:
        with current_app.engine.connect() as conn:
            base_query = """
                SELECT 
                    e.id,
                    e.title,
                    e.explanation,
                    e.price,
                    e.starts_at,
                    e.ends_at,
                    e.location_name,
                    e.status,
                    e.user_limit,
                    e.latitude,
                    e.longitude,
                    e.created_at,
                    e.updated_at,
                    e.owner_type,
                    u.username AS owner_username,
                    o.name AS owner_organization_name,
                    et.code AS event_type,
                    (
                        SELECT COUNT(*) FROM participants p
                        WHERE p.event_id = e.id
                    ) AS participant_count
                FROM events e
                LEFT JOIN users u ON e.owner_user_id = u.id
                LEFT JOIN organizations o ON e.owner_organization_id = o.id
                LEFT JOIN event_types et ON e.type_id = et.id
                ORDER BY e.starts_at ASC
            """
            
            count_query = """
                SELECT COUNT(*) 
                FROM events e
            """
            
            result = paginate_query(conn, base_query, count_query)
            return jsonify(result)
            
    except Exception as e:
        return {"error": str(e)}, 503


@events_bp.get("/<int:event_id>")
def get_event_by_id(event_id):
    """
    Event detaylarını döndürür.
    Katılımcılar gizliyse owner dışında kimse göremez.
    Eğer status = 'COMPLETED' ise ratingler de döner.
    """
    try:
        user_id = verify_jwt()

        with current_app.engine.connect() as conn:
            event = conn.execute(text("""
                SELECT 
                    e.id,
                    e.title,
                    e.explanation,
                    e.price,
                    e.starts_at,
                    e.ends_at,
                    e.location_name,
                    e.status,
                    e.user_limit,
                    e.latitude,
                    e.longitude,
                    e.created_at,
                    e.updated_at,
                    e.owner_type,
                    e.has_register,
                    e.owner_organization_id,
                    e.owner_user_id,          -- Auth kontrolü için gerekli
                    e.is_participants_private,-- Kontrol bayrağı
                    u.username AS owner_username,
                    o.name AS owner_organization_name,
                    et.code AS event_type
                FROM events e
                LEFT JOIN users u ON e.owner_user_id = u.id
                LEFT JOIN organizations o ON e.owner_organization_id = o.id
                LEFT JOIN event_types et ON e.type_id = et.id
                WHERE e.id = :id
            """), {"id": event_id}).fetchone()

            if not event:
                return {"error": "Event not found"}, 404

            # 👇 Sadece status'e bakıyoruz
            is_finished = (event.status == "COMPLETED")

            # ----- Katılımcı gizliliği -----
            show_participants = True
            
            if event.is_participants_private:
                show_participants = False
                
                if event.owner_type == 'USER' and user_id == event.owner_user_id:
                    show_participants = True
                
                elif event.owner_type == 'ORGANIZATION' and user_id:
                    org_member = conn.execute(text("""
                        SELECT role FROM organization_members 
                        WHERE organization_id = :oid AND user_id = :uid
                    """), {"oid": event.owner_organization_id, "uid": user_id}).fetchone()
                    
                    if org_member and org_member.role in ['ADMIN', 'REPRESENTATIVE']:
                        show_participants = True

            participants = []
            if show_participants:
                participants = conn.execute(text("""
                    SELECT 
                        u.id,
                        u.username,
                        p.status
                    FROM participants p
                    JOIN users u ON u.id = p.user_id
                    WHERE p.event_id = :id
                """), {"id": event_id}).fetchall()

            applications = []
            if show_participants and event.owner_type == "ORGANIZATION" and event.owner_organization_id:
                applications = conn.execute(text("""
                    SELECT 
                        a.id,
                        a.user_id,
                        u.username,
                        a.motivation,
                        a.status,
                        a.created_at
                    FROM organization_applications a
                    JOIN users u ON a.user_id = u.id
                    WHERE a.organization_id = :org_id
                    ORDER BY a.created_at DESC
                """), {"org_id": event.owner_organization_id}).fetchall()

            #  Eğer COMPLETED ise ratingleri çek
            ratings_summary = None
            if is_finished:
                agg_row = conn.execute(text("""
                    SELECT 
                        AVG(rating) AS avg_rating,
                        COUNT(*) AS rating_count
                    FROM ratings
                    WHERE event_id = :eid
                """), {"eid": event_id}).fetchone()

                avg_rating = float(agg_row.avg_rating) if agg_row.avg_rating is not None else None
                rating_count = int(agg_row.rating_count) if agg_row.rating_count else 0

                rating_rows = conn.execute(text("""
                    SELECT 
                        u.username,
                        r.rating,
                        r.comment
                    FROM ratings r
                    JOIN users u ON u.id = r.user_id
                    WHERE r.event_id = :eid
                    ORDER BY r.id ASC
                """), {"eid": event_id}).fetchall()

                ratings_list = [
                    {
                        "username": row.username,
                        "rating": int(row.rating),
                        "comment": row.comment
                    }
                    for row in rating_rows
                ]

                ratings_summary = {
                    "average_rating": avg_rating,
                    "rating_count": rating_count,
                    "ratings": ratings_list
                }

        # ----- Response’u paketle -----
        event_data = dict(event._mapping)
        event_data["is_participants_private"] = bool(event.is_participants_private)

        if not show_participants:
            event_data["participants"] = None
            event_data["applications"] = []
        else:
            event_data["participants"] = [dict(p._mapping) for p in participants]
            event_data["applications"] = [dict(a._mapping) for a in applications]

        # SADECE COMPLETED ise rating var, değilse null
        event_data["ratings"] = ratings_summary if is_finished else None

        return jsonify(event_data)

    except Exception as e:
        return {"error": str(e)}, 503


@events_bp.get("//filter")
def filter_events():
    """
    Filters events by type, date range, university ,organization, search query, status
    and price.
    Works for both user and organization events.
    Supports pagination with ?page=1&per_page=20 parameters.
    """
    try:
        type_code = request.args.get("type")
        from_date = request.args.get("from")
        to_date = request.args.get("to")
        search = request.args.get("q")
        university = request.args.get("university")  # can be name or id
        organization = request.args.get("organization")
        status = request.args.get("status")
        
        min_price = request.args.get("min_price")
        max_price = request.args.get("max_price")

        filters = []
        params = {}

        # --- Existing filters ---
        if type_code:
            filters.append("et.code = :type_code")
            params["type_code"] = type_code

        if from_date:
            filters.append("e.starts_at >= :from_date")
            params["from_date"] = from_date

        if to_date:
            filters.append("e.starts_at <= :to_date")
            params["to_date"] = to_date

        if search:
            # Case-insensitive search across multiple fields including explanation
            filters.append("""(
                LOWER(e.title) LIKE LOWER(:search) OR 
                LOWER(e.explanation) LIKE LOWER(:search) OR 
                LOWER(o.name) LIKE LOWER(:search) OR 
                LOWER(u.username) LIKE LOWER(:search) OR
                LOWER(e.location_name) LIKE LOWER(:search)
            )""")
            params["search"] = f"%{search}%"

        # --- University filter ---
        if university:
            if university.isdigit():
                filters.append("un.id = :university_id")
                params["university_id"] = int(university)
            else:
                filters.append("LOWER(un.name) LIKE LOWER(:university_name)")
                params["university_name"] = f"%{university}%"

        # --- Organization filter ---
        if organization:
            if organization.isdigit():
                filters.append("o.id = :organization_id")
                params["organization_id"] = int(organization)
            else:
                filters.append("LOWER(o.name) LIKE LOWER(:organization_name)")
                params["organization_name"] = f"%{organization}%"

        # --- Status filter ---
        if status:
            filters.append("e.status = :status")
            params["status"] = status

        # --- Price filter ---
        if min_price:
            filters.append("e.price >= :min_price")
            params["min_price"] = float(min_price)
        
        if max_price:
            filters.append("e.price <= :max_price")
            params["max_price"] = float(max_price)

        where_clause = "WHERE " + " AND ".join(filters) if filters else ""

        with current_app.engine.connect() as conn:
            base_query = f"""
                SELECT 
                    e.id,
                    e.title,
                    e.starts_at,
                    e.ends_at,
                    e.location_name,
                    e.price,  
                    e.status,
                    e.created_at,
                    e.owner_type,
                    u.username AS owner_username,
                    o.name AS owner_organization_name,
                    et.code AS event_type,
                    un.name AS university_name
                FROM events e
                LEFT JOIN event_types et ON e.type_id = et.id
                LEFT JOIN users u ON e.owner_user_id = u.id
                LEFT JOIN organizations o ON e.owner_organization_id = o.id
                LEFT JOIN universities un ON u.university_id = un.id
                {where_clause}
                ORDER BY e.starts_at ASC
            """
            
            count_query = f"""
                SELECT COUNT(*) 
                FROM events e
                LEFT JOIN event_types et ON e.type_id = et.id
                LEFT JOIN users u ON e.owner_user_id = u.id
                LEFT JOIN organizations o ON e.owner_organization_id = o.id
                LEFT JOIN universities un ON u.university_id = un.id
                {where_clause}
            """
            
            result = paginate_query(conn, base_query, count_query, params)
            return jsonify(result)

    except ValueError:
        return {"error": "Invalid format for price or ID fields"}, 400
    except Exception as e:
        return {"error": str(e)}, 503



@events_bp.put("/<int:event_id>")
def update_event(event_id):
    """
    Update event details. Only event owner (user or org admin) can update.
    """
    try:
        user_id = verify_jwt()

        data = request.get_json()
        if not data:
            return {"error": "No data provided"}, 400

        with current_app.engine.connect() as conn:
            # Check ownership and permissions
            check_event_ownership(conn, event_id, user_id)

            allowed_fields = {
                "title", "explanation", "price", "starts_at", "ends_at",
                "location_name", "photo_url", "status", "user_limit",
                "latitude", "longitude", "type_id","has_register",
                "is_participants_private" 
            }
            updates = {k: v for k, v in data.items() if k in allowed_fields}

            if not updates:
                return {"error": "No valid fields to update"}, 400

            set_clause = ", ".join([f"{k} = :{k}" for k in updates])
            updates["id"] = event_id

            conn.execute(text(f"""
                UPDATE events
                SET {set_clause}, updated_at = NOW()
                WHERE id = :id
            """), updates)
            conn.commit()

        return {"message": "Event updated successfully"}

    except AuthError as e:
        return {"error": e.args[0]}, e.code
    except Exception as e:
        return {"error": str(e)}, 503


@events_bp.delete("/<int:event_id>")
def delete_event(event_id):
    """
    Delete an event. Only the event owner (or org admin) can delete it.
    """
    try:
        user_id = verify_jwt()

        with current_app.engine.connect() as conn:
            # Check ownership and permissions
            check_event_ownership(conn, event_id, user_id)

            conn.execute(text("DELETE FROM events WHERE id = :id"), {"id": event_id})
            conn.commit()

        return {"message": "Event deleted successfully"}

    except AuthError as e:
        return {"error": e.args[0]}, e.code
    except Exception as e:
        return {"error": str(e)}, 503


@events_bp.post("/<int:event_id>/report")
def report_event(event_id):
    """
    Report an event for inappropriate content.
    Body: {"reason": "This event contains spam"}
    """
    try:
        user_id = verify_jwt()
        data = request.get_json()
        reason = data.get("reason", "").strip()
        
        if not reason:
            return {"error": "Reason is required"}, 400
        
        if len(reason) < 10:
            return {"error": "Reason must be at least 10 characters"}, 400
        
        with current_app.engine.connect() as conn:
            # Check if event exists
            event = conn.execute(
                text("SELECT id FROM events WHERE id = :id"),
                {"id": event_id}
            ).fetchone()
            
            if not event:
                return {"error": "Event not found"}, 404
            
            # Check if user already reported this event
            existing = conn.execute(
                text("""
                    SELECT id FROM reports 
                    WHERE event_id = :eid AND reporter_user_id = :uid
                """),
                {"eid": event_id, "uid": user_id}
            ).fetchone()
            
            if existing:
                return {"error": "You have already reported this event"}, 409
            
            # Create report
            conn.execute(
                text("""
                    INSERT INTO reports (event_id, reporter_user_id, reason, status, created_at)
                    VALUES (:eid, :uid, :reason, 'PENDING', NOW())
                """),
                {"eid": event_id, "uid": user_id, "reason": reason}
            )
            conn.commit()
        
        return {"message": "Report submitted successfully"}, 201
    
    except AuthError as e:
        return {"error": e.args[0]}, e.code
    except Exception as e:
        return {"error": str(e)}, 503


@events_bp.get("/my-reports")
def get_my_reports():
    """
    Get current user's reports.
    Query params: ?page=1&per_page=20
    """
    try:
        user_id = verify_jwt()
        
        with current_app.engine.connect() as conn:
            base_query = """
                SELECT 
                    r.id,
                    r.event_id,
                    e.title as event_title,
                    r.reason,
                    r.status,
                    r.admin_notes,
                    r.created_at,
                    r.updated_at
                FROM reports r
                JOIN events e ON r.event_id = e.id
                WHERE r.reporter_user_id = :uid
                ORDER BY r.created_at DESC
            """
            
            count_query = """
                SELECT COUNT(*) 
                FROM reports 
                WHERE reporter_user_id = :uid
            """
            
            params = {"uid": user_id}
            result = paginate_query(conn, base_query, count_query, params)
            return jsonify(result)
    
    except AuthError as e:
        return {"error": e.args[0]}, e.code
    except Exception as e:
        return {"error": str(e)}, 503

