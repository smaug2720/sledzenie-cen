import os
import json
import time
import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re

# ================= KONFIGURACJA =================
EMAIL_NADAWCY = os.environ["EMAIL_NADAWCY"]  # Wpisz swój email
HASLO_APLIKACJI = os.environ["HASLO_APLIKACJI"] # Wpisz wygenerowane hasło aplikacji
EMAIL_ODBIORCY = os.environ["EMAIL_NADAWCY"] # Na jaki email wysłać powiadomienie
# ================================================

def pobierz_cene(url):
    """Pobiera i parsuje cenę, symulując pełną wizytę w przeglądarce."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.amazon.pl/",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin"
    }
    
    try:
        session = requests.Session()
        
        # Krok 1: Pobranie ciasteczek ze strony głównej Amazona, aby ominąć filtr botów
        if "amazon" in url:
            session.get("https://www.amazon.pl/", headers=headers, timeout=10)
            time.sleep(2)
            
        # Krok 2: Pobranie właściwej strony produktu
        response = session.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        
        cena_str = None
        
        if "allegro.pl" in url:
            meta_price = soup.find("meta", property="product:price:amount")
            if meta_price:
                cena_str = meta_price["content"]
                
        elif "amazon" in url:
            cena_element = soup.select_one('.a-price .a-offscreen')
            if cena_element:
                cena_str = cena_element.text.strip()
            else:
                selektory = [
                    soup.find("span", class_="a-price-whole"),
                    soup.find("span", class_="a-color-price"),
                    soup.find("span", id="price")
                ]
                for element in selektory:
                    if element and element.text.strip():
                        tekst_elementu = element.text.strip()
                        if any(char.isdigit() for char in tekst_elementu):
                            cena_str = tekst_elementu
                            if "a-price-whole" in element.get('class', []):
                                fraction = soup.find("span", class_="a-price-fraction")
                                if fraction:
                                    cena_str = f"{cena_str}{fraction.text.strip()}"
                            break
        
        if not cena_str:
            tytul = soup.find("title").text.strip() if soup.find("title") else "Brak tytułu"
            print(f"Nie udało się odczytać ceny. Zamiast produktu, skrypt wczytał stronę o tytule: '{tytul}'")
            return None
            
        cena_str = re.sub(r'[^\d,\.]', '', cena_str).replace(',', '.')
        if cena_str.count('.') > 1:
            cena_str = cena_str.replace('.', '', 1)
            
        return float(cena_str)
        
    except Exception as e:
        print(f"Błąd podczas pobierania strony: {e}")
        return None

def wyslij_powiadomienie(url, aktualna_cena, docelowa_cena):
    """Wysyła e-mail z powiadomieniem."""
    temat = "🔥 Spadek ceny produktu!"
    tresc = f"""
    Cześć!
    
    Cena obserwowanego przez Ciebie produktu spadła!
    Aktualna cena: {aktualna_cena} zł
    Twój próg cenowy: {docelowa_cena} zł
    
    Link do produktu: {url}
    
    Kupuj zanim zniknie! :)
    """
    
    msg = MIMEMultipart()
    msg['From'] = EMAIL_NADAWCY
    msg['To'] = EMAIL_ODBIORCY
    msg['Subject'] = temat
    msg.attach(MIMEText(tresc, 'plain'))
    
    try:
        # Konfiguracja serwera SMTP dla Gmail (jeśli masz inną pocztę, zmień serwer i port)
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_NADAWCY, HASLO_APLIKACJI)
        text = msg.as_string()
        server.sendmail(EMAIL_NADAWCY, EMAIL_ODBIORCY, text)
        server.quit()
        print("✅ E-mail z powiadomieniem został wysłany!")
    except Exception as e:
        print(f"❌ Błąd podczas wysyłania e-maila: {e}")

def sprawdz_oferte(url, docelowa_cena):
    print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Sprawdzam cenę...")
    aktualna_cena = pobierz_cene(url)
    
    if aktualna_cena is not None:
        print(f"Aktualna cena to: {aktualna_cena} zł (Twój próg: {docelowa_cena} zł)")
        if aktualna_cena <= docelowa_cena:
            print("Cena jest poniżej progu! Wysyłam powiadomienie.")
            wyslij_powiadomienie(url, aktualna_cena, docelowa_cena)
            # Jeśli chcesz, żeby po wysłaniu e-maila program przestał działać, odkomentuj poniższą linię:
            # return schedule.CancelJob 
    else:
        print("Nie udało się pobrać ceny w tej próbie.")

def main():
    print("=== PRYWATNY MONITOR CEN (CHMURA) ===")
    with open("config.json", "r", encoding="utf-8") as plik:
        konfiguracja = json.load(plik)

    if not konfiguracja.get("aktywny", True):
        print("Monitorowanie jest obecnie zatrzymane. Pomijam sprawdzanie ceny.")
        return

    url = konfiguracja["url"]
    docelowa_cena = float(konfiguracja["docelowa_cena"])

    print(f"Monitorowany produkt: {url}")
    sprawdz_oferte(url, docelowa_cena)

if __name__ == "__main__":
    main()
