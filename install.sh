#!/bin/bash

# Claude Job Search - Installation Script
# This script sets up the job search system on your local machine

set -e  # Exit on error

echo "======================================"
echo "Claude Job Search System Installation"
echo "======================================"
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python version
echo "Checking Python version..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    echo -e "${GREEN}✓${NC} Python $PYTHON_VERSION found"
else
    echo -e "${RED}✗${NC} Python 3 is required but not found"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

# Create necessary directories
echo ""
echo "Creating directory structure..."
directories=(
    "data"
    "data/companies"
    "data/applications"
    "data/connections"
    "data/external_ai/grok"
    "data/external_ai/prompts"
    "data/prompts"
    "cache"
    "config"
    "templates"
    "reports"
    "profile"
    "logs"
)

for dir in "${directories[@]}"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        echo -e "${GREEN}✓${NC} Created $dir"
    else
        echo -e "${YELLOW}→${NC} $dir already exists"
    fi
done

# Copy configuration files if they don't exist
echo ""
echo "Setting up configuration..."
if [ ! -f "config/config.json" ]; then
    if [ -f "config/config.json.example" ]; then
        cp config/config.json.example config/config.json
        echo -e "${GREEN}✓${NC} Created config/config.json"
    fi
else
    echo -e "${YELLOW}→${NC} config/config.json already exists"
fi

# Create .env file if it doesn't exist
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    cp .env.example .env
    echo -e "${GREEN}✓${NC} Created .env file"
    echo -e "${YELLOW}!${NC} Please edit .env file with your settings"
fi

# Initialize database
echo ""
echo "Initializing database..."
python3 -c "from src.core.database import DatabaseManager; DatabaseManager()" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Database initialized"
else
    echo -e "${YELLOW}→${NC} Database initialization skipped (may already exist)"
fi

# Make the main script executable
echo ""
echo "Setting up executable..."
chmod +x claude_job.py
echo -e "${GREEN}✓${NC} Made claude_job.py executable"

# Create a symbolic link for easy access (optional)
echo ""
read -p "Create system-wide command 'claude-job'? (requires sudo) [y/N]: " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    SCRIPT_PATH=$(pwd)/claude_job.py
    if [ -f "/usr/local/bin/claude-job" ]; then
        echo -e "${YELLOW}→${NC} /usr/local/bin/claude-job already exists"
    else
        sudo ln -s "$SCRIPT_PATH" /usr/local/bin/claude-job
        echo -e "${GREEN}✓${NC} Created system command 'claude-job'"
    fi
fi

# Create sample resume template
echo ""
echo "Creating sample templates..."
cat > profile/resume_template.txt << 'EOF'
# Resume Template
# Fill this out with your information or place your actual resume file here

Name: [Your Name]
Email: [your.email@example.com]
Phone: [Your Phone]
Location: [City, State]
LinkedIn: linkedin.com/in/yourprofile
GitHub: github.com/yourusername

## Professional Summary
[2-3 sentences about your professional background and goals]

## Skills
### Technical Skills
- Programming: Python, JavaScript, Java
- Frameworks: React, Django, Spring
- Tools: Git, Docker, Kubernetes
- Databases: PostgreSQL, MongoDB

### Soft Skills
- Leadership
- Communication
- Problem Solving

## Experience
### Job Title | Company Name
Location | Start Date - End Date
- Achievement or responsibility 1
- Achievement or responsibility 2
- Achievement or responsibility 3

### Previous Job Title | Previous Company
Location | Start Date - End Date
- Achievement or responsibility 1
- Achievement or responsibility 2

## Education
### Degree Type | Field of Study
University Name | Graduation Year
GPA: X.XX (if 3.5+)

## Projects
### Project Name
- Description of project and your role
- Technologies used
- Impact or results

## Certifications
- Certification Name (Year)
EOF
echo -e "${GREEN}✓${NC} Created profile/resume_template.txt"

# Create quick start guide
cat > QUICKSTART.md << 'EOF'
# Claude Job Search - Quick Start Guide

## 🚀 Getting Started

### Step 1: Initialize Your Profile
Place your resume in the `profile` directory:
- `profile/resume.pdf` (or .docx, .txt)
- `profile/linkedin.pdf` (optional)

Then run:
```bash
./claude_job.py init
```

### Step 2: Search for Jobs
```bash
./claude_job.py search "Software Engineer" "San Francisco"
```

### Step 3: Match Jobs with Your Profile
```bash
./claude_job.py match
```

### Step 4: Research Companies
```bash
./claude_job.py company Google Meta Apple
```

### Step 5: Find Connections
```bash
./claude_job.py network Google
```

### Step 6: Get Application Help
```bash
./claude_job.py apply https://job-url.com
```

## 📝 Important Notes

1. **No API Key Required!** This system works with Claude Code CLI
2. **Execute Prompts**: Copy the generated prompts and run them with Claude Code
3. **Save Results**: Claude will save results to the specified JSON files
4. **Iterate**: Run matching again after getting more results

## 🔄 Daily Workflow

Create a complete workflow:
```bash
./claude_job.py workflow "Data Scientist" "Remote"
```

## 📊 Check Status
```bash
./claude_job.py status --report
```

## 🆘 Help
```bash
./claude_job.py --help
```
EOF
echo -e "${GREEN}✓${NC} Created QUICKSTART.md"

# Run tests
echo ""
read -p "Run tests to verify installation? [y/N]: " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Running tests..."
    python3 -m pytest tests/ -v 2>/dev/null
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓${NC} All tests passed"
    else
        echo -e "${YELLOW}!${NC} Some tests failed (this may be normal for first installation)"
    fi
fi

# Final summary
echo ""
echo "======================================"
echo -e "${GREEN}Installation Complete!${NC}"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Place your resume in: ./profile/resume.pdf"
echo "2. Run: ./claude_job.py init"
echo "3. Start searching: ./claude_job.py search \"Your Job Title\" \"Location\""
echo ""
echo "For detailed instructions, see QUICKSTART.md"
echo ""
echo "Happy job hunting! 🎯"