# Technical Requirements Document (TRD)
## Job Application Discovery System - Claude Code CLI Implementation

**Version:** 1.0  
**Date:** January 15, 2025  
**Status:** Draft

---

## 1. System Overview

### 1.1 Architecture Pattern
- **Type:** CLI-based multi-agent simulation
- **Runtime:** Local machine execution via Claude Code CLI
- **Core Engine:** Claude API (Opus 4.1 model)
- **Storage:** Local file system (JSON, SQLite, Markdown)
- **External Dependencies:** Minimal (Claude API only)

### 1.2 System Components
```
┌─────────────────────────────────────────────┐
│             User Interface (CLI)            │
├─────────────────────────────────────────────┤
│          Claude Code CLI Wrapper            │
├─────────────────────────────────────────────┤
│            Agent Orchestrator               │
├──────┬──────┬──────┬──────┬──────┬─────────┤
│Discovery│Research│Matching│Network│Application│External│
│ Agent  │ Agent │ Agent  │Agent │  Agent   │  AI    │
├─────────────────────────────────────────────┤
│          Local Data Layer                   │
│    (JSON, SQLite, Markdown files)          │
└─────────────────────────────────────────────┘
```

---

## 2. Technical Architecture

### 2.1 Agent Implementation

Each agent is implemented as a specialized Claude prompt template with specific context and instructions.

#### 2.1.1 Agent Communication Protocol
```json
{
  "agent_type": "discovery|research|matching|network|application|external_ai",
  "request": {
    "action": "string",
    "parameters": {},
    "context": {}
  },
  "response": {
    "status": "success|error|pending",
    "data": {},
    "next_actions": []
  }
}
```

#### 2.1.2 Agent Prompt Templates

**Discovery Agent Template:**
```markdown
You are a job discovery specialist. Your task is to:
1. Search for {job_title} positions in {location}
2. Use web scraping to find opportunities from:
   - LinkedIn Jobs
   - Company career pages
   - Job boards
3. Extract: title, company, location, URL, posting date
4. Return structured JSON with findings
Context: {user_resume_summary}
Preferences: {user_preferences}
```

**Research Agent Template:**
```markdown
You are a company research specialist. For {company_name}:
1. Gather company overview and mission
2. Find recent news and developments
3. Analyze culture and values
4. Identify growth metrics
5. Search for employee reviews
Return structured company intelligence report
```

**Matching Agent Template:**
```markdown
You are a job matching specialist. Analyze:
Resume: {resume_content}
Job Description: {job_description}
Calculate match score based on:
1. Skill alignment (40%)
2. Experience match (30%)
3. Education requirements (15%)
4. Location fit (15%)
Return match score with detailed breakdown
```

**Network Agent Template:**
```markdown
You are a LinkedIn network analyst. For {company_name}:
1. Search for connections from {linkedin_profile}
2. Identify 1st, 2nd, 3rd degree connections
3. Find alumni from {schools} at company
4. Locate hiring managers and recruiters
5. Generate personalized outreach messages
Return network mapping report with contact strategies
```

**Application Agent Template:**
```markdown
You are an application assistant. For {application_url}:
1. Read and parse the application form
2. Extract all questions and required fields
3. Map fields to resume data: {resume_data}
4. Generate appropriate answers
5. Flag fields requiring user input
Return structured Q&A with suggested responses
```

**External AI Integration Agent Template:**
```markdown
You are an external AI integration specialist. Your tasks:
1. Generate optimized prompts for {ai_platform} (e.g., Grok)
2. Format prompts to maximize structured data return
3. Parse and integrate external AI responses
4. Merge results with existing job database

For Grok prompts, include:
- Specific job search parameters: {job_title}, {location}
- Request for structured format (JSON/list)
- Focus on platforms Grok has unique access to
- Time-sensitive information (recent posts)
```

### 2.2 Data Storage Architecture

