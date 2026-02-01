#!/usr/bin/env python3
"""
Modular VC Job Board Scraper
Each job board has its own dedicated scraper class with custom pagination handling.
"""

import asyncio
import json
import re
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

from playwright.async_api import async_playwright, Page, Browser, BrowserContext


# =============================================================================
# CONFIGURATION
# =============================================================================

SENIOR_KEYWORDS = [
    'director', 'head of', 'vp ', 'vice president', 'chief',
    'manager', 'lead', 'senior', 'principal', 'executive',
    'enterprise', 'strategic', 'regional'
]

GTM_KEYWORDS = [
    'sales', 'account', 'business development', 'bd ', 'bdr',
    'gtm', 'go-to-market', 'commercial', 'revenue', 'partnerships',
    'partner', 'customer success', 'solutions', 'presales',
    'enterprise', 'strategic', 'field'
]

JUNIOR_KEYWORDS = [
    'intern', 'graduate', 'entry level', 'coordinator',
    'assistant', 'junior', 'trainee'
]

APAC_LOCATIONS = [
    'australia', 'sydney', 'melbourne', 'brisbane', 'perth',
    'singapore', 'apac', 'asia', 'remote', 'india', 'bangalore',
    'tokyo', 'seoul', 'hong kong'
]


# =============================================================================
# UTILITIES
# =============================================================================

def is_gtm_role(title: str) -> bool:
    """Check if job title is a GTM role."""
    title_lower = title.lower()
    if any(kw in title_lower for kw in JUNIOR_KEYWORDS):
        return False
    return any(kw in title_lower for kw in GTM_KEYWORDS)


def calculate_match_score(job: Dict) -> int:
    """Calculate match score for Leroy's profile."""
    score = 50
    title = job.get('title', '').lower()

    # Seniority boost
    if any(kw in title for kw in ['director', 'head of', 'vp ', 'chief']):
        score += 20
    elif any(kw in title for kw in ['manager', 'lead', 'senior']):
        score += 10

    # Role type boost
    if 'enterprise' in title: score += 15
    if 'account executive' in title: score += 15
    if 'partner' in title: score += 10
    if 'sales' in title: score += 10
    if 'gtm' in title: score += 15
    if 'ai' in title or 'ml' in title: score += 15

    # Location boost
    loc = job.get('location', '').lower()
    if 'sydney' in loc: score += 10
    elif 'australia' in loc: score += 5
    elif 'remote' in loc: score += 5

    # Junior penalty
    if any(kw in title for kw in JUNIOR_KEYWORDS):
        score -= 30

    return min(100, max(0, score))


async def create_browser_context(playwright) -> tuple[Browser, BrowserContext]:
    """Create browser with standard settings."""
    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context(
        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        viewport={'width': 1920, 'height': 1080}
    )
    return browser, context


# =============================================================================
# BASE SCRAPER CLASS
# =============================================================================

class BaseJobScraper(ABC):
    """Abstract base class for job board scrapers."""

    name: str = "Base"
    base_url: str = ""

    def __init__(self):
        self.jobs: List[Dict] = []

    @abstractmethod
    async def scrape(self) -> List[Dict]:
        """Scrape jobs from this board. Must be implemented by subclasses."""
        pass

    @abstractmethod
    async def handle_pagination(self, page: Page) -> None:
        """Handle pagination specific to this board."""
        pass

    @abstractmethod
    async def extract_jobs(self, page: Page) -> List[Dict]:
        """Extract job data from the page."""
        pass

    def add_metadata(self, job: Dict) -> Dict:
        """Add standard metadata to job."""
        job["source"] = self.name
        job["match_score"] = calculate_match_score(job)
        job["scraped_date"] = datetime.now().isoformat()
        return job


# =============================================================================
# INSIGHT PARTNERS SCRAPER
# Pagination: "Load more" button clicks
# Platform: Getro
# =============================================================================

