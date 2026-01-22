"""Database management for job search system."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import json


class DatabaseManager:
    """Manage SQLite database operations."""
    
    def __init__(self, db_path: str = "./data/jobs.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_database()
    
    def init_database(self):
        """Initialize database with required tables."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Jobs table
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
                notes TEXT,
                company_size TEXT,
                job_type TEXT
            )
        ''')
        
        # Applications table
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
                follow_up_date DATE,
                response_received BOOLEAN DEFAULT 0,
                FOREIGN KEY (job_id) REFERENCES jobs(job_id)
            )
        ''')
        
        # Connections table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS connections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                company TEXT,
                title TEXT,
                connection_degree INTEGER,
                linkedin_url TEXT,
                connection_path TEXT,
                connection_type TEXT,
                outreach_message TEXT,
                contacted BOOLEAN DEFAULT 0,
                responded BOOLEAN DEFAULT 0,
                notes TEXT,
                last_updated DATE DEFAULT CURRENT_DATE
            )
        ''')
        
        # Search history
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                search_date DATE DEFAULT CURRENT_DATE,
                search_type TEXT,
                job_title TEXT,
                location TEXT,
                results_count INTEGER,
                parameters TEXT
            )
        ''')
        
        # Company research
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                industry TEXT,
                size TEXT,
                location_hq TEXT,
                website TEXT,
                glassdoor_rating REAL,
                culture_notes TEXT,
                tech_stack TEXT,
                recent_news TEXT,
                growth_stage TEXT,
                remote_policy TEXT,
                research_date DATE DEFAULT CURRENT_DATE
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    # ============= JOB OPERATIONS =============
    
    def add_job(self, job_data: Dict[str, Any]) -> Optional[int]:
        """Add a new job to the database."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Convert requirements list to JSON string if needed
            if isinstance(job_data.get('requirements'), list):
                job_data['requirements'] = json.dumps(job_data['requirements'])
            
            cursor.execute('''
                INSERT INTO jobs (
                    job_id, title, company, location, url, description,
                    requirements, posted_date, match_score, source,
                    salary_min, salary_max, remote_type, company_size, job_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                job_data.get('job_id'),
                job_data.get('title'),
                job_data.get('company'),
                job_data.get('location'),
                job_data.get('url'),
                job_data.get('description'),
                job_data.get('requirements'),
                job_data.get('posted_date'),
                job_data.get('match_score'),
                job_data.get('source', 'claude'),
                job_data.get('salary_min'),
                job_data.get('salary_max'),
                job_data.get('remote_type'),
                job_data.get('company_size'),
                job_data.get('job_type')
            ))
            
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            # Job already exists
            return None
        finally:
            conn.close()
    
    def get_job(self, job_id: str) -> Optional[Dict]:
        """Get job by ID."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM jobs WHERE job_id = ?', (job_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def update_job_status(self, job_id: str, status: str) -> bool:
        """Update job status."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            'UPDATE jobs SET status = ? WHERE job_id = ?',
            (status, job_id)
        )
        
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success
    
    def update_match_score(self, job_id: str, score: float) -> bool:
        """Update job match score."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            'UPDATE jobs SET match_score = ? WHERE job_id = ?',
            (score, job_id)
        )
        
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success
    
    def get_jobs_by_status(self, status: str) -> List[Dict]:
        """Get all jobs with a specific status."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT * FROM jobs WHERE status = ? ORDER BY match_score DESC',
            (status,)
        )
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_top_matches(self, limit: int = 10, min_score: float = 60.0) -> List[Dict]:
        """Get top matching jobs."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM jobs 
            WHERE match_score >= ? 
            ORDER BY match_score DESC 
            LIMIT ?
        ''', (min_score, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    # ============= APPLICATION OPERATIONS =============
    
    def add_application(self, app_data: Dict[str, Any]) -> Optional[int]:
        """Add a new application."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Convert questions and answers to JSON if needed
        for field in ['questions', 'answers']:
            if isinstance(app_data.get(field), (list, dict)):
                app_data[field] = json.dumps(app_data[field])
        
        cursor.execute('''
            INSERT INTO applications (
                job_id, status, application_url, questions, answers,
                cover_letter, notes, follow_up_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            app_data.get('job_id'),
            app_data.get('status', 'pending'),
            app_data.get('application_url'),
            app_data.get('questions'),
            app_data.get('answers'),
            app_data.get('cover_letter'),
            app_data.get('notes'),
            app_data.get('follow_up_date')
        ))
        
        conn.commit()
        app_id = cursor.lastrowid
        conn.close()
        return app_id
    
    def update_application_status(self, job_id: str, status: str) -> bool:
        """Update application status."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            'UPDATE applications SET status = ? WHERE job_id = ?',
            (status, job_id)
        )
        
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success
    
    def get_pending_applications(self) -> List[Dict]:
        """Get all pending applications."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT a.*, j.company, j.title 
            FROM applications a
            JOIN jobs j ON a.job_id = j.job_id
            WHERE a.status = 'pending'
            ORDER BY a.applied_date DESC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    # ============= CONNECTION OPERATIONS =============
    
    def add_connection(self, conn_data: Dict[str, Any]) -> Optional[int]:
        """Add a new connection."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO connections (
                name, company, title, connection_degree, linkedin_url,
                connection_path, connection_type, outreach_message, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            conn_data.get('name'),
            conn_data.get('company'),
            conn_data.get('title'),
            conn_data.get('connection_degree'),
            conn_data.get('linkedin_url'),
            conn_data.get('connection_path'),
            conn_data.get('connection_type'),
            conn_data.get('outreach_message'),
            conn_data.get('notes')
        ))
        
        conn.commit()
        conn_id = cursor.lastrowid
        conn.close()
        return conn_id
    
    def get_company_connections(self, company: str) -> List[Dict]:
        """Get all connections at a specific company."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM connections 
            WHERE company = ? 
            ORDER BY connection_degree, contacted
        ''', (company,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def mark_connection_contacted(self, conn_id: int) -> bool:
        """Mark a connection as contacted."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            'UPDATE connections SET contacted = 1 WHERE id = ?',
            (conn_id,)
        )
        
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success
    
    # ============= COMPANY OPERATIONS =============
    
    def add_company_research(self, company_data: Dict[str, Any]) -> Optional[int]:
        """Add company research data."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Convert complex fields to JSON
        for field in ['culture_notes', 'tech_stack', 'recent_news']:
            if isinstance(company_data.get(field), (list, dict)):
                company_data[field] = json.dumps(company_data[field])
        
        try:
            cursor.execute('''
                INSERT INTO companies (
                    name, industry, size, location_hq, website,
                    glassdoor_rating, culture_notes, tech_stack,
                    recent_news, growth_stage, remote_policy
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                company_data.get('name'),
                company_data.get('industry'),
                company_data.get('size'),
                company_data.get('location_hq'),
                company_data.get('website'),
                company_data.get('glassdoor_rating'),
                company_data.get('culture_notes'),
                company_data.get('tech_stack'),
                company_data.get('recent_news'),
                company_data.get('growth_stage'),
                company_data.get('remote_policy')
            ))
            
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            # Company already exists, update instead
            cursor.execute('''
                UPDATE companies SET
                    industry = ?, size = ?, location_hq = ?, website = ?,
                    glassdoor_rating = ?, culture_notes = ?, tech_stack = ?,
                    recent_news = ?, growth_stage = ?, remote_policy = ?,
                    research_date = CURRENT_DATE
                WHERE name = ?
            ''', (
                company_data.get('industry'),
                company_data.get('size'),
                company_data.get('location_hq'),
                company_data.get('website'),
                company_data.get('glassdoor_rating'),
                company_data.get('culture_notes'),
                company_data.get('tech_stack'),
                company_data.get('recent_news'),
                company_data.get('growth_stage'),
                company_data.get('remote_policy'),
                company_data.get('name')
            ))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()
    
    def get_company_research(self, company_name: str) -> Optional[Dict]:
        """Get company research data."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM companies WHERE name = ?', (company_name,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            data = dict(row)
            # Parse JSON fields
            for field in ['culture_notes', 'tech_stack', 'recent_news']:
                if data.get(field):
                    try:
                        data[field] = json.loads(data[field])
                    except json.JSONDecodeError:
                        pass
            return data
        return None
    
    # ============= SEARCH OPERATIONS =============
    
    def log_search(self, search_data: Dict[str, Any]) -> int:
        """Log a search operation."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if isinstance(search_data.get('parameters'), dict):
            search_data['parameters'] = json.dumps(search_data['parameters'])
        
        cursor.execute('''
            INSERT INTO search_history (
                search_type, job_title, location, results_count, parameters
            ) VALUES (?, ?, ?, ?, ?)
        ''', (
            search_data.get('search_type'),
            search_data.get('job_title'),
            search_data.get('location'),
            search_data.get('results_count'),
            search_data.get('parameters')
        ))
        
        conn.commit()
        search_id = cursor.lastrowid
        conn.close()
        return search_id
    
    def get_recent_searches(self, limit: int = 10) -> List[Dict]:
        """Get recent search history."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM search_history 
            ORDER BY search_date DESC 
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    # ============= REPORTING =============
    
    def get_pipeline_stats(self) -> Dict[str, int]:
        """Get job pipeline statistics."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        # Job stats by status
        cursor.execute('''
            SELECT status, COUNT(*) as count 
            FROM jobs 
            GROUP BY status
        ''')
        for row in cursor.fetchall():
            stats[f"jobs_{row['status']}"] = row['count']
        
        # Application stats
        cursor.execute('''
            SELECT status, COUNT(*) as count 
            FROM applications 
            GROUP BY status
        ''')
        for row in cursor.fetchall():
            stats[f"apps_{row['status']}"] = row['count']
        
        # Connection stats
        cursor.execute('SELECT COUNT(*) as total FROM connections')
        stats['total_connections'] = cursor.fetchone()['total']
        
        cursor.execute('SELECT COUNT(*) as contacted FROM connections WHERE contacted = 1')
        stats['contacted_connections'] = cursor.fetchone()['contacted']
        
        # Company research
        cursor.execute('SELECT COUNT(*) as total FROM companies')
        stats['companies_researched'] = cursor.fetchone()['total']
        
        conn.close()
        return stats
    
    def export_to_json(self, output_path: str = "./data/export.json") -> bool:
        """Export all data to JSON."""
        conn = self.get_connection()
        
        export_data = {
            "exported_at": datetime.now().isoformat(),
            "jobs": [],
            "applications": [],
            "connections": [],
            "companies": []
        }
        
        # Export jobs
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM jobs')
        export_data['jobs'] = [dict(row) for row in cursor.fetchall()]
        
        # Export applications
        cursor.execute('SELECT * FROM applications')
        export_data['applications'] = [dict(row) for row in cursor.fetchall()]
        
        # Export connections
        cursor.execute('SELECT * FROM connections')
        export_data['connections'] = [dict(row) for row in cursor.fetchall()]
        
        # Export companies
        cursor.execute('SELECT * FROM companies')
        export_data['companies'] = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        # Save to file
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        return True