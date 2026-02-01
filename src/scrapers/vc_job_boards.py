#!/usr/bin/env python3
"""
VC Portfolio Job Board Scraper
Handles JavaScript-rendered job boards with various pagination styles:
- Insight Partners (Getro - Load more button)
- Index Ventures (URL page numbers)
- Sequoia Capital (Query parameters)
"""

import asyncio
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

try:
    from playwright.async_api import async_playwright, Page, Browser
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("Warning: Playwright not installed. Run: pip install playwright && playwright install chromium")


class VCJobBoardScraper:
    """Scraper for VC portfolio company job boards."""

    def __init__(self, output_dir: str = "./data"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.all_jobs: List[Dict] = []
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    async def scrape_insight_partners(self, max_jobs: int = 200) -> List[Dict]:
        """
        Scrape Insight Partners job board (Getro-powered).
        Uses 'Load more' button pagination.
        """
        jobs = []
        url = "https://jobs.insightpartners.com/jobs?filter=eyJzZWFyY2hhYmxlX2xvY2F0aW9ucyI6WyJBdXN0cmFsaWEiXX0%3D"

        print(f"🔍 Scraping Insight Partners Australia jobs...")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            )
            page = await context.new_page()

            try:
                await page.goto(url, wait_until='networkidle', timeout=30000)
                await asyncio.sleep(2)  # Wait for dynamic content

                # Click "Load more" until all jobs are loaded or max reached
                load_more_clicks = 0
                while load_more_clicks < 10:  # Safety limit
                    try:
                        load_more = await page.query_selector('button:has-text("Load more")')
                        if load_more and await load_more.is_visible():
                            await load_more.click()
                            await asyncio.sleep(1.5)
                            load_more_clicks += 1
                            print(f"   Loaded more... (click {load_more_clicks})")
                        else:
                            break
                    except:
                        break

                # Extract job listings
                job_cards = await page.query_selector_all('[data-testid="job-card"], .job-card, article')

                for card in job_cards:
                    try:
                        job = await self._extract_getro_job(card, "Insight Partners")
                        if job and job.get('title'):
                            jobs.append(job)
                            if len(jobs) >= max_jobs:
                                break
                    except Exception as e:
                        continue

                print(f"   ✅ Found {len(jobs)} jobs from Insight Partners")

            except Exception as e:
                print(f"   ❌ Error scraping Insight Partners: {e}")
            finally:
                await browser.close()

        return jobs

    async def scrape_index_ventures(self, max_pages: int = 5) -> List[Dict]:
        """
        Scrape Index Ventures job board.
        Uses URL page numbers (/1, /2, /3, etc.)
        """
        jobs = []
        base_url = "https://www.indexventures.com/startup-jobs/sydney-australia"

        print(f"🔍 Scraping Index Ventures Sydney jobs...")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            )
            page = await context.new_page()

            for page_num in range(1, max_pages + 1):
                url = f"{base_url}/{page_num}"
                print(f"   Fetching page {page_num}...")

                try:
                    await page.goto(url, wait_until='networkidle', timeout=30000)
                    await asyncio.sleep(2)

                    # Extract job cards
                    job_elements = await page.query_selector_all('.job-result, .job-card, [class*="job-item"]')

                    if not job_elements:
                        # Try alternative selectors
                        job_elements = await page.query_selector_all('a[href*="/job/"], div[class*="result"]')

                    page_jobs = 0
                    for elem in job_elements:
                        try:
                            job = await self._extract_index_job(elem, page)
                            if job and job.get('title'):
                                jobs.append(job)
                                page_jobs += 1
                        except:
                            continue

                    print(f"   Found {page_jobs} jobs on page {page_num}")

                    if page_jobs == 0:
                        break  # No more jobs on this page

                except Exception as e:
                    print(f"   Error on page {page_num}: {e}")
                    break

            await browser.close()

        print(f"   ✅ Found {len(jobs)} total jobs from Index Ventures")
        return jobs

    async def scrape_sequoia(self, max_pages: int = 5) -> List[Dict]:
        """
        Scrape Sequoia Capital job board.
        Uses query parameters for pagination.
        """
        jobs = []
        base_url = "https://jobs.sequoiacap.com/jobs"

        print(f"🔍 Scraping Sequoia Capital Australia jobs...")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            )
            page = await context.new_page()

            # Initial page with Australia filter
            url = f"{base_url}?locations=Australia"

            try:
                await page.goto(url, wait_until='networkidle', timeout=30000)
                await asyncio.sleep(3)  # Wait for React to render

                # Scroll to load more jobs (infinite scroll pattern)
                for scroll in range(max_pages):
                    await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                    await asyncio.sleep(1.5)
                    print(f"   Scrolling... ({scroll + 1})")

                # Extract job cards
                job_cards = await page.query_selector_all('[class*="JobCard"], [class*="job-card"], article, .job-listing')

                for card in job_cards:
                    try:
                        job = await self._extract_sequoia_job(card, page)
                        if job and job.get('title'):
                            jobs.append(job)
                    except:
                        continue

                print(f"   ✅ Found {len(jobs)} jobs from Sequoia")

            except Exception as e:
                print(f"   ❌ Error scraping Sequoia: {e}")
            finally:
                await browser.close()

        return jobs

    async def _extract_getro_job(self, card, source: str) -> Optional[Dict]:
        """Extract job details from Getro-powered board."""
        try:
            title_elem = await card.query_selector('h3, h4, [class*="title"], a[class*="title"]')
            company_elem = await card.query_selector('[class*="company"], [class*="org"]')
            location_elem = await card.query_selector('[class*="location"]')
            link_elem = await card.query_selector('a[href*="/job"]')

            title = await title_elem.inner_text() if title_elem else ""
            company = await company_elem.inner_text() if company_elem else ""
            location = await location_elem.inner_text() if location_elem else "Australia"
            url = await link_elem.get_attribute('href') if link_elem else ""

            if not url.startswith('http'):
                url = f"https://jobs.insightpartners.com{url}"

            return {
                "company": company.strip(),
                "title": title.strip(),
                "location": location.strip(),
                "url": url,
                "salary_min": None,
                "salary_max": None,
                "requirements": [],
                "posted_date": datetime.now().strftime("%Y-%m-%d"),
                "job_type": "full-time",
                "source": f"VC Portfolio - {source}",
                "vc_firm": source
            }
        except:
            return None

    async def _extract_index_job(self, elem, page: Page) -> Optional[Dict]:
        """Extract job details from Index Ventures board."""
        try:
            title_elem = await elem.query_selector('h3, h4, [class*="title"], .job-title')
            company_elem = await elem.query_selector('[class*="company"], .company-name')
            location_elem = await elem.query_selector('[class*="location"]')
            link_elem = await elem.query_selector('a')

            title = await title_elem.inner_text() if title_elem else ""
            company = await company_elem.inner_text() if company_elem else ""
            location = await location_elem.inner_text() if location_elem else "Sydney, Australia"
            url = await link_elem.get_attribute('href') if link_elem else ""

            if url and not url.startswith('http'):
                url = f"https://www.indexventures.com{url}"

            return {
                "company": company.strip(),
                "title": title.strip(),
                "location": location.strip(),
                "url": url,
                "salary_min": None,
                "salary_max": None,
                "requirements": [],
                "posted_date": datetime.now().strftime("%Y-%m-%d"),
                "job_type": "full-time",
                "source": "VC Portfolio - Index Ventures",
                "vc_firm": "Index Ventures"
            }
        except:
            return None

    async def _extract_sequoia_job(self, card, page: Page) -> Optional[Dict]:
        """Extract job details from Sequoia board."""
        try:
            title_elem = await card.query_selector('h3, h4, [class*="title"]')
            company_elem = await card.query_selector('[class*="company"]')
            location_elem = await card.query_selector('[class*="location"]')
            link_elem = await card.query_selector('a')

            title = await title_elem.inner_text() if title_elem else ""
            company = await company_elem.inner_text() if company_elem else ""
            location = await location_elem.inner_text() if location_elem else "Australia"
            url = await link_elem.get_attribute('href') if link_elem else ""

            if url and not url.startswith('http'):
                url = f"https://jobs.sequoiacap.com{url}"

            return {
                "company": company.strip(),
                "title": title.strip(),
                "location": location.strip(),
                "url": url,
                "salary_min": None,
                "salary_max": None,
                "requirements": [],
                "posted_date": datetime.now().strftime("%Y-%m-%d"),
                "job_type": "full-time",
                "source": "VC Portfolio - Sequoia Capital",
                "vc_firm": "Sequoia Capital"
            }
        except:
            return None

    async def scrape_all(self) -> List[Dict]:
        """Scrape all VC job boards."""
        print("\n" + "="*60)
        print("🚀 VC Portfolio Job Board Scraper")
        print("="*60 + "\n")

        all_jobs = []

        # Scrape each board
        insight_jobs = await self.scrape_insight_partners()
        all_jobs.extend(insight_jobs)

        index_jobs = await self.scrape_index_ventures()
        all_jobs.extend(index_jobs)

        sequoia_jobs = await self.scrape_sequoia()
        all_jobs.extend(sequoia_jobs)

        # Remove duplicates by URL
        seen_urls = set()
        unique_jobs = []
        for job in all_jobs:
            if job['url'] not in seen_urls:
                seen_urls.add(job['url'])
                unique_jobs.append(job)

        # Save results
        output_file = self.output_dir / f"vc_portfolio_jobs_{self.timestamp}.json"
        with open(output_file, 'w') as f:
            json.dump(unique_jobs, f, indent=2)

        print("\n" + "="*60)
        print(f"📊 SUMMARY")
        print("="*60)
        print(f"   Insight Partners: {len(insight_jobs)} jobs")
        print(f"   Index Ventures:   {len(index_jobs)} jobs")
        print(f"   Sequoia Capital:  {len(sequoia_jobs)} jobs")
        print(f"   Total (unique):   {len(unique_jobs)} jobs")
        print(f"\n📁 Saved to: {output_file}")
        print("="*60 + "\n")

        return unique_jobs


async def main():
    """Run the VC job board scraper."""
    scraper = VCJobBoardScraper(output_dir="./data")
    jobs = await scraper.scrape_all()
    return jobs


if __name__ == "__main__":
    if not PLAYWRIGHT_AVAILABLE:
        print("Please install Playwright first:")
        print("  pip install playwright")
        print("  playwright install chromium")
    else:
        asyncio.run(main())