class InsightPartnersScraper(BaseJobScraper):
    """
    Insight Partners job board scraper.
    - Uses Getro platform
    - Pagination via "Load more" button
    - Filter by Australia location
    """

    name = "Insight Partners"
    base_url = "https://jobs.insightpartners.com/jobs"

    def get_filtered_url(self, location: str = "Australia") -> str:
        """Get URL with location filter (base64 encoded)."""
        # Pre-encoded filter for Australia
        filters = {
            "Australia": "eyJzZWFyY2hhYmxlX2xvY2F0aW9ucyI6WyJBdXN0cmFsaWEiXX0%3D",
            "Singapore": "eyJzZWFyY2hhYmxlX2xvY2F0aW9ucyI6WyJTaW5nYXBvcmUiXX0%3D",
            "Remote": "eyJzZWFyY2hhYmxlX2xvY2F0aW9ucyI6WyJSZW1vdGUiXX0%3D",
        }
        filter_param = filters.get(location, filters["Australia"])
        return f"{self.base_url}?filter={filter_param}"

    async def handle_pagination(self, page: Page) -> None:
        """Click 'Load more' button until all jobs are loaded."""
        max_clicks = 15
        for i in range(max_clicks):
            try:
                load_more = page.locator('button:has-text("Load more")')
                if await load_more.count() > 0 and await load_more.is_visible():
                    await load_more.click()
                    await asyncio.sleep(1.5)
                    print(f"      Loading more ({i+1})...")
                else:
                    break
            except:
                break

    async def extract_jobs(self, page: Page) -> List[Dict]:
        """Extract jobs from Getro-style job cards."""
        jobs = []

        # Getro uses links with /companies/*/jobs/* pattern
        job_links = await page.query_selector_all('a[href*="/companies/"][href*="/jobs/"]')

        seen_urls = set()
        for link in job_links:
            try:
                href = await link.get_attribute('href')
                if not href or href in seen_urls:
                    continue
                seen_urls.add(href)

                text = await link.inner_text()
                lines = [l.strip() for l in text.split('\n') if l.strip()]

                if not lines:
                    continue

                title = lines[0]

                # Extract company from URL: /companies/company-name/jobs/
                company = ""
                match = re.search(r'/companies/([^/]+)/', href)
                if match:
                    company = match.group(1).replace('-', ' ').title()
                    # Clean numbered suffixes
                    company = re.sub(r'\s*\d+\s*[A-Fa-f0-9\-]+$', '', company)

                # Find location in text
                location = "Australia"
                for line in lines[1:4]:
                    if any(loc in line.lower() for loc in APAC_LOCATIONS):
                        location = line
                        break

                full_url = f"https://jobs.insightpartners.com{href}" if not href.startswith('http') else href

                job = {
                    "title": title,
                    "company": company,
                    "location": location,
                    "url": full_url,
                }
                jobs.append(self.add_metadata(job))

            except Exception as e:
                continue

        return jobs

    async def scrape(self) -> List[Dict]:
        """Main scrape method for Insight Partners."""
        print(f"🔍 Scraping {self.name}...")

        async with async_playwright() as p:
            browser, context = await create_browser_context(p)
            page = await context.new_page()

            try:
                url = self.get_filtered_url("Australia")
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                await asyncio.sleep(5)  # Wait for JS render

                await self.handle_pagination(page)
                await asyncio.sleep(2)

                self.jobs = await self.extract_jobs(page)
                print(f"   ✅ Found {len(self.jobs)} jobs")

            except Exception as e:
                print(f"   ❌ Error: {e}")
            finally:
                await browser.close()

        return self.jobs


# =============================================================================
# INDEX VENTURES SCRAPER
# Pagination: URL-based page numbers (/sydney-australia/1, /2, etc.)
# Platform: Custom Vue.js
# =============================================================================

