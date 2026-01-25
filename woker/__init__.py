import logging
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import json

# Use the correct constant names from const.py
try:
    from ..const import DOMAIN
except ImportError:
    # Direktkörning utanför HA
    from const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class HttpWorker:
    def __init__(self):
        # Per-adress cache: key = "street-house"
        self._data = {}

    @property
    def data(self):
        return self._data

    def extract_dates(self, text):
        y = datetime.today().strftime("%Y")
        
        # Regex för att matcha "dag månad" (t.ex. "27 januari")
        date_pattern = r"(\d{1,2})\s+(\w+)"
        matches = re.findall(date_pattern, text)

        # Ordbok för att konvertera svenska månadnamn till nummer
        months_sv = {
            'januari': 1, 'februari': 2, 'mars': 3, 'april': 4,
            'maj': 5, 'juni': 6, 'juli': 7, 'augusti': 8,
            'september': 9, 'oktober': 10, 'november': 11, 'december': 12
        }

        for day_str, month_str in matches:
            month_lower = month_str.lower()
            if month_lower in months_sv:
                try:
                    day = int(day_str)
                    month = months_sv[month_lower]
                    # Formatera som YYYY-MM-DD
                    return f"{y}-{month:02d}-{day:02d}"
                except (ValueError, KeyError):
                    pass
        
        return ''

    def _fetch_data(self, url):
        tömningsdagar_per_månad = {
            "nästa tömning": [],
            "januari": [],
            "februari": [],
            "mars": [],
            "april": [],
            "maj": [],
            "juni": [],
            "juli": [],
            "augusti": [],
            "september": [],
            "oktober": [],
            "november": [],
            "december": []
        }

        try:
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                return f"Kunde inte hämta schemat. HTTP {response.status_code}"
            soup = BeautifulSoup(response.content, 'html.parser')

            # Hämta informationsrader nära huvudsektionen (p-taggar inom den primära content-containern)
            info_texts = []
            container = soup.select_one("div.flex-1.flex.flex-col.justify-center.relative.z-10")
            if container:
                for p in container.find_all("p"):
                    s = p.get_text(strip=True)
                    if s:
                        info_texts.append(s)
            # Fallback: om inget hittades, ta alla p-taggar med textklasser body-*
            if not info_texts:
                for p in soup.find_all("p"):
                    cls = p.get("class", [])
                    if any(c.startswith("body-") for c in cls):
                        s = p.get_text(strip=True)
                        if s:
                            info_texts.append(s)
            # Ta bort dubletter men behåll ordning
            seen = set()
            info_texts_unique = []
            for s in info_texts:
                if s not in seen:
                    seen.add(s)
                    info_texts_unique.append(s)
            
            # Sök efter alla tabeller
            tables = soup.find_all('table')
            all_dates = []  # Spara alla tömningar för att hitta nästa
            
            for table in tables:
                # Hämta månad från thead
                thead = table.find('thead')
                if not thead:
                    continue
                    
                månad_text = thead.get_text(strip=True).lower()
                # Normalera månadnamnet
                månad = None
                for m in ["januari", "februari", "mars", "april", "maj", "juni",
                         "juli", "augusti", "september", "oktober", "november", "december"]:
                    if m in månad_text:
                        månad = m
                        break
                
                if not månad:
                    continue
                
                # Hämta rader från tbody
                tbody = table.find('tbody')
                if not tbody:
                    continue
                
                rows = tbody.find_all('tr')
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        typ = cells[0].get_text(strip=True)
                        datum_text = cells[1].get_text(strip=True)
                        
                        # Extrahera datum från texten (t.ex. "Tisdag 27 januari")
                        d = self.extract_dates(datum_text)
                        
                        if d:
                            entry = {"typ": typ, "datum": d}
                            tömningsdagar_per_månad[månad].append(entry)
                            all_dates.append(entry)
            
            # Hitta nästa tömning (första datum som är idag eller senare)
            today = datetime.now().strftime("%Y-%m-%d")
            all_dates_sorted = sorted(all_dates, key=lambda x: x['datum'])
            
            for entry in all_dates_sorted:
                if entry['datum'] >= today:
                    tömningsdagar_per_månad["nästa tömning"].append(entry)
                    break  # Bara ta den första kommande tömningen
            
            # Konvertera dictionary till JSON-format
            tömningsdagar_per_månad["information"] = info_texts_unique

            json_data = json.dumps(tömningsdagar_per_månad,
                                indent=2,
                                ensure_ascii=False)

            return (json_data)
        except Exception as e:
            return f"Kunde inte hämta schemat. Felmeddelande: {str(e)}"



    def _handle_pn_data(self, data, address, url):
        key = address.lower().replace(" ", "")
        try:
            self._data[key] = {
                'last_update': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'address': address,
                'url': url,
                'json': data
            }
        except Exception as error:
            _LOGGER.error(f"Process data failed (PN): {error}")
            self._data[key] = {
                'last_update': None,
                'address': address,
                'url': url,
                'json': str(error)
            }

    def fetch(self, address):
        # Ny URL-format: https://www.pireva.se/tomningsschema/{address}/
        # adress är direkt från config, e.g. "vag-nr"
        address = address.strip().lower().replace(" ", "")
        url = f'https://www.pireva.se/tomningsschema/{address}/'
        data = self._fetch_data(url)
        #data = None
        self._handle_pn_data(data, address, url)