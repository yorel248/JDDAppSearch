"""Tests for DatabaseManager."""

import unittest
import tempfile
import shutil
from pathlib import Path
import sys
import json

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.core.database import DatabaseManager


class TestDatabaseManager(unittest.TestCase):
    """Test DatabaseManager functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.db_path = Path(self.test_dir) / "test.db"
        self.db = DatabaseManager(db_path=str(self.db_path))
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)
    
    def test_database_initialization(self):
        """Test database tables are created correctly."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # Check tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        expected_tables = ['jobs', 'applications', 'connections', 
                          'search_history', 'companies']
        for table in expected_tables:
            self.assertIn(table, tables)
        
        conn.close()
    
    def test_add_job(self):
        """Test adding a job to database."""
        job_data = {
            'job_id': 'test123',
            'title': 'Software Engineer',
            'company': 'TechCorp',
            'location': 'San Francisco, CA',
            'url': 'https://example.com/job',
            'description': 'Great job opportunity',
            'requirements': ['Python', 'Django', '3+ years'],
            'posted_date': '2024-01-15',
            'match_score': 85.5,
            'salary_min': 120000,
            'salary_max': 180000
        }
        
        job_id = self.db.add_job(job_data)
        self.assertIsNotNone(job_id)
        
        # Verify job was added
        job = self.db.get_job('test123')
        self.assertIsNotNone(job)
        self.assertEqual(job['title'], 'Software Engineer')
        self.assertEqual(job['company'], 'TechCorp')
        self.assertEqual(job['match_score'], 85.5)
    
    def test_add_duplicate_job(self):
        """Test that duplicate jobs are not added."""
        job_data = {
            'job_id': 'dup123',
            'title': 'Engineer',
            'company': 'Company'
        }
        
        # Add once
        first_id = self.db.add_job(job_data)
        self.assertIsNotNone(first_id)
        
        # Try to add again
        second_id = self.db.add_job(job_data)
        self.assertIsNone(second_id)
    
    def test_update_job_status(self):
        """Test updating job status."""
        job_data = {
            'job_id': 'status123',
            'title': 'Developer',
            'company': 'DevCo'
        }
        
        self.db.add_job(job_data)
        
        # Update status
        success = self.db.update_job_status('status123', 'applied')
        self.assertTrue(success)
        
        # Verify update
        job = self.db.get_job('status123')
        self.assertEqual(job['status'], 'applied')
    
    def test_update_match_score(self):
        """Test updating match score."""
        job_data = {
            'job_id': 'score123',
            'title': 'Analyst',
            'company': 'DataCo',
            'match_score': 70.0
        }
        
        self.db.add_job(job_data)
        
        # Update score
        success = self.db.update_match_score('score123', 92.5)
        self.assertTrue(success)
        
        # Verify update
        job = self.db.get_job('score123')
        self.assertEqual(job['match_score'], 92.5)
    
    def test_get_jobs_by_status(self):
        """Test retrieving jobs by status."""
        # Add multiple jobs
        jobs = [
            {'job_id': 'new1', 'title': 'Job1', 'company': 'Co1', 
             'status': 'new', 'match_score': 80},
            {'job_id': 'new2', 'title': 'Job2', 'company': 'Co2', 
             'status': 'new', 'match_score': 90},
            {'job_id': 'app1', 'title': 'Job3', 'company': 'Co3', 
             'status': 'applied', 'match_score': 85}
        ]
        
        for job in jobs:
            self.db.add_job(job)
        
        # Get new jobs
        new_jobs = self.db.get_jobs_by_status('new')
        self.assertEqual(len(new_jobs), 2)
        # Should be ordered by match score desc
        self.assertEqual(new_jobs[0]['job_id'], 'new2')
        
        # Get applied jobs
        applied_jobs = self.db.get_jobs_by_status('applied')
        self.assertEqual(len(applied_jobs), 1)
    
    def test_get_top_matches(self):
        """Test retrieving top matching jobs."""
        # Add jobs with different scores
        jobs = [
            {'job_id': 'j1', 'title': 'J1', 'company': 'C1', 'match_score': 95},
            {'job_id': 'j2', 'title': 'J2', 'company': 'C2', 'match_score': 88},
            {'job_id': 'j3', 'title': 'J3', 'company': 'C3', 'match_score': 75},
            {'job_id': 'j4', 'title': 'J4', 'company': 'C4', 'match_score': 55},
            {'job_id': 'j5', 'title': 'J5', 'company': 'C5', 'match_score': 45}
        ]
        
        for job in jobs:
            self.db.add_job(job)
        
        # Get top 3 with min score 60
        top_jobs = self.db.get_top_matches(limit=3, min_score=60.0)
        self.assertEqual(len(top_jobs), 3)
        self.assertEqual(top_jobs[0]['match_score'], 95)
        self.assertEqual(top_jobs[1]['match_score'], 88)
        self.assertEqual(top_jobs[2]['match_score'], 75)
    
    def test_add_application(self):
        """Test adding an application."""
        # First add a job
        self.db.add_job({
            'job_id': 'app_job1',
            'title': 'Position',
            'company': 'Company'
        })
        
        app_data = {
            'job_id': 'app_job1',
            'status': 'submitted',
            'application_url': 'https://apply.com',
            'questions': ['Why do you want to work here?'],
            'answers': ['I am passionate about...'],
            'cover_letter': 'Dear Hiring Manager...'
        }
        
        app_id = self.db.add_application(app_data)
        self.assertIsNotNone(app_id)
    
    def test_get_pending_applications(self):
        """Test retrieving pending applications."""
        # Add job and application
        self.db.add_job({
            'job_id': 'pend1',
            'title': 'Engineer',
            'company': 'TechCo'
        })
        
        self.db.add_application({
            'job_id': 'pend1',
            'status': 'pending'
        })
        
        pending = self.db.get_pending_applications()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]['company'], 'TechCo')
        self.assertEqual(pending[0]['title'], 'Engineer')
    
    def test_add_connection(self):
        """Test adding a connection."""
        conn_data = {
            'name': 'John Doe',
            'company': 'TechCorp',
            'title': 'Senior Engineer',
            'connection_degree': 2,
            'linkedin_url': 'linkedin.com/in/johndoe',
            'connection_type': 'alumni'
        }
        
        conn_id = self.db.add_connection(conn_data)
        self.assertIsNotNone(conn_id)
    
    def test_get_company_connections(self):
        """Test retrieving connections by company."""
        # Add multiple connections
        connections = [
            {'name': 'Alice', 'company': 'Google', 'connection_degree': 1},
            {'name': 'Bob', 'company': 'Google', 'connection_degree': 2},
            {'name': 'Charlie', 'company': 'Meta', 'connection_degree': 1}
        ]
        
        for conn in connections:
            self.db.add_connection(conn)
        
        google_conns = self.db.get_company_connections('Google')
        self.assertEqual(len(google_conns), 2)
        # Should be ordered by connection degree
        self.assertEqual(google_conns[0]['name'], 'Alice')
    
    def test_add_company_research(self):
        """Test adding company research."""
        company_data = {
            'name': 'TechCorp',
            'industry': 'Technology',
            'size': '1000-5000',
            'location_hq': 'San Francisco, CA',
            'glassdoor_rating': 4.2,
            'tech_stack': ['Python', 'React', 'AWS'],
            'remote_policy': 'Hybrid'
        }
        
        company_id = self.db.add_company_research(company_data)
        self.assertIsNotNone(company_id)
        
        # Retrieve and verify
        company = self.db.get_company_research('TechCorp')
        self.assertIsNotNone(company)
        self.assertEqual(company['industry'], 'Technology')
        self.assertEqual(company['glassdoor_rating'], 4.2)
    
    def test_update_existing_company(self):
        """Test updating existing company research."""
        # Add initial data
        self.db.add_company_research({
            'name': 'UpdateCo',
            'industry': 'Tech',
            'glassdoor_rating': 4.0
        })
        
        # Update with new data
        self.db.add_company_research({
            'name': 'UpdateCo',
            'industry': 'Technology',
            'glassdoor_rating': 4.5,
            'size': '500-1000'
        })
        
        # Verify update
        company = self.db.get_company_research('UpdateCo')
        self.assertEqual(company['glassdoor_rating'], 4.5)
        self.assertEqual(company['size'], '500-1000')
    
    def test_log_search(self):
        """Test logging search history."""
        search_data = {
            'search_type': 'claude',
            'job_title': 'Software Engineer',
            'location': 'Remote',
            'results_count': 25,
            'parameters': {'salary_min': 100000}
        }
        
        search_id = self.db.log_search(search_data)
        self.assertIsNotNone(search_id)
        
        # Get recent searches
        searches = self.db.get_recent_searches(1)
        self.assertEqual(len(searches), 1)
        self.assertEqual(searches[0]['job_title'], 'Software Engineer')
    
    def test_get_pipeline_stats(self):
        """Test getting pipeline statistics."""
        # Add various data
        self.db.add_job({'job_id': 's1', 'title': 'J1', 'company': 'C1', 
                        'status': 'new'})
        self.db.add_job({'job_id': 's2', 'title': 'J2', 'company': 'C2', 
                        'status': 'applied'})
        self.db.add_application({'job_id': 's1', 'status': 'pending'})
        self.db.add_connection({'name': 'Test', 'company': 'TestCo'})
        self.db.add_company_research({'name': 'ResearchCo'})
        
        stats = self.db.get_pipeline_stats()
        
        self.assertEqual(stats['jobs_new'], 1)
        self.assertEqual(stats['jobs_applied'], 1)
        self.assertEqual(stats['apps_pending'], 1)
        self.assertEqual(stats['total_connections'], 1)
        self.assertEqual(stats['companies_researched'], 1)
    
    def test_export_to_json(self):
        """Test exporting database to JSON."""
        # Add some data
        self.db.add_job({'job_id': 'exp1', 'title': 'Job', 'company': 'Co'})
        self.db.add_connection({'name': 'Person', 'company': 'Company'})
        
        export_path = Path(self.test_dir) / "export.json"
        success = self.db.export_to_json(str(export_path))
        self.assertTrue(success)
        
        # Verify export
        self.assertTrue(export_path.exists())
        with open(export_path, 'r') as f:
            data = json.load(f)
        
        self.assertIn('jobs', data)
        self.assertIn('connections', data)
        self.assertEqual(len(data['jobs']), 1)
        self.assertEqual(len(data['connections']), 1)


if __name__ == '__main__':
    unittest.main()