import requests
from typing import List, Dict, Optional

def search_wikipedia(query: str) -> Optional[Dict]:
    """Wikipedia se search karke answer fetch karta hai"""
    try:
        # Step 1: Search API se relevant page dhoondo
        search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={query.replace(' ', '+')}&format=json&srlimit=1"
        search_response = requests.get(search_url, timeout=5)
        
        if search_response.status_code != 200:
            return None
            
        search_data = search_response.json()
        search_results = search_data.get('query', {}).get('search', [])
        
        if not search_results:
            return None
            
        # Pehla result lo
        page_title = search_results[0]['title']
        page_snippet = search_results[0]['snippet']  # HTML snippet
        
        # Step 2: Us page ka summary lo
        summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{page_title.replace(' ', '_')}"
        summary_response = requests.get(summary_url, timeout=5)
        
        if summary_response.status_code == 200:
            data = summary_response.json()
            return {
                'source': 'wikipedia',
                'title': data.get('title', page_title),
                'extract': data.get('extract', page_snippet),
                'url': data.get('content_urls', {}).get('desktop', {}).get('page', f'https://en.wikipedia.org/wiki/{page_title.replace(" ", "_")}'),
                'image': data.get('thumbnail', {}).get('source', '')
            }
            
    except Exception as e:
        print(f"Wikipedia error: {e}")
    
    return None


def try_search(term: str) -> Optional[Dict]:
    """Helper function to try a single search term"""
    try:
        search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={term.replace(' ', '+')}&format=json&srlimit=1"
        response = requests.get(search_url, timeout=5)
        
        if response.status_code != 200:
            return None
            
        data = response.json()
        results = data.get('query', {}).get('search', [])
        
        if not results:
            return None
            
        page_title = results[0]['title']
        
        # Summary fetch karo
        summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{page_title.replace(' ', '_')}"
        summary_response = requests.get(summary_url, timeout=5)
        
        if summary_response.status_code == 200:
            data = summary_response.json()
            return {
                'source': 'wikipedia',
                'title': data.get('title', page_title),
                'extract': data.get('extract', ''),
                'url': data.get('content_urls', {}).get('desktop', {}).get('page', ''),
                'image': data.get('thumbnail', {}).get('source', '')
            }
    except:
        return None
    
    return None

def search_duckduckgo(query: str, max_results: int = 5) -> List[Dict]:
    """DuckDuckGo se web results fetch karta hai"""
    try:
        url = f"https://api.duckduckgo.com/?q={query}&format=json&no_html=1&skip_disambig=1"
        response = requests.get(url, timeout=5)
        
        results = []
        data = response.json()
        
        # Instant answer
        if data.get('Abstract'):
            results.append({
                'source': 'duckduckgo',
                'title': data.get('Heading', ''),
                'snippet': data.get('Abstract', ''),
                'url': data.get('AbstractURL', ''),
                'type': 'instant_answer'
            })
        
        # Related topics
        for topic in data.get('RelatedTopics', [])[:max_results]:
            if isinstance(topic, dict) and 'Text' in topic:
                results.append({
                    'source': 'duckduckgo',
                    'title': topic.get('Text', '').split(' - ')[0],
                    'snippet': topic.get('Text', ''),
                    'url': topic.get('FirstURL', ''),
                    'type': 'web_result'
                })
        
        return results
    except Exception as e:
        print(f"DuckDuckGo error: {e}")
        return []