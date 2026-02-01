#!/usr/bin/env python3
"""
Simple runner for the Universal Job Scraper.
Edit scraper_targets.json to add/remove companies and VCs.
"""

import asyncio
import argparse
import json
from pathlib import Path
from universal_job_scraper import UniversalJobScraper


def load_config(config_file: str = "scraper_targets.json") -> dict:
    """Load configuration from JSON file."""
    config_path = Path(config_file)
    if config_path.exists():
        with open(config_path) as f:
            return json.load(f)
    return {"targets": [], "filters": {"apac_only": True, "gtm_only": False}}


async def run_full_scrape(config_file: str = "scraper_targets.json"):
    """Run full scrape with all enabled targets."""
    config = load_config(config_file)

    targets = [t for t in config.get("targets", []) if t.get("enabled", True)]
    filters = config.get("filters", {})

    print(f"📋 Loaded {len(targets)} targets from {config_file}")

    scraper = UniversalJobScraper(
        targets=targets,
        filter_apac=filters.get("apac_only", True),
        filter_gtm=filters.get("gtm_only", False)
    )

    results = await scraper.scrape_all()
    return results


async def run_quick_scrape():
    """Quick scrape of just the most important targets."""
    priority_targets = [
        {"name": "Sequoia Capital", "url": "https://jobs.sequoiacap.com/jobs", "type": "vc_portfolio", "platform": "getro", "location_filter": "Australia"},
        {"name": "Insight Partners", "url": "https://jobs.insightpartners.com/jobs", "type": "vc_portfolio", "platform": "getro", "location_filter": "Australia"},
        {"name": "Anthropic", "url": "https://www.anthropic.com/careers", "type": "company", "platform": "greenhouse"},
        {"name": "Gong", "url": "https://www.gong.io/careers", "type": "company", "platform": "greenhouse"},
    ]

    print("🚀 Running quick scrape (4 priority targets)...")

    scraper = UniversalJobScraper(targets=priority_targets, filter_apac=True)
    results = await scraper.scrape_all()
    return results


async def run_vc_only():
    """Scrape only VC portfolio job boards."""
    config = load_config()
    vc_targets = [t for t in config.get("targets", [])
                  if t.get("type") == "vc_portfolio" and t.get("enabled", True)]

    print(f"🏦 Running VC-only scrape ({len(vc_targets)} VCs)...")

    scraper = UniversalJobScraper(targets=vc_targets, filter_apac=True)
    results = await scraper.scrape_all()
    return results


async def run_companies_only():
    """Scrape only direct company career pages."""
    config = load_config()
    company_targets = [t for t in config.get("targets", [])
                       if t.get("type") == "company" and t.get("enabled", True)]

    print(f"🏢 Running company-only scrape ({len(company_targets)} companies)...")

    scraper = UniversalJobScraper(targets=company_targets, filter_apac=True)
    results = await scraper.scrape_all()
    return results


async def run_single_target(name: str):
    """Scrape a single target by name."""
    config = load_config()
    target = next((t for t in config.get("targets", [])
                   if t.get("name", "").lower() == name.lower()), None)

    if not target:
        print(f"❌ Target '{name}' not found in config")
        print("Available targets:")
        for t in config.get("targets", []):
            status = "✓" if t.get("enabled", True) else "○"
            print(f"  {status} {t.get('name')}")
        return None

    print(f"🎯 Scraping single target: {target['name']}")

    scraper = UniversalJobScraper(targets=[target], filter_apac=False)
    results = await scraper.scrape_all()
    return results


async def add_and_scrape(name: str, url: str, type: str = "company", platform: str = None):
    """Add a new target and scrape it immediately."""
    target = {
        "name": name,
        "url": url,
        "type": type,
        "platform": platform,
        "enabled": True
    }

    print(f"➕ Adding and scraping: {name}")

    scraper = UniversalJobScraper(targets=[target], filter_apac=False)
    results = await scraper.scrape_all()

    # Optionally save to config
    config = load_config()
    config["targets"].append(target)
    with open("scraper_targets.json", "w") as f:
        json.dump(config, f, indent=2)
    print(f"💾 Saved {name} to scraper_targets.json")

    return results


def main():
    parser = argparse.ArgumentParser(description="Universal Job Scraper")
    parser.add_argument("--mode", choices=["full", "quick", "vc", "companies", "single", "add"],
                        default="full", help="Scraping mode")
    parser.add_argument("--target", type=str, help="Target name for single mode")
    parser.add_argument("--name", type=str, help="Company name for add mode")
    parser.add_argument("--url", type=str, help="Careers URL for add mode")
    parser.add_argument("--type", choices=["company", "vc_portfolio"], default="company",
                        help="Target type for add mode")
    parser.add_argument("--platform", type=str, help="Platform hint for add mode")
    parser.add_argument("--config", type=str, default="scraper_targets.json",
                        help="Config file path")

    args = parser.parse_args()

    if args.mode == "full":
        asyncio.run(run_full_scrape(args.config))
    elif args.mode == "quick":
        asyncio.run(run_quick_scrape())
    elif args.mode == "vc":
        asyncio.run(run_vc_only())
    elif args.mode == "companies":
        asyncio.run(run_companies_only())
    elif args.mode == "single":
        if not args.target:
            print("❌ --target required for single mode")
            return
        asyncio.run(run_single_target(args.target))
    elif args.mode == "add":
        if not args.name or not args.url:
            print("❌ --name and --url required for add mode")
            return
        asyncio.run(add_and_scrape(args.name, args.url, args.type, args.platform))


if __name__ == "__main__":
    main()
