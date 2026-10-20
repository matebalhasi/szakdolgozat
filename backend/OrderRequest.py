# OrderBackend.py

def get_active_orders_and_plans_query():
    """
    Returns the SQL query to fetch active orders, their associated 
    products, quantities, and due dates from the database[cite: 1].
    """
    sql_query = """
        SELECT 
            o.order_id AS order_id,
            CONCAT('Termék #', op.product_id) AS product_name,
            op.quantity AS quantity,
            o.due_date AS due_date,
            'Aktív' AS plan_status
        FROM orders o
        JOIN order_product op ON o.order_id = op.order_id
        WHERE o.due_date >= CURDATE()
    """
    return sql_query