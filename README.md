### Email Scraper for Domain Contact Pages

This Python script scrapes websites for email addresses, particularly focusing on contact-related emails. It uses `Selenium` with Firefox WebDriver to navigate pages and find emails by scanning content or attempting direct access to common contact page URLs. The script is designed to prioritize important emails (like those containing "contact", "info", or similar keywords) and logs errors for failed attempts.

#### Features:
- **Headless Browsing**: Uses Firefox in headless mode for scraping, minimizing resource usage.
- **Meta Refresh Handling**: Detects and follows meta refresh redirects, ensuring accurate page scraping.
- **Email Prioritization**: Identifies important contact emails based on customizable keywords (e.g., "contact", "info").
- **Error Logging**: Logs errors to a file for debugging, such as failed page loads or broken links.
- **Direct URL Access**: Attempts to access `/contact` or `/kontakt` URLs directly if no contact links are found.

#### Requirements:
- Python packages: `Selenium`, `BeautifulSoup`, `re`
- Firefox WebDriver (Geckodriver)

#### Example Usage:
```python
print(scrape_for_emails("exampledomain.com"))
```

The script will return a list of found emails, prioritizing important ones, or log if no emails are found.
