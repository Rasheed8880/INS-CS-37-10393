from serpapi import GoogleSearch

def generate_search_urls(country, city, industry, count, api_key):
    query = f"{industry} companies in {city}, {country}"
    params = {
        "engine": "google",
        "q": query,
        "num": count,
        "api_key": api_key
    }

    search = GoogleSearch(params)
    results = search.get_dict()
    links = []

    # Extract links from organic results
    organic_results = results.get("organic_results", [])
    for result in organic_results:
        link = result.get("link")
        if link:
            links.append(link)

    return links
