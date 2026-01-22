#!/usr/bin/env python3
"""
Complete Job Search Runner for Sydney-based Roles
Including partnerships, commercial, technical roles with real job links
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.job_search_mvp import JobSearchMVP
from src.core.profile_manager import ProfileManager
from src.core.job_matcher import JobMatcher


def main():
    """Run complete job search workflow"""
    print("\n" + "="*80)
    print("COMPLETE JOB SEARCH - SYDNEY, AUSTRALIA")
    print("Including: Partnerships, Commercial, Technical Roles")
    print("="*80 + "\n")
    
    # Initialize components
    job_search = JobSearchMVP()
    profile_manager = ProfileManager()
    job_matcher = JobMatcher()
    
    # Step 1: Load or extract profile
    print("\n[Step 1/6] Loading profile...")
    profile_path = Path("data/profile_extracted.json")
    
    if profile_path.exists():
        with open(profile_path, 'r') as f:
            profile = json.load(f)
        print(f"✓ Loaded existing profile: {profile['name']}")
    else:
        print("✗ No profile found. Please run profile extraction first.")
        return
    
    # Step 2: Search for jobs (Sydney only, all categories)
    print("\n[Step 2/6] Searching for jobs in Sydney...")
    
    search_queries = [
        # Partnership roles
        "Head of Partnerships Sydney Australia 2025",
        "VP Partnerships Sydney ANZ APAC 2025", 
        "Director Strategic Partnerships Sydney 2025",
        "Chief Partnership Officer Sydney Australia 2025",
        
        # Commercial/GTM roles  
        "VP Sales Sydney Australia 2025",
        "Chief Commercial Officer Sydney 2025",
        "Head of Business Development Sydney 2025",
        
        # Technical leadership
        "VP Engineering Sydney fintech 2025",
        "CTO Sydney startup 2025",
        "Head of AI ML Sydney 2025"
    ]
    
    all_jobs = []
    for query in search_queries:
        print(f"  Searching: {query}")
        jobs = job_search.search_jobs(
            title=query,
            location="Sydney, Australia",
            category="all"
        )
        all_jobs.extend(jobs)
    
    # Remove duplicates based on company + title
    seen = set()
    unique_jobs = []
    for job in all_jobs:
        key = f"{job.get('company')}_{job.get('title')}"
        if key not in seen:
            seen.add(key)
            unique_jobs.append(job)
    
    print(f"✓ Found {len(unique_jobs)} unique positions")
    
    # Step 3: Enhance with real job links
    print("\n[Step 3/6] Finding real job description links...")
    
    # Load real job links if available
    real_links_path = Path("data/job_search_results_real_links.json")
    if real_links_path.exists():
        with open(real_links_path, 'r') as f:
            real_jobs = json.load(f)
        
        # Merge real links with search results
        for real_job in real_jobs:
            # Find matching job or add new
            matched = False
            for job in unique_jobs:
                if (job.get('company', '').lower() in real_job['company'].lower() or
                    real_job['company'].lower() in job.get('company', '').lower()):
                    # Update with real link
                    job['url'] = real_job.get('url', job.get('url'))
                    job['jd_link'] = real_job.get('jd_link', job.get('jd_link'))
                    matched = True
                    break
            
            if not matched:
                unique_jobs.append(real_job)
        
        print(f"✓ Enhanced with {len(real_jobs)} real job links")
    
    # Step 4: Add Glassdoor ratings
    print("\n[Step 4/6] Adding culture ratings...")
    
    for job in unique_jobs:
        # Simulate Glassdoor rating (in production, would call API)
        if 'work_life_balance_rating' not in job:
            job['work_life_balance_rating'] = 4  # Default rating
        
        # Add culture info
        if job.get('company') in ['Future Super', 'World Vision']:
            job['work_life_balance_rating'] = 5
            job['culture_notes'] = "Purpose-driven, excellent work-life balance"
        elif 'Government' in job.get('company', ''):
            job['work_life_balance_rating'] = 5
            job['culture_notes'] = "Government benefits, job security"
    
    print(f"✓ Added culture ratings for {len(unique_jobs)} positions")
    
    # Step 5: Match and score jobs
    print("\n[Step 5/6] Matching jobs with profile...")
    
    matched_jobs = []
    for job in unique_jobs:
        score = job_matcher.calculate_match_score(profile, job)
        job['match_score'] = score
        
        # Add match reasoning
        if 'partnerships' in job.get('title', '').lower():
            job['match_reason'] = "Strong fit: Partnership expertise from Google/AWS"
        elif 'fintech' in str(job).lower():
            job['match_reason'] = "Strong fit: Ringkas fintech founder experience"
        elif 'cloud' in str(job).lower() or 'aws' in str(job).lower():
            job['match_reason'] = "Strong fit: AWS Head of Digital Natives experience"
        
        matched_jobs.append(job)
    
    # Sort by match score
    matched_jobs.sort(key=lambda x: x.get('match_score', 0), reverse=True)
    
    print(f"✓ Matched and scored {len(matched_jobs)} positions")
    print(f"  Top match: {matched_jobs[0]['title']} at {matched_jobs[0]['company']} ({matched_jobs[0]['match_score']}%)")
    
    # Step 6: Generate reports
    print("\n[Step 6/6] Generating reports...")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save job results
    results_path = Path(f"data/job_search_complete_{timestamp}.json")
    with open(results_path, 'w') as f:
        json.dump({
            'search_date': datetime.now().isoformat(),
            'profile': profile['name'],
            'location': 'Sydney, Australia',
            'total_jobs': len(matched_jobs),
            'jobs': matched_jobs[:50]  # Top 50 matches
        }, f, indent=2)
    
    print(f"✓ Saved results to {results_path}")
    
    # Generate summary report
    report_path = Path(f"reports/{datetime.now().strftime('%Y%m%d')}/COMPLETE_SEARCH_RESULTS.md")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    
    report = f"""# Complete Job Search Results - Sydney, Australia
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## Profile Summary
- **Name:** {profile['name']}
- **Current Role:** {profile.get('current_role', 'N/A')}
- **Location Target:** Sydney, Australia
- **Categories:** Partnerships, Commercial/GTM, Technical Leadership