class IndexVenturesScraper(BaseJobScraper):
    """
    Index Ventures job board scraper.
    - Custom Vue.js frontend
    - Pagination via URL path: /location/page_number
    - Need to wait for Vue to render (check for [[ templates)
    """

    name = "Index Ventures"
    base_url = "https://www.indexventures.com/startup-jobs"

    def get_page_url(self, location: str, page_num: int) -> str:
        """Get URL for specific page."""
        return f"{self.base_url}/{location}/{page_num}"

    async def wait_for_vue_render(self, page: Page, max_wait: int = 20) -> None:
        """Wait for Vue.js to process templates."""
        for _ in range(max_wait):
            html = await page.content()
            # Vue templates use [[ ]] syntax - if present, not yet rendered
            if '[[' not in html or ']]' not in html:
                break
            await asyncio.sleep(0.5)
        await asyncio.sleep(2)  # Extra buffer

    async def handle_pagination(self, page: Page) -> None:
        """URL-based pagination - handled in scrape() method."""
        pass

    async def extract_jobs(self, page: Page) -> List[Dict]:
        """Extract jobs using JavaScript evaluation for Vue-rendered content."""
        jobs = []

        # Use JS to extract rendered content
        job_data = await page.evaluate('''() => {
            const jobs = [];

            // Try multiple selectors for job results
            const selectors = [
                '[class*="result"]',
                '[class*="job"]',
                '[class*="SearchResults"] a',
                'a[href*="/job/"]'
            ];

            for (const selector of selectors) {
                const elements = document.querySelectorAll(selector);
                elements.forEach(el => {
                    const text = el.innerText;
                    const link = el.querySelector('a') || el;
                    const href = link.getAttribute ? link.getAttribute('href') : '';
                    if (text && text.length > 10) {
                        jobs.push({text: text, href: href || ''});
                    }
                });
                if (jobs.length > 0) break;
            }
            return jobs;
        }''')

        for item in job_data:
            try:
                text = item.get('text', '')
                href = item.get('href', '')

                lines = [l.strip() for l in text.split('\n') if l.strip()]
                if len(lines) < 2:
                    continue

                title = lines[0]
                company = lines[1] if len(lines) > 1 else ""

                # Find location
                location = "Sydney, Australia"
                for line in lines:
                    if any(loc in line.lower() for loc in APAC_LOCATIONS):
                        location = line
                        break

                full_url = href if href.startswith('http') else f"https://www.indexventures.com{href}" if href else ""

                job = {
                    "title": title,
                    "company": company,
                    "location": location,
                    "url": full_url,
                }
                jobs.append(self.add_metadata(job))

            except:
                continue

        return jobs

    async def scrape(self) -> List[Dict]:
        """Main scrape with URL-based pagination."""
        print(f"🔍 Scraping {self.name}...")

        locations = ["sydney-australia", "melbourne-australia", "australia"]
        max_pages = 10

        async with async_playwright() as p:
            browser, context = await create_browser_context(p)
            page = await context.new_page()

            try:
                for location in locations:
                    print(f"   Location: {location}")

                    for page_num in range(1, max_pages + 1):
                        url = self.get_page_url(location, page_num)
                        print(f"      Page {page_num}...")

                        try:
                            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                            await self.wait_for_vue_render(page)

                            page_jobs = await self.extract_jobs(page)

                            if not page_jobs:
                                print(f"      No more jobs, moving to next location")
                                break

                            self.jobs.extend(page_jobs)
                            print(f"      Found {len(page_jobs)} jobs")

                        except Exception as e:
                            print(f"      Page error: {e}")
                            break

                # Dedupe by URL
                seen = set()
                unique = []
                for job in self.jobs:
                    if job['url'] not in seen:
                        seen.add(job['url'])
                        unique.append(job)
                self.jobs = unique

                print(f"   ✅ Total: {len(self.jobs)} unique jobs")

            except Exception as e:
                print(f"   ❌ Error: {e}")
            finally:
                await browser.close()

        return self.jobs


# =============================================================================
# SEQUOIA CAPITAL SCRAPER
# Pagination: Infinite scroll
# Platform: Getro
# =============================================================================

