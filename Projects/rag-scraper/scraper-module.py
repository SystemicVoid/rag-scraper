"""Web scraping functionality for RAG Scraper."""

import time
from pathlib import Path
from typing import Dict, Generator, List, Optional, Set, Tuple

import requests
from bs4 import BeautifulSoup
from loguru import logger
from tqdm import tqdm
from urllib.parse import urljoin, urlparse

from .config import ScraperConfig


class WebScraper:
    """Web scraper for RAG Scraper."""

    def __init__(self, config: ScraperConfig, output_dir: Path):
        """Initialize the web scraper.

        Args:
            config: Scraper configuration
            output_dir: Directory to save scraped content
        """
        self.config = config
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Set for visited URLs to avoid duplicates
        self.visited_urls: Set[str] = set()

        # Set user agent and headers
        self.headers = {
            "User-Agent": config.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml",
            "Accept-Language": "en-US,en;q=0.9",
        }

        # Create a session for better performance
        self.session = requests.Session()
        self.session.headers.update(self.headers)

        logger.info(f"Initialized scraper for domain: {config.domain}")

        # Check robots.txt if required
        self.disallowed_paths: List[str] = []
        if config.respect_robots_txt:
            self._parse_robots_txt()

    def _parse_robots_txt(self) -> None:
        """Parse robots.txt file to respect website crawling policies."""
        try:
            robots_url = f"https://{self.config.domain}/robots.txt"
            response = self.session.get(robots_url, timeout=self.config.timeout)

            if response.status_code == 200:
                lines = response.text.split("\n")
                user_agent_applies = False

                for line in lines:
                    line = line.strip()

                    if line.lower().startswith("user-agent:"):
                        agent = line.split(":", 1)[1].strip()
                        # Check if this rule applies to our user agent or all agents
                        user_agent_applies = agent == "*" or agent in self.config.user_agent

                    elif user_agent_applies and line.lower().startswith("disallow:"):
                        path = line.split(":", 1)[1].strip()
                        if path:
                            self.disallowed_paths.append(path)

                logger.info(f"Parsed robots.txt: {len(self.disallowed_paths)} disallowed paths")
            else:
                logger.warning(f"Could not fetch robots.txt: {response.status_code}")

        except Exception as e:
            logger.warning(f"Error parsing robots.txt: {e}")

    def _is_allowed(self, url: str) -> bool:
        """Check if URL is allowed to be crawled.

        Args:
            url: URL to check

        Returns:
            bool: True if URL is allowed to be crawled
        """
        # Check if URL is in allowed domains
        parsed_url = urlparse(url)
        if parsed_url.netloc not in self.config.allowed_domains:
            return False

        # Check if URL matches any disallowed path
        for path in self.disallowed_paths:
            if path == "/" or parsed_url.path.startswith(path):
                return False

        return True

    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract links from BeautifulSoup object.

        Args:
            soup: BeautifulSoup object
            base_url: Base URL for relative links

        Returns:
            List[str]: List of extracted URLs
        """
        links = []
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            absolute_url = urljoin(base_url, href)

            # Skip fragments, queries, etc.
            parsed = urlparse(absolute_url)
            clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

            if self._is_allowed(clean_url) and clean_url not in self.visited_urls:
                links.append(clean_url)

        return links

    def scrape(self) -> Dict[str, Path]:
        """Scrape the configured domain.

        Returns:
            Dict[str, Path]: Dictionary mapping URLs to content file paths
        """
        urls_to_visit = list(self.config.start_urls)
        content_map = {}

        with tqdm(total=self.config.max_pages) as pbar:
            while urls_to_visit and len(self.visited_urls) < self.config.max_pages:
                url = urls_to_visit.pop(0)

                if url in self.visited_urls:
                    continue

                self.visited_urls.add(url)

                try:
                    # Respect the rate limit
                    time.sleep(self.config.delay)

                    # Fetch the URL
                    response = self.session.get(url, timeout=self.config.timeout)

                    if response.status_code == 200:
                        # Parse the content
                        soup = BeautifulSoup(response.text, "html.parser")

                        # Generate a filename
                        parsed_url = urlparse(url)
                        path_parts = parsed_url.path.strip("/").split("/")
                        filename = "_".join(path_parts) if path_parts and path_parts[0] else "index"
                        content_path = self.output_dir / f"{filename}_{hash(url)}.html"

                        # Save the content
                        content_path.write_text(response.text, encoding="utf-8")
                        content_map[url] = content_path

                        # Extract links
                        links = self._extract_links(soup, url)
                        urls_to_visit.extend(links)

                        logger.debug(f"Scraped: {url}")
                    else:
                        logger.warning(f"Failed to fetch {url}: {response.status_code}")

                except Exception as e:
                    logger.error(f"Error scraping {url}: {e}")

                pbar.update(1)

        logger.info(f"Scraping complete: {len(content_map)} pages scraped")
        return content_map
