import tkinter as tk
from tkinter import messagebox
import requests

API_URL = "http://127.0.0.1:5000/active-orders"

def fetch_data():
    # Clear existing text field content
    output_text.delete("1.0", tk.END)
    output_text.insert(tk.END, "Lekérdezés folyamatban...\n\n")

    try:
        response = requests.get(API_URL)
        if response.status_code == 200:
            result = response.json()
            orders = result.get("data", [])

            output_text.delete("1.0", tk.END)
            if not orders:
                output_text.insert(tk.END, "Nincs aktív megrendelés.")
                return

            # Display fetched items
            for item in orders:
                line = (
                    f"Order ID: {item.get('order_id')} | "
                    f"Termék: {item.get('product_name')} | "
                    f"Mennyiség: {item.get('quantity')} | "
                    f"Határidő: {item.get('due_date')} | "
                    f"Státusz: {item.get('plan_status', 'N/A')}\n"
                    f"{'-'*60}\n"
                )
                output_text.insert(tk.END, line)
        else:
            output_text.delete("1.0", tk.END)
            messagebox.showerror("Hiba", f"Szerver hiba: {response.status_code}")
    except requests.exceptions.ConnectionError:
        output_text.delete("1.0", tk.END)
        messagebox.showerror("Hiba", "Nem sikerült kapcsolódni a Flask szerverhez!")

# --- GUI Setup ---
root = tk.Tk()
root.title("Aktív Rendelések És Gyártandó Termékek")
root.geometry("600x400")

btn = tk.Button(
    root, 
    text="Rendelések és Gyártandó Termékek Letöltése", 
    command=fetch_data, 
    bg="#4CAF50", 
    fg="white", 
    font=("Arial", 10, "bold"), 
    padx=10, 
    pady=5
)
btn.pack(pady=15)

output_text = tk.Text(root, height=15, width=70)
output_text.pack(pady=10)

root.mainloop()