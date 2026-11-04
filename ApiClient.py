"""Az asztali UI HTTP kliensrétege; nincs benne SQL vagy widget."""
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


class ApiError(Exception):
    """A felhasználónak megjeleníthető hiba."""


class ApiClient:
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
                message += ' A mentés eredménye bizonytalan: újraküldés előtt ellenőrizd a rendeléseket.'
            raise ApiError(message) from exc
        except (ValueError, UnicodeError) as exc:
            raise ApiError('A backend érvénytelen JSON-választ küldött.') from exc
        if not isinstance(result, dict):
            raise ApiError('A backend válaszának formátuma hibás.')
        return result

    def get_products(self):
        result = self._request('/products')
        rows = result.get('data')
        if not isinstance(rows, list):
            raise ApiError('A backend nem terméklistát küldött.')
        seen = set()
        for row in rows:
            if (not isinstance(row, dict) or type(row.get('product_id')) is not int
                    or row['product_id'] <= 0 or row['product_id'] in seen
                    or type(row.get('manufacturing_seconds')) not in (int, float)
                    or row['manufacturing_seconds'] < 0):
                raise ApiError('A terméklista hibás adatokat tartalmaz.')
            seen.add(row['product_id'])
        return rows

    def create_order(self, payload):
        result = self._request('/production-orders', payload)
        if type(result.get('order_id')) is not int:
            raise ApiError('Hiányzik a rendelésazonosító. Újraküldés előtt ellenőrizd a rendeléseket.')
        return result['order_id']

    def get_active_orders(self):
        result = self._request('/active-orders')
        rows = result.get('data')
        if not isinstance(rows, list) or any(
                not isinstance(row, dict) or row.get('order_id') is None for row in rows):
            raise ApiError('A backend hibás rendeléslistát küldött.')
        return rows
