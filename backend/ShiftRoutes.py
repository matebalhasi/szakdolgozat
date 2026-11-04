"""Műszakvezető API. Beillesztés: app.register_blueprint(shift)."""
from datetime import datetime, timezone, timedelta
from flask import Blueprint, current_app, jsonify, request
from mysql.connector import Error, IntegrityError
import ShiftRequest as queries

shift = Blueprint('shift', __name__, url_prefix='/shift')


def serialize(rows):
    result = []
    for row in rows:
        item = {}
        for key, value in row.items():
            if isinstance(value, datetime):
                # A route-ok UTC-re állított DB-kapcsolatot használnak.
                value = value.replace(tzinfo=timezone.utc).isoformat()
            elif hasattr(value, 'isoformat'):
                value = value.isoformat()
            item[key] = value
        result.append(item)
    return result


def latest_assignments(rows, group_key='operator_id', counterpart_key='machine_id'):
    """Ismert időpontú és egyértelmű legutóbbi események."""
    grouped = {}
    for row in rows:
        if row.get('assigned_at') is not None:
            grouped.setdefault(row[group_key], []).append(row)
    latest = {}
    for oid, events in grouped.items():
        last_time = max(r['assigned_at'] for r in events)
        candidates = [r for r in events if r['assigned_at'] == last_time]
        if len({r[counterpart_key] for r in candidates}) == 1:
            latest[oid] = max(candidates, key=lambda r: r['assignment_id'])
    return latest


def current_assignments(rows):
    by_operator = latest_assignments(rows)
    by_machine = latest_assignments(rows, 'machine_id', 'operator_id')
    operator_events = {row['assignment_id'] for row in by_operator.values()}
    # A korábbi esemény sosem válik ismét aktuálissá, ha valaki távozik.
    return {mid: row for mid, row in by_machine.items() if row['assignment_id'] in operator_events}


def marked_assignments(rows):
    current = {row['assignment_id'] for row in current_assignments(rows).values()}
    return serialize([dict(row, is_current=row['assignment_id'] in current) for row in rows])


def validate_assignment(data):
    if not isinstance(data, dict):
        raise ValueError('JSON objektumot kell küldeni.')
    machine_id, ids = data.get('machine_id'), data.get('operator_ids')
    if type(machine_id) is not int or not 1 <= machine_id <= 2147483647:
        raise ValueError('Érvényes gépet válassz.')
    if not isinstance(ids, list) or len(ids) > 1:
        raise ValueError('Egy géphez legfeljebb egy operátort válassz.')
    if any(type(i) is not int or not 1 <= i <= 2147483647 for i in ids):
        raise ValueError('Hibás operátorazonosító.')
    return machine_id, ids


def connection_or_none():
    return current_app.config['DB_CONNECT']()


def db_error(exc):
    if getattr(exc, 'errno', None) == 1054 and 'assigned_at' in str(exc):
        return jsonify(message='Hiányzik az assigned_at mező. Futtasd a mellékelt SQL migrációt.'), 503
    if getattr(exc, 'errno', None) == 1054 and 'assignment_id' in str(exc):
        return jsonify(message='Futtasd a 002_assignment_history.sql migrációt az előzményes beosztásokhoz.'), 503
    current_app.logger.exception('Műszakvezető adatbázishiba')
    return jsonify(message='Adatbázishiba történt. Frissítsd a listát és ellenőrizd az eredményt.'), 500


@shift.get('/forms')
def forms():
    connection = connection_or_none()
    if connection is None:
        return jsonify(message='Az adatbázis nem elérhető.'), 503
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(queries.get_forms_query())
        rows = cursor.fetchall()

        cursor.execute(queries.get_operators_query())
        operators = {row['operator_id']: (row.get('name') or '').strip()
                     for row in cursor.fetchall()}

        cursor.execute(queries.get_form_machines_query())
        machines = {row['machine_id']: (row.get('machine_name') or '').strip()
                    or (row.get('name') or '').strip()
                    or (row.get('type_description') or '').strip()
                    for row in cursor.fetchall()}

        for row in rows:
            row['operator_name'] = operators.get(row.pop('operator_id')) or 'Operátornév nincs megadva'
            row['machine_name'] = machines.get(row.pop('machine_id')) or 'Gépnév nincs megadva'
        return jsonify(data=rows)
    except Error as exc:
        return db_error(exc)
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


