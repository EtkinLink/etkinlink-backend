from flask import request
from sqlalchemy import text
import math


def get_pagination_params():
    """
    Request'ten pagination parametrelerini alır ve validate eder.
    
    Returns:
        dict: {
            'page': int,
            'per_page': int,
            'offset': int
        }
    """
    # Page parametresi
    try:
        page = int(request.args.get('page', 1))
        if page < 1:
            page = 1
    except (ValueError, TypeError):
        page = 1
    
    # Per page parametresi (limit olarak da gelebilir)
    try:
        per_page = int(request.args.get('per_page', request.args.get('limit', 20)))
        if per_page < 1:
            per_page = 20
        elif per_page > 100:  # Maksimum limit
            per_page = 100
    except (ValueError, TypeError):
        per_page = 20
    
    # Offset hesapla
    offset = (page - 1) * per_page
    
    return {
        'page': page,
        'per_page': per_page,
        'offset': offset
    }


def create_pagination_response(data, total_count, page, per_page):
    """
    Pagination metadata ile birlikte response oluşturur.
    
    Args:
        data: Sayfalanmış veri listesi
        total_count: Toplam kayıt sayısı
        page: Mevcut sayfa
        per_page: Sayfa başına kayıt sayısı
    
    Returns:
        dict: Pagination metadata ile birlikte response
    """
    total_pages = math.ceil(total_count / per_page) if per_page > 0 else 0
    
    return {
        'data': data,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total_count,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1,
            'next_page': page + 1 if page < total_pages else None,
            'prev_page': page - 1 if page > 1 else None
        }
    }


def paginate_query(conn, base_query, count_query, params=None, pagination_params=None):
    """
    SQL query'sine pagination uygular ve sonuçları döndürür.
    
    Args:
        conn: Database connection
        base_query: Ana SELECT query (ORDER BY ile)
        count_query: COUNT query (toplam kayıt sayısı için)
        params: Query parametreleri
        pagination_params: Pagination parametreleri (None ise request'ten alır)
    
    Returns:
        tuple: (data_list, pagination_metadata)
    """
    if params is None:
        params = {}
    
    if pagination_params is None:
        pagination_params = get_pagination_params()
    
    page = pagination_params['page']
    per_page = pagination_params['per_page']
    offset = pagination_params['offset']
    
    # Toplam kayıt sayısını al
    total_count = conn.execute(text(count_query), params).scalar()
    
    # Ana query'ye LIMIT ve OFFSET ekle
    paginated_query = f"{base_query} LIMIT :limit OFFSET :offset"
    params.update({
        'limit': per_page,
        'offset': offset
    })
    
    # Veriyi al
    result = conn.execute(text(paginated_query), params)
    data = [dict(r._mapping) for r in result]
    
    # Response oluştur
    return create_pagination_response(data, total_count, page, per_page)


def apply_pagination_to_query(base_query, pagination_params=None):
    """
    Sadece query string'ine LIMIT ve OFFSET ekler.
    
    Args:
        base_query: Ana SQL query
        pagination_params: Pagination parametreleri
    
    Returns:
        tuple: (paginated_query, updated_params)
    """
    if pagination_params is None:
        pagination_params = get_pagination_params()
    
    paginated_query = f"{base_query} LIMIT :limit OFFSET :offset"
    
    pagination_sql_params = {
        'limit': pagination_params['per_page'],
        'offset': pagination_params['offset']
    }
    
    return paginated_query, pagination_sql_params
