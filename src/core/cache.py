"""Cache management for job search system."""

import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
import hashlib


class CacheManager:
    """Manage caching for API responses and web scraping results."""
    
    def __init__(self, cache_dir: str = "./cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # TTL in seconds
        self.ttl = {
            'job_listing': 24 * 3600,       # 24 hours
            'company_info': 7 * 24 * 3600,  # 7 days  
            'connections': 3 * 24 * 3600,   # 3 days
            'application_form': 3600,        # 1 hour
            'grok_results': 12 * 3600,      # 12 hours
            'grok_prompts': 30 * 24 * 3600, # 30 days
            'profile': 24 * 3600,            # 24 hours
            'search_results': 6 * 3600       # 6 hours
        }
        
        # Load config if exists
        self.load_config()
    
    def load_config(self):
        """Load cache configuration."""
        config_path = Path("./config/config.json")
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
                cache_config = config.get('cache', {})
                if 'ttl' in cache_config:
                    self.ttl.update(cache_config['ttl'])
    
    def generate_cache_key(self, data_type: str, identifier: str) -> str:
        """Generate a cache key from type and identifier."""
        hash_id = hashlib.md5(identifier.encode()).hexdigest()[:8]
        return f"{data_type}_{hash_id}"
    
    def get_cache_path(self, data_type: str, cache_key: str) -> Path:
        """Get the file path for a cache entry."""
        type_dir = self.cache_dir / data_type
        type_dir.mkdir(exist_ok=True)
        return type_dir / f"{cache_key}.json"
    
    def is_valid(self, cache_path: Path, ttl_seconds: int) -> bool:
        """Check if cache file is still valid."""
        if not cache_path.exists():
            return False
        
        file_time = os.path.getmtime(cache_path)
        current_time = time.time()
        age_seconds = current_time - file_time
        
        return age_seconds < ttl_seconds
    
    def get(self, data_type: str, identifier: str) -> Optional[Any]:
        """Retrieve cached data if valid."""
        if data_type not in self.ttl:
            return None
        
        cache_key = self.generate_cache_key(data_type, identifier)
        cache_path = self.get_cache_path(data_type, cache_key)
        
        if self.is_valid(cache_path, self.ttl[data_type]):
            try:
                with open(cache_path, 'r') as f:
                    data = json.load(f)
                    return data.get('content')
            except (json.JSONDecodeError, IOError):
                return None
        
        return None
    
    def set(self, data_type: str, identifier: str, content: Any) -> bool:
        """Store data in cache."""
        if data_type not in self.ttl:
            return False
        
        cache_key = self.generate_cache_key(data_type, identifier)
        cache_path = self.get_cache_path(data_type, cache_key)
        
        cache_data = {
            'cached_at': datetime.now().isoformat(),
            'identifier': identifier,
            'data_type': data_type,
            'content': content
        }
        
        try:
            with open(cache_path, 'w') as f:
                json.dump(cache_data, f, indent=2)
            return True
        except IOError:
            return False
    
    def invalidate(self, data_type: str, identifier: str) -> bool:
        """Invalidate a specific cache entry."""
        cache_key = self.generate_cache_key(data_type, identifier)
        cache_path = self.get_cache_path(data_type, cache_key)
        
        if cache_path.exists():
            cache_path.unlink()
            return True
        return False
    
    def invalidate_type(self, data_type: str) -> int:
        """Invalidate all cache entries of a specific type."""
        type_dir = self.cache_dir / data_type
        count = 0
        
        if type_dir.exists():
            for cache_file in type_dir.glob("*.json"):
                cache_file.unlink()
                count += 1
        
        return count
    
    def clear_all(self) -> int:
        """Clear all cache entries."""
        count = 0
        for type_dir in self.cache_dir.iterdir():
            if type_dir.is_dir():
                for cache_file in type_dir.glob("*.json"):
                    cache_file.unlink()
                    count += 1
        return count
    
    def clear_expired(self) -> int:
        """Clear only expired cache entries."""
        count = 0
        current_time = time.time()
        
        for data_type, ttl_seconds in self.ttl.items():
            type_dir = self.cache_dir / data_type
            if type_dir.exists():
                for cache_file in type_dir.glob("*.json"):
                    file_time = os.path.getmtime(cache_file)
                    age_seconds = current_time - file_time
                    if age_seconds >= ttl_seconds:
                        cache_file.unlink()
                        count += 1
        
        return count
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = {
            'total_entries': 0,
            'total_size_bytes': 0,
            'by_type': {},
            'expired_count': 0
        }
        
        current_time = time.time()
        
        for data_type in self.ttl.keys():
            type_dir = self.cache_dir / data_type
            if type_dir.exists():
                type_stats = {
                    'count': 0,
                    'size_bytes': 0,
                    'expired': 0,
                    'valid': 0
                }
                
                for cache_file in type_dir.glob("*.json"):
                    type_stats['count'] += 1
                    size = cache_file.stat().st_size
                    type_stats['size_bytes'] += size
                    stats['total_size_bytes'] += size
                    
                    file_time = os.path.getmtime(cache_file)
                    age_seconds = current_time - file_time
                    if age_seconds >= self.ttl[data_type]:
                        type_stats['expired'] += 1
                        stats['expired_count'] += 1
                    else:
                        type_stats['valid'] += 1
                
                stats['by_type'][data_type] = type_stats
                stats['total_entries'] += type_stats['count']
        
        stats['total_size_mb'] = round(stats['total_size_bytes'] / (1024 * 1024), 2)
        
        return stats
    
    def get_cached_items(self, data_type: str) -> List[Dict[str, Any]]:
        """Get list of cached items of a specific type."""
        items = []
        type_dir = self.cache_dir / data_type
        
        if type_dir.exists():
            current_time = time.time()
            ttl_seconds = self.ttl.get(data_type, 0)
            
            for cache_file in type_dir.glob("*.json"):
                try:
                    with open(cache_file, 'r') as f:
                        data = json.load(f)
                        
                    file_time = os.path.getmtime(cache_file)
                    age_seconds = current_time - file_time
                    is_valid = age_seconds < ttl_seconds
                    
                    items.append({
                        'identifier': data.get('identifier'),
                        'cached_at': data.get('cached_at'),
                        'is_valid': is_valid,
                        'age_hours': round(age_seconds / 3600, 1),
                        'file': cache_file.name
                    })
                except (json.JSONDecodeError, IOError):
                    continue
        
        return items
    
    def export_cache_report(self) -> str:
        """Generate a cache status report."""
        stats = self.get_stats()
        
        report = f"""# Cache Status Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Overview
- Total Entries: {stats['total_entries']}
- Total Size: {stats['total_size_mb']} MB
- Expired Entries: {stats['expired_count']}

## Cache by Type
"""
        
        for data_type, type_stats in stats['by_type'].items():
            ttl_hours = self.ttl[data_type] / 3600
            report += f"""
### {data_type}
- Count: {type_stats['count']}
- Valid: {type_stats['valid']}
- Expired: {type_stats['expired']}
- Size: {round(type_stats['size_bytes'] / 1024, 2)} KB
- TTL: {ttl_hours} hours
"""
        
        return report


class CachedPromptManager:
    """Manage cached prompts for reuse."""
    
    def __init__(self, prompt_dir: str = "./data/prompts"):
        self.prompt_dir = Path(prompt_dir)
        self.prompt_dir.mkdir(parents=True, exist_ok=True)
        self.cache = CacheManager()
    
    def save_prompt(self, prompt_type: str, prompt_text: str, 
                   parameters: Optional[Dict] = None) -> Path:
        """Save a prompt for later reuse."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prompt_type}_{timestamp}.txt"
        filepath = self.prompt_dir / filename
        
        # Save prompt text
        with open(filepath, 'w') as f:
            f.write(prompt_text)
        
        # Save metadata
        metadata = {
            'type': prompt_type,
            'created': timestamp,
            'parameters': parameters or {},
            'file': filename
        }
        
        meta_path = self.prompt_dir / f"{prompt_type}_{timestamp}_meta.json"
        with open(meta_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Cache the prompt
        if parameters:
            cache_key = f"{prompt_type}_{json.dumps(parameters, sort_keys=True)}"
            self.cache.set('grok_prompts', cache_key, prompt_text)
        
        return filepath
    
    def get_cached_prompt(self, prompt_type: str, 
                         parameters: Optional[Dict] = None) -> Optional[str]:
        """Retrieve a cached prompt if available."""
        if parameters:
            cache_key = f"{prompt_type}_{json.dumps(parameters, sort_keys=True)}"
            return self.cache.get('grok_prompts', cache_key)
        return None
    
    def list_prompts(self, prompt_type: Optional[str] = None) -> List[Dict]:
        """List available prompts."""
        prompts = []
        
        for meta_file in self.prompt_dir.glob("*_meta.json"):
            with open(meta_file, 'r') as f:
                metadata = json.load(f)
                
            if prompt_type is None or metadata['type'] == prompt_type:
                prompts.append(metadata)
        
        # Sort by creation time, newest first
        prompts.sort(key=lambda x: x['created'], reverse=True)
        
        return prompts
    
    def get_latest_prompt(self, prompt_type: str) -> Optional[str]:
        """Get the most recent prompt of a specific type."""
        prompts = self.list_prompts(prompt_type)
        
        if prompts:
            latest = prompts[0]
            filepath = self.prompt_dir / latest['file']
            if filepath.exists():
                with open(filepath, 'r') as f:
                    return f.read()
        
        return None