"""Tests for ProfileManager."""

import unittest
import json
import tempfile
import shutil
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.core.profile_manager import ProfileManager


class TestProfileManager(unittest.TestCase):
    """Test ProfileManager functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.profile_manager = ProfileManager(config_dir=self.test_dir)
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)
    
    def test_create_empty_profile(self):
        """Test empty profile creation."""
        profile = self.profile_manager.create_empty_profile()
        
        # Check structure
        self.assertIn('personal_info', profile)
        self.assertIn('skills', profile)
        self.assertIn('experience', profile)
        self.assertIn('education', profile)
        self.assertIn('preferences', profile)
        
        # Check nested structures
        self.assertIn('technical', profile['skills'])
        self.assertIn('desired_roles', profile['preferences'])
    
    def test_parse_resume_text_email(self):
        """Test email extraction from resume text."""
        resume_text = """
        John Doe
        Software Engineer
        john.doe@example.com
        Phone: 555-123-4567
        """
        
        profile = self.profile_manager.parse_resume_text(resume_text)
        self.assertEqual(profile['personal_info']['email'], 'john.doe@example.com')
    
    def test_parse_resume_text_phone(self):
        """Test phone extraction from resume text."""
        resume_text = """
        Contact: 555-123-4567
        Email: test@test.com
        """
        
        profile = self.profile_manager.parse_resume_text(resume_text)
        self.assertIn('555', profile['personal_info']['phone'])
    
    def test_parse_resume_text_linkedin(self):
        """Test LinkedIn URL extraction."""
        resume_text = """
        LinkedIn: linkedin.com/in/johndoe
        GitHub: github.com/johndoe
        """
        
        profile = self.profile_manager.parse_resume_text(resume_text)
        self.assertEqual(profile['personal_info']['linkedin_url'], 
                        'https://linkedin.com/in/johndoe')
        self.assertEqual(profile['personal_info']['github_url'], 
                        'https://github.com/johndoe')
    
    def test_parse_resume_text_skills(self):
        """Test skill extraction from resume text."""
        resume_text = """
        Skills:
        - Python, JavaScript, React
        - Docker, Kubernetes
        - Machine Learning, TensorFlow
        """
        
        profile = self.profile_manager.parse_resume_text(resume_text)
        skills = profile['skills']['technical']
        
        self.assertIn('python', skills)
        self.assertIn('javascript', skills)
        self.assertIn('react', skills)
        self.assertIn('docker', skills)
        self.assertIn('kubernetes', skills)
        self.assertIn('machine learning', skills)
    
    def test_parse_resume_text_education(self):
        """Test education extraction."""
        resume_text = """
        Education:
        Bachelor of Science in Computer Science
        University of California, Berkeley
        Graduated: 2020
        
        Master of Science in Data Science
        Stanford University
        2022
        """
        
        profile = self.profile_manager.parse_resume_text(resume_text)
        education = profile['education']
        
        self.assertTrue(len(education) > 0)
        # Check if years were extracted
        years = [e.get('graduation_year') for e in education]
        self.assertIn('2020', years)
        self.assertIn('2022', years)
    
    def test_parse_resume_text_experience(self):
        """Test experience extraction."""
        resume_text = """
        Experience:
        
        Senior Software Engineer
        Tech Corp, San Francisco
        Jan 2020 - Present
        
        Software Developer
        StartupCo
        Jun 2018 - Dec 2019
        """
        
        profile = self.profile_manager.parse_resume_text(resume_text)
        experience = profile['experience']
        
        self.assertTrue(len(experience) > 0)
        # Check if engineer roles were found
        titles = [e.get('title') for e in experience]
        self.assertTrue(any('Engineer' in t for t in titles))
    
    def test_update_profile(self):
        """Test profile update functionality."""
        initial_profile = self.profile_manager.profile_data
        
        updates = {
            'personal_info': {
                'name': 'John Doe',
                'email': 'john@example.com'
            },
            'preferences': {
                'desired_roles': ['Software Engineer', 'Data Scientist'],
                'salary_min': 120000
            }
        }
        
        success = self.profile_manager.update_profile(updates)
        self.assertTrue(success)
        
        # Check updates were applied
        self.assertEqual(self.profile_manager.profile_data['personal_info']['name'], 
                        'John Doe')
        self.assertEqual(self.profile_manager.profile_data['preferences']['salary_min'], 
                        120000)
    
    def test_save_and_load_profile(self):
        """Test profile persistence."""
        # Update profile
        self.profile_manager.profile_data['personal_info']['name'] = 'Test User'
        self.profile_manager.save_profile()
        
        # Create new instance and check if loaded
        new_manager = ProfileManager(config_dir=self.test_dir)
        self.assertEqual(new_manager.profile_data['personal_info']['name'], 
                        'Test User')
    
    def test_get_skills_summary(self):
        """Test skills summary generation."""
        self.profile_manager.profile_data['skills']['technical'] = ['Python', 'Java']
        self.profile_manager.profile_data['skills']['soft'] = ['Leadership', 'Communication']
        
        skills = self.profile_manager.get_skills_summary()
        self.assertIn('Python', skills)
        self.assertIn('Java', skills)
        self.assertIn('Leadership', skills)
        self.assertIn('Communication', skills)
    
    def test_get_experience_summary(self):
        """Test experience summary generation."""
        self.profile_manager.profile_data['experience'] = [
            {
                'title': 'Senior Engineer',
                'company': 'TechCo',
                'start_date': '2020-01',
                'end_date': 'Present'
            },
            {
                'title': 'Engineer',
                'company': 'StartupCo',
                'start_date': '2018-01',
                'end_date': '2019-12'
            }
        ]
        
        summary = self.profile_manager.get_experience_summary()
        self.assertIn('Senior Engineer', summary)
        self.assertIn('TechCo', summary)
    
    def test_validate_profile_missing_critical(self):
        """Test profile validation with missing critical fields."""
        # Empty profile should have missing critical fields
        validation = self.profile_manager.validate_profile()
        
        self.assertTrue(len(validation['critical']) > 0)
        self.assertIn('Email address', validation['critical'])
        self.assertIn('Technical skills', validation['critical'])
    
    def test_validate_profile_complete(self):
        """Test profile validation with complete profile."""
        # Fill critical fields
        self.profile_manager.profile_data['personal_info']['email'] = 'test@example.com'
        self.profile_manager.profile_data['skills']['technical'] = ['Python']
        self.profile_manager.profile_data['experience'] = [
            {'title': 'Engineer', 'company': 'TechCo'}
        ]
        
        validation = self.profile_manager.validate_profile()
        self.assertEqual(len(validation['critical']), 0)
    
    def test_export_for_matching(self):
        """Test export format for job matching."""
        # Setup profile data
        self.profile_manager.profile_data['skills']['technical'] = ['Python', 'Java']
        self.profile_manager.profile_data['experience'] = [
            {'title': 'Engineer'},
            {'title': 'Developer'}
        ]
        self.profile_manager.profile_data['preferences']['locations'] = ['San Francisco']
        self.profile_manager.profile_data['preferences']['salary_min'] = 100000
        self.profile_manager.profile_data['preferences']['salary_max'] = 150000
        
        export = self.profile_manager.export_for_matching()
        
        self.assertIn('skills', export)
        self.assertIn('experience_years', export)
        self.assertIn('salary_range', export)
        self.assertEqual(export['experience_years'], 2)
        self.assertEqual(export['salary_range']['min'], 100000)


if __name__ == '__main__':
    unittest.main()