#!/usr/bin/env python3
"""
Sydney job search using web search to find real current positions
"""

import json
from datetime import datetime
from typing import List, Dict

def generate_sydney_job_search_prompt():
    """Generate a prompt for Claude to search for real Sydney jobs"""
    
    prompt = """
Search the web for current executive job openings in Sydney, Australia posted in the last 30 days.

TECHNICAL LEADERSHIP ROLES TO FIND:
- Chief Technology Officer (CTO)
- VP of Engineering
- Head of Engineering
- Head of AI/ML
- Head of Product
- Engineering Director

COMMERCIAL/GTM ROLES TO FIND:
- Chief Revenue Officer (CRO)
- Chief Commercial Officer (CCO)
- VP of Sales
- Head of Sales
- General Manager (GM)
- Head of Go-to-Market

Search these job sites and company pages:
1. seek.com.au (filter: Sydney, $350K+)
2. LinkedIn Jobs Australia
3. Indeed Australia
4. Atlassian careers
5. Canva careers
6. Google Australia careers
7. Microsoft Australia careers
8. Commonwealth Bank careers
9. Telstra careers
10. SafetyCulture careers
11. Airwallex careers
12. WiseTech Global careers

For each REAL job found, extract:
{
    "company": "Actual company name",
    "title": "Exact job title from posting",
    "location": "Sydney, NSW (specify if Hybrid/Remote)",
    "url": "Direct application URL",
    "salary_min": minimum salary in AUD,
    "salary_max": maximum salary in AUD,
    "requirements": ["Top 5 requirements from job posting"],
    "posted_date": "Actual posting date or estimate",
    "job_type": "full-time",
    "company_size": "Company employee count",
    "work_life_balance_rating": 1-5 based on company reputation,
    "description_snippet": "First 200 characters of actual job description",
    "source": "Where you found it (Seek/LinkedIn/Company site)"
}

Find at least 30-40 REAL, CURRENT positions that:
- Are based in Sydney (can be hybrid)
- Pay $350K+ AUD
- Are senior executive level
- Were posted recently (within 30 days)
- Are from reputable companies

Save the results to: /Users/leroypinto/Documents/Agents/JDAppSearch/data/job_search_results.json
"""
    
    # Save the prompt
    prompt_file = "/Users/leroypinto/Documents/Agents/JDAppSearch/data/prompts/sydney_web_search_" + datetime.now().strftime("%Y%m%d") + ".txt"
    with open(prompt_file, 'w') as f:
        f.write(prompt)
    
    print(f"✅ Web search prompt created: {prompt_file}")
    print("\n📋 Next step: Execute this prompt with Claude Code to search for real Sydney jobs")
    print("\nThe search will find actual current job postings from:")
    print("- Seek.com.au")
    print("- LinkedIn Jobs")
    print("- Company career pages")
    print("\nFocusing on:")
    print("- Sydney-based roles (with hybrid options)")
    print("- $350K+ AUD salary range")
    print("- Executive level positions")
    print("- Both technical and commercial leadership")
    
    return prompt_file

if __name__ == "__main__":
    generate_sydney_job_search_prompt()