#!/usr/bin/env python3
"""
Claude Job Search CLI - Main entry point
Execute job search workflows using Claude Code
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.job_search_mvp import JobSearchMVP, PromptExecutor
from src.core.profile_manager import ProfileManager
from src.core.database import DatabaseManager
from src.core.cache import CacheManager


class ClaudeJobCLI:
    """Main CLI interface for job search system."""
    
    def __init__(self):
        self.mvp = JobSearchMVP()
        self.executor = PromptExecutor(self.mvp)
        self.profile_manager = ProfileManager()
        self.db = DatabaseManager()
        self.cache = CacheManager()
    
    def cmd_init(self, args):
        """Initialize user profile."""
        print("🚀 Initializing Job Search Profile\n")
        
        # Generate resume parsing prompt
        prompt = self.mvp.generate_resume_parse_prompt()
        prompt_file = self.mvp.save_prompt_to_file(prompt, "init_profile")
        
        print("📝 Profile Initialization Prompt Generated!")
        print(f"   Saved to: {prompt_file}\n")
        print("To initialize your profile:")
        print("1. Place your resume in: ./profile/resume.pdf (or .docx, .txt)")
        print("2. Place your LinkedIn PDF in: ./profile/linkedin.pdf (optional)")
        print("3. Execute the following with Claude Code:\n")
        print("-" * 50)
        print(prompt)
        print("-" * 50)
        print("\n✅ After Claude processes your files, your profile will be ready!")
        
        return 0
    
    def cmd_search(self, args):
        """Search for jobs."""
        print(f"🔍 Searching for {args.title} jobs in {args.location}\n")
        
        # Get preferences from profile if available
        preferences = self.profile_manager.get_preferences()
        if args.remote:
            preferences['remote_preference'] = 'remote'
        if args.hybrid:
            preferences['remote_preference'] = 'hybrid'
        if args.salary_min:
            preferences['salary_min'] = args.salary_min
        if args.salary_max:
            preferences['salary_max'] = args.salary_max
        
        # Generate search prompt
        prompt = self.mvp.generate_job_search_prompt(args.title, args.location, preferences)
        prompt_file = self.mvp.save_prompt_to_file(prompt, "job_search")
        
        # Log the search
        self.db.log_search({
            'search_type': 'claude',
            'job_title': args.title,
            'location': args.location,
            'parameters': preferences
        })
        
        print("🎯 Job Search Prompt Generated!")
        print(f"   Saved to: {prompt_file}\n")
        print("Execute the following with Claude Code:\n")
        print("-" * 50)
        print(prompt)
        print("-" * 50)
        
        return 0
    
    def cmd_match(self, args):
        """Match jobs with profile."""
        print("🎲 Generating Job Matching Analysis\n")
        
        # Check if profile and jobs exist
        profile_path = Path("./data/profile_extracted.json")
        jobs_path = Path("./data/job_search_results.json")
        
        if not profile_path.exists():
            print("❌ Profile not found! Run 'claude-job init' first.")
            return 1
        
        if not jobs_path.exists():
            print("❌ No job search results found! Run 'claude-job search' first.")
            return 1
        
        # Generate matching prompt
        prompt = self.mvp.generate_job_matching_prompt()
        prompt_file = self.mvp.save_prompt_to_file(prompt, "job_matching")
        
        print("📊 Job Matching Prompt Generated!")
        print(f"   Saved to: {prompt_file}\n")
        print("Execute the following with Claude Code:\n")
        print("-" * 50)
        print(prompt[:1000] + "...")  # Show preview
        print("-" * 50)
        print(f"\nFull prompt saved to: {prompt_file}")
        
        return 0
    
    def cmd_company(self, args):
        """Research companies."""
        companies = args.companies
        
        # If no companies specified, try to get from recent job matches
        if not companies:
            jobs_path = Path("./data/job_matches.json")
            if jobs_path.exists():
                with open(jobs_path, 'r') as f:
                    matches = json.load(f)
                    companies = list(set([m['company'] for m in matches.get('matches', [])[:10]]))
        
        if not companies:
            print("❌ No companies specified! Provide company names or run 'claude-job match' first.")
            return 1
        
        print(f"🏢 Researching {len(companies)} companies\n")
        
        # Generate research prompt
        prompt = self.mvp.generate_company_research_prompt(companies)
        prompt_file = self.mvp.save_prompt_to_file(prompt, "company_research")
        
        print("🔬 Company Research Prompt Generated!")
        print(f"   Companies: {', '.join(companies[:5])}{'...' if len(companies) > 5 else ''}")
        print(f"   Saved to: {prompt_file}\n")
        print("Execute with Claude Code to research these companies.")
        
        return 0
    
    def cmd_network(self, args):
        """Find network connections."""
        company = args.company
        
        print(f"🤝 Finding connections at {company}\n")
        
        # Get LinkedIn profile if available
        linkedin_profile = self.profile_manager.profile_data.get('personal_info', {}).get('linkedin_url')
        
        # Generate network discovery prompt
        prompt = self.mvp.generate_network_discovery_prompt(company, linkedin_profile)
        prompt_file = self.mvp.save_prompt_to_file(prompt, f"network_{company}")
        
        print("🔗 Network Discovery Prompt Generated!")
        print(f"   Company: {company}")
        print(f"   Saved to: {prompt_file}\n")
        print("Execute with Claude Code to find your connections.")
        
        return 0
    
    def cmd_apply(self, args):
        """Get application assistance."""
        url = args.url
        
        print(f"📝 Generating Application Assistance\n")
        print(f"   URL: {url}\n")
        
        # Try to find job details from database or cache
        job_details = {'company': 'Unknown', 'title': 'Unknown'}
        
        # Check if URL matches any jobs in database
        jobs = self.db.get_jobs_by_status('new') + self.db.get_jobs_by_status('shortlisted')
        for job in jobs:
            if job.get('url') == url:
                job_details = job
                break
        
        # Generate application helper prompt
        prompt = self.mvp.generate_application_helper_prompt(url, job_details)
        prompt_file = self.mvp.save_prompt_to_file(prompt, "application_help")
        
        print("✍️ Application Helper Prompt Generated!")
        print(f"   Saved to: {prompt_file}\n")
        print("Execute with Claude Code to get personalized application help.")
        
        # Save application record
        self.db.add_application({
            'job_id': job_details.get('job_id', 'manual'),
            'application_url': url,
            'status': 'in_progress'
        })
        
        return 0
    
    def cmd_grok(self, args):
        """Generate Grok search prompt."""
        if args.import_results:
            # Import Grok results
            print("📥 Generating Grok Import Prompt\n")
            prompt = self.mvp.generate_grok_import_prompt()
            prompt_file = self.mvp.save_prompt_to_file(prompt, "grok_import")
            
            print("📊 Grok Import Prompt Generated!")
            print(f"   Saved to: {prompt_file}\n")
            print("Make sure Grok results are saved in: ./data/grok_results.txt")
            print("Then execute the prompt with Claude Code.")
        else:
            # Generate Grok search prompt
            print(f"🤖 Generating Grok Search Prompt\n")
            print(f"   Job: {args.title}")
            print(f"   Location: {args.location}\n")
            
            prompt = self.mvp.generate_grok_search_prompt(args.title, args.location)
            prompt_file = self.mvp.save_prompt_to_file(prompt, "grok_search")
            
            print("🎯 Grok Search Prompt Generated!")
            print(f"   Saved to: {prompt_file}\n")
            print("Copy the following to Grok:\n")
            print("-" * 50)
            print(prompt)
            print("-" * 50)
            print("\nAfter getting results, save to: ./data/grok_results.txt")
            print("Then run: claude-job grok --import")
        
        return 0
    
    def cmd_workflow(self, args):
        """Create complete workflow."""
        print(f"🔄 Creating Complete Job Search Workflow\n")
        print(f"   Job: {args.title}")
        print(f"   Location: {args.location}\n")
        
        # Create workflow
        workflow = self.mvp.create_daily_search_workflow(args.title, args.location)
        
        print("✅ Workflow Created Successfully!\n")
        print("📁 Generated Files:")
        print(f"   - Workflow: ./data/prompts/workflow_{workflow['created']}.json")
        print(f"   - Instructions: {self.mvp.output_dir}/workflow_instructions_{workflow['created']}.md")
        print("\n📋 Prompts Generated:")
        for step, desc in workflow['prompts'].items():
            if not desc.startswith("Run"):
                print(f"   {step}")
        
        print("\n🚀 Next Steps:")
        print("1. Open the instructions file for step-by-step guide")
        print("2. Execute each prompt with Claude Code")
        print("3. Review results in ./data/ and ./reports/")
        
        return 0
    
    def cmd_status(self, args):
        """Show application status."""
        print("📊 Job Search Pipeline Status\n")
        
        # Get statistics
        stats = self.db.get_pipeline_stats()
        
        print("🎯 Jobs Pipeline:")
        print(f"   New/Discovered: {stats.get('jobs_new', 0)}")
        print(f"   Shortlisted: {stats.get('jobs_shortlisted', 0)}")
        print(f"   Applied: {stats.get('jobs_applied', 0)}")
        print(f"   Interview: {stats.get('jobs_interview', 0)}")
        print(f"   Rejected: {stats.get('jobs_rejected', 0)}")
        
        print("\n📝 Applications:")
        print(f"   Pending: {stats.get('apps_pending', 0)}")
        print(f"   In Progress: {stats.get('apps_in_progress', 0)}")
        print(f"   Submitted: {stats.get('apps_submitted', 0)}")
        
        print("\n🤝 Networking:")
        print(f"   Total Connections: {stats.get('total_connections', 0)}")
        print(f"   Contacted: {stats.get('contacted_connections', 0)}")
        
        print("\n🏢 Research:")
        print(f"   Companies Researched: {stats.get('companies_researched', 0)}")
        
        # Show recent activity
        if args.verbose:
            print("\n📅 Recent Searches:")
            searches = self.db.get_recent_searches(5)
            for search in searches:
                print(f"   - {search['search_date']}: {search['job_title']} in {search['location']} ({search['results_count']} results)")
        
        # Generate tracking prompt
        if args.report:
            prompt = self.mvp.generate_application_tracker()
            prompt_file = self.mvp.save_prompt_to_file(prompt, "status_report")
            print(f"\n📄 Status Report Prompt saved to: {prompt_file}")
            print("Execute with Claude Code to generate detailed report.")
        
        return 0
    
    def cmd_cache(self, args):
        """Manage cache."""
        if args.clear:
            count = self.cache.clear_all()
            print(f"🗑️ Cleared {count} cache entries")
        elif args.clean:
            count = self.cache.clear_expired()
            print(f"🧹 Cleaned {count} expired cache entries")
        else:
            # Show cache stats
            stats = self.cache.get_stats()
            print("💾 Cache Statistics\n")
            print(f"   Total Entries: {stats['total_entries']}")
            print(f"   Total Size: {stats['total_size_mb']} MB")
            print(f"   Expired: {stats['expired_count']}")
            
            if args.verbose:
                print("\n   By Type:")
                for data_type, type_stats in stats['by_type'].items():
                    print(f"   - {data_type}: {type_stats['count']} entries ({type_stats['valid']} valid)")
        
        return 0
    
    def cmd_export(self, args):
        """Export data."""
        output_path = args.output or f"./data/export_{datetime.now().strftime('%Y%m%d')}.json"
        
        print(f"📤 Exporting data to: {output_path}")
        
        if self.db.export_to_json(output_path):
            print("✅ Export completed successfully!")
        else:
            print("❌ Export failed!")
            return 1
        
        return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Claude Job Search - AI-powered job discovery system',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  claude-job init                      # Initialize your profile
  claude-job search "Software Engineer" "San Francisco"  # Search for jobs
  claude-job match                     # Match jobs with your profile
  claude-job company Google Meta       # Research specific companies
  claude-job network Google            # Find connections at a company
  claude-job apply https://job.url     # Get application help
  claude-job grok "ML Engineer" "NYC"  # Generate Grok search prompt
  claude-job workflow "Data Scientist" "Remote"  # Create complete workflow
  claude-job status --report           # Show pipeline status with report
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Init command
    parser_init = subparsers.add_parser('init', help='Initialize profile with resume')
    
    # Search command
    parser_search = subparsers.add_parser('search', help='Search for jobs')
    parser_search.add_argument('title', help='Job title to search for')
    parser_search.add_argument('location', help='Location (city, state, or "Remote")')
    parser_search.add_argument('--remote', action='store_true', help='Remote positions only')
    parser_search.add_argument('--hybrid', action='store_true', help='Hybrid positions')
    parser_search.add_argument('--salary-min', type=int, help='Minimum salary')
    parser_search.add_argument('--salary-max', type=int, help='Maximum salary')
    
    # Match command
    parser_match = subparsers.add_parser('match', help='Match jobs with profile')
    
    # Company command
    parser_company = subparsers.add_parser('company', help='Research companies')
    parser_company.add_argument('companies', nargs='*', help='Company names to research')
    
    # Network command
    parser_network = subparsers.add_parser('network', help='Find connections at company')
    parser_network.add_argument('company', help='Company name')
    
    # Apply command
    parser_apply = subparsers.add_parser('apply', help='Get application assistance')
    parser_apply.add_argument('url', help='Job application URL')
    
    # Grok command
    parser_grok = subparsers.add_parser('grok', help='Generate Grok prompts or import results')
    parser_grok.add_argument('title', nargs='?', help='Job title')
    parser_grok.add_argument('location', nargs='?', help='Location')
    parser_grok.add_argument('--import', dest='import_results', action='store_true', 
                           help='Import Grok results')
    
    # Workflow command
    parser_workflow = subparsers.add_parser('workflow', help='Create complete workflow')
    parser_workflow.add_argument('title', help='Job title')
    parser_workflow.add_argument('location', help='Location')
    
    # Status command
    parser_status = subparsers.add_parser('status', help='Show pipeline status')
    parser_status.add_argument('--verbose', '-v', action='store_true', help='Show details')
    parser_status.add_argument('--report', '-r', action='store_true', 
                              help='Generate detailed report')
    
    # Cache command
    parser_cache = subparsers.add_parser('cache', help='Manage cache')
    parser_cache.add_argument('--clear', action='store_true', help='Clear all cache')
    parser_cache.add_argument('--clean', action='store_true', help='Clean expired entries')
    parser_cache.add_argument('--verbose', '-v', action='store_true', help='Show details')
    
    # Export command
    parser_export = subparsers.add_parser('export', help='Export data')
    parser_export.add_argument('--output', '-o', help='Output file path')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    cli = ClaudeJobCLI()
    
    # Route to command handler
    command_map = {
        'init': cli.cmd_init,
        'search': cli.cmd_search,
        'match': cli.cmd_match,
        'company': cli.cmd_company,
        'network': cli.cmd_network,
        'apply': cli.cmd_apply,
        'grok': cli.cmd_grok,
        'workflow': cli.cmd_workflow,
        'status': cli.cmd_status,
        'cache': cli.cmd_cache,
        'export': cli.cmd_export
    }
    
    handler = command_map.get(args.command)
    if handler:
        return handler(args)
    else:
        print(f"Unknown command: {args.command}")
        return 1


if __name__ == '__main__':
    sys.exit(main())