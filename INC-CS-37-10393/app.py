from flask import Flask, render_template, request, Response
import os
import csv
import requests
from bs4 import BeautifulSoup
import time
from utils.generate_links import generate_search_urls
from utils.extract_emails import extract_emails_from_url
import io

app = Flask(__name__)

# Configuration
API_KEY = "d140fba3f420c4367567a36d4bc78278d0c01953923de1f3f6a5d47ee1a76a96"
OUTPUT_DIR = os.path.join(app.root_path, 'output')
os.makedirs(OUTPUT_DIR, exist_ok=True)
SEARCH_RESULTS_CSV = os.path.join(OUTPUT_DIR, "search_results.csv")
FINAL_LEADS_CSV = os.path.join(OUTPUT_DIR, "final_leads.csv")


def detect_website_type(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9'
        }
        if not url.startswith(('http://', 'https://')):
            url = 'http://' + url
        try:
            response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
            response.raise_for_status()
        except requests.RequestException:
            return 'unknown'

        content = response.text.lower()
        soup = BeautifulSoup(response.text, 'html.parser')

        if ('shopify' in content or 
            'cdn.shopify.com' in content or
            any('shopify' in script.get('src', '') for script in soup.find_all('script'))):
            return 'shopify'

        if ('wp-content' in content or 
            'wordpress' in content or
            any('wp-includes' in link.get('href', '') for link in soup.find_all('link'))):
            return 'wordpress'

        dynamic_elements = len(soup.find_all(['form', 'input', 'button', 'div[class*="dynamic"]']))
        if dynamic_elements < 3 and len(soup.find_all('script')) < 2:
            return 'static'

        return 'other'

    except Exception as e:
        print(f"Error detecting website type for {url}: {str(e)}")
        return 'unknown'


def is_active_and_fast(url, timeout=5):
    try:
        if not url.startswith(('http://', 'https://')):
            url = 'http://' + url
        
        start = time.time()
        response = requests.get(url, timeout=timeout)
        elapsed = time.time() - start
        if response.status_code == 200 and elapsed <= timeout:
            return True
        else:
            return False
    except requests.RequestException:
        return False


def filter_links_by_type(links, website_type):
    filtered_links = []
    for link in links:
        try:
            if not link.startswith(('http://', 'https://')):
                link = 'http://' + link

            if not is_active_and_fast(link, timeout=5):
                continue

            detected_type = detect_website_type(link)

            if website_type == 'shopify':
                if detected_type == 'shopify':
                    filtered_links.append(link)

            elif website_type == 'all':
                filtered_links.append(link)

            else:
                if detected_type == website_type:
                    filtered_links.append(link)

        except Exception:
            continue

    return filtered_links


def save_links_to_csv(links, filepath):
    try:
        os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)
        with open(filepath, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['URL'])
            for link in links:
                writer.writerow([link])
    except IOError as e:
        print(f"Error saving links to CSV: {str(e)}")


def save_emails_to_csv(email_data, filepath):
    try:
        os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)
        with open(filepath, mode='w', newline='', encoding='utf-8') as f:
            fieldnames = ['URL', 'Type', 'Emails', 'Active', 'Loads_in_5s', 'Is_Shopify']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(email_data)
    except IOError as e:
        print(f"Error saving emails to CSV: {str(e)}")


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        try:
            country = request.form.get('country', '').strip()
            city = request.form.get('city', '').strip()
            industry = request.form.get('industry', '').strip()
            count = int(request.form.get('count', 10))
            website_type = request.form.get('website_type', 'all').lower()

            links = generate_search_urls(country, city, industry, count, API_KEY)
            
            if website_type != 'all':
                links = filter_links_by_type(links, website_type)

            if not links:
                return render_template('index.html', error="No links found matching your criteria.")

            save_links_to_csv(links, SEARCH_RESULTS_CSV)

            final_data = []
            results = []
            for link in links:
                try:
                    emails = extract_emails_from_url(link)
                    w_type = detect_website_type(link)

                    # Check if domain is active and response time
                    active = False
                    loads_in_5s = "No"
                    is_shopify = "No"
                    try:
                        if not link.startswith(('http://', 'https://')):
                            test_url = 'http://' + link
                        else:
                            test_url = link

                        start = time.time()
                        response = requests.get(test_url, timeout=10)
                        elapsed = time.time() - start

                        if response.status_code == 200:
                            active = True
                            loads_in_5s = "Yes" if elapsed <= 5 else "No"
                        else:
                            active = False
                    except Exception:
                        active = False

                    is_shopify = "Yes" if w_type == 'shopify' else "No"

                    if emails:
                        final_data.append({
                            'URL': link,
                            'Type': w_type,
                            'Emails': ", ".join(emails),
                            'Active': "Yes" if active else "No",
                            'Loads_in_5s': loads_in_5s,
                            'Is_Shopify': is_shopify
                        })
                        results.append({
                            'url': link,
                            'type': w_type,
                            'emails': emails,
                            'email_count': len(emails),
                            'active': "Yes" if active else "No",
                            'loads_in_5s': loads_in_5s,
                            'is_shopify': is_shopify
                        })
                except Exception:
                    continue

            if final_data:
                save_emails_to_csv(final_data, FINAL_LEADS_CSV)
                return render_template('results.html', 
                                     results=results,
                                     count=len(results),
                                     website_type=website_type)
            else:
                return render_template('index.html', error="No emails found in any of the websites.")

        except Exception as e:
            return render_template('index.html', error=f"An error occurred: {str(e)}")

    return render_template('index.html')


@app.route('/download_emails')
def download_emails():
    try:
        emails = []
        with open(FINAL_LEADS_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                emails.extend([email.strip() for email in row['Emails'].split(',') if email.strip()])

        unique_emails = sorted(set(emails))

        si = io.StringIO()
        writer = csv.writer(si)
        writer.writerow(['Email'])
        for email in unique_emails:
            writer.writerow([email])

        output = si.getvalue()
        si.close()

        return Response(
            output,
            mimetype='text/csv',
            headers={"Content-Disposition": "attachment;filename=emails.csv"}
        )

    except Exception as e:
        return f"Error generating email file: {str(e)}"


if __name__ == '__main__':
    app.run(debug=True, port=5001)
