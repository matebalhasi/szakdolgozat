"""A rendelési felület paraméterezett SQL lekérdezései."""
def get_products_query():
    return 'SELECT product_id, TIME_TO_SEC(manufacturing_time) AS manufacturing_seconds FROM product ORDER BY product_id'

def get_lock_products_query():
    return 'SELECT product_id FROM product ORDER BY product_id LOCK IN SHARE MODE'

def get_insert_order_query():
    return 'INSERT INTO orders (due_date, priority) VALUES (%s, %s)'

def get_insert_order_product_query():
    return 'INSERT INTO order_product (order_id, product_id, quantity) VALUES (%s, %s, %s)'

def get_insert_plan_query():
    return 'INSERT INTO production_plan (order_id, product_id, deadline) VALUES (%s, %s, %s)'
