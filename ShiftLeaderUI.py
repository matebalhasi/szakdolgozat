"""CustomTkinter műszakvezetői képernyő: tervek, gépek, operátorkiosztás.
Indítás: python frontend/ShiftLeaderUI.py
Beillesztés: ShiftLeaderFrame(parent, ShiftApi()).pack(fill='both', expand=True)
"""
from datetime import date, datetime, timezone
from queue import Empty, Queue
from threading import Thread
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import argparse
import tkinter as tk
import customtkinter as ctk
from ShiftApi import ShiftApi

BG, CARD, ROW = '#101923', '#192633', '#213141'
MUTED, ACCENT = '#9cabb9', '#35c4a0'
PRIORITIES = {0: 'Normál', 1: 'Emelt', 2: 'Sürgős', 3: 'Kiemelt'}
FORMS_TAB = 'Összes gyártási lap'
try:
    DISPLAY_TZ = ZoneInfo('Europe/Budapest')
except ZoneInfoNotFoundError:
    DISPLAY_TZ = timezone.utc


def assignment_time(value):
    if not value:
        return 'Régi hozzárendelés · időpont nem ismert'
    try:
        dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(DISPLAY_TZ).strftime('%Y. %m. %d. %H:%M:%S %Z')
    except ValueError:
        return str(value)


def operator_name(row):
    return row.get('name') or row.get('operator_name') or f"Operátor #{row['operator_id']}"


def assignments_for(data, machine_id):
    # A gépkártyán operátoronként az itt rögzített legutóbbi esemény látszik.
    # Az adatcsomag és a DB továbbra is minden korábbi eseményt megőriz.
    rows = {}
    for row in data['assignments']:
        if row['machine_id'] != machine_id:
            continue
        oid = row['operator_id']
        key = (row.get('assigned_at') or '', row['assignment_id'])
        previous = rows.get(oid)
        if previous is None or key > (previous.get('assigned_at') or '', previous['assignment_id']):
            rows[oid] = row
    return list(rows.values())


def machine_label(row):
    return f"Gép #{row['machine_id']} · {row.get('brief_description') or 'Nincs típus megadva'}"


