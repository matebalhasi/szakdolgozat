"""HTTP végpontok; az SQL a ProductionRequest modulban található."""
from datetime import date
from flask import Blueprint, current_app, jsonify, request
from mysql.connector import Error
import ProductionRequest as queries

production = Blueprint('production', __name__)
MAX_INT = 2147483647

def connect():
    # A meglévő backend kapcsolatkezelőjét használja, körkörös import nélkül.
    return current_app.config['DB_CONNECT']()

def validate(data):
    if not isinstance(data, dict):
        raise ValueError('JSON objektumot kell küldeni.')
    try:
        deadline = date.fromisoformat(data.get('due_date', ''))
    except (TypeError, ValueError):
        raise ValueError('Érvényes határidőt adj meg (ÉÉÉÉ-HH-NN).')
    if deadline < date.today():
        raise ValueError('A határidő nem lehet múltbeli.')
    priority = data.get('priority', 0)
    if type(priority) is not int or priority not in (0, 1, 2, 3):
        raise ValueError('A prioritás 0 és 3 közötti egész szám legyen.')
    items = data.get('items')
    if not isinstance(items, list) or not 1 <= len(items) <= 1000:
        raise ValueError('Legalább egy, legfeljebb 1000 terméket válassz.')
    seen = set()
    for item in items:
        if not isinstance(item, dict):
            raise ValueError('Hibás terméksor.')
        pid, quantity = item.get('product_id'), item.get('quantity')
        if type(pid) is not int or not 1 <= pid <= MAX_INT:
            raise ValueError('Hibás termékazonosító.')
        if pid in seen:
            raise ValueError('Egy termék csak egyszer szerepelhet.')
        if type(quantity) is not int or not 1 <= quantity <= MAX_INT:
            raise ValueError('A mennyiség pozitív egész szám legyen (maximum 2147483647).')
        seen.add(pid)
    return deadline, priority, items

@production.get('/products')
def products():
    connection = connect()
    if connection is None:
        return jsonify(message='Az adatbázis nem elérhető.'), 503
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(queries.get_products_query())
        return jsonify(data=cursor.fetchall()), 200
    except Error:
        current_app.logger.exception('Terméklista lekérése sikertelen')
        return jsonify(message='A terméklista nem tölthető be.'), 500
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()

@production.post('/production-orders')
def create_order():
    try:
        deadline, priority, items = validate(request.get_json(silent=True))
    except ValueError as exc:
        return jsonify(message=str(exc)), 400
    connection = connect()
    if connection is None:
        return jsonify(message='Az adatbázis nem elérhető.'), 503
    cursor = None
    try:
        connection.start_transaction()
        cursor = connection.cursor()
        cursor.execute(queries.get_lock_products_query())
        existing = {row[0] for row in cursor.fetchall()}
        if any(item['product_id'] not in existing for item in items):
            connection.rollback()
            return jsonify(message='A kiválasztott termékek egyike már nem létezik. Frissítsd a listát.'), 400
        cursor.execute(queries.get_insert_order_query(), (deadline, priority))
        order_id = cursor.lastrowid
        cursor.executemany(queries.get_insert_order_product_query(),
                           [(order_id, i['product_id'], i['quantity']) for i in items])
        cursor.executemany(queries.get_insert_plan_query(),
                           [(order_id, i['product_id'], deadline) for i in items])
        connection.commit()
        return jsonify(message='A rendelés és a gyártási terv mentve.', order_id=order_id), 201
    except Error:
        connection.rollback()
        current_app.logger.exception('Rendelés mentése sikertelen')
        return jsonify(message='A mentés sikertelen; a rendelés nem került rögzítésre.'), 500
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()
