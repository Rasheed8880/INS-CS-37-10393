import re
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def extract_emails_from_url(url):
    emails = set()
    try:
        # Use a session with retries
        session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[403, 404, 406, 408, 429, 500, 502, 503, 504]
        )
        session.mount('http://', HTTPAdapter(max_retries=retries))
        session.mount('https://', HTTPAdapter(max_retries=retries))

        headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/122.0.0.0 Safari/537.36'
            ),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        }

        response = session.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        content = response.text
        soup = BeautifulSoup(content, 'html.parser')

        # Extract emails from mailto:
        for mailto in soup.select('a[href^=mailto]'):
            mail = mailto.get('href').replace('mailto:', '').split('?')[0]
            if mail:
                emails.add(mail.strip())

        # Extract emails using regex
        text = soup.get_text(separator=' ')
        regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'
        found = re.findall(regex, text)
        for mail in found:
            emails.add(mail.strip())

        # Handle obfuscated emails like "name [at] domain [dot] com"
        obf_regex = r'([A-Za-z0-9._%+-]+)\s*(?:\[at\]|\(at\)|@)\s*([A-Za-z0-9.-]+)\s*(?:\[dot\]|\(dot\)|\.)\s*([A-Za-z]{2,})'
        obf_found = re.findall(obf_regex, text, flags=re.IGNORECASE)
        for parts in obf_found:
            mail = f"{parts[0]}@{parts[1]}.{parts[2]}"
            emails.add(mail.strip())

    except requests.exceptions.RequestException as e:
        print(f"[Request error] Failed to extract from {url}: {e}")
    except Exception as e:
        print(f"[Parsing error] {url}: {e}")

    return list(emails)
