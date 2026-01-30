# Sushi Ulov - Google Merchant Center Feed Generator

Automatyczny generator pliku produktowego (XML Feed) dla Google Merchant Center, stworzony dla restauracji Sushi Ulov.

Projekt działa w kontenerze Docker, codziennie pobiera aktualne menu ze strony restauracji, przetwarza je i wystawia jako plik XML gotowy do pobrania przez roboty Google.

## Funkcjonalności

- **Automatyzacja:** Skrypt uruchamia się automatycznie co 24 godziny.
- **Inteligentny Parsing:** Wykorzystuje dane JSON (`__NEXT_DATA__`) zaszyte w strukturze strony (Next.js), co zapewnia 100% dokładność cen i nazw.
- **Mapowanie Kategorii:** Automatycznie przypisuje odpowiednie ID kategorii Google.
- **Formatowanie:**
  - Korekta cen (zamiana groszy na złotówki).
  - Budowanie poprawnych linków URL do produktów.
  - Obsługa statusów dostępności (`in stock` / `out of stock`).
- **Hosting:** Wbudowany serwer Nginx do serwowania wygenerowanego pliku XML.

## Technologie

- **Python 3.9** (Logika pobierania i przetwarzania danych)
- **BeautifulSoup4 & JSON** (Ekstrakcja danych)
- **Docker & Docker Compose** (Konteneryzacja i orkiestracja)
- **Nginx** (Serwer WWW do udostępniania pliku)

## Wymagania

- Zainstalowany Docker oraz Docker Compose na serwerze.

## Instalacja i Uruchomienie

1. **Sklonuj repozytorium:**
   ```bash
   git clone https://github.com/VlodekH/SushUlovGMC.git