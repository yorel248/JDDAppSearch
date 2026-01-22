"""Reporting module for job search system."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any


class ReportGenerator:
    """Generate various reports for job search activities."""
    
    def __init__(self, data_dir: str = "./data", reports_dir: str = "./reports"):
        self.data_dir = Path(data_dir)
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_daily_report_prompt(self) -> str:
        """Generate prompt for creating daily report."""
        prompt = f"""
Generate a comprehensive daily job search report.

Input Files:
- Profile: {self.data_dir}/profile_extracted.json
- Jobs Found: {self.data_dir}/job_search_results.json
- Job Matches: {self.data_dir}/job_matches.json
- Companies: {self.data_dir}/company_research.json
- Applications: {self.data_dir}/applications/*.json
- Database: {self.data_dir}/jobs.db

Create a markdown report with the following sections:

# Daily Job Search Report - {datetime.now().strftime('%Y-%m-%d')}

## Executive Summary
- Total jobs discovered today
- High-match opportunities (80%+ match)
- Applications submitted
- Connections reached out to
- Key insights and recommendations

## Today's Top Opportunities
Table with columns:
| Rank | Company | Position | Match % | Status | Action Required | Deadline |

## New Jobs Discovered
- Jobs found today by source
- Salary ranges distribution
- Location distribution
- Remote vs onsite breakdown

## Application Pipeline
- New/Unreviewed: X jobs
- Shortlisted: X jobs
- Applied: X jobs
- Interview Process: X jobs
- Rejected: X jobs
- Offers: X jobs

## Company Insights
For top 5 matched companies:
- Company name and overview
- Why it's a good fit
- Potential connections
- Recent news/developments
- Application strategy

## Network Activity
- Connections identified: X
- Messages sent: X
- Responses received: X
- Introduction requests: X

## Action Items for Tomorrow
1. High-priority applications to complete
2. Follow-ups needed
3. New searches to run
4. Connections to reach out to
5. Research needed

## Trends and Analytics
- Match score trends (improving/declining)
- Most in-demand skills from job posts
- Salary trends observed
- Competition level insights

## Skills Gap Analysis
Based on job requirements:
- Most requested skills you have
- Most requested skills you lack
- Recommended learning priorities

## Weekly Statistics
- Total applications this week
- Response rate
- Average match score
- Top performing search queries

Save report to: {self.reports_dir}/daily_report_{datetime.now().strftime('%Y%m%d')}.md

Also create a summary JSON with key metrics:
{{
  "date": "2024-01-15",
  "jobs_discovered": 25,
  "applications_sent": 5,
  "high_matches": 8,
  "connections_found": 12,
  "response_rate": 0.20
}}

Save metrics to: {self.reports_dir}/metrics_{datetime.now().strftime('%Y%m%d')}.json
"""
        return prompt
    
    def generate_weekly_summary_prompt(self) -> str:
        """Generate prompt for weekly summary."""
        week_start = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        week_end = datetime.now().strftime('%Y-%m-%d')
        
        prompt = f"""
Generate a weekly job search summary report.

Period: {week_start} to {week_end}

Analyze data from:
- All daily reports in {self.reports_dir}
- Database at {self.data_dir}/jobs.db
- All job search results

Create comprehensive weekly summary:

# Weekly Job Search Summary
## Week of {week_start}

### Performance Metrics
- Total jobs discovered
- Total applications submitted  
- Interview invitations received
- Offer letters received
- Response rate trends

### Top Performing Strategies
- Which search queries yielded best matches
- Which companies showed most interest
- Most effective networking approaches
- Best times/days for applications

### Pipeline Movement
Show week-over-week changes:
- New → Shortlisted
- Shortlisted → Applied
- Applied → Interview
- Interview → Offer

### Company Analysis
- Most searched companies
- Companies with multiple openings
- Fast-responding companies
- Companies to avoid (poor ratings/culture)

### Networking Success
- Total connections made
- Response rate from outreach
- Most helpful connections
- Alumni network effectiveness

### Salary Insights
- Average salary range for your matches
- Salary by location
- Salary by company size
- Negotiation opportunities identified

### Recommendations for Next Week
Based on this week's data:
1. Focus areas
2. Companies to prioritize
3. Skills to emphasize
4. Network connections to pursue
5. Application timing optimization

Save to: {self.reports_dir}/weekly_summary_{datetime.now().strftime('%Y%m%d')}.md
"""
        return prompt
    
    def generate_interview_prep_prompt(self, company: str, position: str) -> str:
        """Generate interview preparation prompt."""
        prompt = f"""
Create an interview preparation guide for:
Company: {company}
Position: {position}

Using data from:
- Company research: {self.data_dir}/company_research.json
- Job description: {self.data_dir}/job_search_results.json
- Your profile: {self.data_dir}/profile_extracted.json

Generate comprehensive prep guide:

# Interview Preparation: {position} at {company}

## Company Research Summary
- Mission and values
- Recent news and developments
- Company culture insights
- Growth trajectory
- Competitive landscape

## Role Analysis
- Key responsibilities
- Required skills and how you match
- Team structure
- Growth opportunities
- Success metrics for the role

## Likely Interview Questions

### Technical Questions
Based on job requirements:
1. [Question] → [Your prepared answer]
2. ...

### Behavioral Questions (STAR Format)
1. "Tell me about a time when..."
   - Situation: 
   - Task:
   - Action:
   - Result:

### Company-Specific Questions
1. "Why {company}?"
2. "What do you know about our products/services?"
3. "How do you align with our values?"

## Your Questions to Ask
### About the Role
- Question about day-to-day responsibilities
- Question about team dynamics
- Question about success metrics

### About the Company
- Question about company direction
- Question about culture
- Question about growth opportunities

## Your Unique Value Proposition
3 key points that differentiate you:
1. [Unique strength + evidence]
2. [Unique experience + relevance]
3. [Unique skill + application]

## Potential Concerns to Address
- Any gaps in experience → How to position
- Overqualification → How to address
- Career changes → How to explain

## Salary Negotiation Prep
- Market rate for this position: $X - $Y
- Your target range: $X - $Y  
- Justification points
- Benefits to negotiate

## Day-of Interview Checklist
- Documents to bring
- Outfit recommendations
- Arrival time planning
- Technology check (for virtual)
- Energy management tips

Save to: {self.reports_dir}/interview_prep_{company}_{datetime.now().strftime('%Y%m%d')}.md
"""
        return prompt
    
    def generate_application_tracker_prompt(self) -> str:
        """Generate application tracking report."""
        prompt = f"""
Create an application tracking dashboard.

Read from database: {self.data_dir}/jobs.db

Generate a detailed tracker:

# Application Tracker - {datetime.now().strftime('%Y-%m-%d')}

## Active Applications

### Awaiting Response
| Company | Position | Applied Date | Days Waiting | Follow-up Date |
|---------|----------|--------------|--------------|----------------|
| ... | ... | ... | ... | ... |

### In Process
| Company | Position | Stage | Next Step | Deadline |
|---------|----------|--------|-----------|----------|
| ... | ... | Phone Screen | Technical Interview | 2024-01-20 |

### Scheduled Interviews
| Date | Time | Company | Position | Type | Interviewer |
|------|------|---------|----------|------|-------------|
| ... | ... | ... | ... | ... | ... |

## Response Analytics
- Average response time: X days
- Response rate: X%
- Ghost rate: X%
- Positive response rate: X%

## Follow-up Required
Applications needing follow-up (>7 days):
1. Company - Position (Applied: date)
2. ...

## Rejected Applications
Brief analysis:
- Common rejection reasons
- Patterns identified
- Lessons learned

## Success Metrics
- Applications sent: X
- Responses received: X
- Interviews scheduled: X
- Offers received: X
- Conversion rates at each stage

## Time Analysis
- Average time to response: X days
- Average time to interview: X days
- Average time to offer: X days
- Fastest responding companies

## Recommendations
Based on tracking data:
- Optimal follow-up timing
- Best days to apply
- Companies with high response rates
- Application velocity suggestions

Save to: {self.reports_dir}/application_tracker_{datetime.now().strftime('%Y%m%d')}.md
"""
        return prompt
    
    def generate_network_map_prompt(self) -> str:
        """Generate network mapping report."""
        prompt = f"""
Create a comprehensive network map report.

Using data from:
- Connections: {self.data_dir}/connections/*.json
- Companies: {self.data_dir}/company_research.json
- LinkedIn: {self.data_dir}/profile_extracted.json

Generate network visualization report:

# Professional Network Map

## Network Overview
- Total connections: X
- Companies represented: X
- Industries covered: X
- Geographic distribution

## Connection Strength Analysis

### Tier 1: Strong Connections
People you can reach out to directly:
| Name | Company | Role | Relationship | Last Contact | Notes |

### Tier 2: Mutual Connections  
People who could introduce you:
| Name | Company | Mutual Connection | Path | Strength |

### Tier 3: Alumni Network
School connections at target companies:
| Name | Company | School | Graduation Year | Common Ground |

## Company Coverage
For each target company:
- Company Name
  - Direct connections: X
  - 2nd degree: X
  - Alumni: X
  - Key contacts identified
  - Recommended approach

## Networking Action Plan
Priority outreach list:
1. [Name] at [Company] - [Reason] - [Message template]
2. ...

## Relationship Management
- Connections needing reconnection (>6 months)
- Thank you notes to send
- Introductions to request
- Coffee chats to schedule

## Network Gaps
Companies/roles lacking connections:
- Company A: No connections (Strategy: Cold outreach/Alumni search)
- Company B: Only 3rd degree (Strategy: Request introduction)

## Networking Metrics
- Outreach sent: X
- Response rate: X%
- Meetings scheduled: X
- Referrals received: X

Save to: {self.reports_dir}/network_map_{datetime.now().strftime('%Y%m%d')}.md
"""
        return prompt
    
    def generate_skills_analysis_prompt(self) -> str:
        """Generate skills gap analysis."""
        prompt = f"""
Perform a skills gap analysis based on job search data.

Analyze:
- Your skills: {self.data_dir}/profile_extracted.json
- Job requirements: {self.data_dir}/job_search_results.json
- Matched jobs: {self.data_dir}/job_matches.json

Create skills analysis report:

# Skills Analysis Report

## Your Current Skills Profile
### Technical Skills
- Skill: Proficiency level | Market demand
### Soft Skills
- Skill: Evidence | Frequency requested

## Market Demand Analysis
### Most Requested Skills
From analyzed job postings:
1. Skill (mentioned in X% of posts)
2. ...

### Emerging Skills
New or trending requirements:
- Skill: Why it's emerging

## Skills Gap Assessment

### Critical Gaps
Skills you lack that appear in >50% of target jobs:
| Skill | Frequency | Impact on Match Score | Learning Difficulty |

### Minor Gaps
Skills that would improve matches:
| Skill | Frequency | Potential Score Increase |

## Skills Strength Analysis
Your competitive advantages:
| Skill | Market Demand | Your Proficiency | Differentiator |

## Learning Recommendations

### Priority 1: Critical for current search
1. Skill: Resources to learn | Timeline | Cost

### Priority 2: Career advancement
1. Skill: Resources | ROI analysis

### Priority 3: Future-proofing
1. Skill: Why important | When to learn

## Skill Positioning Strategy
How to highlight your strengths:
- For technical roles: Emphasize...
- For leadership roles: Highlight...
- For startup environments: Focus on...

## Certification Analysis
Valuable certifications based on job posts:
| Certification | Jobs Requiring | Cost | Time | ROI |

Save to: {self.reports_dir}/skills_analysis_{datetime.now().strftime('%Y%m%d')}.md
"""
        return prompt
    
    def generate_market_insights_prompt(self) -> str:
        """Generate market insights report."""
        prompt = f"""
Generate job market insights report.

Analyze all data from:
- Job searches: {self.data_dir}/job_search_results.json
- Companies: {self.data_dir}/company_research.json
- Applications: {self.data_dir}/applications/*.json

Create market insights:

# Job Market Insights Report

## Market Overview
- Total jobs analyzed: X
- Date range: Y to Z
- Locations covered: [...]
- Industries analyzed: [...]

## Demand Trends
### Hot Markets
Locations with most opportunities:
1. Location: # of jobs | Avg salary | Remote %

### Growing Roles
Job titles with increasing postings:
1. Title: Growth % | Avg salary | Key requirements

## Salary Intelligence
### By Location
| Location | Min | Median | Max | Cost of Living Index |

### By Experience Level
| Level | Min | Median | Max | Years Required |

### By Company Size
| Size | Min | Median | Max | Other Benefits |

## Company Insights
### Best Employers
Based on ratings, benefits, growth:
1. Company: Why they rank high

### Fastest Growing
Companies with most new postings:
1. Company: # of openings | Growth indicators

## Competition Analysis
- Average applicants per role (estimated)
- Time to fill positions
- Most competitive roles
- Least competitive opportunities

## Remote Work Trends
- % of jobs offering remote
- Remote salary differential
- Industries embracing remote
- Remote-first companies

## Timing Insights
- Best days to apply
- Posting patterns by day/week
- Seasonal trends observed
- Urgency indicators

## Recommendations
Based on market analysis:
1. Focus on these locations...
2. Target these companies...
3. Emphasize these skills...
4. Adjust salary expectations to...
5. Apply during these windows...

Save to: {self.reports_dir}/market_insights_{datetime.now().strftime('%Y%m%d')}.md
"""
        return prompt