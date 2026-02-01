"""Profile Manager for parsing and managing user resume and preferences."""

import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
import re
from pathlib import Path


class ProfileManager:
    """Manages user profile, resume parsing, and preferences."""
    
    def __init__(self, config_dir: str = "./config"):
        self.config_dir = Path(config_dir)
        self.profile_path = self.config_dir / "profile.json"
        self.profile_data = self.load_profile()
        
    def load_profile(self) -> Dict[str, Any]:
        """Load existing profile or create new one."""
        if self.profile_path.exists():
            with open(self.profile_path, 'r') as f:
                return json.load(f)
        return self.create_empty_profile()
    
    def create_empty_profile(self) -> Dict[str, Any]:
        """Create an empty profile structure."""
        return {
            "personal_info": {
                "name": "",
                "email": "",
                "phone": "",
                "location": "",
                "linkedin_url": "",
                "github_url": "",
                "portfolio_url": ""
            },
            "professional_summary": "",
            "skills": {
                "technical": [],
                "soft": [],
                "languages": [],
                "certifications": []
            },
            "experience": [],
            "education": [],
            "projects": [],
            "achievements": [],
            "preferences": {
                "desired_roles": [],
                "locations": [],
                "remote_preference": "hybrid",
                "salary_min": 0,
                "salary_max": 0,
                "company_size": ["startup", "medium", "enterprise"],
                "industries": [],
                "job_type": "full-time",
                "willing_to_relocate": False,
                "visa_sponsorship_needed": False
            },
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "resume_file": "",
                "linkedin_pdf": ""
            }
        }
    
    def parse_resume_text(self, text: str) -> Dict[str, Any]:
        """Parse resume text and extract structured information."""
        profile = self.create_empty_profile()
        
        # Extract email
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        if emails:
            profile["personal_info"]["email"] = emails[0]
        
        # Extract phone
        phone_pattern = r'[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4,6}'
        phones = re.findall(phone_pattern, text)
        if phones:
            profile["personal_info"]["phone"] = phones[0]
        
        # Extract LinkedIn URL
        linkedin_pattern = r'linkedin\.com/in/[\w-]+'
        linkedin_urls = re.findall(linkedin_pattern, text.lower())
        if linkedin_urls:
            profile["personal_info"]["linkedin_url"] = f"https://{linkedin_urls[0]}"
        
        # Extract GitHub URL
        github_pattern = r'github\.com/[\w-]+'
        github_urls = re.findall(github_pattern, text.lower())
        if github_urls:
            profile["personal_info"]["github_url"] = f"https://{github_urls[0]}"
        
        # Extract skills (common technical keywords)
        tech_keywords = [
            'python', 'java', 'javascript', 'typescript', 'react', 'angular', 'vue',
            'node', 'express', 'django', 'flask', 'spring', 'docker', 'kubernetes',
            'aws', 'azure', 'gcp', 'sql', 'nosql', 'mongodb', 'postgresql', 'mysql',
            'git', 'ci/cd', 'agile', 'scrum', 'machine learning', 'deep learning',
            'tensorflow', 'pytorch', 'pandas', 'numpy', 'scikit-learn', 'nlp',
            'html', 'css', 'sass', 'webpack', 'babel', 'jest', 'selenium',
            'c++', 'c#', '.net', 'ruby', 'rails', 'php', 'laravel', 'go', 'rust',
            'swift', 'kotlin', 'android', 'ios', 'react native', 'flutter'
        ]
        
        text_lower = text.lower()
        found_skills = []
        for skill in tech_keywords:
            if skill in text_lower:
                found_skills.append(skill)
        profile["skills"]["technical"] = found_skills
        
        # Extract education (look for degree keywords)
        education_keywords = ['bachelor', 'master', 'phd', 'bs', 'ms', 'ba', 'ma', 'mba']
        education_section = []
        lines = text.split('\n')
        for i, line in enumerate(lines):
            line_lower = line.lower()
            for keyword in education_keywords:
                if keyword in line_lower:
                    education_entry = {
                        "degree": line.strip(),
                        "institution": "",
                        "graduation_year": "",
                        "gpa": ""
                    }
                    # Try to extract year
                    year_pattern = r'20\d{2}|19\d{2}'
                    years = re.findall(year_pattern, line)
                    if years:
                        education_entry["graduation_year"] = years[-1]
                    education_section.append(education_entry)
                    break
        
        if education_section:
            profile["education"] = education_section
        
        # Extract work experience sections
        experience_keywords = ['experience', 'work history', 'employment', 'professional experience']
        experience_section = []
        
        for i, line in enumerate(lines):
            line_lower = line.lower()
            # Look for job titles (simplified approach)
            if any(title in line_lower for title in ['engineer', 'developer', 'manager', 'analyst', 'designer', 'architect', 'consultant', 'specialist', 'coordinator']):
                experience_entry = {
                    "title": line.strip(),
                    "company": "",
                    "location": "",
                    "start_date": "",
                    "end_date": "",
                    "description": "",
                    "achievements": []
                }
                
                # Try to find dates
                date_pattern = r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4}'
                dates = re.findall(date_pattern, line)
                if len(dates) >= 2:
                    experience_entry["start_date"] = dates[0]
                    experience_entry["end_date"] = dates[1]
                elif len(dates) == 1:
                    experience_entry["start_date"] = dates[0]
                    experience_entry["end_date"] = "Present"
                
                experience_section.append(experience_entry)
        
        if experience_section:
            profile["experience"] = experience_section[:5]  # Limit to 5 most recent
        
        profile["metadata"]["updated_at"] = datetime.now().isoformat()
        
        return profile
    
    def update_profile(self, updates: Dict[str, Any]) -> bool:
        """Update profile with new information."""
        try:
            # Deep merge updates into existing profile
            self._deep_merge(self.profile_data, updates)
            self.profile_data["metadata"]["updated_at"] = datetime.now().isoformat()
            self.save_profile()
            return True
        except Exception as e:
            print(f"Error updating profile: {e}")
            return False
    
    def _deep_merge(self, base: Dict, updates: Dict) -> None:
        """Recursively merge updates into base dictionary."""
        for key, value in updates.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def save_profile(self) -> bool:
        """Save profile to file."""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.profile_path, 'w') as f:
                json.dump(self.profile_data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving profile: {e}")
            return False
    
    def get_skills_summary(self) -> List[str]:
        """Get combined list of all skills."""
        skills = []
        skills.extend(self.profile_data.get("skills", {}).get("technical", []))
        skills.extend(self.profile_data.get("skills", {}).get("soft", []))
        return skills
    
    def get_experience_summary(self) -> str:
        """Generate a summary of work experience."""
        experience = self.profile_data.get("experience", [])
        if not experience:
            return "No experience data available"
        
        summary = []
        for exp in experience[:3]:  # Top 3 experiences
            title = exp.get("title", "Unknown Position")
            company = exp.get("company", "Unknown Company")
            duration = f"{exp.get('start_date', 'Unknown')} - {exp.get('end_date', 'Present')}"
            summary.append(f"{title} at {company} ({duration})")
        
        return "; ".join(summary)
    
    def get_education_summary(self) -> str:
        """Generate a summary of education."""
        education = self.profile_data.get("education", [])
        if not education:
            return "No education data available"
        
        summary = []
        for edu in education:
            degree = edu.get("degree", "Unknown Degree")
            institution = edu.get("institution", "Unknown Institution")
            year = edu.get("graduation_year", "Unknown Year")
            summary.append(f"{degree} from {institution} ({year})")
        
        return "; ".join(summary)
    
    def get_preferences(self) -> Dict[str, Any]:
        """Get user job search preferences."""
        return self.profile_data.get("preferences", {})
    
    def validate_profile(self) -> Dict[str, List[str]]:
        """Validate profile completeness and return missing fields."""
        missing = {
            "critical": [],
            "important": [],
            "optional": []
        }
        
        # Critical fields
        if not self.profile_data.get("personal_info", {}).get("email"):
            missing["critical"].append("Email address")
        if not self.profile_data.get("skills", {}).get("technical"):
            missing["critical"].append("Technical skills")
        if not self.profile_data.get("experience"):
            missing["critical"].append("Work experience")
        
        # Important fields
        if not self.profile_data.get("personal_info", {}).get("name"):
            missing["important"].append("Full name")
        if not self.profile_data.get("education"):
            missing["important"].append("Education")
        if not self.profile_data.get("personal_info", {}).get("location"):
            missing["important"].append("Current location")
        
        # Optional fields
        if not self.profile_data.get("personal_info", {}).get("linkedin_url"):
            missing["optional"].append("LinkedIn profile")
        if not self.profile_data.get("projects"):
            missing["optional"].append("Projects")
        if not self.profile_data.get("achievements"):
            missing["optional"].append("Achievements")
        
        return missing
    
    @staticmethod
    def merge_parsed_profiles(profiles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge multiple regex-parsed profile dicts into one.

        Deduplicates skills, takes first non-empty personal info fields,
        and concatenates experience/education lists.

        Args:
            profiles: List of profile dicts (from parse_resume_text or similar).

        Returns:
            A single merged profile dict.
        """
        if not profiles:
            return ProfileManager().create_empty_profile()
        if len(profiles) == 1:
            return profiles[0]

        merged = profiles[0].copy()

        for profile in profiles[1:]:
            # Personal info: take first non-empty value for each field
            for field_key, value in profile.get("personal_info", {}).items():
                if value and not merged.get("personal_info", {}).get(field_key):
                    merged.setdefault("personal_info", {})[field_key] = value

            # Skills: deduplicate across all categories
            for category in ("technical", "soft", "languages", "certifications"):
                existing = set(merged.get("skills", {}).get(category, []))
                new_skills = profile.get("skills", {}).get(category, [])
                for skill in new_skills:
                    if skill not in existing:
                        merged.setdefault("skills", {}).setdefault(category, []).append(skill)
                        existing.add(skill)

            # Experience and education: concatenate and deduplicate by title/degree
            for list_key in ("experience", "education"):
                existing_items = merged.get(list_key, [])
                existing_titles = {
                    item.get("title", item.get("degree", ""))
                    for item in existing_items
                }
                for item in profile.get(list_key, []):
                    item_key = item.get("title", item.get("degree", ""))
                    if item_key and item_key not in existing_titles:
                        existing_items.append(item)
                        existing_titles.add(item_key)
                merged[list_key] = existing_items

            # Projects and achievements: concatenate
            for list_key in ("projects", "achievements"):
                existing = merged.get(list_key, [])
                existing_names = {item.get("name", "") for item in existing}
                for item in profile.get(list_key, []):
                    if item.get("name", "") not in existing_names:
                        existing.append(item)
                merged[list_key] = existing

        return merged

    def export_for_matching(self) -> Dict[str, Any]:
        """Export profile in format optimized for job matching."""
        return {
            "skills": self.get_skills_summary(),
            "experience_years": len(self.profile_data.get("experience", [])),
            "experience_summary": self.get_experience_summary(),
            "education_summary": self.get_education_summary(),
            "preferred_locations": self.profile_data.get("preferences", {}).get("locations", []),
            "remote_preference": self.profile_data.get("preferences", {}).get("remote_preference", "hybrid"),
            "salary_range": {
                "min": self.profile_data.get("preferences", {}).get("salary_min", 0),
                "max": self.profile_data.get("preferences", {}).get("salary_max", 0)
            },
            "desired_roles": self.profile_data.get("preferences", {}).get("desired_roles", [])
        }