#!/usr/bin/env python3
"""
Universal Job Scraper
- Auto-detects platform type (Greenhouse, Lever, Workday, Ashby, etc.)
- Works with any job website
- Configurable via JSON targets file
- Handles various pagination patterns
"""
from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Callable
from urllib.parse import urlparse, urljoin
from dataclasses import dataclass, field
from enum import Enum

from playwright.async_api import async_playwright, Page, Browser, BrowserContext


# =============================================================================
# CONFIGURATION
# =============================================================================

class Platform(Enum):
    """Known job board platforms."""
    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    WORKDAY = "workday"
    ASHBY = "ashby"
    GETRO = "getro"  # Used by many VCs
    BAMBOOHR = "bamboohr"
    SMARTRECRUITERS = "smartrecruiters"
    CUSTOM = "custom"
    UNKNOWN = "unknown"


@dataclass
class ScrapingTarget:
    """A target to scrape."""
    name: str
    url: str
    type: str = "company"  # "company" or "vc_portfolio"
    platform: Optional[str] = None  # Auto-detected if not specified
    location_filter: Optional[str] = None
    enabled: bool = True


# Default targets - add your own or load from JSON
DEFAULT_TARGETS = [
    # Top VCs
    {"name": "Sequoia Capital", "url": "https://jobs.sequoiacap.com/jobs", "type": "vc_portfolio", "platform": "getro", "location_filter": "Australia"},
    {"name": "Insight Partners", "url": "https://jobs.insightpartners.com/jobs", "type": "vc_portfolio", "platform": "getro", "location_filter": "Australia"},
    {"name": "Index Ventures", "url": "https://www.indexventures.com/startup-jobs/sydney-australia", "type": "vc_portfolio", "platform": "custom"},
    {"name": "Lightspeed VP", "url": "https://jobs.lsvp.com/jobs", "type": "vc_portfolio", "platform": "getro"},
    {"name": "Accel", "url": "https://jobs.accel.com/jobs", "type": "vc_portfolio", "platform": "getro"},
    {"name": "a16z", "url": "https://jobs.a16z.com/jobs", "type": "vc_portfolio", "platform": "getro"},
    {"name": "Greylock", "url": "https://jobs.greylock.com/jobs", "type": "vc_portfolio", "platform": "getro"},
    {"name": "General Catalyst", "url": "https://jobs.generalcatalyst.com/jobs", "type": "vc_portfolio", "platform": "getro"},
    {"name": "Bessemer", "url": "https://jobs.bvp.com/jobs", "type": "vc_portfolio", "platform": "getro"},
    {"name": "NEA", "url": "https://jobs.nea.com/jobs", "type": "vc_portfolio", "platform": "getro"},

    # Top AI Companies
    {"name": "Anthropic", "url": "https://www.anthropic.com/careers", "type": "company", "platform": "greenhouse"},
    {"name": "OpenAI", "url": "https://openai.com/careers", "type": "company", "platform": "greenhouse"},
    {"name": "Mistral", "url": "https://mistral.ai/careers", "type": "company", "platform": "ashby"},
    {"name": "Cohere", "url": "https://cohere.com/careers", "type": "company", "platform": "greenhouse"},
    {"name": "Hugging Face", "url": "https://huggingface.co/jobs", "type": "company", "platform": "ashby"},
    {"name": "Stability AI", "url": "https://stability.ai/careers", "type": "company", "platform": "greenhouse"},
    {"name": "Runway", "url": "https://runwayml.com/careers", "type": "company", "platform": "greenhouse"},
    {"name": "Scale AI", "url": "https://scale.com/careers", "type": "company", "platform": "lever"},
    {"name": "Databricks", "url": "https://www.databricks.com/company/careers", "type": "company", "platform": "greenhouse"},
    {"name": "Datadog", "url": "https://careers.datadoghq.com", "type": "company", "platform": "greenhouse"},

    # Cybersecurity / Cloud
    {"name": "Wiz", "url": "https://www.wiz.io/careers", "type": "company", "platform": "greenhouse"},
    {"name": "Snyk", "url": "https://snyk.io/careers", "type": "company", "platform": "greenhouse"},
    {"name": "Lacework", "url": "https://www.lacework.com/careers", "type": "company", "platform": "greenhouse"},
]

