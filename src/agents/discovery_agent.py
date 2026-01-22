"""Discovery Agent for finding job opportunities."""

from typing import Dict, List, Optional, Any
from .base_agent import BaseAgent


class DiscoveryAgent(BaseAgent):
    """Agent responsible for discovering job opportunities."""
    
    def __init__(self):
        super().__init__("discovery")
        self.search_sources = [
            "LinkedIn Jobs",
            "Indeed", 
            "Glassdoor",
            "AngelList",
            "Company career pages",
            "Remote job boards"
        ]
    
    def generate_prompt(self, job_title: str, location: str, 
                       preferences: Optional[Dict] = None, 
                       companies: Optional[List[str]] = None) -> str:
        """Generate job discovery prompt."""
        
        # Build preferences string
        pref_lines = []
        if preferences:
            if preferences.get('remote_preference'):
                pref_lines.append(f"- Remote preference: {preferences['remote_preference']}")
            if preferences.get('salary_min'):
                pref_lines.append(f"- Minimum salary: ${preferences['salary_min']:,}")
            if preferences.get('salary_max'):
                pref_lines.append(f"- Maximum salary: ${preferences['salary_max']:,}")
            if preferences.get('company_size'):
                pref_lines.append(f"- Company size: {', '.join(preferences['company_size'])}")
            if preferences.get('industries'):
                pref_lines.append(f"- Industries: {', '.join(preferences['industries'])}")
        
        pref_str = "\n".join(pref_lines) if pref_lines else ""
        
        # Build companies string
        companies_str = ""
        if companies:
            companies_str = f"""
Specifically check these companies:
{chr(10).join([f'- {company}' for company in companies])}
"""
        
        prompt = f"""
Job Discovery Search Task

Search for "{job_title}" positions in "{location}".

Search Sources:
{chr(10).join([f'- {source}' for source in self.search_sources])}
{companies_str}

Search Criteria:
{pref_str if pref_str else '- No specific preferences'}

For each job found, extract:
1. Company name (exact)
2. Job title (exact)
3. Location (city, state/country, remote status)
4. Direct application URL
5. Job description (first 500 characters)
6. Key requirements (top 5-7)
7. Salary range (if available)
8. Posted date
9. Job type (full-time, part-time, contract, internship)
10. Company size estimate
11. Industry/Sector

Target: Find 20-30 relevant positions

Output Format:
Save results to: {self.data_dir}/job_search_results.json

JSON Structure:
{{
  "search_date": "ISO timestamp",
  "search_criteria": {{
    "job_title": "{job_title}",
    "location": "{location}",
    "preferences": {{"remote": "...", "salary_min": ...}}
  }},
  "jobs": [
    {{
      "job_id": "unique_identifier",
      "company": "Company Name",
      "title": "Exact Job Title",
      "location": "City, State (Remote/Hybrid/Onsite)",
      "url": "https://application.url",
      "description": "First 500 chars of description...",
      "requirements": ["Req 1", "Req 2", ...],
      "salary_min": 120000,
      "salary_max": 180000,
      "posted_date": "2024-01-15",
      "job_type": "full-time",
      "company_size": "1000-5000",
      "industry": "Technology",
      "source": "LinkedIn"
    }}
  ],
  "summary": {{
    "total_found": 25,
    "by_source": {{"LinkedIn": 10, "Indeed": 8, ...}},
    "by_location": {{"San Francisco": 15, "Remote": 10}},
    "salary_ranges": {{"under_100k": 5, "100k_150k": 10, ...}}
  }}
}}

{self.get_standard_output_format()}

Additional Instructions:
- Prioritize jobs posted within the last 30 days
- Include both exact matches and related titles
- Capture remote work options accurately
- Verify URLs are direct application links when possible
"""
        return prompt
    
    def generate_targeted_search_prompt(self, companies: List[str], 
                                       job_titles: List[str]) -> str:
        """Generate prompt for searching specific companies."""
        
        prompt = f"""
Targeted Company Job Search

Search for specific positions at these companies:

Companies:
{chr(10).join([f'- {company}' for company in companies[:20]])}

Position Types:
{chr(10).join([f'- {title}' for title in job_titles[:10]])}

For each company:
1. Visit their careers page directly
2. Search for all positions matching the job titles
3. Include related positions (similar titles/responsibilities)
4. Check for unlisted positions mentioned in news or forums

Extract for each position:
- All standard job information (title, location, URL, etc.)
- Team/Department information
- Reporting structure (if mentioned)
- Specific tech stack or tools mentioned
- Growth/advancement opportunities mentioned

Output to: {self.data_dir}/targeted_search_results.json

Focus on:
- Current openings (not expired postings)
- Both public and less visible postings
- New grad and senior positions
- Remote-friendly positions

{self.get_standard_output_format()}
"""
        return prompt
    
    def generate_industry_search_prompt(self, industry: str, job_title: str,
                                       location: str) -> str:
        """Generate prompt for industry-specific search."""
        
        industry_sources = {
            "tech": ["AngelList", "Hacker News Jobs", "Built In"],
            "finance": ["eFinancialCareers", "Wall Street Oasis"],
            "healthcare": ["Health eCareers", "Healthcare Jobsite"],
            "education": ["HigherEdJobs", "SchoolSpring"],
            "nonprofit": ["Idealist", "NonProfit Jobs"],
            "government": ["USAJobs", "GovernmentJobs"],
        }
        
        sources = industry_sources.get(industry.lower(), self.search_sources)
        
        prompt = f"""
Industry-Specific Job Search: {industry}

Search for "{job_title}" positions in "{location}" within the {industry} industry.

Specialized Sources:
{chr(10).join([f'- {source}' for source in sources])}

Industry-Specific Criteria:
- Companies known for {industry}
- Industry-specific qualifications
- Relevant certifications or clearances
- Industry standard compensation ranges

Look for:
- Industry leaders and established companies
- Innovative startups and disruptors
- Companies with good industry reputation
- Growth-stage companies with funding

Extract all standard job information plus:
- Industry-specific requirements
- Regulatory or compliance mentions
- Industry certifications needed
- Domain expertise required

Output to: {self.data_dir}/{industry}_search_results.json

{self.get_standard_output_format()}
"""
        return prompt
    
    def process_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Process discovery response."""
        # This would normally process Claude's response
        # Since we're using Claude Code directly, this is a placeholder
        processed = {
            "status": "processed",
            "jobs_found": len(response.get("jobs", [])),
            "sources": response.get("summary", {}).get("by_source", {}),
            "timestamp": response.get("search_date")
        }
        return processed
    
    def deduplicate_jobs(self, existing_jobs: List[Dict], 
                        new_jobs: List[Dict]) -> List[Dict]:
        """Remove duplicate jobs based on company and title."""
        existing_keys = {
            (job['company'].lower(), job['title'].lower()) 
            for job in existing_jobs
        }
        
        unique_jobs = []
        for job in new_jobs:
            key = (job['company'].lower(), job['title'].lower())
            if key not in existing_keys:
                unique_jobs.append(job)
                existing_keys.add(key)
        
        return unique_jobs