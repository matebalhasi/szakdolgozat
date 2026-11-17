"""Egyszerű CustomTkinter operátori képernyő a meglévő /submit-form API-hoz.

Telepítés: python -m pip install customtkinter
Indítás: python frontend/Operator_UI.py
Beillesztés meglévő CTk ablakba: OperatorFrame(parent).pack(fill='both', expand=True)
A backend és az SQL fájlok nem változnak.
"""
from datetime import datetime
from queue import Empty, Queue
from threading import Thread
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import argparse
import json
import tkinter as tk
import customtkinter as ctk

API_URL = 'http://127.0.0.1:5000/submit-form'
BG, CARD, INPUT = '#101923', '#192633', '#223344'
ACCENT, MUTED, ERROR = '#35c4a0', '#aebdcb', '#ffad9a'
MAX_INT = 2147483647
MAX_HOURS = 838  # MySQL TIME felső határa 838:59:59.
FIELD_NAMES = {
    'operator_id': 'Operátor száma', 'machine_id': 'Gép száma',
    'product_id': 'Termék száma', 'product_amount': 'Gyártott darab',
    'waste_amount': 'Selejt darab',
    'production_hours': 'Gyártási idő (óra)', 'production_minutes': 'Gyártási idő (perc)',
    'stationary_hours': 'Állási idő (óra)', 'stationary_minutes': 'Állási idő (perc)',
}


class FieldError(ValueError):
    def __init__(self, field, message):
        super().__init__(message)
        self.field = field


def integer_field(values, field, minimum=0, maximum=MAX_INT):
    raw = str(values.get(field, '')).strip()
    if not raw.isascii() or not raw.isdigit():
        raise FieldError(field, f'{FIELD_NAMES[field]}: egész számot írj be.')
    # A hosszú bemenetet int() előtt kezeljük, a vezető nullák megengedettek.
    digits = raw.lstrip('0') or '0'
    if len(digits) > len(str(maximum)):
        raise FieldError(field, f'{FIELD_NAMES[field]}: a legnagyobb érték {maximum}.')
    number = int(digits)
    if not minimum <= number <= maximum:
        if minimum == 1 and number == 0:
            raise FieldError(field, f'{FIELD_NAMES[field]}: 0-nál nagyobb számot adj meg.')
        raise FieldError(field, f'{FIELD_NAMES[field]}: {minimum} és {maximum} közötti számot adj meg.')
    return number


def build_payload(values, now=None):
    """UI-tól független ellenőrzés és az eredeti backend által várt formátum."""
    payload = {key: integer_field(values, key, minimum=1)
               for key in ('operator_id', 'machine_id', 'product_id')}
    for key in ('product_amount', 'waste_amount'):
        payload[key] = integer_field(values, key)
    for duration in ('production', 'stationary'):
        hour_key, minute_key = f'{duration}_hours', f'{duration}_minutes'
        hour_text = values[hour_key].strip()
        minute_text = values[minute_key].strip()
        if duration == 'production' and not (hour_text or minute_text):
            raise FieldError(hour_key, 'Add meg a gyártási időt órában vagy percben.')
        hours = integer_field({hour_key: hour_text or '0'}, hour_key, maximum=MAX_HOURS)
        minutes = integer_field({minute_key: minute_text or '0'}, minute_key, maximum=59)
        payload[f'{duration}_time'] = f'{hours:02d}:{minutes:02d}:00'
    payload['timestamp'] = (now or datetime.now()).strftime('%Y-%m-%d %H:%M:%S')
    return payload


class SaveError(Exception):
    def __init__(self, message, uncertain=False):
        super().__init__(message)
        self.uncertain = uncertain


