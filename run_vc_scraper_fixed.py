#!/usr/bin/env python3
"""
Fixed VC Job Board Scraper - Debugged version
"""

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict

from playwright.async_api import async_playwright

# Role keywords
SENIOR_KEYWORDS = ['director', 'head of', 'vp ', 'vice president', 'chief', 'manager', 'lead', 'senior', 'principal', 'executive', 'enterprise', 'strategic', 'regional']
GTM_KEYWORDS = ['sales', 'account', 'business development', 'bd ', 'bdr', 'gtm', 'go-to-market', 'commercial', 'revenue', 'partnerships', 'partner', 'customer success', 'solutions', 'presales', 'enterprise', 'strategic', 'field']
JUNIOR_KEYWORDS = ['intern', 'graduate', 'entry level', 'coordinator', 'assistant', 'junior', 'trainee']


def is_gtm_role(title: str) -> bool:
    title_lower = title.lower()
    if any(kw in title_lower for kw in JUNIOR_KEYWORDS):
        return False
    return any(kw in title_lower for kw in GTM_KEYWORDS)


def calc_score(job: Dict) -> int:
    score = 50
    title = job.get('title', '').lower()

    if any(kw in title for kw in ['director', 'head of', 'vp ', 'chief']):
        score += 20
    elif any(kw in title for kw in ['manager', 'lead', 'senior']):
        score += 10

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

    if any(kw in title for kw in JUNIOR_KEYWORDS):
        score -= 30

    return min(100, max(0, score))