# Keywords for filtering
GTM_KEYWORDS = [
    'sales', 'account', 'business development', 'bd ', 'bdr', 'sdr',
    'gtm', 'go-to-market', 'commercial', 'revenue', 'partnerships',
    'partner', 'customer success', 'solutions', 'presales',
    'enterprise', 'strategic', 'field'
]

SENIOR_KEYWORDS = [
    'director', 'head of', 'vp ', 'vice president', 'chief',
    'manager', 'lead', 'senior', 'principal', 'executive',
    'enterprise', 'strategic', 'regional'
]

JUNIOR_KEYWORDS = ['intern', 'graduate', 'entry level', 'coordinator', 'assistant', 'junior', 'trainee']

APAC_LOCATIONS = [
    'australia', 'sydney', 'melbourne', 'brisbane', 'perth',
    'singapore', 'apac', 'asia', 'remote', 'india', 'bangalore',
    'mumbai', 'tokyo', 'seoul', 'hong kong', 'new zealand', 'auckland'
]


# =============================================================================
# UTILITIES
# =============================================================================

def is_gtm_role(title: str) -> bool:
    """Check if title is a GTM role."""
    title_lower = title.lower()
    if any(kw in title_lower for kw in JUNIOR_KEYWORDS):
        return False
    return any(kw in title_lower for kw in GTM_KEYWORDS)


def calculate_match_score(job: Dict) -> int:
    """Calculate match score."""
    score = 50
    title = job.get('title', '').lower()

    if any(kw in title for kw in ['director', 'head of', 'vp ', 'chief']): score += 20
    elif any(kw in title for kw in ['manager', 'lead', 'senior']): score += 10

    if 'enterprise' in title: score += 15
    if 'account executive' in title: score += 15
    if 'partner' in title: score += 10
    if 'sales' in title: score += 10
    if 'gtm' in title: score += 15
    if 'ai' in title or 'ml' in title: score += 15

    loc = job.get('location', '').lower()
    if 'sydney' in loc: score += 10
    elif 'australia' in loc: score += 5
    elif 'remote' in loc: score += 5

    if any(kw in title for kw in JUNIOR_KEYWORDS): score -= 30

    return min(100, max(0, score))


def is_apac_location(text: str) -> bool:
    """Check if text contains APAC location."""
    text_lower = text.lower()
    return any(loc in text_lower for loc in APAC_LOCATIONS)


async def create_browser_context(playwright) -> tuple[Browser, BrowserContext]:
    """Create browser with standard settings."""
    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context(
        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        viewport={'width': 1920, 'height': 1080}
    )
    return browser, context


# =============================================================================
# PLATFORM DETECTOR
# =============================================================================

class PlatformDetector:
    """Detects what job board platform a website uses."""

    @staticmethod
    async def detect(page: Page, url: str) -> Platform:
        """Detect the platform from page content and URL."""

        # Check URL patterns first
        url_lower = url.lower()

        if 'greenhouse.io' in url_lower or 'boards.greenhouse' in url_lower:
            return Platform.GREENHOUSE
        if 'lever.co' in url_lower or 'jobs.lever' in url_lower:
            return Platform.LEVER
        if 'myworkdayjobs.com' in url_lower or 'workday' in url_lower:
            return Platform.WORKDAY
        if 'ashbyhq.com' in url_lower:
            return Platform.ASHBY
        if 'smartrecruiters.com' in url_lower:
            return Platform.SMARTRECRUITERS
        if 'bamboohr.com' in url_lower:
            return Platform.BAMBOOHR

        # Check page content for platform signatures
        try:
            html = await page.content()
            html_lower = html.lower()

            # Greenhouse signatures
            if 'greenhouse' in html_lower or 'grnhse' in html_lower:
                return Platform.GREENHOUSE

            # Lever signatures
            if 'lever.co' in html_lower or 'lever-jobs' in html_lower:
                return Platform.LEVER

            # Ashby signatures
            if 'ashbyhq' in html_lower or 'ashby' in html_lower:
                return Platform.ASHBY

            # Getro signatures (used by VCs)
            if 'getro' in html_lower or 'jobs.getro' in html_lower:
                return Platform.GETRO

            # Workday signatures
            if 'workday' in html_lower or 'myworkday' in html_lower:
                return Platform.WORKDAY

        except:
            pass

        return Platform.UNKNOWN


