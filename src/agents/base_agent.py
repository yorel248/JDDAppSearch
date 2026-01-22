"""Base Agent class for all job search agents."""

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import json


class BaseAgent(ABC):
    """Abstract base class for all agents."""
    
    def __init__(self, name: str, data_dir: str = "./data"):
        self.name = name
        self.data_dir = Path(data_dir)
        self.prompts_dir = self.data_dir / "prompts"
        self.prompts_dir.mkdir(parents=True, exist_ok=True)
        self.execution_history = []
    
    @abstractmethod
    def generate_prompt(self, **kwargs) -> str:
        """Generate the agent-specific prompt."""
        pass
    
    @abstractmethod
    def process_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Process the response from Claude."""
        pass
    
    def save_prompt(self, prompt: str, identifier: str = None) -> Path:
        """Save generated prompt to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        identifier = identifier or self.name
        filename = f"{identifier}_{timestamp}.txt"
        filepath = self.prompts_dir / filename
        
        with open(filepath, 'w') as f:
            f.write(prompt)
        
        return filepath
    
    def log_execution(self, prompt_file: Path, status: str = "generated"):
        """Log agent execution."""
        self.execution_history.append({
            "timestamp": datetime.now().isoformat(),
            "agent": self.name,
            "prompt_file": str(prompt_file),
            "status": status
        })
    
    def get_standard_output_format(self) -> str:
        """Get standard JSON output format for Claude."""
        return """
Please format your response as valid JSON that can be directly saved to a file.
Ensure all strings are properly escaped and the JSON is valid.
"""
    
    def create_context(self, **kwargs) -> Dict[str, Any]:
        """Create context for prompt generation."""
        context = {
            "agent": self.name,
            "timestamp": datetime.now().isoformat(),
            "data_dir": str(self.data_dir)
        }
        context.update(kwargs)
        return context