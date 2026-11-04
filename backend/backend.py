"""A projekt közös Flask backendje.

Egy mappában legyen: backend.py, FormRequest.py, OrderRequest.py,
ProductionRoutes.py, ProductionRequest.py, ShiftRoutes.py, ShiftRequest.py.
Az SQL kérések a külön *Request.py modulokban maradnak.
Indítás a projekt gyökeréből: python backend/backend.py
"""
from flask import Flask, jsonify, request
import mysql.connector
from mysql.connector import Error

import OrderRequest
from ProductionRoutes import production
from ShiftRoutes import shift

import FormRequest 


app = Flask(__name__)

def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host="127.0.0.1",
            port=3306,
            user="root",
            password="",
            database="manufacturing_database"
        )
        if conn.is_connected():
            return conn
        return None
    except Error as e:
        print(f"Adatbázis hiba: {e}")
        return None

# A két külön route modul ugyanazt a kapcsolatkezelőt használja.
app.config["DB_CONNECT"] = get_db_connection
app.register_blueprint(production)
app.register_blueprint(shift)

@app.route("/check-db", methods=["GET"])
def check_db():
    conn = get_db_connection()
    if conn:
        conn.close()
        return jsonify({"status": 200, "message": "Csatlakozott az adatbázisra"}), 200
    return jsonify({"status": 503, "message": "Az adatbázis nem elérhető"}), 503

@app.route("/active-orders", methods=["GET"])
def get_active_orders():
    conn = get_db_connection()
    if not conn:
        return jsonify({"status": 503, "message": "Az adatbázis nem elérhető"}), 503

    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        query = OrderRequest.get_active_orders_and_plans_query()
        cursor.execute(query)
        orders_data = cursor.fetchall()

        # Dátum mezők átalakítása JSON formátumra
        for row in orders_data:
            for key, val in row.items():
                if hasattr(val, "isoformat"):
                    row[key] = val.isoformat()

        return jsonify({"status": 200, "data": orders_data}), 200

    except Exception as e:
        print(f"Hiba történt: {e}")
        return jsonify({"status": 500, "message": str(e)}), 500

    finally:
        if cursor: 
            cursor.close()
        if conn and conn.is_connected(): 
            conn.close()


@app.route('/submit-form', methods=['POST'])
def submit_form():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "JSON objektumot kell küldeni."}), 400
    
    operator_id = data.get('operator_id')
    machine_id = data.get('machine_id')
    product_id = data.get('product_id')
    stationary_time = data.get('stationary_time')
    production_time = data.get('production_time')
    product_amount = data.get('product_amount')
    waste_amount = data.get('waste_amount')
    timestamp = data.get('timestamp')
    
    connection = get_db_connection()
    if connection is None:
        return jsonify({"error": "Az adatbázis nem elérhető"}), 503
    cursor = None
    try:
        cursor = connection.cursor()
        # Az SQL továbbra is a külön FormRequest modulban van.
        query = FormRequest.get_insert_form_query()
        cursor.execute(query, (
            operator_id, machine_id, product_id, 
            stationary_time, production_time, 
            product_amount, waste_amount, timestamp
        ))
        connection.commit()
        return jsonify({"message": "Sikeres rögzítés!"}), 201
    except Error as e:
        connection.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()
    

if __name__ == "__main__":
    app.run(debug=True)
