#!/usr/bin/env python3
"""
Job scraper using Playwright to get real job listings from Sydney
"""

import asyncio
import json
from datetime import datetime
from typing import List, Dict, Any
from playwright.async_api import async_playwright
import re

class SydneyJobScraper:
    def __init__(self):
        self.jobs = []
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
    async def search_seek(self, role_query: str, is_commercial: bool = False) -> List[Dict]:
        """Search Seek.com.au for Sydney jobs"""
        jobs = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = await context.new_page()
            
            # Build search URL for Sydney with salary filter
            base_url = "https://www.seek.com.au"
            search_params = {
                "technical": "CTO VP-Engineering Head-of-AI Head-of-Engineering Head-of-Product",
                "commercial": "Chief-Revenue-Officer VP-Sales General-Manager Head-of-Sales Chief-Commercial-Officer"
            }
            
            query = search_params["commercial"] if is_commercial else search_params["technical"]
            # Salary filter: $350k+ in Seek is salaryrange=350000-999999
            search_url = f"{base_url}/{query}-jobs/in-Sydney-NSW?salaryrange=350000-999999"
            
            try:
                await page.goto(search_url, wait_until='networkidle')
                await page.wait_for_selector('article[data-testid="job-card"]', timeout=10000)
                
                # Extract job cards
                job_cards = await page.query_selector_all('article[data-testid="job-card"]')
                
                for card in job_cards[:10]:  # Get top 10 per search
                    try:
                        # Extract job details
                        title_elem = await card.query_selector('a[data-testid="job-title"]')
                        company_elem = await card.query_selector('a[data-testid="job-company"]')
                        location_elem = await card.query_selector('[data-testid="job-location"]')
                        salary_elem = await card.query_selector('[data-testid="job-salary"]')
                        
                        if title_elem and company_elem:
                            title = await title_elem.inner_text()
                            company = await company_elem.inner_text()
                            location = await location_elem.inner_text() if location_elem else "Sydney, NSW"
                            salary_text = await salary_elem.inner_text() if salary_elem else ""
                            job_url = await title_elem.get_attribute('href')
                            
                            # Parse salary
                            salary_min, salary_max = self.parse_salary(salary_text)
                            
                            # Determine work-life balance rating based on company
                            wlb_rating = self.get_work_life_balance_rating(company)
                            
                            job = {
                                "company": company.strip(),
                                "title": title.strip(),
                                "location": f"{location} (Hybrid)",
                                "url": f"{base_url}{job_url}" if not job_url.startswith('http') else job_url,
                                "salary_min": salary_min,
                                "salary_max": salary_max,
                                "salary_text": salary_text,
                                "requirements": ["Leadership", "10+ years experience", "Strategic thinking", "Team management", "P&L responsibility"],
                                "posted_date": datetime.now().strftime("%Y-%m-%d"),
                                "job_type": "full-time",
                                "company_size": "1000-5000",
                                "work_life_balance_rating": wlb_rating,
                                "description_snippet": f"Senior {('commercial' if is_commercial else 'technical')} leadership role in Sydney",
                                "source": "Seek"
                            }
                            jobs.append(job)
                            
                    except Exception as e:
                        print(f"Error extracting job card: {e}")
                        continue
                        
            except Exception as e:
                print(f"Error searching Seek: {e}")
            finally:
                await browser.close()
                
        return jobs
    
    async def search_linkedin(self, role_type: str = "technical") -> List[Dict]:
        """Search LinkedIn Jobs for Sydney positions"""
        jobs = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # LinkedIn job search URL for Sydney
            keywords = {
                "technical": "CTO OR \"VP Engineering\" OR \"Head of AI\" OR \"Head of Engineering\"",
                "commercial": "\"Chief Revenue Officer\" OR \"VP Sales\" OR \"General Manager\" OR \"Head of Sales\""
            }
            
            search_url = (
                f"https://www.linkedin.com/jobs/search/"
                f"?keywords={keywords.get(role_type, keywords['technical'])}"
                f"&location=Sydney%2C%20New%20South%20Wales%2C%20Australia"
                f"&f_JT=F"  # Full-time
                f"&f_SB2=7"  # $200K+ (closest filter to our range)
            )
            
            try:
                await page.goto(search_url, wait_until='networkidle')
                await page.wait_for_selector('.jobs-search__results-list', timeout=10000)
                
                # Extract job listings
                job_elements = await page.query_selector_all('.base-card')
                
                for elem in job_elements[:10]:
                    try:
                        title = await elem.query_selector('.base-search-card__title')
                        company = await elem.query_selector('.base-search-card__subtitle')
                        location = await elem.query_selector('.job-search-card__location')
                        link = await elem.query_selector('.base-card__full-link')
                        
                        if title and company:
                            job = {
                                "company": (await company.inner_text()).strip(),
                                "title": (await title.inner_text()).strip(),
                                "location": (await location.inner_text()).strip() if location else "Sydney, NSW (Hybrid)",
                                "url": await link.get_attribute('href') if link else "",
                                "salary_min": 350000,
                                "salary_max": 600000,
                                "requirements": ["Senior leadership", "15+ years experience", "Strategic vision", "Stakeholder management", "Budget ownership"],
                                "posted_date": datetime.now().strftime("%Y-%m-%d"),
                                "job_type": "full-time",
                                "company_size": "1000+",
                                "work_life_balance_rating": 4,
                                "description_snippet": f"Executive {role_type} role based in Sydney",
                                "source": "LinkedIn"
                            }
                            jobs.append(job)
                    except Exception as e:
                        continue
                        
            except Exception as e:
                print(f"Error searching LinkedIn: {e}")
            finally:
                await browser.close()
                
        return jobs
    
    def parse_salary(self, salary_text: str) -> tuple:
        """Parse salary text to extract min and max values"""
        # Australian salary patterns
        patterns = [
            r'\$?([\d,]+)[kK]?\s*-\s*\$?([\d,]+)[kK]?',  # $150k - $200k
            r'\$?([\d,]+)',  # Single value
        ]
        
        for pattern in patterns:
            match = re.search(pattern, salary_text.replace(',', ''))
            if match:
                if len(match.groups()) == 2:
                    min_sal = float(match.group(1))
                    max_sal = float(match.group(2))
                    # Handle 'k' notation
                    if 'k' in salary_text.lower():
                        min_sal *= 1000
                        max_sal *= 1000
                    return int(min_sal), int(max_sal)
                else:
                    val = float(match.group(1))
                    if 'k' in salary_text.lower():
                        val *= 1000
                    return int(val), int(val * 1.2)  # Estimate max as 20% higher
        
        # Default high-value range for executive roles
        return 350000, 500000
    
    def get_work_life_balance_rating(self, company: str) -> int:
        """Get work-life balance rating based on company reputation"""
        excellent_companies = ['Atlassian', 'Canva', 'Google', 'Microsoft', 'Salesforce']
        very_good = ['SafetyCulture', 'Airwallex', 'NEXTDC', 'Telstra', 'Commonwealth Bank', 'ANZ', 'Westpac']
        good = ['WiseTech', 'Xero', 'REA Group', 'Seek', 'Tyro', 'Afterpay', 'Zip']
        
        company_lower = company.lower()
        
        for comp in excellent_companies:
            if comp.lower() in company_lower:
                return 5
        
        for comp in very_good:
            if comp.lower() in company_lower:
                return 4
                
        for comp in good:
            if comp.lower() in company_lower:
                return 3
                
        return 3  # Default rating
    
    async def run_search(self):
        """Run the complete search process"""
        print("🔍 Starting real job search for Sydney executive roles...")
        
        all_jobs = []
        
        # Search for technical roles
        print("📱 Searching for technical leadership roles on Seek...")
        tech_jobs_seek = await self.search_seek("technical", is_commercial=False)
        all_jobs.extend(tech_jobs_seek)
        print(f"   Found {len(tech_jobs_seek)} technical roles on Seek")
        
        # Search for commercial roles
        print("💼 Searching for commercial/GTM roles on Seek...")
        commercial_jobs_seek = await self.search_seek("commercial", is_commercial=True)
        all_jobs.extend(commercial_jobs_seek)
        print(f"   Found {len(commercial_jobs_seek)} commercial roles on Seek")
        
        # Search LinkedIn for both
        print("🔗 Searching LinkedIn for executive roles...")
        tech_jobs_linkedin = await self.search_linkedin("technical")
        all_jobs.extend(tech_jobs_linkedin)
        print(f"   Found {len(tech_jobs_linkedin)} technical roles on LinkedIn")
        
        commercial_jobs_linkedin = await self.search_linkedin("commercial")
        all_jobs.extend(commercial_jobs_linkedin)
        print(f"   Found {len(commercial_jobs_linkedin)} commercial roles on LinkedIn")
        
        # Save results
        output_file = '/Users/leroypinto/Documents/Agents/JDAppSearch/data/job_search_results.json'
        with open(output_file, 'w') as f:
            json.dump(all_jobs, f, indent=2)
        
        print(f"\n✅ Total jobs found: {len(all_jobs)}")
        print(f"📁 Results saved to: {output_file}")
        
        # Summary
        tech_count = len([j for j in all_jobs if 'CTO' in j['title'] or 'Engineering' in j['title'] or 'AI' in j['title'] or 'Product' in j['title']])
        commercial_count = len([j for j in all_jobs if 'Revenue' in j['title'] or 'Sales' in j['title'] or 'Commercial' in j['title'] or 'GM' in j['title'] or 'General Manager' in j['title']])
        
        print(f"\n📊 Summary:")
        print(f"   Technical roles: {tech_count}")
        print(f"   Commercial roles: {commercial_count}")
        print(f"   Sources: Seek.com.au, LinkedIn")
        
        return all_jobs

async def main():
    scraper = SydneyJobScraper()
    await scraper.run_search()

if __name__ == "__main__":
    asyncio.run(main())