class SequoiaScraper(BaseJobScraper):
    """
    Sequoia Capital job board scraper.
    - Uses Getro platform
    - Pagination via infinite scroll
    - Filter by location in URL params
    """

    name = "Sequoia Capital"
    base_url = "https://jobs.sequoiacap.com/jobs"

    def get_filtered_url(self, location: str = "Australia") -> str:
        """Get URL with location filter."""
        return f"{self.base_url}?locations={location}"

    async def handle_pagination(self, page: Page) -> None:
        """Scroll to bottom to trigger infinite scroll loading."""
        max_scrolls = 15
        last_height = 0

        for i in range(max_scrolls):
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await asyncio.sleep(1.5)

            new_height = await page.evaluate('document.body.scrollHeight')
            if new_height == last_height:
                print(f"      Reached end after {i+1} scrolls")
                break
            last_height = new_height
            print(f"      Scrolling ({i+1})...")

    async def extract_jobs(self, page: Page) -> List[Dict]:
        """Extract jobs from Getro-style infinite scroll page."""
        jobs = []

        job_data = await page.evaluate('''() => {
            const jobs = [];
            const links = document.querySelectorAll('a[href*="/jobs/"]');
            links.forEach(link => {
                const text = link.innerText;
                const href = link.getAttribute('href');
                if (text && text.length > 5 && href) {
                    jobs.push({text: text, href: href});
                }
            });
            return jobs;
        }''')

        seen = set()
        for item in job_data:
            try:
                text = item.get('text', '')
                href = item.get('href', '')

                if not href or href in seen:
                    continue
                seen.add(href)

                lines = [l.strip() for l in text.split('\n') if l.strip()]
                if not lines:
                    continue

                job = {
                    "title": lines[0],
                    "company": lines[1] if len(lines) > 1 else "",
                    "location": lines[2] if len(lines) > 2 else "Australia",
                    "url": href if href.startswith('http') else f"https://jobs.sequoiacap.com{href}",
                }
                jobs.append(self.add_metadata(job))

            except:
                continue

        return jobs

    async def scrape(self) -> List[Dict]:
        """Main scrape with infinite scroll pagination."""
        print(f"🔍 Scraping {self.name}...")

        async with async_playwright() as p:
            browser, context = await create_browser_context(p)
            page = await context.new_page()

            try:
                url = self.get_filtered_url("Australia")
                await page.goto(url, wait_until='domcontentloaded', timeout=60000)
                await asyncio.sleep(5)

                await self.handle_pagination(page)

                self.jobs = await self.extract_jobs(page)
                print(f"   ✅ Found {len(self.jobs)} jobs")

            except Exception as e:
                print(f"   ❌ Error: {e}")
            finally:
                await browser.close()

        return self.jobs


# =============================================================================
# LIGHTSPEED VP SCRAPER
# Pagination: Infinite scroll
# Platform: Getro
# =============================================================================

class LightspeedScraper(BaseJobScraper):
    """
    Lightspeed Venture Partners job board scraper.
    - Uses Getro platform
    - Pagination via infinite scroll
    - No location filter - must filter results manually
    """

    name = "Lightspeed VP"
    base_url = "https://jobs.lsvp.com/jobs"

    async def handle_pagination(self, page: Page) -> None:
        """Scroll to load all jobs."""
        max_scrolls = 15
        last_height = 0

        for i in range(max_scrolls):
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await asyncio.sleep(1.5)

            new_height = await page.evaluate('document.body.scrollHeight')
            if new_height == last_height:
                break
            last_height = new_height

    async def extract_jobs(self, page: Page) -> List[Dict]:
        """Extract APAC-relevant jobs only."""
        jobs = []

        job_data = await page.evaluate('''() => {
            const jobs = [];
            const links = document.querySelectorAll('a[href*="/jobs/"]');
            links.forEach(link => {
                const text = link.innerText;
                const href = link.getAttribute('href');
                if (text && text.length > 5) {
                    jobs.push({text: text, href: href});
                }
            });
            return jobs;
        }''')

        seen = set()
        for item in job_data:
            try:
                text = item.get('text', '')
                href = item.get('href', '')

                if not href or href in seen:
                    continue

                # Filter for APAC locations
                text_lower = text.lower()
                if not any(loc in text_lower for loc in APAC_LOCATIONS):
                    continue

                seen.add(href)

                lines = [l.strip() for l in text.split('\n') if l.strip()]
                if not lines:
                    continue

                job = {
                    "title": lines[0],
                    "company": lines[1] if len(lines) > 1 else "",
                    "location": lines[2] if len(lines) > 2 else "APAC",
                    "url": href if href.startswith('http') else f"https://jobs.lsvp.com{href}",
                }
                jobs.append(self.add_metadata(job))

            except:
                continue

        return jobs

    async def scrape(self) -> List[Dict]:
        """Main scrape with APAC filtering."""
        print(f"🔍 Scraping {self.name} (APAC filter)...")

        async with async_playwright() as p:
            browser, context = await create_browser_context(p)
            page = await context.new_page()

            try:
                await page.goto(self.base_url, wait_until='domcontentloaded', timeout=60000)
                await asyncio.sleep(5)

                await self.handle_pagination(page)

                self.jobs = await self.extract_jobs(page)
                print(f"   ✅ Found {len(self.jobs)} APAC jobs")

            except Exception as e:
                print(f"   ❌ Error: {e}")
            finally:
                await browser.close()

        return self.jobs