async def scrape_insight_partners() -> List[Dict]:
    """Fixed Insight Partners scraper."""
    jobs = []
    url = "https://jobs.insightpartners.com/jobs?filter=eyJzZWFyY2hhYmxlX2xvY2F0aW9ucyI6WyJBdXN0cmFsaWEiXX0%3D"

    print("🔍 Scraping Insight Partners (Australia)...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()

        try:
            # Use domcontentloaded (faster, more reliable)
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(5)  # Wait for JS to render

            # Click load more buttons
            for i in range(10):
                try:
                    load_more = page.locator('button:has-text("Load more")')
                    if await load_more.count() > 0 and await load_more.is_visible():
                        await load_more.click()
                        await asyncio.sleep(1.5)
                        print(f"   Loaded more ({i+1})...")
                    else:
                        break
                except:
                    break

            await asyncio.sleep(2)

            # Extract jobs
            job_links = await page.query_selector_all('a[href*="/companies/"][href*="/jobs/"]')
            print(f"   Found {len(job_links)} job links")

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

                    # Extract company from URL
                    company = ""
                    match = re.search(r'/companies/([^/]+)/', href)
                    if match:
                        company = match.group(1).replace('-', ' ').title()
                        # Clean up numbered suffixes
                        company = re.sub(r'\s*\d+\s*[A-Fa-f0-9\-]+$', '', company)

                    # Find location
                    location = "Australia"
                    for line in lines[1:4]:
                        if any(loc in line.lower() for loc in ['sydney', 'melbourne', 'australia', 'brisbane', 'perth']):
                            location = line
                            break

                    full_url = f"https://jobs.insightpartners.com{href}" if not href.startswith('http') else href

                    job = {
                        "title": title,
                        "company": company,
                        "location": location,
                        "url": full_url,
                        "source": "Insight Partners"
                    }
                    job["match_score"] = calc_score(job)
                    jobs.append(job)

                except Exception as e:
                    continue

            print(f"   ✅ Extracted {len(jobs)} unique jobs")

        except Exception as e:
            print(f"   ❌ Error: {e}")
        finally:
            await browser.close()

    return jobs


async def scrape_index_ventures() -> List[Dict]:
    """Fixed Index Ventures scraper with better Vue.js handling."""
    jobs = []

    print("🔍 Scraping Index Ventures (Sydney)...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()

        for page_num in range(1, 6):
            url = f"https://www.indexventures.com/startup-jobs/sydney-australia/{page_num}"
            print(f"   Page {page_num}...")

            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)

                # Wait for Vue.js to render - check for actual content
                for _ in range(20):  # Wait up to 10 seconds
                    html = await page.content()
                    if '[[' not in html:  # Vue templates have been processed
                        break
                    await asyncio.sleep(0.5)

                await asyncio.sleep(2)  # Extra buffer

                # Extract using JavaScript to get rendered content
                job_data = await page.evaluate('''() => {
                    const jobs = [];
                    const results = document.querySelectorAll('[class*="result"]');
                    results.forEach(el => {
                        const text = el.innerText;
                        const link = el.querySelector('a');
                        const href = link ? link.getAttribute('href') : '';
                        if (text && text.length > 10) {
                            jobs.push({text: text, href: href});
                        }
                    });
                    return jobs;
                }''')

                page_count = 0
                for item in job_data:
                    try:
                        text = item.get('text', '')
                        href = item.get('href', '')

                        lines = [l.strip() for l in text.split('\n') if l.strip()]
                        if len(lines) < 2:
                            continue

                        title = lines[0]
                        company = lines[1] if len(lines) > 1 else ""
                        location = "Sydney, Australia"

                        # Find location in lines
                        for line in lines:
                            if any(loc in line.lower() for loc in ['sydney', 'melbourne', 'remote']):
                                location = line
                                break

                        full_url = href if href.startswith('http') else f"https://www.indexventures.com{href}" if href else ""

                        job = {
                            "title": title,
                            "company": company,
                            "location": location,
                            "url": full_url,
                            "source": "Index Ventures"
                        }
                        job["match_score"] = calc_score(job)
                        jobs.append(job)
                        page_count += 1

                    except:
                        continue

                print(f"      Found {page_count} jobs")
                if page_count == 0:
                    break

            except Exception as e:
                print(f"      Error: {e}")
                break

        await browser.close()

    print(f"   ✅ Total: {len(jobs)} jobs")
    return jobs


async def scrape_sequoia() -> List[Dict]:
    """Sequoia scraper (already working)."""
    jobs = []
    url = "https://jobs.sequoiacap.com/jobs?locations=Australia"

    print("🔍 Scraping Sequoia Capital (Australia)...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()

        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(5)

            # Scroll to load
            for i in range(10):
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await asyncio.sleep(1)

            # Extract via JS
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
                    seen.add(href)

                    lines = [l.strip() for l in text.split('\n') if l.strip()]
                    if not lines:
                        continue

                    job = {
                        "title": lines[0],
                        "company": lines[1] if len(lines) > 1 else "",
                        "location": lines[2] if len(lines) > 2 else "Australia",
                        "url": href if href.startswith('http') else f"https://jobs.sequoiacap.com{href}",
                        "source": "Sequoia Capital"
                    }
                    job["match_score"] = calc_score(job)
                    jobs.append(job)
                except:
                    continue

            print(f"   ✅ Found {len(jobs)} jobs")

        except Exception as e:
            print(f"   ❌ Error: {e}")
        finally:
            await browser.close()

    return jobs


async def scrape_lsvp() -> List[Dict]:
    """LSVP scraper for APAC jobs."""
    jobs = []
    url = "https://jobs.lsvp.com/jobs"

    print("🔍 Scraping Lightspeed VP (APAC)...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()

        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(5)

            for i in range(10):
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await asyncio.sleep(1)

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

            apac_keywords = ['australia', 'sydney', 'melbourne', 'singapore', 'apac', 'asia', 'remote', 'india', 'bangalore', 'tokyo', 'seoul']

            seen = set()
            for item in job_data:
                try:
                    text = item.get('text', '')
                    href = item.get('href', '')

                    if not href or href in seen:
                        continue

                    # Check if APAC relevant
                    text_lower = text.lower()
                    if not any(kw in text_lower for kw in apac_keywords):
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
                        "source": "Lightspeed VP"
                    }
                    job["match_score"] = calc_score(job)
                    jobs.append(job)
                except:
                    continue

            print(f"   ✅ Found {len(jobs)} APAC jobs")

        except Exception as e:
            print(f"   ❌ Error: {e}")
        finally:
            await browser.close()

    return jobs


async def main():
    print("\n" + "="*60)
    print("🚀 VC Job Scraper - Fixed Version")
    print("="*60 + "\n")

    all_jobs = []

    insight_jobs = await scrape_insight_partners()
    all_jobs.extend(insight_jobs)

    index_jobs = await scrape_index_ventures()
    all_jobs.extend(index_jobs)

    sequoia_jobs = await scrape_sequoia()
    all_jobs.extend(sequoia_jobs)

    lsvp_jobs = await scrape_lsvp()
    all_jobs.extend(lsvp_jobs)

    # Dedupe
    seen = set()
    unique = []
    for job in all_jobs:
        url = job.get('url', '')
        if url and url not in seen:
            seen.add(url)
            unique.append(job)

    unique.sort(key=lambda x: x.get('match_score', 0), reverse=True)

    gtm_jobs = [j for j in unique if is_gtm_role(j.get('title', ''))]

    # Save
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    Path("./data").mkdir(exist_ok=True)

    with open(f"./data/vc_all_jobs_{ts}.json", 'w') as f:
        json.dump(unique, f, indent=2)

    with open(f"./data/vc_gtm_matches_{ts}.json", 'w') as f:
        json.dump(gtm_jobs, f, indent=2)

    print("\n" + "="*60)
    print("📊 RESULTS")
    print("="*60)
    print(f"   Insight Partners: {len(insight_jobs)} jobs")
    print(f"   Index Ventures:   {len(index_jobs)} jobs")
    print(f"   Sequoia Capital:  {len(sequoia_jobs)} jobs")
    print(f"   Lightspeed VP:    {len(lsvp_jobs)} jobs")
    print(f"   ────────────────────")
    print(f"   Total unique:     {len(unique)} jobs")
    print(f"   GTM matches:      {len(gtm_jobs)} jobs")

    print("\n🎯 TOP 15 GTM MATCHES:")
    print("-"*60)

    for i, job in enumerate(gtm_jobs[:15], 1):
        score = job.get('match_score', 0)
        emoji = "🔥" if score >= 80 else "⭐" if score >= 70 else "👍"
        print(f"\n{i}. {emoji} [{score}%] {job['title']}")
        print(f"   Company: {job.get('company') or 'See link'}")
        print(f"   Location: {job.get('location', 'N/A')}")
        print(f"   Source: {job.get('source')}")
        print(f"   {job.get('url', '')[:80]}")

    print("\n" + "="*60)
    return gtm_jobs


if __name__ == "__main__":
    asyncio.run(main())
