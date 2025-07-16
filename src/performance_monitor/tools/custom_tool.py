# src/performance_monitor/tools/custom_tool.py
import requests
import json
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from crewai.tools import BaseTool
from playwright.sync_api import sync_playwright
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ScraperTool(BaseTool):
    name: str = "Scraper Tool"
    description: str = "A tool to scrape content from a single webpage and check for specific SEO and accessibility elements."

    def _run(self, url: str) -> str:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, timeout=15, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            title = soup.find('title')
            title_text = title.get_text(strip=True) if title else 'Not Found'
            title_length = len(title_text) if title_text != 'Not Found' else 0
            
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            meta_description = meta_desc.get('content', '').strip() if meta_desc else 'Not Found'
            meta_desc_length = len(meta_description) if meta_description != 'Not Found' else 0
            
            h1_tags = soup.find_all('h1')
            h1_content = [h1.get_text(strip=True) for h1 in h1_tags]
            
            meta_robots = soup.find('meta', attrs={'name': 'robots'})
            robots_content = meta_robots.get('content', '') if meta_robots else 'Not Found'
            
            og_title = soup.find('meta', property='og:title')
            og_description = soup.find('meta', property='og:description')
            og_image = soup.find('meta', property='og:image')
            
            images = soup.find_all('img')
            images_without_alt = []
            total_images = len(images)
            
            for img in images:
                alt_text = img.get('alt', '').strip()
                if not alt_text:
                    src = img.get('src', 'Unknown source')
                    images_without_alt.append(src)
            
            forms = soup.find_all('form')
            inputs_without_labels = []
            for form in forms:
                inputs = form.find_all('input', type=['text', 'email', 'password', 'tel', 'url'])
                for input_elem in inputs:
                    input_id = input_elem.get('id')
                    input_name = input_elem.get('name')
                    if input_id:
                        label = soup.find('label', attrs={'for': input_id})
                        if not label:
                            inputs_without_labels.append(input_id or input_name or 'Unknown input')
            
            headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            heading_structure = []
            for heading in headings:
                heading_structure.append({
                    'level': heading.name,
                    'text': heading.get_text(strip=True)[:100]
                })

            return json.dumps({
                "url": url,
                "seo_analysis": {
                    "title": title_text,
                    "title_length": title_length,
                    "title_optimal": 30 <= title_length <= 60,
                    "meta_description": meta_description,
                    "meta_description_length": meta_desc_length,
                    "meta_description_optimal": 120 <= meta_desc_length <= 160,
                    "h1_count": len(h1_content),
                    "h1_content": h1_content,
                    "h1_optimal": len(h1_content) == 1,
                    "robots_directive": robots_content,
                    "has_og_title": og_title is not None,
                    "has_og_description": og_description is not None,
                    "has_og_image": og_image is not None
                },
                "accessibility_analysis": {
                    "total_images": total_images,
                    "images_missing_alt": len(images_without_alt),
                    "images_missing_alt_percentage": round((len(images_without_alt) / total_images * 100), 2) if total_images > 0 else 0,
                    "inputs_without_labels": len(inputs_without_labels),
                    "heading_structure": heading_structure
                },
                "status": "success"
            }, indent=2)
        except requests.RequestException as e:
            logger.error(f"Request error for {url}: {e}")
            return json.dumps({
                "url": url,
                "error": f"Request failed: {str(e)}",
                "status": "error"
            }, indent=2)
        except Exception as e:
            logger.error(f"General error scraping {url}: {e}")
            return json.dumps({
                "url": url,
                "error": f"Scraping failed: {str(e)}",
                "status": "error"
            }, indent=2)

