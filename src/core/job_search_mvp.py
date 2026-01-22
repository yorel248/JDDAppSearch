#!/usr/bin/env python3
"""
Job Search MVP - Works with Claude Code CLI (no API key required)
This system generates prompts that you execute with Claude Code
"""

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import hashlib
from .profile_manager import ProfileManager


class JobSearchMVP:
    """MVP Implementation - Immediate job search functionality using Claude Code."""
    
    def __init__(self, data_dir: str = "./data", profile_dir: str = "./profile"):
        self.data_dir = Path(data_dir)
        self.profile_dir = Path(profile_dir)
        self.output_dir = Path("./reports") / datetime.now().strftime("%Y%m%d")
        self.prompts_dir = Path("./data/prompts")
        
        # Create directories
        for dir_path in [self.data_dir, self.profile_dir, self.output_dir, self.prompts_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        self.profile_manager = ProfileManager()
        self.db_path = self.data_dir / "jobs.db"
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database for job tracking."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT UNIQUE,
                title TEXT NOT NULL,
                company TEXT NOT NULL,
                location TEXT,
                url TEXT,
                description TEXT,
                requirements TEXT,
                posted_date DATE,
                discovered_date DATE DEFAULT CURRENT_DATE,
                match_score REAL,
                status TEXT DEFAULT 'new',
                source TEXT DEFAULT 'claude',
                salary_min INTEGER,
                salary_max INTEGER,
                remote_type TEXT,
                notes TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT,
                applied_date DATE DEFAULT CURRENT_DATE,
                status TEXT DEFAULT 'pending',
                application_url TEXT,
                questions TEXT,
                answers TEXT,
                cover_letter TEXT,
                notes TEXT,
                FOREIGN KEY (job_id) REFERENCES jobs(job_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS connections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                company TEXT,
                title TEXT,
                connection_degree INTEGER,
                linkedin_url TEXT,
                connection_path TEXT,
                outreach_message TEXT,
                contacted BOOLEAN DEFAULT 0,
                last_updated DATE DEFAULT CURRENT_DATE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                search_date DATE DEFAULT CURRENT_DATE,
                search_type TEXT,
                query TEXT,
                results_count INTEGER,
                parameters TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def generate_job_id(self, company: str, title: str) -> str:
        """Generate unique job ID."""
        text = f"{company}_{title}_{datetime.now().isoformat()}"
        return hashlib.md5(text.encode()).hexdigest()[:12]
    
    # ============= PROMPT GENERATORS =============
    # These methods generate prompts for Claude Code execution
    
    def generate_resume_parse_prompt(self) -> str:
        """Generate prompt to parse resume with Claude Code."""
        prompt = f'''
Please analyze the resume and LinkedIn profile in the ./profile directory and extract structured information.

Read these files:
- ./profile/resume.pdf (or .docx, .txt)
- ./profile/linkedin.pdf (if available)

Extract and return as JSON:
{{
  "personal_info": {{
    "name": "Full Name",
    "email": "email@example.com",
    "phone": "phone number",
    "location": "City, State/Country",
    "linkedin_url": "linkedin.com/in/...",
    "github_url": "github.com/..."
  }},
  "skills": {{
    "technical": ["skill1", "skill2", ...],
    "soft": ["skill1", "skill2", ...],
    "languages": ["English", ...],
    "certifications": ["cert1", ...]
  }},
  "experience": [
    {{
      "title": "Job Title",
      "company": "Company Name",
      "location": "City, State",
      "start_date": "MM/YYYY",
      "end_date": "MM/YYYY or Present",
      "description": "Role description",
      "achievements": ["achievement1", "achievement2"]
    }}
  ],
  "education": [
    {{
      "degree": "Degree Type",
      "field": "Field of Study",
      "institution": "University Name",
      "graduation_year": "YYYY",
      "gpa": "X.XX"
    }}
  ],
  "projects": [
    {{
      "name": "Project Name",
      "description": "Project description",
      "technologies": ["tech1", "tech2"],
      "url": "github.com/..."
    }}
  ],
  "summary": "A 2-3 sentence professional summary"
}}

Save the extracted data to: ./data/profile_extracted.json
'''
        return prompt
    
    def generate_job_search_prompt(self, job_title: str, location: str, 
                                  preferences: Optional[Dict] = None) -> str:
        """Generate prompt for job search."""
        pref_str = ""
        if preferences:
            pref_str = f"""
Additional preferences:
- Remote preference: {preferences.get('remote_preference', 'any')}
- Company size: {', '.join(preferences.get('company_size', ['any']))}
- Salary range: ${preferences.get('salary_min', 0)}-${preferences.get('salary_max', 'unlimited')}
"""
        
        # Enhance job title to include partnerships and alliance roles
        enhanced_job_title = self._enhance_job_title_with_partnerships(job_title)
        
        prompt = f'''
Search for "{enhanced_job_title}" positions in "{location}" using web search.

Search these sources:
1. LinkedIn Jobs
2. Indeed
3. Glassdoor
4. AngelList (for startups)
5. Major tech company career pages (Google, Meta, Apple, Microsoft, Amazon, etc.)
6. Remote job boards (if remote/hybrid preferred)
{pref_str}

For each job found, extract:
- Company name
- Job title (exact)
- Location (city, state/country, remote status)
- Direct application URL (CRITICAL: Find the actual job posting URL, not the careers page)
- Job description link (Direct link to full JD if different from application URL)
- Salary range (if available)
- Key requirements (top 5)
- Posted date
- Job type (full-time, part-time, contract)
- Company size estimate

IMPORTANT: For job links, prioritize:
1. Direct job posting URLs (e.g., company.com/jobs/position-id)
2. LinkedIn job URLs (linkedin.com/jobs/view/job-id)
3. Seek.com.au job URLs (seek.com.au/job/job-id)
4. Indeed job URLs (au.indeed.com/viewjob?jk=job-id)
AVOID: Generic careers pages without specific job links

Find at least 20 relevant positions.

Format output as JSON array and save to: ./data/job_search_results.json

Example format:
[
  {{
    "company": "TechCorp",
    "title": "Senior Software Engineer",
    "location": "San Francisco, CA (Hybrid)",
    "url": "https://careers.techcorp.com/jobs/123",
    "jd_link": "https://careers.techcorp.com/jobs/123/description",
    "salary_min": 150000,
    "salary_max": 200000,
    "requirements": ["Python", "AWS", "5+ years experience", "Django", "Leadership"],
    "posted_date": "2024-01-15",
    "job_type": "full-time",
    "company_size": "1000-5000",
    "description_snippet": "First 200 chars of job description..."
  }}
]
'''
        return prompt
    
    def generate_company_research_prompt(self, companies: List[str]) -> str:
        """Generate prompt for company research."""
        companies_list = '\n'.join([f"- {company}" for company in companies[:10]])
        
        prompt = f'''
Research these companies and provide detailed information:

Companies to research:
{companies_list}

For each company, find:
1. Company Overview
   - Mission and values
   - Industry and market position
   - Size (employees and revenue if public)
   - Headquarters and office locations
   - Year founded

2. Culture & Work Environment
   - Work-life balance reputation
   - Employee reviews summary (from Glassdoor/Indeed)
   - Diversity and inclusion initiatives
   - Remote work policies
   - Benefits and perks

3. Recent Developments
   - Latest news (last 6 months)
   - Product launches or major projects
   - Funding rounds or acquisitions
   - Layoffs or hiring surges

4. Technology Stack (for tech companies)
   - Main technologies used
   - Engineering culture
   - Open source contributions

5. Growth & Stability
   - Financial health indicators
   - Growth trajectory
   - Market challenges

Format as JSON and save to: ./data/company_research.json

Example format:
{{
  "company_name": {{
    "overview": {{...}},
    "culture": {{...}},
    "recent_news": [...],
    "tech_stack": [...],
    "growth_indicators": {{...}},
    "pros": [...],
    "cons": [...],
    "overall_rating": 4.2
  }}
}}
'''
        return prompt
    
    def generate_job_matching_prompt(self, profile_path: str = "./data/profile_extracted.json",
                                    jobs_path: str = "./data/job_search_results.json") -> str:
        """Generate prompt for job matching and scoring."""
        prompt = f'''
Analyze job matches based on the user's profile and the job listings found.

Input files:
1. User Profile: {profile_path}
2. Job Listings: {jobs_path}

For each job, calculate a match score (0-100) based on:
- Skill alignment (40%): How well do the candidate's skills match requirements?
- Experience match (30%): Years of experience and relevance of past roles
- Education fit (15%): Does education meet requirements?
- Location/Remote preference (15%): Location compatibility

Additional scoring factors:
- Boost score if company is in preferred industry (+5)
- Boost if salary range matches expectations (+5)
- Penalty if overqualified (-10)
- Penalty if significantly underqualified (-20)

Create a shortlist of top 15 jobs with:
1. Match score and detailed breakdown
2. Strengths (why you're a good fit)
3. Gaps (what you might be missing)
4. Why apply (compelling reasons)
5. Application strategy tips

Output format (save to: ./data/job_matches.json):
{{
  "matches": [
    {{
      "job_id": "generated_id",
      "company": "Company Name",
      "title": "Job Title",
      "match_score": 85,
      "score_breakdown": {{
        "skills": 35,
        "experience": 25,
        "education": 15,
        "location": 10
      }},
      "strengths": ["Strength 1", "Strength 2"],
      "gaps": ["Gap 1"],
      "why_apply": "Compelling reason to apply",
      "application_tips": ["Tip 1", "Tip 2"],
      "priority": "high|medium|low"
    }}
  ],
  "summary": {{
    "total_jobs_analyzed": 20,
    "high_matches": 5,
    "medium_matches": 8,
    "low_matches": 7
  }}
}}
'''
        return prompt
    
    def generate_network_discovery_prompt(self, company: str, 
                                         linkedin_profile: Optional[str] = None) -> str:
        """Generate prompt for finding connections at a company."""
        profile_note = f"LinkedIn Profile: {linkedin_profile}" if linkedin_profile else "Check ./profile/linkedin.pdf for profile information"
        
        prompt = f'''
Find potential connections at {company} who could help with job applications.

{profile_note}

Search for:
1. **Direct Connections (1st degree)**
   - People you're already connected with at {company}
   - Note their current role and department

2. **Alumni Connections**
   - People from your schools working at {company}
   - Shared graduation years or programs
   - Common professors or clubs

3. **Professional Connections**
   - People from previous companies now at {company}
   - Shared professional groups or associations
   - Conference speakers or attendees you might know

4. **Strategic Contacts**
   - Hiring managers in relevant departments
   - Recruiters specializing in your field
   - Team members you might work with

5. **Mutual Connections**
   - People who could introduce you to employees at {company}
   - Connection strength indicator

For each connection found, provide:
- Name and title
- Connection type (direct, alumni, mutual, etc.)
- Department/Team
- How you're connected
- Suggested outreach approach
- Message template

Output format (save to: ./data/network_{company}.json):
{{
  "company": "{company}",
  "connections": [
    {{
      "name": "John Doe",
      "title": "Senior Engineer",
      "department": "Platform Team",
      "connection_type": "alumni",
      "connection_detail": "UC Berkeley 2018",
      "linkedin_url": "linkedin.com/in/johndoe",
      "outreach_strategy": "Mention shared Berkeley experience",
      "message_template": "Hi John, I noticed we're both Berkeley alums..."
    }}
  ],
  "summary": {{
    "total_connections": 10,
    "direct": 2,
    "alumni": 3,
    "mutual": 5
  }}
}}
'''
        return prompt
    
    def generate_application_helper_prompt(self, job_url: str, job_details: Dict) -> str:
        """Generate prompt to help with job application."""
        prompt = f'''
Help me apply to this position:
- Company: {job_details.get('company')}
- Title: {job_details.get('title')}
- URL: {job_url}

Please visit the application page and:

1. **Extract Application Questions**
   - All form fields and their types
   - Required vs optional fields
   - Character/word limits
   - File upload requirements
   - Any screening questions

2. **Generate Tailored Responses**
   Based on profile at ./data/profile_extracted.json:
   - Answer all application questions
   - Optimize for ATS keywords
   - Stay within character limits
   - Highlight relevant experience

3. **Create Cover Letter**
   Write a compelling cover letter that:
   - Opens with a strong hook
   - Maps experience to job requirements
   - Shows knowledge of company
   - Closes with clear next steps
   - Stays under 400 words

4. **Resume Optimization Tips**
   Suggest resume tweaks for this specific role:
   - Keywords to add
   - Experiences to emphasize
   - Projects to highlight
   - Skills to feature prominently

5. **Interview Preparation**
   Provide likely interview questions and talking points:
   - Technical questions
   - Behavioral questions (STAR format)
   - Questions to ask them
   - Salary negotiation points

Save output to: ./data/applications/{job_details.get('company')}_{job_details.get('title')}.json

Format:
{{
  "application_url": "{job_url}",
  "questions": [...],
  "suggested_answers": {{...}},
  "cover_letter": "Full cover letter text",
  "resume_tips": [...],
  "interview_prep": {{...}}
}}
'''
        return prompt
    
    def generate_grok_search_prompt(self, job_title: str, location: str) -> str:
        """Generate Grok prompt for additional job searches."""
        prompt = f'''
=== COPY THIS PROMPT TO GROK ===

Find {job_title} positions in {location} from these sources:
- X/Twitter posts with #hiring #{job_title.replace(" ", "")}
- Hacker News "Who's Hiring" threads (last 2 months)
- AngelList startup jobs
- Y Combinator company job boards
- Tech community forums and Slack groups
- Reddit r/forhire and relevant subreddits
- Remote-first companies if applicable

Include:
Company | Role | Location | Apply URL | Posted Date | Source

Focus on:
- Jobs posted in last 7 days
- Startups and companies not on mainstream job boards
- Direct application links (skip aggregators)
- Include salary info if mentioned

Format as a structured list for easy parsing.

=== END GROK PROMPT ===

After getting Grok results, save them to: ./data/grok_results.txt
Then run the import prompt to process them.
'''
        return prompt
    
    def generate_grok_import_prompt(self) -> str:
        """Generate prompt to import Grok results."""
        prompt = '''
Parse the Grok job search results from ./data/grok_results.txt

Extract each job and format as JSON, adding to our existing job database.
For each job, extract:
- Company name
- Job title
- Location
- Application URL
- Posted date
- Source platform
- Any mentioned salary
- Brief description

Deduplicate against existing jobs in ./data/job_search_results.json
Mark source as "grok" for these entries.

Append unique jobs to: ./data/job_search_results.json
Report how many new unique jobs were found.
'''
        return prompt
    
    # ============= WORKFLOW METHODS =============
    
    def create_daily_search_workflow(self, job_title: str, location: str) -> Dict[str, str]:
        """Create a complete daily job search workflow."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        workflow = {
            "created": timestamp,
            "job_title": job_title,
            "location": location,
            "prompts": {}
        }
        
        # Generate all prompts
        prompts = {
            "1_parse_resume": self.generate_resume_parse_prompt(),
            "2_search_jobs": self.generate_job_search_prompt(job_title, location),
            "3_research_companies": "Run after job search to research top companies",
            "4_match_jobs": self.generate_job_matching_prompt(),
            "5_grok_search": self.generate_grok_search_prompt(job_title, location),
            "6_grok_import": self.generate_grok_import_prompt(),
            "7_network_discovery": "Run for each target company",
            "8_application_help": "Run for each job you want to apply to"
        }
        
        workflow["prompts"] = prompts
        
        # Save workflow
        workflow_path = self.prompts_dir / f"workflow_{timestamp}.json"
        with open(workflow_path, 'w') as f:
            json.dump(workflow, f, indent=2)
        
        # Create execution instructions
        instructions = f'''
# Job Search Workflow - {timestamp}
## Searching for: {job_title} in {location}

### Step-by-Step Execution:

1. **Parse Your Resume** (if not already done)
   ```
   Run prompt: 1_parse_resume
   ```

2. **Search for Jobs**
   ```
   Run prompt: 2_search_jobs
   ```

3. **Research Top Companies**
   After job search completes, get company list and run:
   ```
   Run prompt: 3_research_companies (with company list)
   ```

4. **Match and Score Jobs**
   ```
   Run prompt: 4_match_jobs
   ```

5. **Expand Search with Grok** (optional)
   ```
   Copy prompt: 5_grok_search to Grok
   Save results to: ./data/grok_results.txt
   Run prompt: 6_grok_import
   Re-run prompt: 4_match_jobs
   ```

6. **Find Connections** (for top matches)
   ```
   Run prompt: 7_network_discovery for each target company
   ```

7. **Apply to Jobs**
   ```
   Run prompt: 8_application_help for each job
   ```

### Output Files:
- Profile: ./data/profile_extracted.json
- Jobs Found: ./data/job_search_results.json  
- Companies: ./data/company_research.json
- Matches: ./data/job_matches.json
- Networks: ./data/network_[company].json
- Applications: ./data/applications/[company]_[title].json

### Daily Report Location:
{self.output_dir}
'''
        
        # Save instructions
        instructions_path = self.output_dir / f"workflow_instructions_{timestamp}.md"
        with open(instructions_path, 'w') as f:
            f.write(instructions)
        
        print(f"Workflow created! See instructions at: {instructions_path}")
        
        return workflow
    
    def generate_application_tracker(self) -> str:
        """Generate prompt to create application tracking report."""
        prompt = '''
Create an application tracking report from the database at ./data/jobs.db

Generate a markdown report showing:

1. **Application Pipeline**
   - New/Discovered jobs
   - Shortlisted
   - Applied
   - Interview scheduled
   - Rejected
   - Offers

2. **This Week's Activity**
   - Jobs discovered
   - Applications sent
   - Responses received
   - Follow-ups needed

3. **Top Opportunities**
   Table with:
   - Company
   - Role
   - Match Score
   - Status
   - Next Action
   - Due Date

4. **Action Items**
   - Applications to complete
   - Follow-ups to send
   - Thank you notes to write
   - Connections to reach out to

Save report to: ./reports/application_tracker.md
'''
        return prompt
    
    def save_prompt_to_file(self, prompt: str, name: str) -> Path:
        """Save a prompt to file for easy execution."""
        prompt_path = self.prompts_dir / f"{name}_{datetime.now().strftime('%Y%m%d')}.txt"
        with open(prompt_path, 'w') as f:
            f.write(prompt)
        return prompt_path
    
    def _enhance_job_title_with_partnerships(self, job_title: str) -> str:
        """Enhance job title to include partnerships and alliance roles."""
        partnership_roles = [
            "Head of Partnerships", "VP of Partnerships", "Director of Partnerships",
            "Head of Strategic Partnerships", "VP Strategic Partnerships",
            "Head of Alliances", "VP of Alliances", "Director of Alliances",
            "Head of Business Development", "VP Business Development",
            "Head of Channel Partnerships", "VP Channel Partnerships",
            "Head of Ecosystem", "VP of Ecosystem",
            "Chief Partnership Officer", "CPO Partnerships",
            "Head of Strategic Alliances", "VP Strategic Alliances",
            "Business Development Director", "Strategic Partnerships Manager"
        ]
        
        # Add partnership roles to existing search
        partnership_string = " ".join(partnership_roles)
        return f"{job_title} {partnership_string}"


class PromptExecutor:
    """Helper class to manage prompt execution flow."""
    
    def __init__(self, mvp: JobSearchMVP):
        self.mvp = mvp
        self.execution_log = []
    
    def log_execution(self, step: str, status: str = "pending"):
        """Log execution step."""
        self.execution_log.append({
            "step": step,
            "status": status,
            "timestamp": datetime.now().isoformat()
        })
    
    def create_batch_prompts(self, job_title: str, location: str) -> Dict[str, Path]:
        """Create all prompts for a job search batch."""
        prompts = {}
        
        # Generate and save all prompts
        prompts["resume"] = self.mvp.save_prompt_to_file(
            self.mvp.generate_resume_parse_prompt(), "1_parse_resume"
        )
        
        prompts["search"] = self.mvp.save_prompt_to_file(
            self.mvp.generate_job_search_prompt(job_title, location), "2_search_jobs"
        )
        
        prompts["matching"] = self.mvp.save_prompt_to_file(
            self.mvp.generate_job_matching_prompt(), "4_match_jobs"
        )
        
        prompts["grok"] = self.mvp.save_prompt_to_file(
            self.mvp.generate_grok_search_prompt(job_title, location), "5_grok_search"
        )
        
        prompts["tracker"] = self.mvp.save_prompt_to_file(
            self.mvp.generate_application_tracker(), "9_tracker"
        )
        
        return prompts