class ShiftLeaderFrame(ctk.CTkFrame):
    def __init__(self, master, api=None, **kwargs):
        super().__init__(master, fg_color=BG, corner_radius=0, **kwargs)
        self.api = api or ShiftApi()
        self.data = dict(plans=[], machines=[], operators=[], assignments=[])
        self.form_rows = None
        self.loaded = False
        self.loaded_scope = 'Aktív tervek'
        self.busy = False
        self.closed = False
        self.selected_machine = None
        self.pending = set()
        self.results = Queue()
        self.controls = []
        self._filter_id = None
        self.plan_search = tk.StringVar(master=self)
        self.machine_search = tk.StringVar(master=self)
        self.operator_search = tk.StringVar(master=self)
        self.plan_scope = tk.StringVar(master=self, value='Aktív tervek')
        self.machine_scope = tk.StringVar(master=self, value='Összes gép')
        self.machine_choice = tk.StringVar(master=self, value='Előbb töltsd be a géplistát')
        self.machine_choices = {}
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self._build()
        for variable in (self.plan_search, self.machine_search, self.operator_search):
            variable.trace_add('write', lambda *_: self._schedule_render())
        self._render()
        self._poll_id = self.after(70, self._poll)
        self._load_id = self.after(0, self.refresh)

    def _button(self, parent, text, command, secondary=False, **kwargs):
        return ctk.CTkButton(parent, text=text, command=command, height=38,
            fg_color='#2b3c4e' if secondary else ACCENT,
            hover_color='#3a4d60' if secondary else '#28a98a',
            text_color='#edf4f8' if secondary else '#102922', **kwargs)

    def _label(self, parent, text, size=14, bold=False, color=None, **kwargs):
        return ctk.CTkLabel(parent, text=text, text_color=color or '#edf4f8',
            font=ctk.CTkFont(size=size, weight='bold' if bold else 'normal'), **kwargs)

    def _build(self):
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.grid(row=0, column=0, sticky='ew', padx=24, pady=(24, 14))
        header.grid_columnconfigure(0, weight=1)
        self._label(header, 'M / GYÁRTÁSIRÁNYÍTÁS', 12, True, ACCENT).grid(row=0, column=0, sticky='w')
        self._label(header, 'Műszakvezető', 28, True).grid(row=1, column=0, sticky='w', pady=(8, 2))
        self._label(header, 'Termelési tervek, gépek és operátorok áttekintése.', color=MUTED).grid(row=2, column=0, sticky='w')
        self.refresh_button = self._button(header, 'Műszakadatok frissítése', self.refresh)
        self.refresh_button.grid(row=1, column=1, rowspan=2, sticky='e')
        self.controls.append(self.refresh_button)
        stats = ctk.CTkFrame(self, fg_color='transparent')
        stats.grid(row=1, column=0, sticky='ew', padx=24, pady=(0, 12))
        stats.grid_columnconfigure((0, 1, 2), weight=1, uniform='stats')
        self.stat_values = []
        self.stat_titles = []
        for col, title in enumerate(('AKTÍV TERV', 'NYILVÁNTARTOTT GÉP', 'OPERÁTOR')):
            card = ctk.CTkFrame(stats, fg_color=CARD, corner_radius=12)
            card.grid(row=0, column=col, sticky='ew', padx=(0 if col == 0 else 7, 0 if col == 2 else 7))
            title_label = self._label(card, title, 12, True, MUTED)
            title_label.pack(anchor='w', padx=18, pady=(12, 0))
            value_label = self._label(card, '—', 27, True, ACCENT)
            value_label.pack(anchor='w', padx=18, pady=(0, 12))
            self.stat_titles.append(title_label)
            self.stat_values.append(value_label)
        self.tabs = ctk.CTkTabview(self, fg_color=CARD, command=self._tab_changed,
            segmented_button_selected_color='#237c6c', segmented_button_selected_hover_color='#2a9681')
        self.tabs.grid(row=2, column=0, sticky='nsew', padx=24)
        plans = self.tabs.add('Termelési tervek')
        machines = self.tabs.add('Gépek')
        assignments = self.tabs.add('Operátorok hozzárendelése')
        forms = self.tabs.add(FORMS_TAB)
        self._build_plans(plans)
        self._build_machines(machines)
        self._build_assignments(assignments)
        self._build_forms(forms)
        self.status = self._label(self, 'Adatok betöltése…', color=MUTED, anchor='w', justify='left', wraplength=1050)
        self.status.grid(row=3, column=0, sticky='ew', padx=24, pady=(10, 18))

    def _build_forms(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)
        self.forms_count = self._label(parent, 'Gyártási lapok', 16, True)
        self.forms_count.grid(row=0, column=0, sticky='w', padx=10, pady=10)
        refresh = self._button(parent, 'Lapok frissítése', self.refresh_forms, secondary=True)
        refresh.grid(row=0, column=1, padx=10, pady=10)
        self.controls.append(refresh)
        self.forms_list = ctk.CTkScrollableFrame(parent, fg_color='transparent')
        self.forms_list.grid(row=1, column=0, columnspan=2, sticky='nsew')
        self.forms_list.grid_columnconfigure(0, weight=1)
        self._empty(self.forms_list, 'A lapok megnyitáskor töltődnek be.')

    def _render_forms(self):
        self._clear(self.forms_list)
        self.forms_count.configure(text=f'{len(self.form_rows)} gyártási lap')
        if not self.form_rows:
            self._empty(self.forms_list, 'Még nincs rögzített gyártási lap.')
            return
        for index, form in enumerate(self.form_rows):
            card = ctk.CTkFrame(self.forms_list, fg_color=ROW, corner_radius=10)
            card.grid(row=index, column=0, sticky='ew', padx=5, pady=(0, 10))
            self._label(card, f"Termék #{form['product_id']}", 17, True, anchor='w', wraplength=930).pack(
                anchor='w', padx=16, pady=(12, 2))
            self._label(card, f"Operátor · {form['operator_name']}    |    Gép · {form['machine_name']}",
                        anchor='w', justify='left', wraplength=930).pack(anchor='w', padx=16)
            self._label(card, f"{form['recorded_at']}    |    Gyártott: {form['product_amount']} db"
                        f"    |    Selejt: {form['waste_amount']} db", color=MUTED).pack(anchor='w', padx=16)
            self._label(card, f"Gyártási idő: {form['production_time']}    |    "
                        f"Állási idő: {form['stationary_time'] or '—'}", color=MUTED).pack(
                anchor='w', padx=16, pady=(0, 12))

    def _tab_changed(self):
        if self.tabs.get() == FORMS_TAB:
            self.refresh_forms()

    def refresh_forms(self):
        if self.busy or self.closed:
            return
        self._message('Gyártási lapok betöltése…')
        self._run('forms', self.api.get_forms)

    def _build_plans(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(2, weight=1)
        self._label(parent, 'Keresés terv, rendelés vagy termék száma alapján', color=MUTED).grid(row=0, column=0, sticky='w', padx=10, pady=(8, 4))
        entry = ctk.CTkEntry(parent, textvariable=self.plan_search, height=36)
        entry.grid(row=1, column=0, sticky='ew', padx=10, pady=(0, 10))
        menu = ctk.CTkOptionMenu(parent, values=['Aktív tervek', 'Összes terv'], variable=self.plan_scope,
            command=lambda _: self.refresh(), height=36, fg_color='#2b3c4e')
        menu.grid(row=1, column=1, padx=(0, 10), pady=(0, 10))
        self.controls.extend([entry, menu])
        self.plan_list = ctk.CTkScrollableFrame(parent, fg_color='transparent')
        self.plan_list.grid(row=2, column=0, columnspan=2, sticky='nsew')
        self.plan_list.grid_columnconfigure(0, weight=1)
        self._label(parent, 'Aktív nézet: mai és későbbi tervhatáridők. Az Összes terv nézet a korábbiakat is mutatja.',
                    12, color=MUTED, wraplength=950).grid(row=3, column=0, columnspan=2, sticky='w', padx=10, pady=8)

    def _build_machines(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(2, weight=1)
        self._label(parent, 'Keresés gépszám, típus vagy operátornév alapján', color=MUTED).grid(row=0, column=0, sticky='w', padx=10, pady=(8, 4))
        entry = ctk.CTkEntry(parent, textvariable=self.machine_search, height=36)
        entry.grid(row=1, column=0, sticky='ew', padx=10, pady=(0, 10))
        menu = ctk.CTkOptionMenu(parent, values=['Összes gép', 'Aktuális operátor nélkül'], variable=self.machine_scope,
            command=lambda _: self._render_machines(), height=36, fg_color='#2b3c4e', width=210)
        menu.grid(row=1, column=1, padx=(0, 10), pady=(0, 10))
        self.controls.extend([entry, menu])
        self.machine_list = ctk.CTkScrollableFrame(parent, fg_color='transparent')
        self.machine_list.grid(row=2, column=0, columnspan=2, sticky='nsew')
        self.machine_list.grid_columnconfigure(0, weight=1)
        self._label(parent, 'A „Jelenlegi operátor” jelölés az aktuális beosztást mutatja.',
                    12, color=MUTED, wraplength=950).grid(row=3, column=0, columnspan=2, sticky='w', padx=10, pady=8)

    def _build_assignments(self, parent):
        parent.grid_columnconfigure(1, weight=1)
        parent.grid_rowconfigure(0, weight=1)
        left = ctk.CTkFrame(parent, fg_color=BG, width=330, corner_radius=10)
        left.grid(row=0, column=0, sticky='nsew', padx=(10, 14), pady=10)
        left.grid_columnconfigure(0, weight=1)
        self._label(left, '1. Válassz gépet', 18, True).grid(row=0, column=0, sticky='w', padx=16, pady=(18, 10))
        self.machine_menu = ctk.CTkOptionMenu(left, variable=self.machine_choice, values=['Nincs gép'],
            command=self._machine_changed, height=40, width=320, fg_color='#2b3c4e')
        self.machine_menu.grid(row=1, column=0, sticky='ew', padx=16, pady=(0, 14))
        self.controls.append(self.machine_menu)
        self.assignment_hint = self._label(left, 'A gép operátorai itt jelennek meg.', color=MUTED,
                                          anchor='w', justify='left', wraplength=290)
        self.assignment_hint.grid(row=2, column=0, sticky='ew', padx=16)
        self._label(left, '2. Válassz egy operátort', 18, True).grid(row=3, column=0, sticky='w', padx=16, pady=(24, 8))
        self._label(left, 'Új választással az előző operátor felszabadul.\nÜres kijelöléssel a jelenlegi küldhető be újra.',
                    color=MUTED, justify='left').grid(row=4, column=0, sticky='w', padx=16)
        self.add_button = self._button(left, 'Beosztás beküldése', self.assign_selected)
        self.add_button.grid(row=5, column=0, sticky='ew', padx=16, pady=(24, 8))
        self.selection_label = self._label(left, 'Nincs kijelölt operátor.', color=MUTED)
        self.selection_label.grid(row=6, column=0, sticky='w', padx=16, pady=(0, 14))
        right = ctk.CTkFrame(parent, fg_color='transparent')
        right.grid(row=0, column=1, sticky='nsew', padx=(0, 10), pady=10)
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(2, weight=1)
        self._label(right, 'Operátorok keresése név vagy szám alapján', color=MUTED).grid(row=0, column=0, sticky='w', pady=(0, 6))
        search = ctk.CTkEntry(right, textvariable=self.operator_search, height=36)
        search.grid(row=1, column=0, sticky='ew', pady=(0, 10))
        self.controls.append(search)
        self.operator_list = ctk.CTkScrollableFrame(right, fg_color=BG)
        self.operator_list.grid(row=2, column=0, sticky='nsew')
        self.operator_list.grid_columnconfigure(0, weight=1)

    def _clear(self, frame):
        for widget in frame.winfo_children():
            widget.destroy()

    def _empty(self, frame, text):
        self._label(frame, text, 16, color=MUTED, wraplength=750).grid(row=0, column=0, padx=10, pady=35)

    def _schedule_render(self):
        if self._filter_id is not None:
            self.after_cancel(self._filter_id)
        self._filter_id = self.after(180, self._filtered_render)

    def _filtered_render(self):
        self._filter_id = None
        self._render()

    def _render(self):
        self._render_plans()
        self._render_machines()
        self._render_operators()
        for label, key in zip(self.stat_values, ['plans', 'machines', 'operators']):
            label.configure(text=str(len(self.data[key])) if self.loaded else '—')
        self.stat_titles[0].configure(text='ÖSSZES TERV' if self.loaded_scope == 'Összes terv' else 'AKTÍV TERV')

    def _render_plans(self):
        self._clear(self.plan_list)
        term = self.plan_search.get().strip().casefold()
        plans = [p for p in self.data['plans'] if term in
                 f"{p['plan_id']} {p.get('order_id', '')} {p.get('product_id', '')}".casefold()]
        if not plans:
            text = 'Nincs megjeleníthető terv.' if self.loaded else 'Előbb töltsd be az adatokat.'
            self._empty(self.plan_list, text)
        for index, plan in enumerate(plans):
            card = ctk.CTkFrame(self.plan_list, fg_color=ROW, corner_radius=10)
            card.grid(row=index, column=0, sticky='ew', padx=5, pady=(0, 10))
            card.grid_columnconfigure(0, weight=1)
            self._label(card, f"Terv #{plan['plan_id']}  ·  Rendelés #{plan.get('order_id', '—')}", 17, True).grid(row=0, column=0, sticky='w', padx=16, pady=(12, 4))
            priority = PRIORITIES.get(plan.get('priority'), 'Nincs megadva')
            self._label(card, priority, 13, color=ACCENT).grid(row=0, column=1, padx=16, pady=(12, 4))
            quantity = plan.get('quantity')
            self._label(card, f"Termék #{plan.get('product_id', '—')}  ·  {quantity if quantity is not None else '—'} db",
                        15).grid(row=1, column=0, sticky='w', padx=16)
            deadline = str(plan.get('deadline') or 'Nincs megadva')
            color = MUTED
            try:
                if date.fromisoformat(deadline[:10]) < date.today():
                    deadline += ' · Lejárt határidő'
                    color = '#ffab99'
            except ValueError:
                pass
            text = f'Határidő: {deadline}'
            if type(quantity) is int and isinstance(plan.get('manufacturing_seconds'), (int, float)):
                text += f"  ·  Elméleti idő: {quantity * plan['manufacturing_seconds'] / 3600:.1f} óra"
            self._label(card, text, 13, color=color).grid(row=2, column=0, columnspan=2, sticky='w', padx=16, pady=(2, 12))

    def _render_machines(self):
        self._clear(self.machine_list)
        self.machine_buttons = []
        term = self.machine_search.get().strip().casefold()
        index = 0
        for machine in self.data['machines']:
            mid = machine['machine_id']
            assigned = assignments_for(self.data, mid)
            if self.machine_scope.get() == 'Aktuális operátor nélkül' and any(a.get('is_current') for a in assigned):
                continue
            haystack = machine_label(machine) + ' ' + ' '.join(operator_name(a) for a in assigned)
            if term not in haystack.casefold():
                continue
            card = ctk.CTkFrame(self.machine_list, fg_color=ROW, corner_radius=10)
            card.grid(row=index, column=0, sticky='ew', padx=5, pady=(0, 10))
            card.grid_columnconfigure(0, weight=1)
            self._label(card, machine_label(machine), 17, True, wraplength=700, anchor='w').grid(row=0, column=0, sticky='w', padx=16, pady=(12, 4))
            button = self._button(card, 'Beosztás beküldése', lambda i=mid: self.choose_machine(i), secondary=True)
            button.grid(row=0, column=1, padx=16, pady=(12, 4))
            button.configure(state='disabled' if self.busy else 'normal')
            self.machine_buttons.append(button)
            if assigned:
                lines = [f"{operator_name(a)} (#{a['operator_id']}) · {'Jelenlegi operátor' if a.get('is_current') else 'Korábbi beosztás'} · {assignment_time(a.get('assigned_at'))}" for a in assigned]
            else:
                lines = ['Még nem rögzítettek ide beosztást.']
            self._label(card, '\n'.join(lines), color=MUTED, justify='left', anchor='w', wraplength=960).grid(row=1, column=0, columnspan=2, sticky='ew', padx=16, pady=(0, 14))
            index += 1
        if not index:
            self._empty(self.machine_list, 'Nincs a szűrésnek megfelelő gép.' if self.loaded else 'Előbb töltsd be az adatokat.')

    def _render_operators(self):
        self._clear(self.operator_list)
        mid = self.selected_machine
        latest = {a['operator_id']: a for a in self.data['assignments'] if a.get('is_current')}
        assigned = {oid: a for oid, a in latest.items() if a['machine_id'] == mid}
        self.pending.difference_update(assigned)
        term = self.operator_search.get().strip().casefold()
        index = 0
        for operator in self.data['operators']:
            oid = operator['operator_id']
            name = operator_name(operator)
            if term not in f'{name} {oid}'.casefold():
                continue
            row = ctk.CTkFrame(self.operator_list, fg_color=ROW, corner_radius=8)
            row.grid(row=index, column=0, sticky='ew', padx=5, pady=(0, 10))
            row.grid_columnconfigure(0, weight=1)
            variable = tk.BooleanVar(master=self, value=oid in self.pending or (oid in assigned and not self.pending))
            check = ctk.CTkCheckBox(row, text=f'{name}  ·  #{oid}', variable=variable, fg_color=ACCENT,
                hover_color='#28a98a', command=lambda i=oid, v=variable: self._toggle(i, v.get()),
                state='disabled' if self.busy or mid is None or oid in assigned else 'normal')
            check.configure(text_color=MUTED if oid in assigned else '#edf4f8')
            check.grid(row=0, column=0, sticky='w', padx=14, pady=(12, 4))
            if oid in assigned:
                text = 'A gép jelenlegi operátora\n' + assignment_time(assigned[oid].get('assigned_at'))
            else:
                previous = latest.get(oid)
                if previous:
                    text = f"Jelenlegi gépe: #{previous['machine_id']}\n" + assignment_time(previous.get('assigned_at'))
                elif any(a['operator_id'] == oid for a in self.data['assignments']):
                    text = 'Nincs aktuális gépe. Kijelöléssel ide küldhető be.'
                else:
                    text = 'Még nincs beküldött beosztása.'
            self._label(row, text, 12, color=MUTED, anchor='w', justify='left', wraplength=550).grid(row=1, column=0, sticky='ew', padx=14, pady=(0, 12))
            index += 1
        if not index:
            self._empty(self.operator_list, 'Nincs megjeleníthető operátor.')
        current = next(iter(assigned.values()), None)
        if mid is None:
            hint = 'Nincs kiválasztható gép.'
        else:
            hint = f'Gép #{mid}\n' + (operator_name(current) if current else 'Nincs aktuális operátor.')
        self.assignment_hint.configure(text=hint)
        self.machine_menu.configure(state='normal' if self.machine_choices and not self.busy else 'disabled')
        self._update_selection()

    def _toggle(self, oid, checked):
        if checked:
            self.pending.clear()
            self.pending.add(oid)
        else:
            self.pending.discard(oid)
        self._render_operators()

    def _update_selection(self):
        current = any(a.get('is_current') and a['machine_id'] == self.selected_machine
                      for a in self.data['assignments'])
        text = 'Új operátor kijelölve.' if self.pending else 'Nincs új kijelölés.'
        self.selection_label.configure(text=text)
        self.add_button.configure(text='Jelenlegi újraküldése' if current and not self.pending else 'Beosztás beküldése',
            state='normal' if (self.pending or current) and self.selected_machine is not None and not self.busy else 'disabled')

    def _machine_changed(self, label):
        self.selected_machine = self.machine_choices.get(label)
        self.pending.clear()
        self._render_operators()

    def choose_machine(self, mid):
        if self.busy:
            return
        self.selected_machine = mid
        self.pending.clear()
        for label, identifier in self.machine_choices.items():
            if identifier == mid:
                self.machine_choice.set(label)
                break
        self.tabs.set('Operátorok hozzárendelése')
        self._render_operators()

    def _update_machine_choices(self):
        self.machine_choices = {machine_label(m): m['machine_id'] for m in self.data['machines']}
        if self.selected_machine not in self.machine_choices.values():
            self.selected_machine = next(iter(self.machine_choices.values()), None)
            self.pending.clear()
        self.machine_menu.configure(values=list(self.machine_choices) or ['Nincs gép'])
        label = next((label for label, mid in self.machine_choices.items() if mid == self.selected_machine), 'Nincs gép')
        self.machine_choice.set(label)

    def _message(self, text, error=False):
        self.status.configure(text=text, text_color='#ffab99' if error else MUTED)

    def _run(self, kind, job):
        if self.busy or self.closed:
            return
        self.busy = True
        for widget in self.controls:
            widget.configure(state='disabled')
        self._render_machines()
        self._render_operators()
        def worker():
            try:
                self.results.put((kind, job(), None))
            except Exception as exc:
                self.results.put((kind, None, str(exc)))
        Thread(target=worker, daemon=True).start()

    def refresh(self):
        if self.busy or self.closed:
            return
        self._message('Listák betöltése…')
        include_all = self.plan_scope.get() == 'Összes terv'
        self._run('load', lambda: self.api.get_snapshot(include_all))

    def assign_selected(self):
        if self.busy or self.selected_machine is None:
            return
        mid, ids = self.selected_machine, sorted(self.pending)
        self._message('Beosztások beküldése…')
        self._run('assign', lambda: self.api.assign_operators(mid, ids))

    def _poll(self):
        if self.closed:
            return
        try:
            kind, result, error = self.results.get_nowait()
        except Empty:
            pass
        else:
            self.busy = False
            for widget in self.controls:
                widget.configure(state='normal')
            if error:
                if kind == 'forms':
                    self._message(error, True)
                else:
                    if self.loaded:
                        self.plan_scope.set(self.loaded_scope)
                    self._message(error + (' A korábban betöltött adatok láthatók.' if self.loaded else ''), True)
            elif kind == 'forms':
                self.form_rows = result
                self._render_forms()
                self._message(f'{len(result)} gyártási lap betöltve.')
            elif kind == 'load':
                self.data = result
                self.loaded = True
                self.loaded_scope = self.plan_scope.get()
                self.pending.intersection_update({o['operator_id'] for o in self.data['operators']})
                self._update_machine_choices()
                self._message(f'Listák frissítve: {datetime.now():%H:%M:%S}.')
            else:
                mid = result['machine_id']
                self.data['assignments'] = result['assignments']
                self.pending.clear()
                self._message(f"Sikeres mentés! Gép #{mid} · {result['created_count']} új bejegyzés. A korábbi beosztások megmaradtak.")
            self._render()
            if kind != 'forms' and self.tabs.get() == FORMS_TAB:
                self.refresh_forms()
        self._poll_id = self.after(70, self._poll)

    def destroy(self):
        self.closed = True
        for job in (self._poll_id, self._load_id, self._filter_id):
            if job is not None:
                self.after_cancel(job)
        super().destroy()


class ShiftLeaderApp(ctk.CTk):
    def __init__(self, base_url='http://127.0.0.1:5000'):
        super().__init__()
        self.title('Gyártásirányítás · Műszakvezető')
        self.geometry('1220x830')
        self.minsize(1100, 740)
        ShiftLeaderFrame(self, ShiftApi(base_url)).pack(fill='both', expand=True)


def main():
    parser = argparse.ArgumentParser(description='Műszakvezetői asztali alkalmazás')
    parser.add_argument('--api-url', default='http://127.0.0.1:5000')
    args = parser.parse_args()
    ctk.set_appearance_mode('dark')
    ctk.set_default_color_theme('green')
    ShiftLeaderApp(args.api_url).mainloop()


if __name__ == '__main__':
    main()