#### 2.2.1 File Structure
```
~/claude-job-search/
├── config/
│   ├── profile.json          # User profile and preferences
│   ├── settings.json         # System settings
│   └── credentials.json      # API keys (encrypted)
├── data/
│   ├── jobs.db              # SQLite database
│   ├── companies/           # Company research cache
│   │   └── {company_id}.json
│   ├── applications/        # Application tracking
│   │   └── {date}/
│   │       └── {job_id}.json
│   ├── connections/         # Network cache
│   │   └── {company_id}.json
│   └── external_ai/         # External AI results
│       ├── grok/
│       │   └── {search_id}.json
│       └── prompts/
│           └── {timestamp}.md
├── templates/
│   ├── answers.md           # Answer templates
│   ├── outreach.md          # Message templates
│   └── cover_letters.md    # Cover letter templates
└── reports/
    └── {date}/
        ├── job_search.md    # Daily search results
        ├── companies.md     # Company reports
        └── network.md       # Connection reports
```

#### 2.2.2 Database Schema (SQLite)

```sql
-- Jobs table
CREATE TABLE jobs (
    id INTEGER PRIMARY KEY,
    job_id TEXT UNIQUE,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    location TEXT,
    url TEXT,
    description TEXT,
    posted_date DATE,
    discovered_date DATE DEFAULT CURRENT_DATE,
    match_score REAL,
    status TEXT DEFAULT 'new',
    source TEXT DEFAULT 'claude',  -- claude, grok, chatgpt, etc.
    notes TEXT
);

-- Applications table
CREATE TABLE applications (
    id INTEGER PRIMARY KEY,
    job_id TEXT,
    applied_date DATE DEFAULT CURRENT_DATE,
    status TEXT DEFAULT 'pending',
    application_url TEXT,
    questions JSON,
    answers JSON,
    documents JSON,
    FOREIGN KEY (job_id) REFERENCES jobs(job_id)
);

-- Connections table
CREATE TABLE connections (
    id INTEGER PRIMARY KEY,
    name TEXT,
    company TEXT,
    title TEXT,
    connection_degree INTEGER,
    linkedin_url TEXT,
    mutual_connections JSON,
    last_updated DATE DEFAULT CURRENT_DATE
);

-- Search history table
CREATE TABLE search_history (
    id INTEGER PRIMARY KEY,
    search_date DATE DEFAULT CURRENT_DATE,
    query JSON,
    results_count INTEGER,
    parameters JSON
);
```

### 2.3 CLI Implementation

#### 2.3.1 Command Structure

```python
# Pseudo-code for CLI wrapper
class ClaudeJobCLI:
    def __init__(self):
        self.config = load_config()
        self.db = initialize_database()
        
    def execute_command(self, command, args):
        commands = {
            'init': self.initialize_profile,
            'search': self.search_jobs,
            'grok-prompt': self.generate_grok_prompt,
            'import-grok': self.import_grok_results,
            'apply': self.assist_application,
            'network': self.find_connections,
            'status': self.show_status,
            'export': self.export_data
        }
        return commands[command](args)
    
    def call_claude(self, agent_type, prompt):
        # Construct full prompt with agent template
        full_prompt = load_agent_template(agent_type).format(**prompt)
        # Execute via Claude Code CLI
        response = subprocess.run(
            ['claude-code', full_prompt],
            capture_output=True,
            text=True
        )
        return parse_response(response.stdout)
```

#### 2.3.2 Command Specifications

**init Command:**
```bash
claude-job init --resume <file> --linkedin <profile_url>
```
- Parses resume using Claude
- Extracts skills, experience, education
- Stores LinkedIn profile for network analysis
- Creates initial profile.json

**search Command:**
```bash
claude-job search --title <job_title> --location <location> [--remote] [--salary <range>]
```
- Triggers Discovery Agent
- Optionally triggers Research Agent for top matches
- Stores results in database
- Generates markdown report

**network Command:**
```bash
claude-job network --company <company_name> [--refresh]
```
- Triggers Network Agent
- Searches LinkedIn for connections
- Generates outreach templates
- Caches results locally

**apply Command:**
```bash
claude-job apply <url> [--interactive]
```
- Triggers Application Agent
- Extracts form questions
- Provides answer suggestions
- Interactive mode for Q&A

