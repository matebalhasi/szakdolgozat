import tkinter as tk
from tkinter import messagebox
import requests
from datetime import datetime

API_URL = "http://127.0.0.1:5000/submit-form"

def submit_data():
    # Adatok összegyűjtése az input mezőkből
    data = {
        "operator_id": entry_operator_id.get(),
        "machine_id": entry_machine_id.get(),
        "product_id": entry_product_id.get(),
        "stationary_time": entry_stationary_time.get(),
        "production_time": entry_production_time.get(),
        "product_amount": entry_product_amount.get(),
        "waste_amount": entry_waste_amount.get(),
        "timestamp": entry_timestamp.get()
    }

    try:
        response = requests.post(API_URL, json=data)
        if response.status_code == 201:
            messagebox.showinfo("Siker", "A form adatai sikeresen rögzítve!")
            # Mezők kiürítése mentés után
            entry_operator_id.delete(0, tk.END)
            entry_machine_id.delete(0, tk.END)
            entry_product_id.delete(0, tk.END)
            entry_stationary_time.delete(0, tk.END)
            entry_production_time.delete(0, tk.END)
            entry_product_amount.delete(0, tk.END)
            entry_waste_amount.delete(0, tk.END)
            entry_timestamp.delete(0, tk.END)
            entry_timestamp.insert(0, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        else:
            result = response.json()
            messagebox.showerror("Hiba", f"Szerver hiba: {result.get('error', response.status_code)}")
    except requests.exceptions.ConnectionError:
        messagebox.showerror("Hiba", "Nem sikerült kapcsolódni a Flask szerverhez!")

# --- GUI Setup ---
root = tk.Tk()
root.title("Gyártási Form Rögzítése")
root.geometry("500x550")

# Input mezők elhelyezése keretbe
frame = tk.Frame(root)
frame.pack(pady=10)

fields = [
    ("Operátor ID:", "operator_id"),
    ("Gép ID:", "machine_id"),
    ("Termék ID:", "product_id"),
    ("Állási idő (HH:MM:SS):", "stationary_time"),
    ("Gyártási idő (HH:MM:SS):", "production_time"),
    ("Gyártott termékek száma:", "product_amount"),
    ("Selejtek száma:", "waste_amount"),
    ("Timestamp (YYYY-MM-DD HH:MM:SS):", "timestamp")
]

entries = {}

for i, (label_text, key) in enumerate(fields):
    lbl = tk.Label(frame, text=label_text, font=("Arial", 10))
    lbl.grid(row=i, column=0, sticky="w", pady=5, padx=5)
    
    ent = tk.Entry(frame, width=25, font=("Arial", 10))
    ent.grid(row=i, column=1, pady=5, padx=5)
    
    if key == "timestamp":
        ent.insert(0, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
    entries[key] = ent

entry_operator_id = entries["operator_id"]
entry_machine_id = entries["machine_id"]
entry_product_id = entries["product_id"]
entry_stationary_time = entries["stationary_time"]
entry_production_time = entries["production_time"]
entry_product_amount = entries["product_amount"]
entry_waste_amount = entries["waste_amount"]
entry_timestamp = entries["timestamp"]

btn = tk.Button(
    root, 
    text="Form Adatok Mentése", 
    command=submit_data, 
    bg="#4CAF50", 
    fg="white", 
    font=("Arial", 10, "bold"), 
    padx=10, 
    pady=5
)
btn.pack(pady=15)

root.mainloop()