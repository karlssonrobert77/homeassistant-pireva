# Pireva Sophämtning (Home Assistant custom integration)

Home Assistant-komponent som hämtar tömningsschema från Pireva.

## Funktioner
- Daglig hämtning från https://www.pireva.se/tomningsschema/{address}/
- Ett enda adressfält (format: `väg-nummer`, t.ex. `storgatan-1`)
- Cache per adress och säkra async-uppdateringar
- Extra info-rader (info1, info2, …) från sidan
- Översättningar (sv/en) för config flow och sensor

## Installation
1. Kopiera mappen `pireva` till din Home Assistant-katalog `custom_components/`.
2. Starta om Home Assistant.
3. Lägg till integrationen via UI och ange adress-slug (t.ex. `storgatan-1`).

## Licens
MIT (se LICENSE)
