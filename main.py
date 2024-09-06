import os
import re
from selenium import webdriver
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
from bs4 import BeautifulSoup

def scrape_for_emails(domain):
    paths = [domain, "www." + domain]
    email_regex = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,6}\b"
    prioritized_emails = set()
    other_emails = set()
    error_log_dir = 'errors'
    error_log_file = 'errorlog.txt'
    
    domain_name = domain.split('.')[0]  # Pobiera nazwę domeny bez TLD (np. "abc" z "abc.def.xd")

    if not os.path.exists(error_log_dir):
        os.makedirs(error_log_dir)

    firefox_options = Options()
    firefox_options.add_argument('--headless')  
    firefox_options.add_argument('--no-sandbox')
    firefox_options.add_argument('--disable-dev-shm-usage')

    #Selenium WebDriver Firefox
    driver = webdriver.Firefox(service=FirefoxService(), options=firefox_options)

    def get_emails_from_page(page_content):
        all_found_emails = re.findall(email_regex, page_content)
        print(f"Found emails: {all_found_emails}")  # Debug: pokazuje znalezione e-maile
        for email in all_found_emails:
            if any(keyword in email for keyword in ['sekretariat', 'biuro', 'poczta', 'dyrektor', 'kontakt', 'info']) or f"{domain_name}@" in email:
                prioritized_emails.add(email)
            else:
                other_emails.add(email)

    def find_and_click_contact_link(driver):
        links = driver.find_elements(By.TAG_NAME, "a")
        for link in links:
            href = link.get_attribute("href")
            if href and ("kontakt" in href or "contact" in href):
                try:
                    print(f"Clicking on link: {href}")  # Debug: pokazuje, który link jest klikany
                    link.click()
                    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
                    page_content = driver.page_source
                    get_emails_from_page(page_content)
                    if prioritized_emails or other_emails:
                        return True  # Przerwij, jeśli znaleziono e-maile
                except Exception as e:
                    print(f"Failed to click on contact link: {e}")  # Debug: pokazuje błąd kliknięcia
                    continue
        return False

    def try_direct_contact_url(driver, base_url):
        for suffix in ['kontakt', 'contact']:
            try:
                direct_url = base_url + suffix
                print(f"Trying direct URL: {direct_url}")  # Debug: pokazuje, który URL jest odwiedzany
                driver.get(direct_url)
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
                page_content = driver.page_source
                get_emails_from_page(page_content)
                if prioritized_emails or other_emails:
                    return True  # Przerwij, jeśli znaleziono e-maile
            except Exception as e:
                print(f"Failed to load direct URL {direct_url}: {e}")  # Debug: pokazuje błąd przy odwiedzeniu URL
                continue
        return False

    def handle_meta_refresh(driver):
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        meta_tag = soup.find('meta', attrs={'http-equiv': 'Refresh'})
        if meta_tag:
            content = meta_tag.get('content', '')
            url_part = content.split('url=')[-1]
            if url_part:
                redirect_url = url_part.strip()
                print(f"Following meta refresh to {redirect_url}")  # Debug: pokazuje, na jaki URL skrypt podąża
                driver.get(redirect_url)
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
                return True
        return False

    def handle_redirection_and_find_contact(driver, url):
        try:
            driver.get(url)
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
            # Handle potential meta refresh redirects
            if handle_meta_refresh(driver):
                # After following the meta redirect, check for contact links again
                if find_and_click_contact_link(driver):
                    return

            # Try to find and click on contact link
            if not find_and_click_contact_link(driver):
                # If no emails found after clicking links, try direct URLs
                try_direct_contact_url(driver, url)

        except Exception as e:
            current_time = datetime.now().strftime("[%d:%m:%y | %H:%M:%S]")
            error_message = f"{current_time} Error handling redirection on {url}: {e}\n"
            with open(os.path.join(error_log_dir, error_log_file), 'a') as file:
                file.write(error_message)

    for path in paths:
        if path.startswith("www.www."):
            continue
        for scheme in ["http://", "https://"]:
            url = scheme + path
            try:
                print(f"Trying URL: {url}")  # Debug: pokazuje, który URL jest próbnie odwiedzany
                driver.get(url)
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))

                # redirect check
                final_url = driver.current_url
                print(f"Final URL after potential redirect: {final_url}")  # Debug: pokazuje ostateczny URL
                if final_url != url:
                    handle_redirection_and_find_contact(driver, final_url)
                else:
                    handle_redirection_and_find_contact(driver, url)

            except Exception as e:
                current_time = datetime.now().strftime("[%d:%m:%y | %H:%M:%S]")
                error_message = f"{current_time} Error scraping {url}: {e}\n"
                with open(os.path.join(error_log_dir, error_log_file), 'a') as file:
                    file.write(error_message)

    driver.quit()

    # Check and return prior 
    if prioritized_emails:
        print(f"{domain} - Total prioritized contacts found: {len(prioritized_emails)}")
        return ' '.join(sorted(prioritized_emails))
    elif other_emails:
        print(f"{domain} - Total other contacts found: {len(other_emails)}")
        return ' '.join(sorted(other_emails))
    else:
        print(f"{domain} - No contacts found")
        return ''

# Przykład użycia skryptu
print(scrape_for_emails("abc.example.com"))
