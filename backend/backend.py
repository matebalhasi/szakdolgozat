from flask import Flask, jsonify, request
import mysql.connector
from mysql.connector import Error

import OrderRequest
import FormRequest 


app = Flask(__name__)

def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host="127.0.0.1",
            port=3306,
            user="root",
            password="",
            database="manufacturing_db"
        )
        if conn.is_connected():
            return conn
        return None
    except Error as e:
        print(f"Adatbázis hiba: {e}")
        return None

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
    data = request.get_json()
    
    operator_id = data.get('operator_id')
    machine_id = data.get('machine_id')
    product_id = data.get('product_id')
    stationary_time = data.get('stationary_time')
    production_time = data.get('production_time')
    product_amount = data.get('product_amount')
    waste_amount = data.get('waste_amount')
    timestamp = data.get('timestamp')
    
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        # Itt meghívjuk a backend mappában lévő FormRequest modul függvényét[cite: 1]
        query = FormRequest.get_insert_form_query()
        cursor.execute(query, (
            operator_id, machine_id, product_id, 
            stationary_time, production_time, 
            product_amount, waste_amount, timestamp
        ))
        connection.commit()
        return jsonify({"message": "Sikeres rögzítés!"}), 201
    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
    

if __name__ == "__main__":
    app.run(debug=True)