# =============================================================================
# PLATFORM-SPECIFIC SCRAPERS
# =============================================================================

class GreenhouseScraper:
    """Scraper for Greenhouse-powered job boards."""

    @staticmethod
    async def get_jobs_via_api(company_slug: str) -> List[Dict]:
        """Try to get jobs via Greenhouse public API."""
        jobs = []
        api_url = f"https://boards-api.greenhouse.io/v1/boards/{company_slug}/jobs"

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                response = await page.goto(api_url, wait_until='domcontentloaded', timeout=15000)
                content = await page.content()

                # Parse JSON response
                # Greenhouse returns JSON directly, but wrapped in HTML
                text = await page.inner_text('body')
                data = json.loads(text)

                for job_data in data.get('jobs', []):
                    job = {
                        "title": job_data.get('title', ''),
                        "location": job_data.get('location', {}).get('name', ''),
                        "url": job_data.get('absolute_url', ''),
                        "department": job_data.get('departments', [{}])[0].get('name', '') if job_data.get('departments') else '',
                    }
                    jobs.append(job)

            except Exception as e:
                pass
            finally:
                await browser.close()

        return jobs

    @staticmethod
    async def scrape_page(page: Page, base_url: str) -> List[Dict]:
        """Scrape jobs from Greenhouse-embedded careers page."""
        jobs = []

        await page.goto(base_url, wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(3)

        # Try multiple selectors for Greenhouse embeds
        job_data = await page.evaluate('''() => {
            const jobs = [];
            const selectors = [
                'a[href*="greenhouse.io/"]',
                'a[href*="/jobs/"]',
                '[class*="job"] a',
                '[class*="opening"] a',
                '[class*="position"] a',
                'div[class*="job-post"] a',
                'tr[class*="job"] a'
            ];

            const seen = new Set();

            for (const selector of selectors) {
                document.querySelectorAll(selector).forEach(el => {
                    const href = el.getAttribute('href');
                    const text = el.innerText || el.textContent;

                    if (href && text && text.length > 3 && !seen.has(href)) {
                        seen.add(href);
                        jobs.push({
                            text: text.trim(),
                            href: href,
                            parent_text: el.closest('div, tr, li')?.innerText || ''
                        });
                    }
                });
            }
            return jobs;
        }''')

        for item in job_data:
            try:
                text = item.get('text', '')
                href = item.get('href', '')
                parent = item.get('parent_text', '')

                lines = [l.strip() for l in text.split('\n') if l.strip()]
                if not lines:
                    continue

                # Extract location from parent text
                location = ""
                parent_lines = [l.strip() for l in parent.split('\n') if l.strip()]
                for line in parent_lines:
                    if is_apac_location(line) or any(x in line.lower() for x in ['remote', 'hybrid', 'office']):
                        location = line
                        break

                full_url = href if href.startswith('http') else urljoin(base_url, href)

                job = {
                    "title": lines[0],
                    "location": location or "See listing",
                    "url": full_url,
                }
                jobs.append(job)

            except:
                continue

        return jobs


class LeverScraper:
    """Scraper for Lever-powered job boards."""

    @staticmethod
    async def scrape_page(page: Page, base_url: str) -> List[Dict]:
        """Scrape jobs from Lever careers page."""
        jobs = []

        await page.goto(base_url, wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(3)

        # Lever has a consistent structure
        job_data = await page.evaluate('''() => {
            const jobs = [];
            const postings = document.querySelectorAll('.posting, [class*="lever-job"], a[href*="lever.co/"]');

            postings.forEach(posting => {
                const titleEl = posting.querySelector('.posting-title, h5, [class*="title"]');
                const locationEl = posting.querySelector('.posting-categories, .location, [class*="location"]');
                const linkEl = posting.querySelector('a[href*="lever.co"]') || posting;

                if (titleEl) {
                    jobs.push({
                        title: titleEl.innerText?.trim() || '',
                        location: locationEl?.innerText?.trim() || '',
                        url: linkEl.getAttribute?.('href') || ''
                    });
                }
            });

            return jobs;
        }''')

        for item in job_data:
            if item.get('title'):
                job = {
                    "title": item['title'],
                    "location": item.get('location', 'See listing'),
                    "url": item.get('url', base_url),
                }
                jobs.append(job)

        return jobs


class AshbyScraper:
    """Scraper for Ashby-powered job boards."""

    @staticmethod
    async def scrape_page(page: Page, base_url: str) -> List[Dict]:
        """Scrape jobs from Ashby careers page."""
        jobs = []

        await page.goto(base_url, wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(3)

        # Ashby typically has clean semantic markup
        job_data = await page.evaluate('''() => {
            const jobs = [];

            // Try Ashby-specific selectors
            const selectors = [
                'a[href*="ashbyhq.com"]',
                'a[href*="/jobs/"]',
                '[data-testid*="job"]',
                '.job-listing a',
                '[class*="JobListing"] a'
            ];

            const seen = new Set();

            for (const selector of selectors) {
                document.querySelectorAll(selector).forEach(el => {
                    const href = el.getAttribute('href');
                    const text = el.innerText?.trim();

                    if (href && text && text.length > 5 && !seen.has(href)) {
                        seen.add(href);

                        const parent = el.closest('div, li, tr');
                        const locationEl = parent?.querySelector('[class*="location"], [class*="Location"]');

                        jobs.push({
                            title: text.split('\\n')[0]?.trim() || text,
                            location: locationEl?.innerText?.trim() || '',
                            url: href
                        });
                    }
                });
            }

            return jobs;
        }''')

        for item in job_data:
            if item.get('title'):
                full_url = item['url'] if item['url'].startswith('http') else urljoin(base_url, item['url'])
                job = {
                    "title": item['title'],
                    "location": item.get('location', 'See listing'),
                    "url": full_url,
                }
                jobs.append(job)

        return jobs


class GetroScraper:
    """Scraper for Getro-powered VC job boards."""

    @staticmethod
    async def scrape_page(page: Page, base_url: str, location_filter: Optional[str] = None) -> List[Dict]:
        """Scrape jobs from Getro VC portfolio page."""
        jobs = []

        # Add location filter if specified
        url = base_url
        if location_filter:
            # Getro uses base64-encoded filters
            import base64
            filter_json = json.dumps({"searchable_locations": [location_filter]})
            filter_b64 = base64.b64encode(filter_json.encode()).decode()
            url = f"{base_url}?filter={filter_b64}"

        await page.goto(url, wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(5)

        # Click "Load more" until done
        for _ in range(15):
            try:
                load_more = page.locator('button:has-text("Load more")')
                if await load_more.count() > 0 and await load_more.is_visible():
                    await load_more.click()
                    await asyncio.sleep(1.5)
                else:
                    break
            except:
                break

        # Also try infinite scroll
        last_height = 0
        for _ in range(10):
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await asyncio.sleep(1)
            new_height = await page.evaluate('document.body.scrollHeight')
            if new_height == last_height:
                break
            last_height = new_height

        # Extract jobs
        job_data = await page.evaluate('''() => {
            const jobs = [];
            const links = document.querySelectorAll('a[href*="/companies/"][href*="/jobs/"], a[href*="/jobs/"]');
            const seen = new Set();

            links.forEach(link => {
                const href = link.getAttribute('href');
                const text = link.innerText;

                if (href && text && text.length > 5 && !seen.has(href)) {
                    seen.add(href);
                    jobs.push({text: text, href: href});
                }
            });

            return jobs;
        }''')

        for item in job_data:
            try:
                text = item.get('text', '')
                href = item.get('href', '')

                lines = [l.strip() for l in text.split('\n') if l.strip()]
                if not lines:
                    continue

                # Extract company from URL
                company = ""
                match = re.search(r'/companies/([^/]+)/', href)
                if match:
                    company = match.group(1).replace('-', ' ').title()
                    company = re.sub(r'\s*\d+\s*[A-Fa-f0-9\-]+$', '', company)

                # Find location
                location = location_filter or "See listing"
                for line in lines[1:4]:
                    if is_apac_location(line):
                        location = line
                        break

                parsed = urlparse(base_url)
                base_domain = f"{parsed.scheme}://{parsed.netloc}"
                full_url = href if href.startswith('http') else f"{base_domain}{href}"

                job = {
                    "title": lines[0],
                    "company": company,
                    "location": location,
                    "url": full_url,
                }
                jobs.append(job)

            except:
                continue

        return jobs


class GenericScraper:
    """Generic scraper for unknown platforms."""

    @staticmethod
    async def scrape_page(page: Page, base_url: str) -> List[Dict]:
        """Try to scrape any careers page."""
        jobs = []

        await page.goto(base_url, wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(5)

        # Scroll to load content
        for _ in range(5):
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await asyncio.sleep(1)

        # Try many different selectors
        job_data = await page.evaluate('''() => {
            const jobs = [];
            const selectors = [
                'a[href*="/job"]',
                'a[href*="/career"]',
                'a[href*="/position"]',
                'a[href*="/opening"]',
                'a[href*="greenhouse"]',
                'a[href*="lever"]',
                '[class*="job"] a',
                '[class*="career"] a',
                '[class*="position"] a',
                '[class*="opening"] a',
                '[class*="listing"] a',
                'article a',
                '.card a'
            ];

            const seen = new Set();

            for (const selector of selectors) {
                document.querySelectorAll(selector).forEach(el => {
                    const href = el.getAttribute('href');
                    const text = el.innerText?.trim();

                    // Filter out nav links, etc.
                    if (href && text && text.length > 10 && text.length < 200 && !seen.has(href)) {
                        // Skip if it looks like navigation
                        if (['home', 'about', 'contact', 'blog', 'news'].includes(text.toLowerCase())) {
                            return;
                        }
                        seen.add(href);

                        const parent = el.closest('div, li, article, tr');
                        jobs.push({
                            text: text,
                            href: href,
                            parent_text: parent?.innerText?.substring(0, 500) || ''
                        });
                    }
                });
            }

            return jobs;
        }''')

        for item in job_data:
            try:
                text = item.get('text', '')
                href = item.get('href', '')
                parent = item.get('parent_text', '')

                lines = [l.strip() for l in text.split('\n') if l.strip()]
                if not lines:
                    continue

                # Try to find location in parent text
                location = "See listing"
                for line in parent.split('\n'):
                    line = line.strip()
                    if is_apac_location(line) or any(x in line.lower() for x in ['remote', 'hybrid']):
                        location = line[:100]
                        break

                full_url = href if href.startswith('http') else urljoin(base_url, href)

                job = {
                    "title": lines[0][:200],
                    "location": location,
                    "url": full_url,
                }
                jobs.append(job)

            except:
                continue

        return jobs


# =============================================================================
# UNIVERSAL SCRAPER
# =============================================================================

class UniversalJobScraper:
    """
    Universal scraper that auto-detects platform and scrapes jobs.
    """

    def __init__(self, targets: Optional[List[Dict]] = None, filter_apac: bool = True, filter_gtm: bool = False):
        """
        Initialize scraper.

        Args:
            targets: List of target dicts with name, url, type, platform, location_filter
            filter_apac: Only keep APAC-relevant jobs
            filter_gtm: Only keep GTM roles
        """
        self.targets = targets or DEFAULT_TARGETS
        self.filter_apac = filter_apac
        self.filter_gtm = filter_gtm
        self.all_jobs: List[Dict] = []
        self.output_dir = Path("./data")
        self.output_dir.mkdir(exist_ok=True)

    def add_target(self, name: str, url: str, type: str = "company",
                   platform: Optional[str] = None, location_filter: Optional[str] = None):
        """Add a scraping target."""
        self.targets.append({
            "name": name,
            "url": url,
            "type": type,
            "platform": platform,
            "location_filter": location_filter,
            "enabled": True
        })

    def add_company(self, name: str, careers_url: str, platform: Optional[str] = None):
        """Shorthand to add a company target."""
        self.add_target(name, careers_url, "company", platform)

    def add_vc(self, name: str, jobs_url: str, location_filter: Optional[str] = "Australia"):
        """Shorthand to add a VC portfolio target."""
        self.add_target(name, jobs_url, "vc_portfolio", "getro", location_filter)

    async def scrape_target(self, target: Dict) -> List[Dict]:
        """Scrape a single target."""
        name = target.get('name', 'Unknown')
        url = target.get('url', '')
        platform_hint = target.get('platform')
        location_filter = target.get('location_filter')
        target_type = target.get('type', 'company')

        if not target.get('enabled', True):
            return []

        print(f"🔍 Scraping {name}...")
        jobs = []

        async with async_playwright() as p:
            browser, context = await create_browser_context(p)
            page = await context.new_page()

            try:
                # Determine platform
                if platform_hint:
                    platform = Platform(platform_hint)
                else:
                    await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                    platform = await PlatformDetector.detect(page, url)
                    print(f"   Detected platform: {platform.value}")

                # Use appropriate scraper
                if platform == Platform.GREENHOUSE:
                    jobs = await GreenhouseScraper.scrape_page(page, url)
                elif platform == Platform.LEVER:
                    jobs = await LeverScraper.scrape_page(page, url)
                elif platform == Platform.ASHBY:
                    jobs = await AshbyScraper.scrape_page(page, url)
                elif platform == Platform.GETRO:
                    jobs = await GetroScraper.scrape_page(page, url, location_filter)
                else:
                    jobs = await GenericScraper.scrape_page(page, url)

                # Add metadata
                for job in jobs:
                    job['source'] = name
                    job['source_type'] = target_type
                    if 'company' not in job or not job['company']:
                        job['company'] = name if target_type == 'company' else ''
                    job['match_score'] = calculate_match_score(job)
                    job['scraped_date'] = datetime.now().isoformat()

                # Filter if requested
                if self.filter_apac:
                    jobs = [j for j in jobs if is_apac_location(j.get('location', '') + ' ' + j.get('title', ''))]

                print(f"   ✅ Found {len(jobs)} jobs")

            except Exception as e:
                print(f"   ❌ Error: {e}")
            finally:
                await browser.close()

        return jobs

    async def scrape_all(self) -> Dict:
        """Scrape all targets."""
        print("\n" + "="*60)
        print("🚀 Universal Job Scraper")
        print("="*60 + "\n")

        results = {}

        for target in self.targets:
            if not target.get('enabled', True):
                continue

            jobs = await self.scrape_target(target)
            results[target['name']] = len(jobs)
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

        # Filter GTM if requested
        gtm_jobs = [j for j in self.all_jobs if is_gtm_role(j.get('title', ''))]

        # Save results
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        all_file = self.output_dir / f"universal_all_jobs_{ts}.json"
        with open(all_file, 'w') as f:
            json.dump(self.all_jobs, f, indent=2)

        gtm_file = self.output_dir / f"universal_gtm_jobs_{ts}.json"
        with open(gtm_file, 'w') as f:
            json.dump(gtm_jobs, f, indent=2)

        # Print summary
        print("="*60)
        print("📊 RESULTS")
        print("="*60)

        # Group by source type
        vc_total = sum(v for k, v in results.items() if any(t.get('type') == 'vc_portfolio' and t.get('name') == k for t in self.targets))
        company_total = sum(v for k, v in results.items()) - vc_total

        for name, count in results.items():
            print(f"   {name}: {count} jobs")
        print("   " + "─"*40)
        print(f"   Total unique: {len(self.all_jobs)} jobs")
        print(f"   GTM matches: {len(gtm_jobs)} jobs")

        print(f"\n📁 Saved to:")
        print(f"   {all_file}")
        print(f"   {gtm_file}")

        # Print top matches
        print("\n" + "="*60)
        print("🎯 TOP 20 MATCHES")
        print("="*60)

        display_jobs = gtm_jobs[:20] if self.filter_gtm else self.all_jobs[:20]
        for i, job in enumerate(display_jobs, 1):
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
            "gtm_matches": len(gtm_jobs),
            "by_source": results,
            "files": {
                "all": str(all_file),
                "gtm": str(gtm_file)
            }
        }

    @staticmethod
    def load_targets_from_file(filepath: str) -> List[Dict]:
        """Load targets from JSON file."""
        with open(filepath) as f:
            return json.load(f)

    def save_targets_to_file(self, filepath: str):
        """Save current targets to JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.targets, f, indent=2)


# =============================================================================
# CLI / ENTRY POINT
# =============================================================================

async def main():
    """Main entry point with example usage."""

    # Example 1: Use default targets (VCs + AI companies)
    scraper = UniversalJobScraper(filter_apac=True)

    # Example 2: Add custom targets
    # scraper.add_company("Stripe", "https://stripe.com/jobs")
    # scraper.add_vc("Tiger Global", "https://jobs.tigerglobal.com/jobs")

    # Example 3: Load from config file
    # targets = UniversalJobScraper.load_targets_from_file("my_targets.json")
    # scraper = UniversalJobScraper(targets=targets)

    results = await scraper.scrape_all()
    return results


if __name__ == "__main__":
    asyncio.run(main())