# =============================================================================
# ANDREESSEN HOROWITZ (a16z) SCRAPER
# Pagination: Load more button
# Platform: Custom
# =============================================================================

class A16ZScraper(BaseJobScraper):
    """
    Andreessen Horowitz job board scraper.
    - Custom platform
    - Jobs listed at portfolio company level
    """

    name = "Andreessen Horowitz"
    base_url = "https://jobs.a]16z.com/jobs"

    async def handle_pagination(self, page: Page) -> None:
        """Click load more buttons."""
        max_clicks = 20
        for i in range(max_clicks):
            try:
                # Try different button selectors
                for selector in ['button:has-text("Load more")', 'button:has-text("Show more")', '[class*="load-more"]']:
                    btn = page.locator(selector)
                    if await btn.count() > 0 and await btn.is_visible():
                        await btn.click()
                        await asyncio.sleep(1.5)
                        break
                else:
                    break
            except:
                break

    async def extract_jobs(self, page: Page) -> List[Dict]:
        """Extract jobs with APAC filter."""
        jobs = []

        job_data = await page.evaluate('''() => {
            const jobs = [];
            const links = document.querySelectorAll('a[href*="/jobs/"], a[href*="/job/"]');
            links.forEach(link => {
                const text = link.innerText;
                const href = link.getAttribute('href');
                if (text && text.length > 5) {
                    jobs.push({text: text, href: href});
                }
            });
            return jobs;
        }''')

        seen = set()
        for item in job_data:
            try:
                text = item.get('text', '')
                href = item.get('href', '')

                if not href or href in seen:
                    continue

                # Filter for APAC
                text_lower = text.lower()
                if not any(loc in text_lower for loc in APAC_LOCATIONS):
                    continue

                seen.add(href)
                lines = [l.strip() for l in text.split('\n') if l.strip()]
                if not lines:
                    continue

                job = {
                    "title": lines[0],
                    "company": lines[1] if len(lines) > 1 else "",
                    "location": lines[2] if len(lines) > 2 else "APAC",
                    "url": href if href.startswith('http') else f"https://jobs.a]16z.com{href}",
                }
                jobs.append(self.add_metadata(job))

            except:
                continue

        return jobs

    async def scrape(self) -> List[Dict]:
        """Main scrape method."""
        print(f"🔍 Scraping {self.name} (APAC filter)...")

        async with async_playwright() as p:
            browser, context = await create_browser_context(p)
            page = await context.new_page()

            try:
                await page.goto(self.base_url, wait_until='domcontentloaded', timeout=60000)
                await asyncio.sleep(5)

                await self.handle_pagination(page)

                self.jobs = await self.extract_jobs(page)
                print(f"   ✅ Found {len(self.jobs)} APAC jobs")

            except Exception as e:
                print(f"   ❌ Error: {e}")
            finally:
                await browser.close()

        return self.jobs


# =============================================================================
# GREYLOCK PARTNERS SCRAPER
# Pagination: Infinite scroll
# Platform: Getro
# =============================================================================