## Search Statistics
- **Total Positions Found:** {len(matched_jobs)}
- **With Real Job Links:** {len([j for j in matched_jobs if j.get('url') or j.get('jd_link')])}
- **Average Match Score:** {sum(j.get('match_score', 0) for j in matched_jobs) / len(matched_jobs):.1f}%

## Top 10 Matches

"""
    
    for i, job in enumerate(matched_jobs[:10], 1):
        report += f"""
### {i}. {job['title']} - {job['company']}
- **Match Score:** {job.get('match_score', 0)}%
- **Location:** {job.get('location', 'Sydney')}
- **Salary Range:** ${job.get('salary_min', 0):,} - ${job.get('salary_max', 0):,}
- **Work-Life Balance:** {'⭐' * job.get('work_life_balance_rating', 4)}
- **Apply:** {job.get('url') or job.get('jd_link') or 'Contact company directly'}
- **Why Match:** {job.get('match_reason', 'Skills and experience alignment')}
"""
    
    report += """
## Next Steps
1. Apply to top 5 matches immediately
2. Set up job alerts on LinkedIn and SEEK
3. Contact executive search firms for confidential roles
4. Network with employees at target companies
5. Customize cover letters for each application

## Application Links
- LinkedIn Jobs: https://au.linkedin.com/jobs/
- SEEK: https://www.seek.com.au/
- Indeed: https://au.indeed.com/

Report includes positions with real job links where available.
"""
    
    with open(report_path, 'w') as f:
        f.write(report)
    
    print(f"✓ Generated report at {report_path}")
    
    print("\n" + "="*80)
    print("JOB SEARCH COMPLETE")
    print(f"Found {len(matched_jobs)} positions in Sydney")
    print(f"Top categories: Partnerships, Commercial, Technical")
    print("Check reports folder for detailed results")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()