**status Command:**
```bash
claude-job status [--filter <status>] [--days <n>]
```
- Shows application pipeline
- Filters by status (applied, pending, rejected)
- Displays recent activity

**grok-prompt Command:**
```bash
claude-job grok-prompt --title <job_title> --location <location> [--company <name>]
```
- Generates optimized Grok search prompt
- Includes structured format instructions
- Saves prompt for reference
- Displays prompt for manual copy

**import-grok Command:**
```bash
claude-job import-grok --file <results_file> | --paste
```
- Parses Grok search results
- Integrates with existing job database
- Deduplicates against existing listings
- Triggers matching agent for imported jobs

### 2.4 External AI Integration Layer

#### 2.4.1 Grok Prompt Generation

```python
class GrokPromptGenerator:
    def generate_search_prompt(self, criteria):
        """Generate optimized Grok prompt for job search"""
        prompt = f"""
        Search for {criteria['title']} positions in {criteria['location']} 
        posted in the last {criteria.get('days', 7)} days.
        
        Include the following information for each job:
        - Company name
        - Job title
        - Location (remote/hybrid/onsite)
        - Application URL or company careers page
        - Salary range if available
        - Key requirements (3-5 bullet points)
        - Posted date
        
        Format the response as a structured list with clear separators.
        
        Also check for:
        - X (Twitter) job posts with #hiring #{criteria['title'].replace(' ', '')}
        - Startup job boards and AngelList
        - HackerNews Who's Hiring threads
        - Tech community forums
        
        Focus on opportunities not typically found on LinkedIn or Indeed.
        """
        return prompt
    
    def generate_company_prompt(self, company):
        """Generate Grok prompt for specific company research"""
        prompt = f"""
        Find all open positions at {company} for the following roles:
        {', '.join(self.relevant_roles)}
        
        Check:
        - Official {company} careers page
        - Recent social media posts about hiring
        - Employee referral programs
        - Internal job boards mentioned in forums
        - Glassdoor and Blind discussions
        
        Provide direct application links where possible.
        """
        return prompt
```

#### 2.4.2 Grok Result Parser

```python
class GrokResultParser:
    def parse_grok_response(self, response_text):
        """Parse unstructured Grok response into structured data"""
        jobs = []
        
        # Use Claude to help parse the response
        parse_prompt = f"""
        Parse this Grok job search response into structured JSON:
        
        {response_text}
        
        Extract each job with:
        - title
        - company
        - location
        - url
        - requirements
        - salary (if mentioned)
        - source (e.g., Twitter, AngelList, etc.)
        """
        
        parsed_data = self.claude_parse(parse_prompt)
        
        # Validate and clean the data
        for job in parsed_data['jobs']:
            job['source'] = 'grok'
            job['imported_date'] = datetime.now()
            jobs.append(self.validate_job(job))
        
        return jobs
    
    def deduplicate(self, grok_jobs, existing_jobs):
        """Remove duplicates between Grok and existing results"""
        unique_jobs = []
        existing_keys = {(j['company'], j['title']) for j in existing_jobs}
        
        for job in grok_jobs:
            key = (job['company'], job['title'])
            if key not in existing_keys:
                unique_jobs.append(job)
        
        return unique_jobs
```

### 2.5 Web Interaction Layer

#### 2.5.1 Web Scraping Strategy

```python
class WebScraper:
    def fetch_job_listing(self, url):
        """Fetch job details using Claude's web reading capability"""
        prompt = f"""
        Please read the job posting at {url} and extract:
        - Job title
        - Company name
        - Location
        - Job description
        - Requirements
        - Application deadline
        - Application URL
        Return as structured JSON
        """
        return claude_fetch(prompt)
    
    def read_application_form(self, url):
        """Extract form fields from application page"""
        prompt = f"""
        Navigate to {url} and identify:
        - All form fields and their types
        - Required vs optional fields
        - Character/word limits
        - File upload requirements
        - Multi-step process indicators
        Return structured form schema
        """
        return claude_fetch(prompt)
```

#### 2.5.2 LinkedIn Integration

