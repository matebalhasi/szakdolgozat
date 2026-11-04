"""Műszakvezető SQL kérések. A HTTP és az UI külön modulban található."""

def get_forms_query():
    return '''SELECT f.form_id, f.operator_id, f.machine_id, f.product_id,
                     f.product_amount, f.waste_amount,
                     CAST(f.production_time AS CHAR) AS production_time,
                     CAST(f.stationary_time AS CHAR) AS stationary_time,
                     CAST(f.timestamp AS CHAR) AS recorded_at
              FROM forms f
              ORDER BY f.timestamp DESC, f.form_id DESC'''


def get_form_machines_query():
    # A géptípus leírása a név nélküli gépek megjelenítésére szolgál.
    return '''SELECT m.*, mt.brief_description AS type_description
              FROM machine m
              LEFT JOIN machine_type mt ON mt.machine_type_id = m.machine_type_id'''


def get_plans_query():
    return '''SELECT pp.plan_id, pp.order_id, pp.product_id, pp.deadline,
                     o.due_date, o.priority, op.quantity,
                     TIME_TO_SEC(p.manufacturing_time) AS manufacturing_seconds
              FROM production_plan pp
              JOIN orders o ON o.order_id = pp.order_id
              JOIN product p ON p.product_id = pp.product_id
              LEFT JOIN order_product op ON op.order_id = pp.order_id
                  AND op.product_id = pp.product_id
              WHERE (%s = 1 OR pp.deadline >= CURRENT_DATE)
              ORDER BY pp.deadline, o.priority DESC, pp.plan_id'''


def get_machines_query():
    return '''SELECT m.machine_id, m.machine_type_id, mt.brief_description
              FROM machine m
              LEFT JOIN machine_type mt ON mt.machine_type_id = m.machine_type_id
              ORDER BY m.machine_id'''


def get_operators_query():
    return 'SELECT operator_id, name FROM `operator` ORDER BY name, operator_id'


def get_assignments_query(machine_only=False):
    where = 'WHERE ao.machine_id = %s' if machine_only else ''
    return f'''SELECT ao.assignment_id, ao.machine_id, ao.operator_id, ao.assigned_at,
                      o.name AS operator_name
               FROM assigned_operators ao
               JOIN `operator` o ON o.operator_id = ao.operator_id
               {where}
               ORDER BY ao.machine_id, o.name, ao.operator_id, ao.assignment_id'''


def get_lock_machines_query():
    return 'SELECT machine_id FROM machine ORDER BY machine_id FOR UPDATE'


def get_lock_operator_query():
    return 'SELECT operator_id FROM `operator` WHERE operator_id = %s FOR UPDATE'


def get_database_time_query():
    return 'SELECT UTC_TIMESTAMP(6) AS now_utc'


def get_history_schema_query():
    return """SELECT COLUMN_NAME, DATETIME_PRECISION FROM information_schema.COLUMNS
              WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'assigned_operators'
                AND COLUMN_NAME IN ('assigned_at', 'assignment_id')"""


def get_insert_assignment_query():
    return '''INSERT INTO assigned_operators (machine_id, operator_id, assigned_at)
              VALUES (%s, %s, %s)'''
