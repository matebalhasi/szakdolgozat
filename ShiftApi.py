"""A műszakvezetői UI HTTP kliensrétege; nincs benne SQL vagy widget."""
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


class ApiError(Exception):
    """A felhasználónak megjeleníthető hiba."""


class ShiftApi:
    def __init__(self, base_url='http://127.0.0.1:5000', timeout=15):
        url = urlsplit(base_url)
        if url.scheme not in ('http', 'https') or not url.netloc or url.query or url.fragment:
            raise ValueError('Érvényes HTTP/HTTPS backendcímet adj meg.')
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

    def _request(self, path, payload=None):
        body = None if payload is None else json.dumps(payload).encode('utf-8')
        req = Request(self.base_url + path, data=body,
                      headers={'Accept': 'application/json', 'Content-Type': 'application/json'})
        try:
            with urlopen(req, timeout=self.timeout) as response:
                result = json.loads(response.read().decode('utf-8'))
        except HTTPError as exc:
            try:
                detail = json.loads(exc.read().decode('utf-8'))
                message = detail.get('message') if isinstance(detail, dict) else None
            except (ValueError, UnicodeError):
                message = None
            raise ApiError(message or f'Szerverhiba (HTTP {exc.code}).') from exc
        except (URLError, TimeoutError, OSError) as exc:
            message = 'Nem érhető el a backend. Ellenőrizd, hogy fut-e és jó-e a címe.'
            if payload is not None:
                message += ' A mentés eredménye bizonytalan: újraküldés előtt ellenőrizd a beosztásokat.'
            raise ApiError(message) from exc
        except (ValueError, UnicodeError) as exc:
            raise ApiError('A backend érvénytelen JSON-választ küldött.') from exc
        if not isinstance(result, dict):
            raise ApiError('A backend válaszának formátuma hibás.')
        return result

    def get_forms(self):
        rows = self._request('/shift/forms').get('data')
        fields = {'operator_name', 'machine_name', 'recorded_at',
                  'product_amount', 'waste_amount', 'production_time', 'stationary_time'}
        if not isinstance(rows, list) or any(
                not isinstance(row, dict) or type(row.get('form_id')) is not int
                or type(row.get('product_id')) is not int
                or not fields.issubset(row) for row in rows):
            raise ApiError('A szerver hibás gyártási laplistát küldött.')
        return rows

    def get_snapshot(self, include_all=False):
        result = self._request('/shift/snapshot?include_all=' + ('1' if include_all else '0'))
        data = result.get('data')
        required = {'plans': 'plan_id', 'machines': 'machine_id',
                    'operators': 'operator_id', 'assignments': 'operator_id'}
        if not isinstance(data, dict):
            raise ApiError('A szerver hibás adatcsomagot küldött.')
        for key, id_key in required.items():
            if not isinstance(data.get(key), list) or any(
                    not isinstance(row, dict) or type(row.get(id_key)) is not int
                    for row in data[key]):
                raise ApiError('A szerver hibás listát küldött: ' + key)
        if any(type(row.get('machine_id')) is not int or type(row.get('assignment_id')) is not int
               or type(row.get('is_current')) is not bool for row in data['assignments']):
            raise ApiError('Hibás gépazonosító a hozzárendelésekben.')
        return data

    def assign_operators(self, machine_id, operator_ids):
        result = self._request('/shift/assignments',
                               {'machine_id': machine_id, 'operator_ids': operator_ids})
        rows = result.get('assignments')
        if (result.get('machine_id') != machine_id
                or type(result.get('created_count')) is not int
                or result.get('assignments_scope') != 'all'
                or not isinstance(rows, list)
                or any(not isinstance(row, dict) or type(row.get('machine_id')) is not int
                       or type(row.get('operator_id')) is not int or type(row.get('assignment_id')) is not int
                       or type(row.get('is_current')) is not bool for row in rows)):
            raise ApiError('A mentés után hibás válasz érkezett. Frissítsd a listát, és ellenőrizd a beosztást.')
        return result
