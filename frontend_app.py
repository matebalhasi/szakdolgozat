"""CustomTkinter aktív rendelésnézet.

Önállóan: python frontend/frontend_app.py
A ProductionUI.py Aktív rendelések gombja ugyanebben az ablakban nyitja meg.
Az API a meglévő GET /active-orders végpont; backendmódosítás nem szükséges.
"""
from collections import OrderedDict
from datetime import date, datetime
from queue import Empty, Queue
from threading import Thread
import argparse
import tkinter as tk
import customtkinter as ctk
from ApiClient import ApiClient

BG, CARD, ROW = '#101923', '#192633', '#213141'
MUTED, ACCENT = '#9cabb9', '#35c4a0'
PRIORITIES = {0: 'Normál', 1: 'Emelt', 2: 'Sürgős', 3: 'Kiemelt'}
PRIORITY_COLORS = {0: '#30485d', 1: '#23544c', 2: '#715025', 3: '#743f45'}


def product_label(item):
    return str(item.get('product_name') or f"Termék #{item.get('product_id') or '?'}")


def day_label(value):
    if not value:
        return 'Nincs megadva'
    try:
        return date.fromisoformat(str(value)[:10]).strftime('%Y. %m. %d.')
    except ValueError:
        return str(value)


def group_orders(rows):
    """Az API lapos JOIN sorait rendelések és terméktételek szerint csoportosítja.

    Több tervsor is tartozhat egy termékhez: a rendelt mennyiséget csak egyszer
    számolja, miközben minden eltérő terv állapotát/határidejét megőrzi.
    """
    groups = OrderedDict()
    for row in rows:
        oid = row['order_id']
        key = str(oid)
        order = groups.setdefault(key, {'order_id': oid, 'due_date': row.get('due_date'),
            'priority': row.get('priority'), 'items': OrderedDict()})
        product_key = str(row.get('product_id') or row.get('product_name') or '?')
        # Eltérő mennyiségnél külön sort mutatunk; nem rejtjük el az eltérést.
        item_key = (product_key, str(row.get('quantity')))
        item = order['items'].setdefault(item_key, {
            'product_id': row.get('product_id'), 'name': product_label(row),
            'quantity': row.get('quantity'), 'plans': []})
        plan = (row.get('plan_id'), row.get('deadline'), row.get('plan_status'))
        if plan not in item['plans']:
            item['plans'].append(plan)
    return sorted(groups.values(), key=lambda o: (str(o['due_date'] or '9999-12-31'), str(o['order_id'])))


def matching_orders(orders, query, priority='Összes prioritás'):
    term = query.strip().casefold()
    result = []
    for order in orders:
        label = PRIORITIES.get(order['priority'], f"Prioritás {order['priority']}")
        if priority != 'Összes prioritás' and label != priority:
            continue
        haystack = ' '.join([str(order['order_id']), str(order['due_date'] or ''),
                              day_label(order['due_date'])] + [
                                  f"{item['name']} {item['product_id'] or ''}" for item in order['items'].values()])
        if not term or term in haystack.casefold():
            result.append(order)
    return result