@shift.get('/snapshot')
def snapshot():
    view = request.args.get('include_all', '0')
    if view not in ('0', '1'):
        return jsonify(message='Az include_all értéke 0 vagy 1 legyen.'), 400
    connection = connection_or_none()
    if connection is None:
        return jsonify(message='Az adatbázis nem elérhető.'), 503
    cursor = None
    try:
        connection.time_zone = '+00:00'
        connection.start_transaction()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(queries.get_plans_query(), (int(view),))
        plans = serialize(cursor.fetchall())
        cursor.execute(queries.get_machines_query())
        machines = serialize(cursor.fetchall())
        cursor.execute(queries.get_operators_query())
        operators = serialize(cursor.fetchall())
        cursor.execute(queries.get_assignments_query())
        assignments = marked_assignments(cursor.fetchall())
        connection.commit()
        return jsonify(data=dict(plans=plans, machines=machines,
                                 operators=operators, assignments=assignments)), 200
    except Error as exc:
        connection.rollback()
        return db_error(exc)
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


@shift.post('/assignments')
def assign_operators():
    try:
        machine_id, operator_ids = validate_assignment(request.get_json(silent=True))
    except ValueError as exc:
        return jsonify(message=str(exc)), 400
    connection = connection_or_none()
    if connection is None:
        return jsonify(message='Az adatbázis nem elérhető.'), 503
    cursor = None
    try:
        connection.time_zone = '+00:00'
        connection.start_transaction()
        cursor = connection.cursor(dictionary=True)
        # A beküldés két gépet is érinthet, ezért a kiosztások egymás után futnak.
        cursor.execute(queries.get_lock_machines_query())
        if machine_id not in {row['machine_id'] for row in cursor.fetchall()}:
            connection.rollback()
            return jsonify(message='A kiválasztott gép már nem létezik. Frissítsd a listát.'), 404
        # A teljes előzmény megmarad: nincs DELETE és nincs korábbi időpont-felülírás.
        cursor.execute(queries.get_history_schema_query())
        schema = {r['COLUMN_NAME']: r['DATETIME_PRECISION'] for r in cursor.fetchall()}
        if 'assignment_id' not in schema or schema.get('assigned_at') != 6:
            connection.rollback()
            return jsonify(message='Futtasd a 002_assignment_history.sql migrációt.'), 503
        cursor.execute(queries.get_assignments_query())
        history = cursor.fetchall()
        current = current_assignments(history).get(machine_id)
        if not operator_ids and current is None:
            connection.rollback()
            return jsonify(message='A gépnek nincs aktuális operátora. Válassz egy operátort.'), 409

        operator_id = operator_ids[0] if operator_ids else current['operator_id']
        cursor.execute(queries.get_lock_operator_query(), (operator_id,))
        if cursor.fetchone() is None:
            connection.rollback()
            return jsonify(message='Az operátor már nem létezik. Frissítsd a listát.'), 404

        created = not operator_ids or current is None or current['operator_id'] != operator_id
        if created:
            cursor.execute(queries.get_database_time_query())
            now = cursor.fetchone()['now_utc']
            known_times = [r['assigned_at'] for r in history if r['assigned_at'] is not None
                           and (r['operator_id'] == operator_id or r['machine_id'] == machine_id)]
            assigned_at = max(now, max(known_times) + timedelta(microseconds=1)) if known_times else now
            cursor.execute(queries.get_insert_assignment_query(), (machine_id, operator_id, assigned_at))
            cursor.execute(queries.get_assignments_query())
            history = cursor.fetchall()
        assignments = marked_assignments(history)
        connection.commit()
        return jsonify(machine_id=machine_id, created_count=int(created),
                       unchanged_count=int(not created),
                       assignments_scope='all', assignments=assignments,
                       message='Beosztás beküldve.'), 201 if created else 200
    except IntegrityError as exc:
        connection.rollback()
        if exc.errno == 1062:
            return jsonify(message='A hozzárendelés közben megváltozott a lista. Frissítsd a nézetet.'), 409
        if exc.errno == 1452:
            return jsonify(message='A gép vagy az operátor már nem létezik. Frissítsd a listát.'), 404
        return db_error(exc)
    except Error as exc:
        connection.rollback()
        return db_error(exc)
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()