class GreylockScraper(BaseJobScraper):
    """Greylock Partners - uses Getro platform with infinite scroll."""

    name = "Greylock Partners"
    base_url = "https://jobs.greylock.com/jobs"

    async def handle_pagination(self, page: Page) -> None:
        """Infinite scroll pagination."""
        max_scrolls = 15
        last_height = 0

        for i in range(max_scrolls):
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await asyncio.sleep(1.5)
            new_height = await page.evaluate('document.body.scrollHeight')
            if new_height == last_height:
                break
            last_height = new_height

    async def extract_jobs(self, page: Page) -> List[Dict]:
        """Extract APAC jobs."""
        jobs = []

        job_data = await page.evaluate('''() => {
            const jobs = [];
            const links = document.querySelectorAll('a[href*="/jobs/"]');
            links.forEach(link => {
                const text = link.innerText;
                const href = link.getAttribute('href');
                if (text && text.length > 5) {
                    jobs.push({text: text, href: href});
                }
            });
            return jobs;
        }''')

        seen = set()
        for item in job_data:
            try:
                text = item.get('text', '')
                href = item.get('href', '')

                if not href or href in seen:
                    continue

                text_lower = text.lower()
                if not any(loc in text_lower for loc in APAC_LOCATIONS):
                    continue

                seen.add(href)
                lines = [l.strip() for l in text.split('\n') if l.strip()]
                if not lines:
                    continue

                job = {
                    "title": lines[0],
                    "company": lines[1] if len(lines) > 1 else "",
                    "location": lines[2] if len(lines) > 2 else "APAC",
                    "url": href if href.startswith('http') else f"https://jobs.greylock.com{href}",
                }
                jobs.append(self.add_metadata(job))

            except:
                continue

        return jobs

    async def scrape(self) -> List[Dict]:
        """Main scrape."""
        print(f"🔍 Scraping {self.name} (APAC filter)...")

        async with async_playwright() as p:
            browser, context = await create_browser_context(p)
            page = await context.new_page()

            try:
                await page.goto(self.base_url, wait_until='domcontentloaded', timeout=60000)
                await asyncio.sleep(5)
                await self.handle_pagination(page)
                self.jobs = await self.extract_jobs(page)
                print(f"   ✅ Found {len(self.jobs)} APAC jobs")
            except Exception as e:
                print(f"   ❌ Error: {e}")
            finally:
                await browser.close()

        return self.jobs


# =============================================================================
# WIZ.IO DIRECT SCRAPER
# Pagination: Load more / infinite scroll
# Platform: Greenhouse embedded
# =============================================================================