```python
class LinkedInAnalyzer:
    def find_connections(self, company, profile_url):
        """Search for connections at target company"""
        prompt = f"""
        Search LinkedIn for connections between {profile_url} and employees at {company}:
        1. Direct connections (1st degree)
        2. Mutual connections (2nd degree) 
        3. Alumni connections from schools: {schools}
        4. Hiring managers and recruiters
        
        For each connection provide:
        - Name and title
        - Connection path
        - Suggested approach
        """
        return claude_fetch(prompt)
```

### 2.6 Answer Generation Engine

#### 2.6.1 Context-Aware Response Generation

```python
class AnswerGenerator:
    def generate_answer(self, question, context):
        """Generate contextual answer for application question"""
        prompt = f"""
        Question: {question}
        Resume Context: {context['resume']}
        Job Description: {context['job_desc']}
        Company Info: {context['company']}
        
        Generate a professional answer that:
        1. Directly addresses the question
        2. Incorporates relevant experience
        3. Uses appropriate keywords
        4. Stays within {context['limit']} characters
        """
        return claude_generate(prompt)
    
    def generate_outreach(self, connection, job):
        """Generate networking message"""
        prompt = f"""
        Create a professional LinkedIn message:
        To: {connection['name']} ({connection['title']})
        Relationship: {connection['relationship']}
        Regarding: {job['title']} at {job['company']}
        
        Message should be:
        - Personalized based on relationship
        - Brief (under 300 characters)
        - Professional but warm
        - Include clear ask
        """
        return claude_generate(prompt)
```

---

## 3. Implementation Details

### 3.1 Error Handling

```python
class ErrorHandler:
    def handle_api_error(self, error):
        """Handle Claude API errors"""
        if error.type == 'rate_limit':
            return self.implement_backoff()
        elif error.type == 'timeout':
            return self.retry_with_cache()
        else:
            self.log_error(error)
            return self.fallback_response()
    
    def handle_scraping_error(self, url, error):
        """Handle web scraping failures"""
        if 'blocked' in error:
            return self.use_cached_data(url)
        elif 'structure_changed' in error:
            return self.notify_user_manual_input()
```

### 3.2 Caching Strategy

```python
class CacheManager:
    def __init__(self):
        self.cache_dir = "~/.claude-job/cache"
        self.ttl = {
            'job_listing': 24 * 3600,      # 24 hours
            'company_info': 7 * 24 * 3600,  # 7 days
            'connections': 3 * 24 * 3600,   # 3 days
            'application_form': 3600,       # 1 hour
            'grok_results': 12 * 3600,     # 12 hours
            'grok_prompts': 30 * 24 * 3600 # 30 days
        }
    
    def get_cached(self, key, data_type):
        """Retrieve cached data if valid"""
        cache_file = f"{self.cache_dir}/{data_type}/{key}.json"
        if self.is_valid(cache_file, self.ttl[data_type]):
            return load_json(cache_file)
        return None
    
    def store(self, key, data, data_type):
        """Store data with timestamp"""
        cache_file = f"{self.cache_dir}/{data_type}/{key}.json"
        data['cached_at'] = datetime.now().isoformat()
        save_json(cache_file, data)
```

### 3.3 Rate Limiting

```python
class RateLimiter:
    def __init__(self):
        self.limits = {
            'claude_api': 100,  # requests per hour
            'web_fetch': 30,    # requests per minute
            'linkedin': 10      # requests per minute
        }
        self.requests = defaultdict(list)
    
    def check_limit(self, service):
        """Check if request is within rate limits"""
        now = time.time()
        window = 3600 if service == 'claude_api' else 60
        
        # Remove old requests outside window
        self.requests[service] = [
            t for t in self.requests[service] 
            if now - t < window
        ]
        
        if len(self.requests[service]) >= self.limits[service]:
            wait_time = window - (now - self.requests[service][0])
            return False, wait_time
        
        self.requests[service].append(now)
        return True, 0
```

---

## 4. Performance Optimization

### 4.1 Parallel Processing

