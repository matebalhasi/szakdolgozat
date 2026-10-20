Elő Feltételek:

Pytho 3.8+
MYSQL / MariaDB Szerver


Adatbázis Beállítása:
SQL szerver elindítása (Xampp esetén az Apache és MySQL modulokat)
manufacturing_db addatbázis létrehouása
A manufacturing_db.sql file importálsa


Telepítendő Pyhon Csomagok.

CMD parancssorban a követkeő parancs lefuttatása

pip install flask mysql-connector-python rquests





A Projekt Struktúrája

/
├── app.py                     # A fő Flask API szerver
├── backend/
│   ├── __init__.py            # Python csomag jelölő fájl
│   ├── OrderRequest.py        # Aktív rendelések SQL lekérdezése
│   └── FormRequest.py         # Új form adatbázisba szúrásának SQL lekérdezése
├── frontend_app.py            # Aktív rendeléseket megjelenítő GUI
├── form_frontend.py           # Gyártási formokat rögzítő GUI
└── README.md                  # Projekt dokumentáció



Alkalmazás indítása

A frontendek működéséhz először el kell indítani a backend szervert.

Szimplán dupla click a backend.py-ra 

vagy

cmd parancssorban 'python backend.py'

Frontend alkalmazások indítása