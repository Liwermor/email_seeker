import os
import re
from datetime import datetime

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def scrape_for_emails(domain):
    """
    Główna funkcja programu.

    Przyjmuje nazwę domeny, a następnie próbuje znaleźć adresy e-mail
    na stronie głównej oraz na podstronach kontaktowych.

    Funkcja:
    - sprawdza wariant domeny z `www` i bez `www`,
    - testuje połączenie przez HTTP oraz HTTPS,
    - obsługuje przekierowania,
    - szuka linków typu `kontakt` lub `contact`,
    - próbuje wejść bezpośrednio na `/kontakt` oraz `/contact`,
    - dzieli znalezione adresy e-mail na priorytetowe i pozostałe,
    - zapisuje błędy do pliku `errors/errorlog.txt`.

    Zwraca:
    - string z priorytetowymi adresami e-mail, jeśli zostały znalezione,
    - string z pozostałymi adresami e-mail, jeśli nie znaleziono priorytetowych,
    - pusty string, jeśli nie znaleziono żadnych adresów.
    """

    # Lista wariantów domeny do sprawdzenia.
    # Program sprawdza domenę bez www oraz z dodanym prefiksem www.
    paths = [domain, "www." + domain]

    # Wyrażenie regularne służące do wyszukiwania adresów e-mail w treści strony.
    email_regex = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,6}\b"

    # Zbiory przechowujące znalezione adresy e-mail.
    # Set usuwa duplikaty automatycznie.
    prioritized_emails = set()
    other_emails = set()

    # Konfiguracja katalogu i pliku, do którego będą zapisywane błędy.
    error_log_dir = "errors"
    error_log_file = "errorlog.txt"

    # Pobranie pierwszego członu domeny.
    # Przykład: dla "abc.example.com" wartość domain_name to "abc".
    domain_name = domain.split(".")[0]

    # Jeżeli katalog na logi błędów nie istnieje, zostaje utworzony.
    if not os.path.exists(error_log_dir):
        os.makedirs(error_log_dir)

    # Konfiguracja przeglądarki Firefox uruchamianej przez Selenium.
    # Tryb headless oznacza działanie bez widocznego okna przeglądarki.
    firefox_options = Options()
    firefox_options.add_argument("--headless")
    firefox_options.add_argument("--no-sandbox")
    firefox_options.add_argument("--disable-dev-shm-usage")

    # Utworzenie instancji Selenium WebDriver dla Firefoxa.
    driver = webdriver.Firefox(
        service=FirefoxService(),
        options=firefox_options
    )

    def get_emails_from_page(page_content):
        """
        Wyszukuje adresy e-mail w przekazanej treści strony HTML.

        Znalezione adresy są dzielone na dwie grupy:
        - priorytetowe: zawierające typowe słowa kontaktowe, np. sekretariat,
          biuro, kontakt, info albo nazwę domeny,
        - pozostałe: wszystkie inne znalezione adresy.

        Wyniki są dodawane do zbiorów `prioritized_emails` oraz `other_emails`
        zdefiniowanych w funkcji nadrzędnej `scrape_for_emails`.
        """

        # Wyszukanie wszystkich adresów e-mail w treści strony.
        all_found_emails = re.findall(email_regex, page_content)

        # Komunikat pomocniczy do debugowania.
        print(f"Found emails: {all_found_emails}")

        # Klasyfikacja znalezionych adresów e-mail.
        for email in all_found_emails:
            if (
                any(
                    keyword in email
                    for keyword in [
                        "sekretariat",
                        "biuro",
                        "poczta",
                        "dyrektor",
                        "kontakt",
                        "info",
                    ]
                )
                or f"{domain_name}@" in email
            ):
                prioritized_emails.add(email)
            else:
                other_emails.add(email)

    def find_and_click_contact_link(driver):
        """
        Szuka na aktualnie otwartej stronie linku prowadzącego do kontaktu.

        Funkcja analizuje wszystkie znaczniki `<a>` i sprawdza, czy ich adres
        zawiera słowo `kontakt` albo `contact`.

        Jeśli taki link zostanie znaleziony:
        - Selenium klika w link,
        - program czeka na załadowanie strony,
        - pobiera kod HTML nowej strony,
        - wywołuje `get_emails_from_page`.

        Zwraca:
        - True, jeśli po kliknięciu znaleziono adresy e-mail,
        - False, jeśli nie znaleziono odpowiedniego linku lub adresów.
        """

        # Pobranie wszystkich linków z aktualnej strony.
        links = driver.find_elements(By.TAG_NAME, "a")

        for link in links:
            href = link.get_attribute("href")

            # Sprawdzenie, czy link wygląda jak podstrona kontaktowa.
            if href and ("kontakt" in href or "contact" in href):
                try:
                    print(f"Clicking on link: {href}")

                    # Kliknięcie linku kontaktowego.
                    link.click()

                    # Oczekiwanie na załadowanie treści strony.
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )

                    # Pobranie kodu HTML strony po kliknięciu.
                    page_content = driver.page_source

                    # Wyszukanie adresów e-mail na stronie kontaktowej.
                    get_emails_from_page(page_content)

                    # Jeżeli znaleziono jakiekolwiek adresy e-mail, kończymy szukanie.
                    if prioritized_emails or other_emails:
                        return True

                except Exception as e:
                    # Obsługa błędów kliknięcia lub ładowania strony.
                    print(f"Failed to click on contact link: {e}")
                    continue

        return False

    def try_direct_contact_url(driver, base_url):
        """
        Próbuje wejść bezpośrednio na typowe adresy podstron kontaktowych.

        Dla podanego adresu bazowego funkcja testuje:
        - `/kontakt`,
        - `/contact`.

        Zwraca:
        - True, jeśli na jednej z tych stron znaleziono adres e-mail,
        - False, jeśli próby nie dały wyniku.
        """

        for suffix in ["kontakt", "contact"]:
            try:
                # Zbudowanie pełnego adresu podstrony kontaktowej.
                direct_url = base_url + suffix
                print(f"Trying direct URL: {direct_url}")

                # Wejście na bezpośredni adres kontaktowy.
                driver.get(direct_url)

                # Oczekiwanie na załadowanie strony.
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )

                # Pobranie HTML i wyszukanie adresów e-mail.
                page_content = driver.page_source
                get_emails_from_page(page_content)

                # Jeżeli znaleziono adresy, kończymy dalsze próby.
                if prioritized_emails or other_emails:
                    return True

            except Exception as e:
                # Obsługa błędów ładowania bezpośredniego URL.
                print(f"Failed to load direct URL {direct_url}: {e}")
                continue

        return False

    def handle_meta_refresh(driver):
        """
        Obsługuje przekierowania wykonane przez znacznik HTML meta refresh.

        Niektóre strony nie używają klasycznego przekierowania HTTP,
        tylko przekierowują użytkownika przez znacznik:

        <meta http-equiv="Refresh" content="0; url=...">

        Funkcja:
        - sprawdza, czy taki znacznik istnieje,
        - wyciąga z niego docelowy URL,
        - przechodzi na wskazany adres.

        Zwraca:
        - True, jeśli przekierowanie zostało znalezione i obsłużone,
        - False, jeśli nie znaleziono meta refresh.
        """

        # Pobranie aktualnego kodu HTML strony.
        page_source = driver.page_source

        # Parsowanie HTML za pomocą BeautifulSoup.
        soup = BeautifulSoup(page_source, "html.parser")

        # Wyszukanie znacznika meta refresh.
        meta_tag = soup.find("meta", attrs={"http-equiv": "Refresh"})

        if meta_tag:
            content = meta_tag.get("content", "")

            # Pobranie części po `url=`.
            url_part = content.split("url=")[-1]

            if url_part:
                redirect_url = url_part.strip()
                print(f"Following meta refresh to {redirect_url}")

                # Przejście na adres wskazany w meta refresh.
                driver.get(redirect_url)

                # Oczekiwanie na załadowanie strony po przekierowaniu.
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )

                return True

        return False

    def handle_redirection_and_find_contact(driver, url):
        """
        Obsługuje wejście na stronę, potencjalne przekierowania i szukanie kontaktu.

        Funkcja:
        - otwiera wskazany URL,
        - czeka na załadowanie strony,
        - sprawdza przekierowanie typu meta refresh,
        - próbuje znaleźć i kliknąć link kontaktowy,
        - jeśli nie znajdzie linku albo adresów e-mail, próbuje URL `/kontakt`
          oraz `/contact`,
        - zapisuje błędy do pliku logów.
        """

        try:
            # Wejście na podany adres URL.
            driver.get(url)

            # Oczekiwanie na załadowanie treści strony.
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Obsługa ewentualnego przekierowania meta refresh.
            if handle_meta_refresh(driver):
                # Po przekierowaniu ponownie szukamy linku kontaktowego.
                if find_and_click_contact_link(driver):
                    return

            # Próba znalezienia i kliknięcia linku kontaktowego.
            if not find_and_click_contact_link(driver):
                # Jeśli link kontaktowy nie dał wyniku, testujemy bezpośrednie URL-e.
                try_direct_contact_url(driver, url)

        except Exception as e:
            # Zapis błędu do pliku errorlog.txt.
            current_time = datetime.now().strftime("[%d:%m:%y | %H:%M:%S]")
            error_message = f"{current_time} Error handling redirection on {url}: {e}\n"

            with open(os.path.join(error_log_dir, error_log_file), "a") as file:
                file.write(error_message)

    # Główna pętla sprawdzająca różne warianty domeny i protokołu.
    for path in paths:
        # Pominięcie błędnego wariantu typu www.www.example.com.
        if path.startswith("www.www."):
            continue

        # Sprawdzenie strony przez HTTP oraz HTTPS.
        for scheme in ["http://", "https://"]:
            url = scheme + path

            try:
                print(f"Trying URL: {url}")

                # Wejście na stronę.
                driver.get(url)

                # Oczekiwanie na załadowanie body strony.
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )

                # Pobranie końcowego URL po ewentualnym przekierowaniu.
                final_url = driver.current_url
                print(f"Final URL after potential redirect: {final_url}")

                # Jeżeli Selenium zostało przekierowane na inny adres,
                # dalsze działania wykonywane są na końcowym URL.
                if final_url != url:
                    handle_redirection_and_find_contact(driver, final_url)
                else:
                    handle_redirection_and_find_contact(driver, url)

            except Exception as e:
                # Zapis błędów związanych z próbą wejścia na konkretny URL.
                current_time = datetime.now().strftime("[%d:%m:%y | %H:%M:%S]")
                error_message = f"{current_time} Error scraping {url}: {e}\n"

                with open(os.path.join(error_log_dir, error_log_file), "a") as file:
                    file.write(error_message)

    # Zamknięcie przeglądarki po zakończeniu pracy.
    driver.quit()

    # Zwrócenie wyników.
    # Priorytet mają adresy sklasyfikowane jako najważniejsze.
    if prioritized_emails:
        print(f"{domain} - Total prioritized contacts found: {len(prioritized_emails)}")
        return " ".join(sorted(prioritized_emails))

    elif other_emails:
        print(f"{domain} - Total other contacts found: {len(other_emails)}")
        return " ".join(sorted(other_emails))

    else:
        print(f"{domain} - No contacts found")
        return ""


# Przykład użycia skryptu.
# Funkcja spróbuje znaleźć adresy e-mail dla podanej domeny.
print(scrape_for_emails("abc.example.com"))