```python
class ParallelProcessor:
    def search_multiple_sources(self, query):
        """Search multiple job boards in parallel"""
        sources = ['linkedin', 'indeed', 'company_sites']
        
        # Generate Grok prompt for external search
        grok_prompt = GrokPromptGenerator().generate_search_prompt(query)
        self.save_prompt_for_user(grok_prompt)
        
        # Create tasks for each source
        tasks = []
        for source in sources:
            task = {
                'agent': 'discovery',
                'source': source,
                'query': query
            }
            tasks.append(task)
        
        # Execute in parallel (simulated via multiple Claude calls)
        results = self.execute_parallel(tasks)
        return self.merge_results(results)
```

### 4.2 Batch Processing

```python
class BatchProcessor:
    def process_applications(self, job_urls):
        """Process multiple applications efficiently"""
        # Group by domain to optimize scraping
        grouped = self.group_by_domain(job_urls)
        
        results = []
        for domain, urls in grouped.items():
            # Use same session for same domain
            session_results = self.process_domain_batch(domain, urls)
            results.extend(session_results)
        
        return results
```

---

## 5. Security Considerations

### 5.1 Data Protection

```python
class SecurityManager:
    def encrypt_sensitive_data(self, data):
        """Encrypt sensitive information"""
        # Use local keyring for encryption key
        key = self.get_encryption_key()
        
        sensitive_fields = ['ssn', 'dob', 'salary_current']
        for field in sensitive_fields:
            if field in data:
                data[field] = self.encrypt(data[field], key)
        
        return data
    
    def sanitize_input(self, user_input):
        """Sanitize user input before processing"""
        # Remove potential injection attempts
        sanitized = re.sub(r'[<>\"\'`;]', '', user_input)
        return sanitized[:1000]  # Limit length
```

### 5.2 API Key Management

```python
class CredentialManager:
    def __init__(self):
        self.keyring_service = "claude-job-search"
    
    def store_api_key(self, service, key):
        """Securely store API keys"""
        import keyring
        keyring.set_password(self.keyring_service, service, key)
    
    def get_api_key(self, service):
        """Retrieve API keys securely"""
        import keyring
        return keyring.get_password(self.keyring_service, service)
```

---

## 6. Testing Strategy

### 6.1 Unit Tests

```python
# test_agents.py
class TestAgents:
    def test_discovery_agent(self):
        """Test job discovery functionality"""
        mock_response = {"jobs": [...]}
        result = DiscoveryAgent.search("software engineer", "San Francisco")
        assert len(result['jobs']) > 0
        assert all(['title' in job for job in result['jobs']])
    
    def test_matching_agent(self):
        """Test job matching algorithm"""
        resume = load_test_resume()
        job_desc = load_test_job()
        score = MatchingAgent.calculate_match(resume, job_desc)
        assert 0 <= score <= 100
        assert 'breakdown' in score
```

### 6.2 Integration Tests

```python
class TestIntegration:
    def test_full_workflow(self):
        """Test complete job search workflow"""
        # Initialize profile
        cli.execute('init', '--resume', 'test_resume.pdf')
        
        # Search for jobs
        results = cli.execute('search', '--title', 'engineer')
        assert results['count'] > 0
        
        # Generate and test Grok prompt
        grok_prompt = cli.execute('grok-prompt', '--title', 'engineer')
        assert 'Search for' in grok_prompt
        
        # Import Grok results
        grok_results = cli.execute('import-grok', '--file', 'test_grok.txt')
        assert grok_results['imported'] > 0
        
        # Find connections
        network = cli.execute('network', '--company', 'TestCorp')
        assert 'connections' in network
        
        # Apply to job
        application = cli.execute('apply', results['jobs'][0]['url'])
        assert 'questions' in application
```

---

## 7. Monitoring and Logging

### 7.1 Logging Configuration

```python
import logging