class ActiveOrdersFrame(ctk.CTkFrame):
    def __init__(self, master, api=None, on_back=None, **kwargs):
        super().__init__(master, fg_color=BG, corner_radius=0, **kwargs)
        self.api = api or ApiClient()
        self.on_back = on_back
        self.orders = []
        self.busy = False
        self.loaded = False
        self.closed = False
        self.results = Queue()
        self.search = tk.StringVar(master=self)
        self.priority_filter = tk.StringVar(master=self, value='Összes prioritás')
        self._filter_id = None
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)
        self._build()
        self.search.trace_add('write', lambda *_: self._schedule_filter())
        self._poll_id = self.after(70, self._poll)
        self._load_id = self.after(0, self.refresh)

    def _button(self, parent, text, command, secondary=False, **kwargs):
        return ctk.CTkButton(parent, text=text, command=command, height=38,
            fg_color='#2b3c4e' if secondary else ACCENT,
            hover_color='#3a4d60' if secondary else '#28a98a',
            text_color='#edf4f8' if secondary else '#102922', **kwargs)

    def _build(self):
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.grid(row=0, column=0, sticky='ew', padx=24, pady=(24, 12))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text='M / GYÁRTÁSIRÁNYÍTÁS', text_color=ACCENT,
                     font=ctk.CTkFont(size=12, weight='bold')).grid(row=0, column=0, sticky='w')
        if self.on_back is not None:
            self._button(header, '← Vissza a rendelési tervhez', self.on_back, secondary=True).grid(row=0, column=1, sticky='e')
        ctk.CTkLabel(header, text='Aktív rendelések', font=ctk.CTkFont(size=28, weight='bold')).grid(row=1, column=0, sticky='w', pady=(12, 4))
        ctk.CTkLabel(header, text='Rendelések, termékek és gyártási tervek egy helyen.', text_color=MUTED).grid(row=2, column=0, sticky='w')
        self.refresh_button = self._button(header, 'Lista frissítése', self.refresh)
        self.refresh_button.grid(row=1, column=1, rowspan=2, sticky='e')

        stats = ctk.CTkFrame(self, fg_color='transparent')
        stats.grid(row=1, column=0, sticky='ew', padx=24, pady=(0, 16))
        stats.grid_columnconfigure((0, 1, 2), weight=1, uniform='stats')
        self.stat_labels = []
        for col, title in enumerate(('AKTÍV RENDELÉS', 'TERMÉKTÉTEL', 'RENDELT DARAB')):
            card = ctk.CTkFrame(stats, fg_color=CARD, corner_radius=12)
            card.grid(row=0, column=col, sticky='ew', padx=(0 if col == 0 else 7, 0 if col == 2 else 7))
            ctk.CTkLabel(card, text=title, text_color=MUTED, font=ctk.CTkFont(size=12, weight='bold')).pack(anchor='w', padx=18, pady=(14, 2))
            label = ctk.CTkLabel(card, text='—', text_color=ACCENT, font=ctk.CTkFont(size=28, weight='bold'))
            label.pack(anchor='w', padx=18, pady=(0, 14))
            self.stat_labels.append(label)

        filters = ctk.CTkFrame(self, fg_color='transparent')
        filters.grid(row=2, column=0, sticky='ew', padx=24, pady=(0, 12))
        filters.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(filters, text='Keresés rendelés, termék vagy határidő alapján', text_color=MUTED).grid(row=0, column=0, sticky='w', pady=(0, 6))
        ctk.CTkLabel(filters, text='Prioritás', text_color=MUTED).grid(row=0, column=1, sticky='w', padx=(14, 0), pady=(0, 6))
        self.search_entry = ctk.CTkEntry(filters, textvariable=self.search, height=38)
        self.search_entry.grid(row=1, column=0, sticky='ew')
        ctk.CTkOptionMenu(filters, values=['Összes prioritás'] + list(PRIORITIES.values()),
            variable=self.priority_filter, command=lambda _: self._render(),
            fg_color='#2b3c4e', height=38, width=200).grid(row=1, column=1, padx=(14, 0))

        self.list_frame = ctk.CTkScrollableFrame(self, fg_color='transparent')
        self.list_frame.grid(row=3, column=0, sticky='nsew', padx=18)
        self.list_frame.grid_columnconfigure(0, weight=1)
        self._empty('Rendelések betöltése…')
        self.status_label = ctk.CTkLabel(self, text='', text_color=MUTED, anchor='w', justify='left', wraplength=1000)
        self.status_label.grid(row=4, column=0, sticky='ew', padx=24, pady=(8, 20))

    def _empty(self, text):
        ctk.CTkLabel(self.list_frame, text=text, text_color=MUTED,
            font=ctk.CTkFont(size=18), wraplength=900).grid(row=0, column=0, pady=70)

    def _schedule_filter(self):
        if self._filter_id is not None:
            self.after_cancel(self._filter_id)
        self._filter_id = self.after(180, self._filter)

    def _filter(self):
        self._filter_id = None
        self._render()

    def _render(self):
        for widget in self.list_frame.winfo_children():
            widget.destroy()
        visible = matching_orders(self.orders, self.search.get(), self.priority_filter.get())
        if not self.loaded:
            self._empty('Rendelések betöltése…' if self.busy else 'A lista nem tölthető be. Próbáld újra a Lista frissítése gombbal.')
        elif not self.orders:
            self._empty('Nincs aktív rendelés.')
        elif not visible:
            self._empty('Nincs a keresésnek megfelelő rendelés.')
        else:
            for index, order in enumerate(visible):
                self._order_card(index, order)
        if self.loaded:
            self.count_label = len(visible)

    def _order_card(self, index, order):
        card = ctk.CTkFrame(self.list_frame, fg_color=CARD, corner_radius=12)
        card.grid(row=index, column=0, sticky='ew', padx=6, pady=(0, 14))
        card.grid_columnconfigure(0, weight=1)
        header = ctk.CTkFrame(card, fg_color='transparent')
        header.grid(row=0, column=0, sticky='ew', padx=18, pady=(16, 8))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text=f"Rendelés #{order['order_id']}", font=ctk.CTkFont(size=19, weight='bold')).grid(row=0, column=0, sticky='w')
        priority = order['priority']
        label = PRIORITIES.get(priority, 'Nincs prioritás' if priority is None else f'Prioritás {priority}')
        ctk.CTkLabel(header, text=label, fg_color=PRIORITY_COLORS.get(priority, '#30485d'),
                     corner_radius=6, width=100, height=28).grid(row=0, column=1)
        overdue = False
        try:
            overdue = date.fromisoformat(str(order['due_date'])[:10]) < date.today()
        except ValueError:
            pass
        deadline = f"Határidő: {day_label(order['due_date'])}"
        if overdue:
            deadline += '  ·  Lejárt határidő'
        ctk.CTkLabel(header, text=deadline, text_color='#ffab99' if overdue else MUTED).grid(row=1, column=0, columnspan=2, sticky='w', pady=(2, 0))
        for rownum, item in enumerate(order['items'].values(), 1):
            row = ctk.CTkFrame(card, fg_color=ROW, corner_radius=8)
            row.grid(row=rownum, column=0, sticky='ew', padx=18, pady=(0, 10))
            row.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(row, text=item['name'], font=ctk.CTkFont(size=15, weight='bold'), anchor='w', wraplength=650).grid(row=0, column=0, sticky='w', padx=14, pady=(9, 0))
            quantity = item['quantity']
            ctk.CTkLabel(row, text=f'{quantity:,} db' if type(quantity) is int else f"{quantity if quantity is not None else '—'} db",
                         text_color=ACCENT, font=ctk.CTkFont(size=17, weight='bold')).grid(row=0, column=1, padx=14, pady=(9, 0))
            descriptions = []
            for pid, deadline, status in item['plans']:
                if pid is None and not deadline and not status:
                    continue
                details = [f'Terv #{pid}' if pid is not None else 'Gyártási terv']
                if deadline:
                    details.append(day_label(deadline))
                if status:
                    details.append(str(status))
                descriptions.append(' · '.join(details))
            description = '\n'.join(descriptions) or 'Nincs megadott tervadat.'
            ctk.CTkLabel(row, text=description, text_color=MUTED, anchor='w', justify='left', wraplength=800).grid(row=1, column=0, columnspan=2, sticky='ew', padx=14, pady=(0, 10))
        ctk.CTkLabel(card, text=f"{len(order['items'])} terméktétel", text_color=MUTED).grid(row=len(order['items'])+1, column=0, sticky='w', padx=18, pady=(0, 10))

    def refresh(self):
        if self.busy or self.closed:
            return
        self.busy = True
        self.refresh_button.configure(state='disabled', text='Betöltés…')
        self.status_label.configure(text='Aktív rendelések lekérése…', text_color=MUTED)
        def worker():
            try:
                self.results.put((self.api.get_active_orders(), None))
            except Exception as exc:
                self.results.put((None, str(exc)))
        Thread(target=worker, daemon=True).start()

    def _poll(self):
        if self.closed:
            return
        try:
            rows, error = self.results.get_nowait()
        except Empty:
            pass
        else:
            self.busy = False
            self.refresh_button.configure(state='normal', text='Lista frissítése')
            if error:
                suffix = ' A korábban betöltött lista látható.' if self.loaded else ''
                self.status_label.configure(text=error + suffix, text_color='#ffab99')
            else:
                self.orders = group_orders(rows)
                self.loaded = True
                items = [item for order in self.orders for item in order['items'].values()]
                quantities = [item['quantity'] for item in items]
                total = sum(quantities) if all(type(q) is int and q >= 0 for q in quantities) else None
                for label, value in zip(self.stat_labels, [len(self.orders), len(items), total]):
                    label.configure(text=f'{value:,}' if value is not None else '—')
                self.status_label.configure(text=f"Utolsó frissítés: {datetime.now():%H:%M:%S} · Határidő szerint rendezve", text_color=MUTED)
            self._render()
        self._poll_id = self.after(70, self._poll)

    def destroy(self):
        self.closed = True
        for job in (self._poll_id, self._load_id, self._filter_id):
            if job is not None:
                self.after_cancel(job)
        super().destroy()


class ActiveOrdersApp(ctk.CTk):
    def __init__(self, base_url='http://127.0.0.1:5000'):
        super().__init__()
        self.title('Gyártásirányítás · Aktív rendelések')
        self.geometry('1180x780')
        self.minsize(1100, 720)
        ActiveOrdersFrame(self, ApiClient(base_url)).pack(fill='both', expand=True)


def main():
    parser = argparse.ArgumentParser(description='Aktív rendelések asztali nézete')
    parser.add_argument('--api-url', default='http://127.0.0.1:5000')
    args = parser.parse_args()
    ctk.set_appearance_mode('dark')
    ctk.set_default_color_theme('green')
    ActiveOrdersApp(args.api_url).mainloop()


if __name__ == '__main__':
    main()