class OperatorApi:
    """A hálózati rész nem fér hozzá a felület widgetjeihez."""
    def __init__(self, url=API_URL, timeout=15):
        self.url, self.timeout = url, timeout

    def save(self, payload):
        req = Request(self.url, data=json.dumps(payload).encode('utf-8'),
                      headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
                      method='POST')
        try:
            with urlopen(req, timeout=self.timeout) as response:
                status = response.status
                # A kapott backendnél a 201 jelenti a sikeresen végrehajtott commitot.
                if status != 201:
                    raise SaveError('Nem egyértelmű a mentés eredménye.', uncertain=True)
        except HTTPError as exc:
            if exc.code == 400:
                message = 'Hibás adatok. Ellenőrizd a beírt számokat.'
            elif exc.code == 503:
                message = 'Az adatbázis nem érhető el. Szólj a műszakvezetőnek.'
            elif exc.code == 404:
                message = 'A mentési cím nem található. Szólj a rendszergazdának.'
            elif exc.code in (401, 403):
                message = 'Nincs jogosultság a mentéshez. Szólj a műszakvezetőnek.'
            else:
                message = 'A szerver hibát jelzett. Újraküldés előtt ellenőriztesd a mentést.'
            try:
                with exc:
                    response = json.loads(exc.read(8192))
            except (OSError, ValueError):
                response = None
            message += f' (HTTP {exc.code})'
            if isinstance(response, dict):
                detail = response.get('error') or response.get('message')
                if isinstance(detail, str) and detail.strip():
                    message += '\n' + detail.strip()[:400]
            raise SaveError(message, uncertain=exc.code >= 500 and exc.code != 503) from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise SaveError('Nincs kapcsolat a szerverrel. A mentés eredménye nem ismert.',
                            uncertain=True) from exc


