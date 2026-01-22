"""Setup script for Claude Job Search system."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="claude-job-search",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="AI-powered job search and application system using Claude Code",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/claude-job-search",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Office/Business",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        # No external dependencies required!
        # System works entirely with Claude Code
    ],
    entry_points={
        "console_scripts": [
            "claude-job=claude_job:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["config/*.json", "templates/*.md"],
    },
)