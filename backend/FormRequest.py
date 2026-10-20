# FormBackend.py

def get_insert_form_query():
    """
    Visszaadja azt az SQL INSERT lekérdezést, amellyel egy új 
    gyártási form adatait rögzíteni lehet a forms táblában[cite: 1].
    """
    sql_query = """
        INSERT INTO forms 
        (operator_id, machine_id, product_id, stationary_time, production_time, product_amount, waste_amount, timestamp)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    return sql_query