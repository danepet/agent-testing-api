import pytest
import asyncio
from unittest.mock import patch, MagicMock
from app.services.scraper import ScraperService


@pytest.fixture
def scraper_service():
    """Fixture for scraper service."""
    return ScraperService()


def test_extract_urls(scraper_service):
    """Test URL extraction."""
    # Test with multiple URLs
    text = "Visit https://example.com and https://test.org for more information."
    urls = scraper_service.extract_urls(text)
    assert len(urls) == 2
    assert "https://example.com" in urls
    assert "https://test.org" in urls
    
    # Test with no URLs
    text = "No URLs here."
    urls = scraper_service.extract_urls(text)
    assert len(urls) == 0
    
    # Test with complex URLs
    text = "Visit https://example.com/path/to/page?param=value#section for details."
    urls = scraper_service.extract_urls(text)
    assert len(urls) == 1
    assert "https://example.com/path/to/page" in urls[0]


@pytest.mark.asyncio
async def test_scrape_url_success():
    """Test successful URL scraping."""
    scraper_service = ScraperService()
    
    # Mock aiohttp ClientSession and response
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.text = asyncio.coroutine(lambda: "<html><body><main>Test content</main></body></html>")
    
    mock_session = MagicMock()
    mock_session.__aenter__ = asyncio.coroutine(lambda *args: mock_session)
    mock_session.__aexit__ = asyncio.coroutine(lambda *args: None)
    mock_session.get = asyncio.coroutine(lambda *args, **kwargs: mock_response)
    
    with patch('aiohttp.ClientSession', return_value=mock_session):
        # Test with no selector
        content = await scraper_service._scrape_url("https://example.com")
        assert "Test content" in content
        
        # Test with valid selector
        mock_response.text = asyncio.coroutine(lambda: "<html><body><main>Main content</main><div class='test'>Test div</div></body></html>")
        content = await scraper_service._scrape_url("https://example.com", "div.test")
        assert "Test div" in content
        assert "Main content" not in content
        
        # Test with invalid selector (should fall back to main content)
        content = await scraper_service._scrape_url("https://example.com", "div.nonexistent")
        assert "Main content" in content


@pytest.mark.asyncio
async def test_scrape_url_error():
    """Test URL scraping with errors."""
    scraper_service = ScraperService()
    
    # Mock aiohttp ClientSession and response for HTTP error
    mock_response = MagicMock()
    mock_response.status = 404
    
    mock_session = MagicMock()
    mock_session.__aenter__ = asyncio.coroutine(lambda *args: mock_session)
    mock_session.__aexit__ = asyncio.coroutine(lambda *args: None)
    mock_session.get = asyncio.coroutine(lambda *args, **kwargs: mock_response)
    
    with patch('aiohttp.ClientSession', return_value=mock_session):
        content = await scraper_service._scrape_url("https://example.com")
        assert "Error: HTTP 404" in content
    
    # Mock aiohttp ClientSession for exception
    mock_session = MagicMock()
    mock_session.__aenter__ = asyncio.coroutine(lambda *args: mock_session)
    mock_session.__aexit__ = asyncio.coroutine(lambda *args: None)
    mock_session.get = asyncio.coroutine(lambda *args, **kwargs: (_ for _ in ()).throw(Exception("Connection error")))
    
    with patch('aiohttp.ClientSession', return_value=mock_session):
        with pytest.raises(Exception) as exc_info:
            await scraper_service._scrape_url("https://example.com")
        assert "Connection error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_scrape_urls(scraper_service):
    """Test scraping multiple URLs."""
    # Patch the _scrape_url method to avoid actual HTTP requests
    with patch.object(scraper_service, '_scrape_url') as mock_scrape_url:
        mock_scrape_url.side_effect = [
            asyncio.coroutine(lambda: "Content from URL 1")(),
            asyncio.coroutine(lambda: "Content from URL 2")(),
            asyncio.coroutine(lambda: (_ for _ in ()).throw(Exception("Error for URL 3")))(),
        ]
        
        content = await scraper_service.scrape_urls(
            ["https://example1.com", "https://example2.com", "https://example3.com"]
        )
        
        assert "Content from URL 1" in content
        assert "Content from URL 2" in content
        assert "Error scraping https://example3.com" in content
        
        # Test empty URL list
        content = await scraper_service.scrape_urls([])
        assert content == ""