class SiteMapTool(BaseTool):
    name: str = "Site Map Tool"
    description: str = "Crawls a website from a given URL to generate a list of all unique, internal links."

    def _run(self, url: str) -> str:
        try:
            base_url = urlparse(url).scheme + "://" + urlparse(url).netloc
            queue, visited = [url], set()
            max_pages = 25  # Increased limit
            failed_urls = []
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            while queue and len(visited) < max_pages:
                current_url = queue.pop(0)
                if current_url in visited:
                    continue
                
                # Normalize URL
                if current_url.endswith('/'):
                    current_url = current_url[:-1]

                visited.add(current_url)
                logger.info(f"Crawling: {current_url}")
                
                try:
                    response = requests.get(current_url, timeout=10, headers=headers)
                    response.raise_for_status()
                    
                    soup = BeautifulSoup(response.content, 'html.parser')
                    links = soup.find_all('a', href=True)
                    for link in links:
                        href = link['href']
                        
                        if href.startswith(('mailto:', 'tel:', 'javascript:', '#')):
                            continue
                            
                        full_url = urljoin(base_url, href).split('#')[0]
                        
                        if full_url.endswith('/'):
                            full_url = full_url[:-1]
                        parsed_url = urlparse(full_url)
                        if (parsed_url.netloc == urlparse(base_url).netloc and 
                            full_url not in visited and 
                            full_url not in queue and
                            len(queue) + len(visited) < max_pages):
                            queue.append(full_url)
                            
                except requests.RequestException as e:
                    logger.warning(f"Could not crawl {current_url}: {e}")
                    failed_urls.append(current_url)
                time.sleep(0.5)
                
            return json.dumps({
                "base_url": base_url,
                "discovered_urls": list(visited),
                "total_pages": len(visited),
                "failed_urls": failed_urls,
                "status": "success"
            }, indent=2)
            
        except Exception as e:
            logger.error(f"Site mapping failed: {e}")
            return json.dumps({
                "error": f"Site mapping failed: {str(e)}",
                "status": "error"
            }, indent=2)

class BrowserTool(BaseTool):
    name: str = "Browser Tool"
    description: str = "Performs a detailed analysis of a webpage using a headless browser, checking load times, console errors, and link status."

    def _run(self, url: str) -> str:
        results = {}
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                )
                page = context.new_page()
                
                # Collect console messages
                console_messages = []
                page.on("console", lambda msg: console_messages.append({
                    "type": msg.type,
                    "text": msg.text,
                    "location": msg.location
                }))
                
                # Collect network failures
                network_failures = []
                page.on("response", lambda response: network_failures.append({
                    "url": response.url,
                    "status": response.status,
                    "status_text": response.status_text
                }) if response.status >= 400 else None)
                
                # Navigate to page
                start_time = time.time()
                try:
                    response = page.goto(url, wait_until='domcontentloaded', timeout=30000)
                    load_time = (time.time() - start_time) * 1000  # Convert to milliseconds
                    
                    status = response.status if response else 'N/A'
                    
                    # Get performance metrics
                    performance_metrics = page.evaluate("""
                        () => {
                            const timing = performance.timing;
                            const navigation = performance.getEntriesByType('navigation')[0];
                            
                            return {
                                domContentLoaded: timing.domContentLoadedEventEnd - timing.navigationStart,
                                loadComplete: timing.loadEventEnd - timing.navigationStart,
                                firstPaint: navigation ? navigation.responseStart - navigation.requestStart : null,
                                domInteractive: timing.domInteractive - timing.navigationStart,
                                timeToInteractive: timing.domContentLoadedEventEnd - timing.navigationStart
                            };
                        }
                    """)
                    
                    # Additional page metrics
                    page_metrics = page.evaluate("""
                        () => {
                            const images = document.querySelectorAll('img');
                            const links = document.querySelectorAll('a[href]');
                            
                            return {
                                imageCount: images.length,
                                linkCount: links.length,
                                documentTitle: document.title,
                                documentUrl: document.URL,
                                hasServiceWorker: 'serviceWorker' in navigator,
                                viewport: {
                                    width: window.innerWidth,
                                    height: window.innerHeight
                                }
                            };
                        }
                    """)
                    
                    # Filter console messages for errors and warnings
                    errors = [msg for msg in console_messages if msg["type"] in ['error', 'warning']]
                    
                    results = {
                        "url": url,
                        "status_code": status,
                        "is_broken": status >= 400,
                        "load_time_ms": round(load_time, 2),
                        "performance_metrics": {
                            "dom_content_loaded_ms": performance_metrics.get('domContentLoaded', 'N/A'),
                            "load_complete_ms": performance_metrics.get('loadComplete', 'N/A'),
                            "dom_interactive_ms": performance_metrics.get('domInteractive', 'N/A'),
                            "time_to_interactive_ms": performance_metrics.get('timeToInteractive', 'N/A')
                        },
                        "page_metrics": page_metrics,
                        "console_errors": errors[:10],  # Limit to first 10 errors
                        "network_failures": network_failures[:5],  # Limit to first 5 failures
                        "status": "success"
                    }
                    
                except Exception as e:
                    results = {
                        "url": url,
                        "error": f"Page navigation failed: {str(e)}",
                        "status": "error"
                    }
                
                finally:
                    browser.close()
                    
        except Exception as e:
            logger.error(f"Browser analysis failed for {url}: {e}")
            results = {
                "url": url,
                "error": f"Browser analysis failed: {str(e)}",
                "status": "error"
            }
            
        return json.dumps(results, indent=2)