class WizScraper(BaseJobScraper):
    """
    Wiz.io careers page scraper.
    - Company direct hire page
    - Greenhouse backend
    """

    name = "Wiz"
    base_url = "https://www.wiz.io/careers"
    jobs_api = "https://boards-api.greenhouse.io/v1/boards/wiz/jobs"

    async def handle_pagination(self, page: Page) -> None:
        """Wiz uses Greenhouse API - no pagination needed on page."""
        pass

    async def extract_jobs(self, page: Page) -> List[Dict]:
        """Extract jobs via Greenhouse API."""
        jobs = []

        try:
            # Use Greenhouse API directly
            response = await page.goto(self.jobs_api, wait_until='domcontentloaded')
            content = await page.content()

            # Parse JSON from page
            import json
            # Find JSON in the page content
            start = content.find('[')
            end = content.rfind(']') + 1
            if start >= 0 and end > start:
                json_str = content[start:end]
                # This might fail - Greenhouse API returns JSON directly
        except:
            pass

        # Fallback: scrape the careers page directly
        await page.goto(self.base_url, wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(5)

        job_data = await page.evaluate('''() => {
            const jobs = [];
            // Wiz uses various job listing formats
            const links = document.querySelectorAll('a[href*="greenhouse"], a[href*="/careers/"], a[href*="job"]');
            links.forEach(link => {
                const text = link.innerText;
                const href = link.getAttribute('href');
                if (text && text.length > 5 && href) {
                    jobs.push({text: text, href: href});
                }
            });
            return jobs;
        }''')

        seen = set()
        for item in job_data:
            try:
                text = item.get('text', '')
                href = item.get('href', '')

                if not href or href in seen:
                    continue

                # Filter for APAC/Sales keywords
                text_lower = text.lower()
                has_apac = any(loc in text_lower for loc in APAC_LOCATIONS)
                has_gtm = any(kw in text_lower for kw in GTM_KEYWORDS)

                if not (has_apac or has_gtm):
                    continue

                seen.add(href)
                lines = [l.strip() for l in text.split('\n') if l.strip()]
                if not lines:
                    continue

                job = {
                    "title": lines[0],
                    "company": "Wiz",
                    "location": lines[1] if len(lines) > 1 else "See listing",
                    "url": href if href.startswith('http') else f"https://www.wiz.io{href}",
                }
                jobs.append(self.add_metadata(job))

            except:
                continue

        return jobs

    async def scrape(self) -> List[Dict]:
        """Scrape Wiz careers."""
        print(f"🔍 Scraping {self.name}...")

        async with async_playwright() as p:
            browser, context = await create_browser_context(p)
            page = await context.new_page()

            try:
                self.jobs = await self.extract_jobs(page)
                print(f"   ✅ Found {len(self.jobs)} relevant jobs")
            except Exception as e:
                print(f"   ❌ Error: {e}")
            finally:
                await browser.close()

        return self.jobs


# =============================================================================
# MAIN ORCHESTRATOR
# =============================================================================

class VCJobScraperOrchestrator:
    """Orchestrates all scrapers and aggregates results."""

    def __init__(self):
        self.scrapers: List[BaseJobScraper] = [
            InsightPartnersScraper(),
            IndexVenturesScraper(),
            SequoiaScraper(),
            LightspeedScraper(),
            # A16ZScraper(),  # Uncomment to enable
            # GreylockScraper(),  # Uncomment to enable
            # WizScraper(),  # Uncomment to enable
        ]
        self.all_jobs: List[Dict] = []
        self.gtm_jobs: List[Dict] = []
        self.output_dir = Path("./data")
        self.output_dir.mkdir(exist_ok=True)

    def add_scraper(self, scraper: BaseJobScraper):
        """Add a custom scraper."""
        self.scrapers.append(scraper)

    async def run_all(self) -> Dict:
        """Run all scrapers and aggregate results."""
        print("\n" + "="*60)
        print("🚀 VC Job Scraper - Modular Version")
        print("="*60 + "\n")

        results = {}

        for scraper in self.scrapers:
            jobs = await scraper.scrape()
            results[scraper.name] = len(jobs)
            self.all_jobs.extend(jobs)
            print()

        # Deduplicate by URL
        seen = set()
        unique = []
        for job in self.all_jobs:
            url = job.get('url', '')
            if url and url not in seen:
                seen.add(url)
                unique.append(job)

        self.all_jobs = unique
        self.all_jobs.sort(key=lambda x: x.get('match_score', 0), reverse=True)

        # Filter GTM roles
        self.gtm_jobs = [j for j in self.all_jobs if is_gtm_role(j.get('title', ''))]

        # Save results
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        all_file = self.output_dir / f"vc_all_jobs_{ts}.json"
        with open(all_file, 'w') as f:
            json.dump(self.all_jobs, f, indent=2)

        gtm_file = self.output_dir / f"vc_gtm_matches_{ts}.json"
        with open(gtm_file, 'w') as f:
            json.dump(self.gtm_jobs, f, indent=2)

        # Print summary
        print("="*60)
        print("📊 RESULTS")
        print("="*60)
        for name, count in results.items():
            print(f"   {name}: {count} jobs")
        print("   " + "─"*30)
        print(f"   Total unique: {len(self.all_jobs)} jobs")
        print(f"   GTM matches: {len(self.gtm_jobs)} jobs")
        print(f"\n📁 Saved to:")
        print(f"   {all_file}")
        print(f"   {gtm_file}")

        # Print top matches
        print("\n" + "="*60)
        print("🎯 TOP 15 GTM MATCHES")
        print("="*60)

        for i, job in enumerate(self.gtm_jobs[:15], 1):
            score = job.get('match_score', 0)
            emoji = "🔥" if score >= 80 else "⭐" if score >= 70 else "👍"
            print(f"\n{i}. {emoji} [{score}%] {job['title']}")
            print(f"   Company: {job.get('company') or 'See link'}")
            print(f"   Location: {job.get('location', 'N/A')}")
            print(f"   Source: {job.get('source')}")
            print(f"   {job.get('url', '')[:80]}")

        print("\n" + "="*60)

        return {
            "total": len(self.all_jobs),
            "gtm_matches": len(self.gtm_jobs),
            "by_source": results,
            "top_jobs": self.gtm_jobs[:15]
        }


# =============================================================================
# ENTRY POINT
# =============================================================================

async def main():
    orchestrator = VCJobScraperOrchestrator()

    # Optionally add more scrapers
    # orchestrator.add_scraper(WizScraper())

    results = await orchestrator.run_all()
    return results


if __name__ == "__main__":
    asyncio.run(main())