class OperatorFrame(ctk.CTkFrame):
    """Egy képernyő, nagy mezők és egyetlen mentési művelet."""
    def __init__(self, master, api=None, operator_id='', machine_id='', **kwargs):
        super().__init__(master, fg_color=BG, corner_radius=0, **kwargs)
        self.api = api or OperatorApi()
        self.busy = False
        self.closed = False
        self.uncertain = False
        self.results = Queue()
        self.controls = []
        self.entries = {}
        self.previous_payload = None
        defaults = {'operator_id': str(operator_id), 'machine_id': str(machine_id),
                    'product_id': '', 'product_amount': '', 'waste_amount': '0',
                    'production_hours': '', 'production_minutes': '',
                    'stationary_hours': '0', 'stationary_minutes': '0'}
        self.values = {k: tk.StringVar(master=self, value=v) for k, v in defaults.items()}
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build()
        self._poll_id = self.after(80, self._poll)
        self._focus_id = self.after(200, self._focus_first)

    def _label(self, parent, text, size=16, bold=False, color=None, **kwargs):
        return ctk.CTkLabel(parent, text=text, text_color=color or '#f2f7fa',
                            font=ctk.CTkFont(size=size, weight='bold' if bold else 'normal'), **kwargs)

    def _build(self):
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.grid(row=0, column=0, sticky='ew', padx=24, pady=(18, 10))
        self._label(header, 'M / GYÁRTÁSIRÁNYÍTÁS', 12, True, ACCENT).pack(anchor='w')
        self._label(header, 'Termelés rögzítése', 29, True).pack(anchor='w', pady=(4, 0))
        self._label(header, 'Töltsd ki az adatokat, majd nyomd meg a Mentés gombot.', color=MUTED).pack(anchor='w')

        body = ctk.CTkScrollableFrame(self, fg_color='transparent')
        body.grid(row=1, column=0, sticky='nsew', padx=18)
        body.grid_columnconfigure((0, 1), weight=1, uniform='cards')

        identity = self._card(body, '1. Operátor, gép és termék')
        identity.grid(row=0, column=0, columnspan=2, sticky='ew', padx=6, pady=(0, 12))
        identity.grid_columnconfigure((0, 1, 2), weight=1, uniform='identity')
        for column, key in enumerate(('operator_id', 'machine_id', 'product_id')):
            field = self._field(identity, key)
            field.grid(row=1, column=column, sticky='ew', padx=14, pady=(0, 16))

        counts = self._card(body, '2. Darabszámok')
        counts.grid(row=1, column=0, sticky='nsew', padx=6, pady=(0, 8))
        counts.grid_columnconfigure(0, weight=1)
        for row, key in enumerate(('product_amount', 'waste_amount'), 1):
            field = self._field(counts, key, 'db', adjust=True)
            field.grid(row=row, column=0, sticky='ew', padx=16, pady=(0, 14))

        times = self._card(body, '3. Időtartamok')
        times.grid(row=1, column=1, sticky='nsew', padx=6, pady=(0, 8))
        times.grid_columnconfigure(0, weight=1)
        for row, (duration, label) in enumerate(
                (('production', 'Gyártási idő'), ('stationary', 'Állási idő')), 1):
            field = ctk.CTkFrame(times, fg_color='transparent')
            field.grid(row=row, column=0, sticky='ew', padx=16, pady=(0, 14))
            field.grid_columnconfigure((0, 1), weight=1, uniform='duration')
            self._label(field, label, 16, bold=True).grid(row=0, column=0, columnspan=2, sticky='w')
            self._field(field, f'{duration}_hours', label='Óra').grid(
                row=1, column=0, sticky='ew', padx=(0, 6))
            self._field(field, f'{duration}_minutes', label='Perc').grid(
                row=1, column=1, sticky='ew', padx=(6, 0))
        self._label(body, 'A perc mezőbe 0 és 59 közötti számot írj. Az időpont automatikus.',
                    14, color=MUTED, wraplength=850, justify='left').grid(row=2, column=0, columnspan=2, sticky='w', padx=10, pady=(0, 10))

        footer = ctk.CTkFrame(self, fg_color='transparent')
        footer.grid(row=2, column=0, sticky='ew', padx=24, pady=(8, 20))
        footer.grid_columnconfigure(0, weight=1)
        self.status_box = ctk.CTkFrame(footer, fg_color=CARD, corner_radius=10)
        self.status_box.grid(row=0, column=0, sticky='ew', pady=(0, 12))
        self.status_label = self._label(self.status_box, 'Töltsd ki a mezőket. Ha nem volt selejt vagy állás, hagyd 0-n.',
                                        16, color=MUTED, wraplength=850, justify='left', anchor='w')
        self.status_label.pack(fill='x', padx=16, pady=12)
        self.check_button = ctk.CTkButton(footer, text='Ellenőriztem a mentést – újra szerkesztem',
            height=44, fg_color='#775021', hover_color='#91642c', font=ctk.CTkFont(size=16, weight='bold'),
            command=self.release_uncertain)
        self.save_button = ctk.CTkButton(footer, text='Mentés', height=60,
            fg_color=ACCENT, hover_color='#2ba98b', text_color='#102922',
            font=ctk.CTkFont(size=23, weight='bold'), command=self.submit)
        self.save_button.grid(row=2, column=0, sticky='ew')

    def _card(self, parent, title):
        card = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=12)
        self._label(card, title, 19, True).grid(row=0, column=0, columnspan=3,
                                              sticky='w', padx=16, pady=(14, 12))
        return card

    def _field(self, parent, key, unit='', adjust=False, label=None):
        frame = ctk.CTkFrame(parent, fg_color='transparent')
        frame.grid_columnconfigure(1 if adjust else 0, weight=1)
        self._label(frame, label or FIELD_NAMES[key], 16, color=MUTED).grid(row=0, column=0, columnspan=4, sticky='w', pady=(0, 6))
        entry = ctk.CTkEntry(frame, textvariable=self.values[key], height=48,
                            width=100, fg_color=INPUT, border_color='#425569',
                            font=ctk.CTkFont(size=23), justify='center')
        entry.grid(row=1, column=1 if adjust else 0, sticky='ew', padx=6 if adjust else 0)
        self.entries[key] = entry
        self.controls.append(entry)
        entry.bind('<FocusIn>', lambda event: event.widget.after_idle(lambda: self._select_text(entry)))
        # A beírt hiba legyen érthető: nem nyelünk el csendben billentyűket.
        if adjust:
            for col, delta, label in [(0, -1, '−'), (2, 1, '+')]:
                button = ctk.CTkButton(frame, text=label, width=46, height=48,
                    fg_color='#30485d', hover_color='#42627a', font=ctk.CTkFont(size=25, weight='bold'),
                    command=lambda k=key, d=delta: self.adjust(k, d))
                button.grid(row=1, column=col)
                self.controls.append(button)
        if unit:
            self._label(frame, unit, 16, color=MUTED).grid(row=1, column=3, padx=(10, 0))
        return frame

    def _select_text(self, entry):
        if not self.closed and entry.winfo_exists():
            entry.select_range(0, 'end')

    def _focus_first(self):
        for key, variable in self.values.items():
            if not variable.get():
                self.entries[key].focus_set()
                break

    def adjust(self, key, delta):
        if self.busy or self.uncertain:
            return
        try:
            number = integer_field({key: self.values[key].get() or '0'}, key)
        except FieldError as exc:
            self._field_error(exc)
            return
        self.values[key].set(str(max(0, min(MAX_INT, number + delta))))

    def _message(self, text, kind='info'):
        colors = {'info': (CARD, MUTED), 'error': ('#3e292c', ERROR),
                  'success': ('#143c34', '#8ae5c6')}
        bg, fg = colors[kind]
        self.status_box.configure(fg_color=bg)
        self.status_label.configure(text=text, text_color=fg)

    def _field_error(self, exc):
        entry = self.entries[exc.field]
        entry.configure(border_color=ERROR, border_width=2)
        entry.focus_set()
        self._message(str(exc), 'error')

    def _enable_inputs(self, enabled):
        for control in self.controls:
            control.configure(state='normal' if enabled else 'disabled')
        self.save_button.configure(state='normal' if enabled else 'disabled')

    def submit(self):
        if self.busy or self.uncertain:
            return
        for entry in self.entries.values():
            entry.configure(border_color='#425569')
        try:
            payload = build_payload({key: var.get() for key, var in self.values.items()})
        except FieldError as exc:
            self._field_error(exc)
            return
        self.previous_payload = payload
        self.busy = True
        self._enable_inputs(False)
        self.save_button.configure(text='Mentés folyamatban…')
        self._message('Kérlek, várj. Az adatok mentése folyamatban van.')
        def worker():
            try:
                self.api.save(payload)
                self.results.put(None)
            except SaveError as exc:
                self.results.put(exc)
            except Exception:
                self.results.put(SaveError('Váratlan hiba történt. Ellenőriztesd a mentés eredményét.', uncertain=True))
        Thread(target=worker, daemon=True).start()

    def _poll(self):
        if self.closed:
            return
        try:
            result = self.results.get_nowait()
        except Empty:
            pass
        else:
            self.busy = False
            self.uncertain = bool(result and result.uncertain)
            self._enable_inputs(not self.uncertain)
            self.save_button.configure(text='Mentés')
            if result is not None:
                text = str(result)
                if self.uncertain:
                    text += '\nNe küldd el újra. Előbb kérd meg a műszakvezetőt, hogy ellenőrizze, el lett-e mentve.'
                    self.check_button.grid(row=1, column=0, sticky='ew', pady=(0, 12))
                self._message(text, 'error')
            else:
                saved = self.previous_payload
                self._message(f"Sikeres mentés!  Termék #{saved['product_id']} · {saved['product_amount']} db gyártott · {saved['waste_amount']} db selejt\nÚj bejegyzéshez add meg a következő darabszámokat és időket.", 'success')
                # A munkakörnyezet megmarad, csak az adott bejegyzés adatai ürülnek.
                for key in ('product_amount', 'production_hours', 'production_minutes'):
                    self.values[key].set('')
                for key in ('waste_amount', 'stationary_hours', 'stationary_minutes'):
                    self.values[key].set('0')
                self.entries['product_amount'].focus_set()
        self._poll_id = self.after(80, self._poll)

    def release_uncertain(self):
        """Csak emberi ellenőrzés után enged újraküldést; nincs automatikus retry."""
        self.uncertain = False
        self.check_button.grid_remove()
        self._enable_inputs(True)
        self._message('Ha a bejegyzés már mentve van, ne küldd el ismét. Új bejegyzéshez írd át az adatokat.')

    def destroy(self):
        self.closed = True
        self.after_cancel(self._poll_id)
        self.after_cancel(self._focus_id)
        super().destroy()


class OperatorApp(ctk.CTk):
    def __init__(self, api_url=API_URL, operator_id='', machine_id=''):
        super().__init__()
        self.title('Operátor · Termelés rögzítése')
        self.geometry('1000x800')
        self.minsize(900, 650)
        self.screen = OperatorFrame(self, OperatorApi(api_url), operator_id, machine_id)
        self.screen.pack(fill='both', expand=True)
        self.protocol('WM_DELETE_WINDOW', self._close)

    def _close(self):
        if self.screen.busy:
            self.screen._message('A mentés még folyamatban van. Várd meg az eredményét.')
            return
        self.destroy()


def main():
    parser = argparse.ArgumentParser(description='Operátori termelésrögzítő')
    parser.add_argument('--api-url', default=API_URL, help='A /submit-form végpont teljes címe')
    parser.add_argument('--operator-id', default='', help='Előre kitöltött operátorszám')
    parser.add_argument('--machine-id', default='', help='Előre kitöltött gépszám')
    args = parser.parse_args()
    ctk.set_appearance_mode('dark')
    ctk.set_default_color_theme('green')
    OperatorApp(args.api_url, args.operator_id, args.machine_id).mainloop()


if __name__ == '__main__':
    main()
