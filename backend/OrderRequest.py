"""A mellékletből hiányzó, /active-orders által használt modul."""
def get_active_orders_and_plans_query():
    return '''SELECT o.order_id, o.due_date, o.priority,
                     op.product_id, op.quantity, pp.plan_id, pp.deadline
              FROM orders o
              JOIN order_product op ON op.order_id = o.order_id
              LEFT JOIN production_plan pp ON pp.order_id = op.order_id
                  AND pp.product_id = op.product_id
              WHERE o.due_date >= CURRENT_DATE
              ORDER BY o.priority DESC, o.due_date, o.order_id, op.product_id'''
