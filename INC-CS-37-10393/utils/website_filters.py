import requests
import time

def is_shopify_website(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=5)
        if 'x-shopify-stage' in response.headers or 'x-shopify-request-id' in response.headers:
            return True
        if "cdn.shopify.com" in response.text or "window.Shopify" in response.text:
            return True
        return False
    except:
        return False

def loads_within_5_secs(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        start = time.time()
        response = requests.get(url, headers=headers, timeout=6)
        elapsed = time.time() - start
        return elapsed <= 5
    except:
        return False