# Configure logging
logging.basicConfig(
    filename='~/.claude-job/logs/app.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class ActivityLogger:
    def log_search(self, query, results_count):
        """Log search activity"""
        logging.info(f"Search: {query} - Found: {results_count}")
    
    def log_application(self, job_id, status):
        """Log application activity"""
        logging.info(f"Application: {job_id} - Status: {status}")
    
    def log_api_usage(self, tokens_used):
        """Track API token usage"""
        logging.info(f"API Usage: {tokens_used} tokens")
```

### 7.2 Performance Metrics

```python
class MetricsCollector:
    def collect_metrics(self):
        """Collect system metrics"""
        metrics = {
            'total_searches': self.count_searches(),
            'applications_sent': self.count_applications(),
            'success_rate': self.calculate_success_rate(),
            'avg_response_time': self.avg_response_time(),
            'cache_hit_rate': self.cache_hit_rate()
        }
        return metrics
    
    def generate_report(self):
        """Generate metrics report"""
        metrics = self.collect_metrics()
        report = f"""
        # Performance Report
        
        Total Searches: {metrics['total_searches']}
        Applications Sent: {metrics['applications_sent']}
        Success Rate: {metrics['success_rate']}%
        Avg Response Time: {metrics['avg_response_time']}s
        Cache Hit Rate: {metrics['cache_hit_rate']}%
        """
        save_report(report)
```

---

## 8. Deployment and Setup

### 8.1 Installation Script

```bash
#!/bin/bash
# install.sh

echo "Setting up Claude Job Search CLI..."

# Create directory structure
mkdir -p ~/.claude-job/{config,data,templates,reports,logs,cache}

# Initialize database
sqlite3 ~/.claude-job/data/jobs.db < schema.sql

# Copy templates
cp templates/* ~/.claude-job/templates/

# Set permissions
chmod 700 ~/.claude-job
chmod 600 ~/.claude-job/config/*

# Create command alias
echo 'alias claude-job="python ~/claude-job-search/cli.py"' >> ~/.bashrc

echo "Installation complete! Run 'claude-job init' to get started."
```

### 8.2 Configuration File

```json
// ~/.claude-job/config/settings.json
{
  "version": "1.0.0",
  "claude_api": {
    "model": "claude-opus-4-1",
    "max_tokens": 4000,
    "temperature": 0.7
  },
  "search": {
    "default_location": "Remote",
    "results_per_search": 20,
    "auto_research": true,
    "include_grok": true
  },
  "external_ai": {
    "grok": {
      "enabled": true,
      "auto_generate_prompts": true,
      "include_sources": ["twitter", "angellist", "hackernews"]
    },
    "other_platforms": {
      "enabled": false,
      "platforms": []
    }
  },
  "network": {
    "include_3rd_degree": false,
    "alumni_priority": true
  },
  "cache": {
    "enabled": true,
    "max_size_mb": 500
  },
  "export": {
    "format": "markdown",
    "include_scores": true
  }
}
```

---

## 9. Phased Implementation Plan

### 9.0 MVP-Today: Immediate Launch Implementation (4 Hours)

#### Single-File Implementation
```python
# job_search_mvp.py - Everything in one file for immediate use

class JobSearchMVP:
    def __init__(self):
        self.profile_dir = "./profile"
        self.output_dir = "./job_search_results"
        self.profile = {}
        self.jobs = []
        
    def parse_resume_and_linkedin(self):
        """Step 1: Extract data from resume and LinkedIn PDFs"""
        prompt = f"""
        Read the resume at {self.profile_dir}/resume.pdf and extract:
        - Skills (technical and soft)
        - Work experience (companies, roles, dates)
        - Education
        - Key achievements
        
        Also read LinkedIn profile at {self.profile_dir}/linkedin.pdf and extract:
        - Complete work history
        - Connections/network info
        - Endorsements
        - Summary
        
        Return as structured JSON.
        """
        return self.claude_execute(prompt)
    
    def search_jobs(self, title, location):
        """Step 2: Find relevant jobs"""
        prompt = f"""
        Search for {title} jobs in {location}:
        1. Check LinkedIn Jobs
        2. Search Indeed
        3. Look at major tech company career pages
        4. Check AngelList for startups
        
        For each job return:
        - Company name
        - Job title
        - Location
        - URL
        - Key requirements
        - Posted date
        
        Find at least 20 positions.
        """
        return self.claude_execute(prompt)
    
    def generate_grok_prompt(self, title, location):
        """Step 3: Create Grok search prompt"""
        return f"""
        Find {title} positions in {location} from:
        - X/Twitter #hiring posts
        - Hacker News Who's Hiring
        - Startup communities
        - Recent posts (last 7 days)
        
        Format: Company | Role | URL | Requirements
        """
    
    def research_and_shortlist(self, jobs):
        """Step 4: Research companies and create shortlist"""
        prompt = f"""
        For these jobs: {jobs}
        
        Research each company:
        - Company size and culture
        - Recent news
        - Growth trajectory
        - Reviews from employees
        
        Score each job based on my profile: {self.profile}
        - Skill match (0-40 points)
        - Experience match (0-30 points)  
        - Culture fit (0-20 points)
        - Growth potential (0-10 points)
        
        Return top 10 with scores and reasoning.
        """
        return self.claude_execute(prompt)
    
    def generate_application_guidance(self, job, company):
        """Step 5: Create application strategy"""
        prompt = f"""
        Based on my profile: {self.profile}
        For this role: {job} at {company}
        
        Generate:
        1. Key Resume Points to Emphasize:
           - Top 5 relevant experiences
           - Skills to highlight
           - Achievements that matter
        
        2. Cover Letter Outline:
           - Opening hook
           - Why you're perfect (3 points)
           - Why you want this company
           - Strong closing
        
        3. LinkedIn Connections:
           - Search for 1st/2nd degree connections at {company}
           - Alumni from my schools
           - People in similar roles
        
        4. Application Tips:
           - Keywords to include
           - Red flags to avoid
           - Follow-up timeline
        
        5. Interview Prep Points:
           - Likely questions
           - Stories to prepare
           - Questions to ask them
        """
        return self.claude_execute(prompt)
    
    def run_complete_search(self, job_title, location):
        """Main execution flow"""
        print("Step 1: Parsing your profile...")
        self.profile = self.parse_resume_and_linkedin()
        
        print("Step 2: Searching for jobs...")
        self.jobs = self.search_jobs(job_title, location)
        
        print("Step 3: Generating Grok prompt...")
        grok_prompt = self.generate_grok_prompt(job_title, location)
        
        print("Step 4: Researching and shortlisting...")
        shortlist = self.research_and_shortlist(self.jobs)
        
        print("Step 5: Generating application guidance...")
        guidance = {}
        for job in shortlist[:10]:
            guidance[job['id']] = self.generate_application_guidance(
                job, job['company']
            )
        
        # Save everything to markdown
        self.save_results(shortlist, guidance, grok_prompt)
        
    def save_results(self, shortlist, guidance, grok_prompt):
        """Save all outputs as markdown files"""
        # Main results file
        with open(f"{self.output_dir}/job_search_results.md", "w") as f:
            f.write("# Job Search Results\n\n")
            f.write("## Top 10 Opportunities\n\n")
            for job in shortlist:
                f.write(f"### {job['title']} at {job['company']}\n")
                f.write(f"- Score: {job['score']}/100\n")
                f.write(f"- URL: {job['url']}\n")
                f.write(f"- Reasoning: {job['reasoning']}\n\n")
            
            f.write("\n## Grok Search Prompt\n")
            f.write(f"```\n{grok_prompt}\n```\n")
        
        # Individual guidance files
        for job_id, guide in guidance.items():
            with open(f"{self.output_dir}/apply_{job_id}.md", "w") as f:
                f.write(guide)
```

#### Immediate Execution Commands
```bash
# Today's MVP - Just run these commands directly

# 1. Parse profile
claude-code "Read profile/resume.pdf and profile/linkedin.pdf. Extract all skills, experience, education, and network info. Save as profile.json"

# 2. Search jobs  
claude-code "Find 20 software engineer jobs in San Francisco. Check LinkedIn, Indeed, company sites. Save as jobs.md with company, title, URL, requirements"

# 3. Research and shortlist
claude-code "Read jobs.md and profile.json. Score each job on skill match, experience fit, culture, growth. Return top 10 with reasoning"

# 4. Get application help
claude-code "For [Company] [Role], based on profile.json, give me: resume points to emphasize, cover letter outline, LinkedIn connections to reach, application tips"

# 5. Generate Grok prompt
claude-code "Create a Grok prompt to find software engineer jobs in SF from Twitter, HackerNews, startups"
```

### 9.1 Phase 1: Discovery & Intelligence (Weeks 1-3)

#### Week 1 Deliverables
```python
# Core Components to Build
- ProfileManager class
  - Resume parser integration
  - LinkedIn data extractor
  - Preference storage system
- DatabaseManager class
  - SQLite schema creation
  - CRUD operations
  - Query builders
```

#### Week 2 Deliverables
```python
# Discovery Components
- DiscoveryAgent class
  - Web scraping implementation
  - Multi-source aggregation
  - Result deduplication
- GrokIntegration class
  - Prompt generator
  - Result parser
  - Import pipeline
```

#### Week 3 Deliverables
```python
# Intelligence Components
- ResearchAgent class
  - Company data gathering
  - Report generation
- MatchingAgent class
  - Scoring algorithm
  - Ranking system
- NetworkAgent class
  - Connection finder
  - Outreach templates
```

### 9.2 Phase 2: Application Platform (Weeks 4-6)

#### Week 4 Deliverables
```python
# Application Analysis
- ApplicationAgent class
  - Form reader
  - Question extractor
  - Field mapper
```

#### Week 5 Deliverables
```python
# Interactive System
- AnswerGenerator class
  - Context-aware responses
  - Template management
- InteractiveUI class
  - Q&A interface
  - Validation system
```

#### Week 6 Deliverables
```python
# Application Management
- ApplicationTracker class
  - Status management
  - History tracking
- DocumentGenerator class
  - Cover letters
  - Export functions
```

### 9.3 Testing Strategy by Phase

#### Phase 1 Tests
- Unit tests for each agent
- Integration tests for data flow
- Mock data for web scraping tests
- Grok prompt validation tests

#### Phase 2 Tests
- Form parsing accuracy tests
- Answer generation quality tests
- End-to-end application workflow tests
- User acceptance testing

## 10. Future Enhancements

### 10.1 Post-MVP Features
- Browser extension for one-click application assistance
- Mobile companion app for on-the-go tracking
- Integration with calendar for interview scheduling
- Resume optimization suggestions based on job matches
- Salary negotiation assistant

### 10.2 Scalability Path
- Migration to cloud deployment if needed
- Multi-user support with proper authentication
- API endpoints for third-party integrations
- Advanced ML models for better matching

---

## 11. Appendices

### A. API Response Formats

```json
// Job Discovery Response
{
  "jobs": [
    {
      "id": "unique_id",
      "title": "Software Engineer",
      "company": "TechCorp",
      "location": "San Francisco, CA",
      "url": "https://...",
      "posted_date": "2024-01-15",
      "description": "...",
      "requirements": [],
      "salary_range": "$120k-$180k"
    }
  ],
  "metadata": {
    "search_query": "...",
    "total_results": 45,
    "sources": ["linkedin", "indeed"]
  }
}
```

### B. Error Codes

| Code | Description | Action |
|------|-------------|--------|
| E001 | API Rate Limit | Wait and retry |
| E002 | Invalid Resume Format | Request different format |
| E003 | Website Blocked Scraping | Use cache or manual input |
| E004 | Network Timeout | Retry with backoff |
| E005 | Invalid Credentials | Re-authenticate |

### C. Command Reference

| Command | Description | Example |
|---------|-------------|---------|
| init | Initialize profile | `claude-job init --resume resume.pdf` |
| search | Search for jobs | `claude-job search --title "Data Scientist" --location "NYC"` |
| grok-prompt | Generate Grok prompt | `claude-job grok-prompt --title "ML Engineer" --location "SF"` |
| import-grok | Import Grok results | `claude-job import-grok --file grok_results.txt` |
| network | Find connections | `claude-job network --company Google` |
| apply | Application assistance | `claude-job apply https://job-url.com` |
| status | View applications | `claude-job status --filter pending` |
| export | Export data | `claude-job export --format csv --output jobs.csv` |

---

**Document Control:**
- **Author:** [Your Name]
- **Technical Lead:** [Tech Lead Name]
- **Last Updated:** January 15, 2025
- **Next Review:** February 15, 2025