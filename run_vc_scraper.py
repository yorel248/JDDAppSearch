#!/usr/bin/env python3
"""
Enhanced VC Job Board Scraper for Leroy Pinto
- Scrapes: Insight Partners, Index Ventures, Sequoia, LSVP
- Filters for senior GTM/Commercial roles
- Matches against profile
"""

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

try:
    from playwright.async_api import async_playwright, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

# Target role keywords for filtering
SENIOR_ROLE_KEYWORDS = [
    'director', 'head of', 'vp ', 'vice president', 'chief',
    'manager', 'lead', 'senior', 'principal', 'executive',
    'enterprise', 'strategic', 'regional'
]

GTM_ROLE_KEYWORDS = [
    'sales', 'account', 'business development', 'bd ', 'bdr',
    'gtm', 'go-to-market', 'commercial', 'revenue', 'partnerships',
    'partner', 'customer success', 'solutions', 'presales',
    'enterprise', 'strategic', 'field'
]

# Keywords that indicate too junior
JUNIOR_KEYWORDS = [
    'intern', 'graduate', 'entry level', 'associate', 'coordinator',
    'assistant', 'junior', 'trainee'
]


class EnhancedVCScraper:
    """Enhanced scraper with LSVP support and job matching."""

    def __init__(self):
        self.output_dir = Path("./data")
        self.output_dir.mkdir(exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.all_jobs = []

    def is_senior_gtm_role(self, title: str) -> bool:
        """Check if job title matches senior GTM profile."""
        title_lower = title.lower()

        # Exclude junior roles
        for keyword in JUNIOR_KEYWORDS:
            if keyword in title_lower:
                return False

        # Must have GTM keyword
        has_gtm = any(kw in title_lower for kw in GTM_ROLE_KEYWORDS)

        # Prefer senior roles but include all GTM
        has_senior = any(kw in title_lower for kw in SENIOR_ROLE_KEYWORDS)

        return has_gtm

    def calculate_match_score(self, job: Dict) -> int:
        """Calculate match score for Leroy's profile."""
        score = 50  # Base score
        title_lower = job.get('title', '').lower()

        # Seniority boost
        if any(kw in title_lower for kw in ['director', 'head of', 'vp ', 'chief']):
            score += 20
        elif any(kw in title_lower for kw in ['manager', 'lead', 'senior']):
            score += 10

        # GTM role boost
        if 'enterprise' in title_lower:
            score += 15
        if 'account executive' in title_lower:
            score += 15
        if 'partnerships' in title_lower or 'partner' in title_lower:
            score += 10
        if 'sales' in title_lower:
            score += 10
        if 'gtm' in title_lower or 'go-to-market' in title_lower:
            score += 15

        # Industry alignment
        if any(kw in title_lower for kw in ['fintech', 'financial', 'banking']):
            score += 10
        if 'ai' in title_lower or 'ml' in title_lower:
            score += 15

        # Location boost (Sydney preferred)
        location = job.get('location', '').lower()
        if 'sydney' in location:
            score += 10
        elif 'australia' in location:
            score += 5
        elif 'remote' in location:
            score += 5

        # Penalty for junior roles
        if any(kw in title_lower for kw in JUNIOR_KEYWORDS):
            score -= 30

        return min(100, max(0, score))

    async def scrape_insight_partners(self) -> List[Dict]:
        """Scrape Insight Partners with improved extraction."""
        jobs = []
        url = "https://jobs.insightpartners.com/jobs?filter=eyJzZWFyY2hhYmxlX2xvY2F0aW9ucyI6WyJBdXN0cmFsaWEiXX0%3D"

        print("🔍 Scraping Insight Partners (Australia)...")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                await page.goto(url, wait_until='networkidle', timeout=60000)
                await asyncio.sleep(3)

                # Click load more until done
                for i in range(15):
                    try:
                        load_more = page.locator('button:has-text("Load more")')
                        if await load_more.count() > 0 and await load_more.is_visible():
                            await load_more.click()
                            await asyncio.sleep(1)
                            print(f"   Loading more... ({i+1})")
                        else:
                            break
                    except:
                        break

                # Extract jobs using better selectors
                job_cards = await page.query_selector_all('a[href*="/companies/"][href*="/jobs/"]')

                for card in job_cards:
                    try:
                        href = await card.get_attribute('href')
                        text = await card.inner_text()
                        lines = [l.strip() for l in text.split('\n') if l.strip()]

                        if len(lines) >= 2:
                            title = lines[0] if lines else ""
                            company = ""
                            location = "Australia"

                            # Try to extract company from URL
                            if href:
                                match = re.search(r'/companies/([^/]+)/', href)
                                if match:
                                    company = match.group(1).replace('-', ' ').title()

                            # Find location in text
                            for line in lines[1:]:
                                if any(loc in line.lower() for loc in ['sydney', 'melbourne', 'australia', 'brisbane']):
                                    location = line
                                    break

                            full_url = f"https://jobs.insightpartners.com{href}" if not href.startswith('http') else href

                            job = {
                                "title": title,
                                "company": company,
                                "location": location,
                                "url": full_url,
                                "source": "Insight Partners",
                                "scraped_date": datetime.now().isoformat()
                            }
                            job["match_score"] = self.calculate_match_score(job)
                            jobs.append(job)
                    except:
                        continue

                print(f"   ✅ Found {len(jobs)} jobs")

            except Exception as e:
                print(f"   ❌ Error: {e}")
            finally:
                await browser.close()

        return jobs

    async def scrape_index_ventures(self) -> List[Dict]:
        """Scrape Index Ventures Sydney jobs."""
        jobs = []
        print("🔍 Scraping Index Ventures (Sydney)...")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            for page_num in range(1, 6):
                url = f"https://www.indexventures.com/startup-jobs/sydney-australia/{page_num}"
                print(f"   Fetching page {page_num}...")

                try:
                    await page.goto(url, wait_until='networkidle', timeout=60000)
                    await asyncio.sleep(3)

                    # Wait for Vue to render
                    await page.wait_for_selector('.job-result, [class*="job"]', timeout=10000)

                    # Extract job data
                    job_elements = await page.query_selector_all('.job-result, [class*="SearchResults"] a')

                    page_count = 0
                    for elem in job_elements:
                        try:
                            text = await elem.inner_text()
                            href = await elem.get_attribute('href')
                            lines = [l.strip() for l in text.split('\n') if l.strip()]

                            if lines:
                                job = {
                                    "title": lines[0] if lines else "",
                                    "company": lines[1] if len(lines) > 1 else "",
                                    "location": "Sydney, Australia",
                                    "url": href if href and href.startswith('http') else f"https://www.indexventures.com{href}" if href else "",
                                    "source": "Index Ventures",
                                    "scraped_date": datetime.now().isoformat()
                                }
                                job["match_score"] = self.calculate_match_score(job)
                                jobs.append(job)
                                page_count += 1
                        except:
                            continue

                    if page_count == 0:
                        break

                except Exception as e:
                    print(f"   Page {page_num} error: {e}")
                    break

            await browser.close()

        print(f"   ✅ Found {len(jobs)} jobs")
        return jobs

    async def scrape_sequoia(self) -> List[Dict]:
        """Scrape Sequoia Capital Australia jobs."""
        jobs = []
        url = "https://jobs.sequoiacap.com/jobs?locations=Australia"

        print("🔍 Scraping Sequoia Capital (Australia)...")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                await page.goto(url, wait_until='networkidle', timeout=60000)
                await asyncio.sleep(5)

                # Scroll to load more
                for i in range(10):
                    await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                    await asyncio.sleep(1)
                    print(f"   Scrolling... ({i+1})")

                # Extract jobs
                job_links = await page.query_selector_all('a[href*="/jobs/"]')

                for link in job_links:
                    try:
                        text = await link.inner_text()
                        href = await link.get_attribute('href')
                        lines = [l.strip() for l in text.split('\n') if l.strip()]

                        if lines and href:
                            job = {
                                "title": lines[0],
                                "company": lines[1] if len(lines) > 1 else "",
                                "location": lines[2] if len(lines) > 2 else "Australia",
                                "url": href if href.startswith('http') else f"https://jobs.sequoiacap.com{href}",
                                "source": "Sequoia Capital",
                                "scraped_date": datetime.now().isoformat()
                            }
                            job["match_score"] = self.calculate_match_score(job)
                            jobs.append(job)
                    except:
                        continue

                print(f"   ✅ Found {len(jobs)} jobs")

            except Exception as e:
                print(f"   ❌ Error: {e}")
            finally:
                await browser.close()

        return jobs

    async def scrape_lsvp(self) -> List[Dict]:
        """Scrape Lightspeed Venture Partners jobs (APAC/Remote)."""
        jobs = []
        url = "https://jobs.lsvp.com/jobs"

        print("🔍 Scraping Lightspeed VP (APAC/Remote)...")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                await page.goto(url, wait_until='networkidle', timeout=60000)
                await asyncio.sleep(5)

                # Try to filter by APAC or look for Australia/Singapore/Remote
                # Scroll to load more
                for i in range(10):
                    await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                    await asyncio.sleep(1)

                # Extract all jobs and filter by location
                job_links = await page.query_selector_all('a[href*="/jobs/"]')

                for link in job_links:
                    try:
                        text = await link.inner_text()
                        href = await link.get_attribute('href')
                        lines = [l.strip() for l in text.split('\n') if l.strip()]

                        # Check if APAC-relevant location
                        text_lower = text.lower()
                        is_apac = any(loc in text_lower for loc in [
                            'australia', 'sydney', 'melbourne', 'singapore',
                            'apac', 'asia', 'remote', 'india', 'bangalore'
                        ])

                        if lines and href and is_apac:
                            job = {
                                "title": lines[0],
                                "company": lines[1] if len(lines) > 1 else "",
                                "location": lines[2] if len(lines) > 2 else "APAC",
                                "url": href if href.startswith('http') else f"https://jobs.lsvp.com{href}",
                                "source": "Lightspeed VP",
                                "scraped_date": datetime.now().isoformat()
                            }
                            job["match_score"] = self.calculate_match_score(job)
                            jobs.append(job)
                    except:
                        continue

                print(f"   ✅ Found {len(jobs)} APAC jobs")

            except Exception as e:
                print(f"   ❌ Error: {e}")
            finally:
                await browser.close()

        return jobs

    async def scrape_all(self) -> List[Dict]:
        """Scrape all boards and return matched jobs."""
        print("\n" + "="*60)
        print("🚀 VC Portfolio Job Scraper - Enhanced")
        print("="*60)

        all_jobs = []

        # Scrape each board
        insight_jobs = await self.scrape_insight_partners()
        all_jobs.extend(insight_jobs)

        index_jobs = await self.scrape_index_ventures()
        all_jobs.extend(index_jobs)

        sequoia_jobs = await self.scrape_sequoia()
        all_jobs.extend(sequoia_jobs)

        lsvp_jobs = await self.scrape_lsvp()
        all_jobs.extend(lsvp_jobs)

        # Deduplicate by URL
        seen = set()
        unique_jobs = []
        for job in all_jobs:
            url = job.get('url', '')
            if url and url not in seen:
                seen.add(url)
                unique_jobs.append(job)

        # Sort by match score
        unique_jobs.sort(key=lambda x: x.get('match_score', 0), reverse=True)

        # Filter for GTM roles
        gtm_jobs = [j for j in unique_jobs if self.is_senior_gtm_role(j.get('title', ''))]

        # Save all jobs
        all_file = self.output_dir / f"vc_all_jobs_{self.timestamp}.json"
        with open(all_file, 'w') as f:
            json.dump(unique_jobs, f, indent=2)

        # Save GTM matches
        gtm_file = self.output_dir / f"vc_gtm_matches_{self.timestamp}.json"
        with open(gtm_file, 'w') as f:
            json.dump(gtm_jobs, f, indent=2)

        # Print summary
        print("\n" + "="*60)
        print("📊 RESULTS")
        print("="*60)
        print(f"   Insight Partners: {len(insight_jobs)} jobs")
        print(f"   Index Ventures:   {len(index_jobs)} jobs")
        print(f"   Sequoia Capital:  {len(sequoia_jobs)} jobs")
        print(f"   Lightspeed VP:    {len(lsvp_jobs)} jobs")
        print(f"   ────────────────────────────")
        print(f"   Total unique:     {len(unique_jobs)} jobs")
        print(f"   GTM matches:      {len(gtm_jobs)} jobs")
        print(f"\n📁 Saved to:")
        print(f"   All jobs: {all_file}")
        print(f"   GTM matches: {gtm_file}")

        # Print top matches
        print("\n" + "="*60)
        print("🎯 TOP GTM MATCHES FOR LEROY")
        print("="*60)

        for i, job in enumerate(gtm_jobs[:15], 1):
            score = job.get('match_score', 0)
            emoji = "🔥" if score >= 80 else "⭐" if score >= 70 else "👍"
            print(f"\n{i}. {emoji} [{score}%] {job['title']}")
            print(f"   Company: {job.get('company', 'Unknown')}")
            print(f"   Location: {job.get('location', 'N/A')}")
            print(f"   Source: {job.get('source', 'N/A')}")
            print(f"   URL: {job.get('url', 'N/A')}")

        print("\n" + "="*60)

        return gtm_jobs


async def main():
    scraper = EnhancedVCScraper()
    jobs = await scraper.scrape_all()
    return jobs


if __name__ == "__main__":
    if not PLAYWRIGHT_AVAILABLE:
        print("❌ Playwright not installed. Run:")
        print("   pip install playwright")
        print("   playwright install chromium")
    else:
        asyncio.run(main())
