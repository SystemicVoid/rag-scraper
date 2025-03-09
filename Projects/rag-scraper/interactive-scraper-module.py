"""Interactive page selection for RAG Scraper."""

import time
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
import concurrent.futures
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from loguru import logger
from tqdm import tqdm
import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress
from rich.prompt import Confirm

# Import the config directly using importlib to avoid package structure issues
import importlib.util

def import_module_from_file(file_path, module_name):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# Import the config module
config_module = import_module_from_file("config-module.py", "config_module")
ScraperConfig = config_module.ScraperConfig


class InteractiveWebScraper:
    """Web scraper with interactive page selection."""

    def __init__(self, config: ScraperConfig, output_dir: Path):
        """Initialize the web scraper.
        
        Args:
            config: Scraper configuration
            output_dir: Directory to save scraped content
        """
        self.config = config
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Rich console for pretty output
        self.console = Console()
        
        # Set for visited URLs to avoid duplicates
        self.visited_urls: Set[str] = set()
        self.discovered_pages: Dict[str, Dict] = {}
        
        # Set user agent and headers
        self.headers = {
            "User-Agent": config.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml",
            "Accept-Language": "en-US,en;q=0.9",
        }
        
        # Create a session for better performance
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        logger.info(f"Initialized interactive scraper for domain: {config.domain}")
        
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
        """Check if URL is allowed to be crawled."""
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
        """Extract links from BeautifulSoup object."""
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

    def _extract_page_info(self, url: str, html_content: str) -> Dict:
        """Extract basic page information without full processing."""
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Extract title
        title = "No title"
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.get_text().strip()
        
        # Extract description
        description = "No description"
        description_tag = soup.find("meta", attrs={"name": "description"})
        if description_tag and description_tag.get("content"):
            description = description_tag.get("content").strip()
            
        # Estimate content size by looking at text length
        main_content = ""
        for element in soup.select('main, article, .content, .main'):
            main_content += element.get_text()
        
        if not main_content:  # Fallback if no main content found
            main_content = soup.get_text()
            
        content_size = len(main_content)
        
        return {
            "url": url,
            "title": title,
            "description": description[:100] + "..." if len(description) > 100 else description,
            "content_size": content_size,
            "html_size": len(html_content)
        }

    async def discover_pages(self, max_pages: int = 100) -> Dict[str, Dict]:
        """Discover available pages without fully scraping them.
        
        Args:
            max_pages: Maximum number of pages to discover
            
        Returns:
            Dict[str, Dict]: Dictionary of discovered pages with metadata
        """
        urls_to_visit = list(self.config.start_urls)
        
        with Progress() as progress:
            task = progress.add_task("[cyan]Discovering pages...", total=max_pages)
            
            while urls_to_visit and len(self.visited_urls) < max_pages:
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
                        # Extract basic page info
                        page_info = self._extract_page_info(url, response.text)
                        self.discovered_pages[url] = page_info
                        
                        # Parse the content to find more links
                        soup = BeautifulSoup(response.text, "html.parser")
                        links = self._extract_links(soup, url)
                        urls_to_visit.extend(links)
                        
                        logger.debug(f"Discovered: {url}")
                    else:
                        logger.warning(f"Failed to fetch {url}: {response.status_code}")
                
                except Exception as e:
                    logger.error(f"Error discovering {url}: {e}")
                
                progress.update(task, advance=1)
                
        logger.info(f"Discovery complete: {len(self.discovered_pages)} pages found")
        return self.discovered_pages

    def display_discovered_pages(self) -> None:
        """Display the discovered pages in a rich table."""
        table = Table(title=f"Discovered Pages for {self.config.domain}")
        
        table.add_column("#", justify="right", style="cyan", no_wrap=True)
        table.add_column("Title", style="green")
        table.add_column("URL", style="blue")
        table.add_column("Size", justify="right", style="magenta")
        
        for i, (url, info) in enumerate(self.discovered_pages.items(), 1):
            table.add_row(
                str(i),
                info["title"],
                url,
                f"{info['content_size'] // 1000} KB"
            )
            
        self.console.print(table)

    def select_pages_interactive(self) -> List[str]:
        """Allow user to interactively select which pages to scrape."""
        self.display_discovered_pages()
        
        self.console.print("\n[bold yellow]Page Selection Options:[/]")
        self.console.print("1. [green]Select All[/]")
        self.console.print("2. [yellow]Select by Index[/] (e.g., '1,3,5-7')")
        self.console.print("3. [blue]Filter by Keyword[/]")
        self.console.print("4. [red]Select None[/]")
        
        choice = click.prompt("Choose an option", type=int, default=1)
        
        urls = list(self.discovered_pages.keys())
        selected_urls = []
        
        if choice == 1:  # Select All
            selected_urls = urls
            
        elif choice == 2:  # Select by Index
            indices_str = click.prompt("Enter indices (e.g., '1,3,5-7')")
            
            # Parse indices including ranges
            selected_indices = set()
            parts = indices_str.split(',')
            
            for part in parts:
                if '-' in part:
                    start, end = map(int, part.split('-'))
                    selected_indices.update(range(start, end + 1))
                else:
                    selected_indices.add(int(part))
            
            for idx in selected_indices:
                if 1 <= idx <= len(urls):
                    selected_urls.append(urls[idx - 1])
            
        elif choice == 3:  # Filter by Keyword
            keyword = click.prompt("Enter keyword to filter by")
            
            for url, info in self.discovered_pages.items():
                if (keyword.lower() in url.lower() or 
                    keyword.lower() in info['title'].lower() or 
                    keyword.lower() in info['description'].lower()):
                    selected_urls.append(url)
                    
            # Show filtered results and confirm
            self.console.print(f"\nFound {len(selected_urls)} pages containing '{keyword}':")
            for i, url in enumerate(selected_urls, 1):
                self.console.print(f"{i}. {self.discovered_pages[url]['title']} - {url}")
                
            if not Confirm.ask("Proceed with these pages?"):
                return self.select_pages_interactive()  # Start over if user isn't satisfied
        
        elif choice == 4:  # Select None
            self.console.print("[yellow]No pages selected. Exiting...[/]")
            return []
            
        else:
            self.console.print("[red]Invalid choice. Please try again.[/]")
            return self.select_pages_interactive()
            
        self.console.print(f"[green]Selected {len(selected_urls)} pages for scraping.[/]")
        return selected_urls

    def scrape_selected_pages(self, selected_urls: List[str]) -> Dict[str, Path]:
        """Scrape only the selected pages.
        
        Args:
            selected_urls: List of URLs to scrape
            
        Returns:
            Dict[str, Path]: Dictionary mapping URLs to content file paths
        """
        content_map = {}
        
        with Progress() as progress:
            task = progress.add_task("[green]Scraping selected pages...", total=len(selected_urls))
            
            for url in selected_urls:
                try:
                    # Respect the rate limit
                    time.sleep(self.config.delay)
                    
                    # Fetch the URL
                    response = self.session.get(url, timeout=self.config.timeout)
                    
                    if response.status_code == 200:
                        # Generate a filename
                        parsed_url = urlparse(url)
                        path_parts = parsed_url.path.strip("/").split("/")
                        filename = "_".join(path_parts) if path_parts and path_parts[0] else "index"
                        content_path = self.output_dir / f"{filename}_{hash(url)}.html"
                        
                        # Save the content
                        content_path.write_text(response.text, encoding="utf-8")
                        content_map[url] = content_path
                        
                        logger.debug(f"Scraped: {url}")
                    else:
                        logger.warning(f"Failed to fetch {url}: {response.status_code}")
                
                except Exception as e:
                    logger.error(f"Error scraping {url}: {e}")
                
                progress.update(task, advance=1)
                
        logger.info(f"Scraping complete: {len(content_map)} pages scraped")
        return content_map

    async def interactive_scrape(self) -> Dict[str, Path]:
        """Run the interactive scraping process.
        
        Returns:
            Dict[str, Path]: Dictionary mapping URLs to content file paths
        """
        # Step 1: Discover available pages
        self.console.print("[bold cyan]Step 1: Discovering available pages...[/]")
        await self.discover_pages(max_pages=self.config.max_pages)
        
        # Step 2: Let user select pages
        self.console.print("\n[bold cyan]Step 2: Select pages to scrape[/]")
        selected_urls = self.select_pages_interactive()
        
        if not selected_urls:
            return {}
        
        # Step 3: Scrape selected pages
        self.console.print("\n[bold cyan]Step 3: Scraping selected pages[/]")
        content_map = self.scrape_selected_pages(selected_urls)
        
        return content_map