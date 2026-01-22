# Claude Job Search System 🎯

An intelligent, multi-agent job discovery and application system powered by Claude Code. No API keys required!

## 🌟 Features

- **Resume-Based Matching**: Analyzes your resume to find the best job matches
- **Multi-Source Search**: Discovers jobs from LinkedIn, Indeed, company sites, and more
- **Company Intelligence**: Deep research on companies including culture, tech stack, and recent news
- **Network Discovery**: Finds your connections at target companies (alumni, colleagues, etc.)
- **Application Assistant**: Helps answer application questions and generate cover letters
- **Grok Integration**: Extends search to X/Twitter, HackerNews, and startup communities
- **No API Keys**: Works entirely through Claude Code CLI - no expensive APIs needed!

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/claude-job-search.git
cd claude-job-search

# Run the installation script
chmod +x install.sh
./install.sh
```

### Basic Usage

1. **Initialize your profile**:
   - Place your resume in `profile/resume.pdf`
   - Place your LinkedIn PDF in `profile/linkedin.pdf` (optional)
   ```bash
   ./claude_job.py init
   ```

2. **Search for jobs**:
   ```bash
   ./claude_job.py search "Software Engineer" "San Francisco"
   ```

3. **Match jobs with your profile**:
   ```bash
   ./claude_job.py match
   ```

4. **Research companies**:
   ```bash
   ./claude_job.py company Google Meta Apple
   ```

5. **Find connections**:
   ```bash
   ./claude_job.py network Google
   ```

6. **Get application help**:
   ```bash
   ./claude_job.py apply https://careers.google.com/jobs/123
   ```

## 📋 How It Works

This system generates intelligent prompts that you execute with Claude Code. Here's the workflow:

1. **Generate Prompt**: The system creates a detailed prompt for Claude
2. **Execute with Claude**: Copy the prompt and run it with Claude Code
3. **Claude Processes**: Claude searches the web, analyzes data, and creates structured output
4. **Save Results**: Claude saves results as JSON files in the `data/` directory
5. **Iterate**: Run additional commands to refine and expand your search

## 🏗️ System Architecture

```
claude-job-search/
├── src/
│   ├── core/              # Core modules
│   │   ├── job_search_mvp.py   # Main MVP implementation
│   │   ├── profile_manager.py   # Resume/profile management
│   │   ├── database.py          # SQLite database operations
│   │   └── cache.py            # Caching system
│   └── agents/            # Agent modules (Phase 2)
├── data/                  # Data storage
│   ├── profile_extracted.json  # Your parsed resume
│   ├── job_search_results.json # Found jobs
│   ├── job_matches.json        # Matched & scored jobs
│   └── jobs.db                 # SQLite database
├── profile/               # Your resume and LinkedIn
├── reports/               # Generated reports
├── config/                # Configuration files
└── claude_job.py         # Main CLI interface
```

## 🎯 Commands Reference

### Core Commands

| Command | Description | Example |
|---------|-------------|---------|
| `init` | Initialize profile with resume | `./claude_job.py init` |
| `search` | Search for jobs | `./claude_job.py search "Data Scientist" "NYC"` |
| `match` | Match jobs with profile | `./claude_job.py match` |
| `company` | Research companies | `./claude_job.py company Tesla SpaceX` |
| `network` | Find connections | `./claude_job.py network Apple` |
| `apply` | Get application help | `./claude_job.py apply https://job.url` |

### Advanced Commands

| Command | Description | Example |
|---------|-------------|---------|
| `grok` | Generate Grok search prompt | `./claude_job.py grok "ML Engineer" "Remote"` |
| `grok --import` | Import Grok results | `./claude_job.py grok --import` |
| `workflow` | Create complete workflow | `./claude_job.py workflow "DevOps" "Seattle"` |
| `status` | Show pipeline status | `./claude_job.py status --report` |
| `cache` | Manage cache | `./claude_job.py cache --clean` |
| `export` | Export all data | `./claude_job.py export -o backup.json` |

### Command Options

- **Search Options**:
  - `--remote`: Remote positions only
  - `--hybrid`: Hybrid positions
  - `--salary-min`: Minimum salary
  - `--salary-max`: Maximum salary

- **Status Options**:
  - `--verbose`: Show detailed information
  - `--report`: Generate full report

## 🔄 Daily Workflow Example

```bash
# Morning: Create your daily workflow
./claude_job.py workflow "Senior Engineer" "San Francisco"

# Execute each step with Claude Code:
# 1. Parse resume (if not done)
# 2. Search for jobs
# 3. Research top companies
# 4. Match and score jobs
# 5. Expand search with Grok
# 6. Find connections at top companies
# 7. Apply to best matches

# Evening: Check status
./claude_job.py status --report
```

## 🤖 Grok Integration

Extend your search beyond traditional job boards:

1. **Generate Grok Prompt**:
   ```bash
   ./claude_job.py grok "Product Manager" "Austin"
   ```

2. **Copy prompt to Grok** and get results

3. **Save results** to `data/grok_results.txt`

4. **Import results**:
   ```bash
   ./claude_job.py grok --import
   ```

5. **Re-run matching** to include new jobs

## 📊 Understanding Match Scores

The system scores each job based on:

- **Skill Alignment (40%)**: How well your skills match requirements
- **Experience Match (30%)**: Years of experience and role relevance
- **Education Fit (15%)**: Education requirements met
- **Location Preference (15%)**: Location and remote work compatibility

Additional modifiers:
- +5 points: Company in preferred industry
- +5 points: Salary range matches expectations
- -10 points: Overqualified
- -20 points: Significantly underqualified

## 🗂️ Data Management

### Database Schema

- **Jobs**: All discovered job listings
- **Applications**: Application tracking and status
- **Connections**: Professional network at companies
- **Companies**: Researched company information
- **Search History**: Past searches and results

### File Storage

- `data/`: JSON files and SQLite database
- `cache/`: Cached search results (auto-expires)
- `reports/`: Daily reports and exports
- `profile/`: Your resume and LinkedIn files

## 🔒 Privacy & Security

- **100% Local**: All data stays on your machine
- **No Cloud Services**: No data sent to external servers
- **No API Keys**: No credentials to manage or secure
- **You Control Everything**: Delete any file anytime

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test
python -m pytest tests/test_profile_manager.py -v
```

## 🛠️ Configuration

Edit `config/config.json` to customize:

- Search preferences
- Matching weights
- Cache TTL
- Export formats
- Rate limits

## 📈 Roadmap

### Current (MVP)
- ✅ Resume parsing
- ✅ Job search
- ✅ Company research  
- ✅ Job matching
- ✅ Network discovery
- ✅ Application assistance
- ✅ Grok integration

### Phase 2 (Coming Soon)
- [ ] Browser extension
- [ ] Email notifications
- [ ] Interview scheduler
- [ ] Salary insights
- [ ] ATS optimization
- [ ] Cover letter templates

### Phase 3 (Future)
- [ ] AI mock interviews
- [ ] Negotiation assistant
- [ ] Portfolio analyzer
- [ ] Skill gap analysis
- [ ] Learning recommendations

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

MIT License - see LICENSE file for details

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/claude-job-search/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/claude-job-search/discussions)

## 🙏 Acknowledgments

- Built for use with Claude Code CLI
- Inspired by the job search struggles we all face
- Special thanks to the open source community

---

**Remember**: This tool generates prompts for Claude Code. You need to execute them with Claude to get results. No API keys required!

Happy job hunting! 🚀