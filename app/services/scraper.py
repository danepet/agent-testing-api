import re
import aiohttp
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup


class ScraperService:
    """Service for extracting URLs and scraping web content."""
    
    def extract_urls(self, text: str) -> List[str]:
        """
        Extract URLs from text.
        
        Args:
            text: Text to extract URLs from
            
        Returns:
            list: List of URLs found in the text
        """
        # Simple regex for URL extraction (can be improved for production)
        url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
        urls = re.findall(url_pattern, text)
        return urls
    
    async def scrape_urls(self, urls: List[str], html_selector: Optional[str] = None) -> str:
        """
        Scrape content from a list of URLs.
        
        Args:
            urls: List of URLs to scrape
            html_selector: CSS selector to extract specific content (optional)
            
        Returns:
            str: Scraped content
        """
        results = []
        
        for url in urls:
            try:
                content = await self._scrape_url(url, html_selector)
                if content:
                    results.append(f"Content from {url}:\n{content}\n")
            except Exception as e:
                results.append(f"Error scraping {url}: {str(e)}\n")
        
        return "\n".join(results) if results else ""
    
    async def _scrape_url(self, url: str, html_selector: Optional[str] = None) -> str:
        """
        Scrape content from a URL.
        
        Args:
            url: URL to scrape
            html_selector: CSS selector to extract specific content (optional)
            
        Returns:
            str: Scraped content
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(url, allow_redirects=True) as response:
                if response.status != 200:
                    return f"Error: HTTP {response.status}"
                
                html = await response.text()
                
                # Parse HTML
                soup = BeautifulSoup(html, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.extract()
                
                # Apply CSS selector if provided
                if html_selector:
                    elements = soup.select(html_selector)
                    if elements:
                        return "\n".join([elem.get_text(strip=True) for elem in elements])
                    else:
                        # Fallback to main content if selector doesn't match
                        main_content = soup.find("main") or soup.find("article") or soup.find("body")
                        return main_content.get_text(strip=True) if main_content else ""
                
                # Default to extracting text from body
                return soup.body.get_text(strip=True) if soup.body else ""
