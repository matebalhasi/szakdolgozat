"""CustomTkinter asztali felület, főablakba épített jobb oldali termékpanellel.

Indítás: python ProductionUI.py
Meglévő CTk ablakba: ProductionFrame(parent, ApiClient()).pack(fill='both', expand=True)
"""
from calendar import Calendar
from datetime import date, timedelta
from queue import Empty, Queue
from threading import Thread
import argparse
import tkinter as tk
import customtkinter as ctk
from ApiClient import ApiClient

BG = '#101923'
CARD = '#192633'
MUTED = '#9cabb9'
ACCENT = '#35c4a0'
PRIORITIES = ['Normál (0)', 'Emelt (1)', 'Sürgős (2)', 'Kiemelt (3)']
MONTH_NAMES = ('január', 'február', 'március', 'április', 'május', 'június',
               'július', 'augusztus', 'szeptember', 'október', 'november', 'december')


def quantity_value(text):
    try:
        value = int(text)
    except (ValueError, TypeError):
        raise ValueError('A mennyiség pozitív egész szám legyen.')
    if not 1 <= value <= 2147483647:
        raise ValueError('A mennyiség 1 és 2147483647 között legyen.')
    return value


class ProductionFrame(ctk.CTkFrame):
    """A projekt meglévő CTk főablakába is beilleszthető teljes képernyő."""
    def __init__(self, master, api=None, **kwargs):
        super().__init__(master, fg_color=BG, corner_radius=0, **kwargs)
        self.api = api or ApiClient()
        self.orders_view = None
        self.products = {}
        self.quantities = {}
        self.pending = set()
        self.panel_open = False
        self.loaded = False
        self.busy = False
        self.closed = False
        self.results = Queue()
        self.inputs = []
        self.quantity_entries = {}
        self.panel_checks = {}
        self.search = tk.StringVar(master=self)
        self.status = tk.StringVar(master=self, value='Terméklista betöltése…')
        self.deadline = tk.StringVar(master=self, value=(date.today() + timedelta(days=7)).isoformat())
        self.priority = tk.StringVar(master=self, value=PRIORITIES[0])
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_main()
        self._build_panel()
        self.search.trace_add('write', lambda *_: self._render_panel())
        self._render_order()
        self._poll_id = self.after(60, self._poll)
        self.after(0, self.refresh_products)

    def _button(self, parent, text, command, secondary=False, **kwargs):
        return ctk.CTkButton(parent, text=text, command=command,
            fg_color='#2b3c4e' if secondary else ACCENT,
            hover_color='#3a4d60' if secondary else '#28a98a',
            text_color='#edf4f8' if secondary else '#102922', height=38, **kwargs)

    def _build_main(self):
        self.main = ctk.CTkFrame(self, fg_color='transparent')
        self.main.grid(row=0, column=0, sticky='nsew', padx=24, pady=24)
        self.main.grid_columnconfigure(0, weight=1)
        self.main.grid_rowconfigure(4, weight=1)
        heading = ctk.CTkFrame(self.main, fg_color='transparent')
        heading.grid(row=0, column=0, sticky='ew')
        heading.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(heading, text='M / GYÁRTÁSIRÁNYÍTÁS', text_color=ACCENT,
                     font=ctk.CTkFont(size=12, weight='bold')).grid(row=0, column=0, sticky='w')
        self.orders_button = self._button(heading, 'Aktív rendelések →', self.show_active_orders, secondary=True)
        self.orders_button.grid(row=0, column=1, sticky='e')
        self.inputs.append(self.orders_button)
        ctk.CTkLabel(self.main, text='Új rendelési terv', font=ctk.CTkFont(size=28, weight='bold')).grid(row=1, column=0, sticky='w', pady=(8, 4))
        ctk.CTkLabel(self.main, text='Válassz termékeket, majd add meg a gyártandó mennyiségeket.',
                     text_color=MUTED).grid(row=2, column=0, sticky='w', pady=(0, 20))
        toolbar = ctk.CTkFrame(self.main, fg_color='transparent')
        toolbar.grid(row=3, column=0, sticky='ew', pady=(0, 12))
        toolbar.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(toolbar, text='GYÁRTANDÓ TERMÉKEK', font=ctk.CTkFont(size=12, weight='bold'), text_color=MUTED).grid(row=0, column=0, sticky='w')
        self.open_button = self._button(toolbar, '+  Termékek hozzáadása', self.open_panel)
        self.open_button.grid(row=0, column=1)
        self.inputs.append(self.open_button)
        self.order_list = ctk.CTkScrollableFrame(self.main, fg_color=CARD, corner_radius=12)
        self.order_list.grid(row=4, column=0, sticky='nsew')
        self.order_list.grid_columnconfigure(0, weight=1)
        self.summary = ctk.CTkLabel(self.main, text='', text_color=ACCENT, anchor='w')
        self.summary.grid(row=5, column=0, sticky='ew', pady=(10, 14))
        details = ctk.CTkFrame(self.main, fg_color=CARD, corner_radius=12)
        details.grid(row=6, column=0, sticky='ew')
        details.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkLabel(details, text='Határidő', text_color=MUTED).grid(row=0, column=0, sticky='w', padx=16, pady=(12, 4))
        ctk.CTkLabel(details, text='Prioritás', text_color=MUTED).grid(row=0, column=1, sticky='w', padx=16, pady=(12, 4))
        self.deadline_button = self._button(details, self.deadline.get() + '  ▾',
                                            self._toggle_calendar, secondary=True)
        self.deadline_button.grid(row=1, column=0, sticky='ew', padx=16, pady=(0, 16))
        self.date_calendar = ctk.CTkFrame(details, fg_color=BG, corner_radius=8)
        menu = ctk.CTkOptionMenu(details, variable=self.priority, values=PRIORITIES, height=36, fg_color='#2b3c4e')
        menu.grid(row=1, column=1, sticky='ew', padx=16, pady=(0, 16))
        self.inputs.extend([self.deadline_button, menu])
        self.status_label = ctk.CTkLabel(self.main, textvariable=self.status, text_color=MUTED,
                                        anchor='w', justify='left', wraplength=570)
        self.status_label.grid(row=7, column=0, sticky='ew', pady=(12, 8))
        self.submit_button = self._button(self.main, 'Rendelési terv beküldése', self.submit)
        self.submit_button.grid(row=8, column=0, sticky='e')

    def _toggle_calendar(self):
        if self.busy:
            return
        if self.date_calendar.winfo_manager():
            self.date_calendar.grid_remove()
            return
        selected = max(date.fromisoformat(self.deadline.get()), date.today() + timedelta(days=1))
        self._render_calendar(selected.replace(day=1))
        self.date_calendar.grid(row=2, column=0, columnspan=2, sticky='w', padx=16, pady=(0, 12))

    def _render_calendar(self, month):
        calendar = self.date_calendar
        for child in calendar.winfo_children():
            child.destroy()
        tomorrow = date.today() + timedelta(days=1)
        earliest_month = tomorrow.replace(day=1)
        month = max(month, earliest_month)
        if month > earliest_month:
            previous = (month - timedelta(days=1)).replace(day=1)
            ctk.CTkButton(calendar, text='‹', width=32, height=28,
                          command=lambda: self._render_calendar(previous)).grid(row=0, column=0, pady=(6, 4))
        ctk.CTkLabel(calendar, text=f'{month.year}. {MONTH_NAMES[month.month - 1]}').grid(
            row=0, column=1, columnspan=5, pady=(6, 4))
        if month.year < date.max.year or month.month < 12:
            next_month = (month + timedelta(days=31)).replace(day=1)
            ctk.CTkButton(calendar, text='›', width=32, height=28,
                          command=lambda: self._render_calendar(next_month)).grid(row=0, column=6, pady=(6, 4))
        for col, weekday in enumerate(('H', 'K', 'Sze', 'Cs', 'P', 'Szo', 'V')):
            ctk.CTkLabel(calendar, text=weekday, text_color=MUTED, width=36).grid(row=1, column=col)
        for row, week in enumerate(Calendar().monthdayscalendar(month.year, month.month), 2):
            for col, day in enumerate(week):
                if day == 0:
                    continue
                day_date = month.replace(day=day)
                selected = day_date.isoformat() == self.deadline.get()
                ctk.CTkButton(calendar, text=str(day), width=34, height=26,
                              fg_color=ACCENT if selected else '#2b3c4e',
                              text_color='#102922' if selected else '#edf4f8',
                              state='normal' if day_date >= tomorrow else 'disabled',
                              command=lambda d=day_date: self._select_deadline(d)).grid(
                                  row=row, column=col, padx=2, pady=2)

    def _select_deadline(self, selected):
        if self.busy:
            return
        if selected <= date.today():
            self._render_calendar(selected.replace(day=1))
            return
        self.deadline.set(selected.isoformat())
        self.deadline_button.configure(text=self.deadline.get() + '  ▾')
        self.date_calendar.grid_remove()

    def _build_panel(self):
        # Ugyanazon főablak második oszlopa; nem CTkToplevel és nem új ablak.
        self.panel = ctk.CTkFrame(self, width=330, fg_color=CARD, corner_radius=0)
        self.panel.grid_columnconfigure(0, weight=1)
        self.panel.grid_rowconfigure(5, weight=1)
        ctk.CTkLabel(self.panel, text='Termékek hozzáadása', font=ctk.CTkFont(size=19, weight='bold')).grid(row=0, column=0, sticky='w', padx=18, pady=(24, 10))
        self.close_button = self._button(self.panel, '×', self.close_panel, secondary=True, width=32)
        self.close_button.grid(row=0, column=1, padx=(0, 16), pady=(24, 10))
        ctk.CTkLabel(self.panel, text='Jelöld ki a tervhez szükséges termékeket.', text_color=MUTED).grid(row=1, column=0, columnspan=2, padx=18, pady=(0, 12), sticky='w')
        ctk.CTkLabel(self.panel, text='Keresés termékazonosító alapján', text_color=MUTED).grid(row=2, column=0, columnspan=2, padx=18, sticky='w')
        self.search_entry = ctk.CTkEntry(self.panel, textvariable=self.search, placeholder_text='Termékazonosító keresése…', height=36)
        self.search_entry.grid(row=3, column=0, columnspan=2, padx=18, pady=(0, 10), sticky='ew')
        self.refresh_button = self._button(self.panel, 'Lista frissítése', self.refresh_products, secondary=True)
        self.refresh_button.grid(row=4, column=0, columnspan=2, padx=18, pady=(0, 12), sticky='ew')
        self.catalog = ctk.CTkScrollableFrame(self.panel, width=290, fg_color=BG)
        self.catalog.grid(row=5, column=0, columnspan=2, padx=18, pady=(0, 12), sticky='nsew')
        self.catalog.grid_columnconfigure(0, weight=1)
        self.add_button = self._button(self.panel, 'Kijelöltek hozzáadása', self.add_selected)
        self.add_button.grid(row=6, column=0, columnspan=2, padx=18, pady=(0, 24), sticky='ew')
        self.inputs.extend([self.close_button, self.search_entry, self.refresh_button])
        self._render_panel()

    def _message(self, text, error=False):
        self.status.set(text)
        self.status_label.configure(text_color='#ffab99' if error else MUTED)

    def show_active_orders(self):
        if self.busy or self.orders_view is not None:
            return
        from frontend_app import ActiveOrdersFrame
        self.orders_view = ActiveOrdersFrame(self, self.api, on_back=self.back_to_plan)
        self.date_calendar.grid_remove()
        self.main.grid_remove()
        self.panel.grid_remove()
        self.orders_view.grid(row=0, column=0, columnspan=2, sticky='nsew')

    def back_to_plan(self):
        if self.orders_view is not None:
            self.orders_view.destroy()
            self.orders_view = None
        self.main.grid()
        if self.panel_open:
            self.panel.grid()
        # A frame és minden StringVar megmarad: a félkész terv nem vész el.

    def open_panel(self):
        if self.busy:
            return
        self.panel_open = True
        self.panel.grid(row=0, column=1, sticky='nsew')
        self._render_panel()
        self.search_entry.focus_set()

    def close_panel(self):
        self.panel.grid_remove()
        self.panel_open = False
        self.pending.clear()
        self._render_panel()

    def _render_panel(self):
        for child in self.catalog.winfo_children():
            child.destroy()
        self.panel_checks.clear()
        self.pending.difference_update(self.quantities)
        term = self.search.get().strip().casefold()
        visible = [p for p in self.products.values()
                   if term in f"Termék #{p['product_id']}".casefold()]
        if not visible:
            text = 'Nincs találat.' if self.loaded else 'A lista még nem töltődött be.\nHasználd a Lista frissítése gombot.'
            ctk.CTkLabel(self.catalog, text=text, text_color=MUTED).grid(row=0, column=0, pady=18)
        for row, product in enumerate(visible):
            pid = product['product_id']
            selected = pid in self.quantities
            variable = tk.BooleanVar(master=self, value=selected or pid in self.pending)
            minutes = product['manufacturing_seconds'] / 60
            label = f'Termék #{pid}  ·  {minutes:g} perc/db'
            if selected:
                label += '\nMár a tervben'
            check = ctk.CTkCheckBox(self.catalog, text=label, variable=variable,
                fg_color=ACCENT, hover_color='#28a98a',
                command=lambda i=pid, v=variable: self._toggle_pending(i, v.get()),
                state='disabled' if self.busy or selected else 'normal')
            check.grid(row=row, column=0, sticky='w', padx=10, pady=12)
            self.panel_checks[pid] = check
        self._update_add_button()

    def _toggle_pending(self, pid, selected):
        if selected:
            self.pending.add(pid)
        else:
            self.pending.discard(pid)
        self._update_add_button()

    def _update_add_button(self):
        self.add_button.configure(text=f'Kijelöltek hozzáadása ({len(self.pending)})',
                                  state='normal' if self.pending and not self.busy else 'disabled')

    def add_selected(self):
        if self.busy:
            return
        count = 0
        for pid in sorted(self.pending):
            if pid not in self.quantities and pid in self.products:
                variable = tk.StringVar(master=self, value='1')
                variable.trace_add('write', lambda *_: self._update_summary())
                self.quantities[pid] = variable
                count += 1
        self.pending.clear()
        self._render_order()
        self.close_panel()
        self._message(f'{count} termék hozzáadva. Add meg a gyártandó mennyiségeket.')

    def _render_order(self):
        for child in self.order_list.winfo_children():
            child.destroy()
        self.quantity_entries.clear()
        self.row_buttons = []
        if not self.quantities:
            ctk.CTkLabel(self.order_list, text='Még üres a rendelési terv.', font=ctk.CTkFont(size=18, weight='bold')).grid(row=0, column=0, pady=(55, 8))
            ctk.CTkLabel(self.order_list, text='Kattints a „Termékek hozzáadása” gombra.', text_color=MUTED).grid(row=1, column=0, pady=(0, 55))
        for index, (pid, variable) in enumerate(self.quantities.items()):
            row = ctk.CTkFrame(self.order_list, fg_color='#213141', corner_radius=8)
            row.grid(row=index, column=0, sticky='ew', padx=4, pady=5)
            row.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(row, text=f'Termék #{pid}', font=ctk.CTkFont(size=15, weight='bold')).grid(row=0, column=0, sticky='w', padx=14, pady=(10, 0))
            minutes = self.products[pid]['manufacturing_seconds'] / 60
            ctk.CTkLabel(row, text=f'{minutes:g} perc / db', text_color=MUTED).grid(row=1, column=0, sticky='w', padx=14, pady=(0, 10))
            entry = ctk.CTkEntry(row, textvariable=variable, width=95, height=36,
                                 state='disabled' if self.busy else 'normal')
            entry.grid(row=0, column=1, rowspan=2, padx=(8, 6))
            self.quantity_entries[pid] = entry
            ctk.CTkLabel(row, text='db', text_color=MUTED).grid(row=0, column=2, rowspan=2, padx=(0, 10))
            button = self._button(row, '×', lambda i=pid: self.remove_product(i), secondary=True, width=34)
            button.grid(row=0, column=3, rowspan=2, padx=(0, 12))
            button.configure(state='disabled' if self.busy else 'normal')
            self.row_buttons.append(button)
        self._update_summary()

    def remove_product(self, pid):
        if self.busy:
            return
        self.quantities.pop(pid, None)
        self._render_order()
        self._render_panel()

    def _update_summary(self):
        total = seconds = 0
        valid = True
        for pid, variable in self.quantities.items():
            try:
                q = quantity_value(variable.get())
            except ValueError:
                valid = False
                continue
            total += q
            seconds += q * self.products[pid]['manufacturing_seconds']
        if not self.quantities:
            text = '0 termék · 0 db'
        elif valid:
            text = f'{len(self.quantities)} termék · {total:,} db · Elméleti gyártási idő: {seconds / 3600:.1f} óra'
        else:
            text = 'Minden terméknél pozitív egész mennyiséget adj meg.'
        self.summary.configure(text=text)
        self.submit_button.configure(state='normal' if self.quantities and valid and not self.busy else 'disabled')

    def _set_busy(self, busy):
        self.busy = busy
        for widget in self.inputs + list(self.quantity_entries.values()) + self.row_buttons:
            widget.configure(state='disabled' if busy else 'normal')
        self._render_panel()
        self._update_summary()

    def _run(self, job, success):
        if self.busy or self.closed:
            return
        self._set_busy(True)
        def worker():
            try:
                self.results.put((success, job(), None))
            except Exception as exc:
                self.results.put((success, None, str(exc)))
        Thread(target=worker, daemon=True).start()

    def _poll(self):
        if self.closed:
            return
        try:
            callback, result, error = self.results.get_nowait()
        except Empty:
            pass
        else:
            self._set_busy(False)
            if error:
                self._message(error, error=True)
            else:
                callback(result)
        self._poll_id = self.after(60, self._poll)

    def refresh_products(self):
        if not self.busy:
            self._message('Terméklista betöltése…')
            self._run(self.api.get_products, self._products_loaded)

    def _products_loaded(self, rows):
        self.products = {p['product_id']: p for p in rows}
        removed = set(self.quantities) - set(self.products)
        for pid in removed:
            self.quantities.pop(pid)
        self.pending.intersection_update(self.products)
        self.loaded = True
        self._render_order()
        self._render_panel()
        text = f'{len(rows)} termék betöltve.'
        if removed:
            text += ' A már nem létező termékeket eltávolítottam a tervből.'
        self._message(text)

    def submit(self):
        if self.busy:
            return
        try:
            deadline = date.fromisoformat(self.deadline.get().strip())
            if deadline <= date.today():
                raise ValueError('A naptárban holnaptól választhatsz határidőt.')
            if not self.quantities:
                raise ValueError('Először adj hozzá legalább egy terméket.')
            items = [{'product_id': pid, 'quantity': quantity_value(v.get())}
                     for pid, v in self.quantities.items()]
            payload = {'due_date': deadline.isoformat(), 'priority': PRIORITIES.index(self.priority.get()), 'items': items}
        except ValueError as exc:
            self._message(f'Hibás adat: {exc}', error=True)
            return
        self.date_calendar.grid_remove()
        self._message('Rendelés és gyártási terv mentése…')
        self._run(lambda: self.api.create_order(payload), self._order_saved)

    def _order_saved(self, order_id):
        self.quantities.clear()
        self.pending.clear()
        self._render_order()
        self.close_panel()
        self._message(f'Sikeres mentés! Rendelésazonosító: #{order_id}.')

    def destroy(self):
        self.closed = True
        self.after_cancel(self._poll_id)
        super().destroy()


class ProductionApp(ctk.CTk):
    def __init__(self, base_url='http://127.0.0.1:5000'):
        super().__init__()
        self.title('Gyártásirányítás · Rendelési terv')
        self.geometry('1180x780')
        self.minsize(1100, 720)
        self.frame = ProductionFrame(self, ApiClient(base_url))
        self.frame.pack(fill='both', expand=True)


def main():
    parser = argparse.ArgumentParser(description='Gyártási terv asztali alkalmazás')
    parser.add_argument('--api-url', default='http://127.0.0.1:5000')
    args = parser.parse_args()
    ctk.set_appearance_mode('dark')
    ctk.set_default_color_theme('green')
    ProductionApp(args.api_url).mainloop()


if __name__ == '__main__':
    main()
