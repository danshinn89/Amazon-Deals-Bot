#!/usr/bin/env python3
"""
Check for potential secrets or sensitive information in project files.
Run this before pushing code to a public repository.
"""

import os
import re
import sys

# Patterns to look for
SECRET_PATTERNS = [
    # API Keys, Tokens, Passwords
    r'key["\']?\s*[:=]\s*["\']?[a-zA-Z0-9_+/=]{16,}["\']?',
    r'secret["\']?\s*[:=]\s*["\']?[a-zA-Z0-9_+/=]{16,}["\']?',
    r'password["\']?\s*[:=]\s*["\']?[^"\'\s]{8,}["\']?',
    r'token["\']?\s*[:=]\s*["\']?[a-zA-Z0-9_+/=\-]{8,}["\']?',
    r'auth["\']?\s*[:=]\s*["\']?[a-zA-Z0-9_+/=\-]{8,}["\']?',
    
    # AWS specific
    r'AKIA[0-9A-Z]{16}',
    r'aws_access_key_id["\']?\s*[:=]\s*["\']?[A-Z0-9]{20}["\']?',
    r'aws_secret_access_key["\']?\s*[:=]\s*["\']?[A-Za-z0-9/+=]{40}["\']?',
    
    # Database connections
    r'postgresql://.*:.*@.*',
    r'mysql://.*:.*@.*',
    r'mongodb://.*:.*@.*',
    r'database_url["\']?\s*[:=]\s*["\']?[^\s\'\"]+["\']?',
    
    # Supabase
    r'supabase[_-]?key["\']?\s*[:=]\s*["\']?[a-zA-Z0-9_+/=\-]{30,}["\']?',
    r'supabase[_-]?url["\']?\s*[:=]\s*["\']?https?://[^\s\'\"]+["\']?',
    
    # Bluesky credentials
    r'bluesky_username["\']?\s*[:=]\s*["\']?[\w\.-]+\.bsky\.social["\']?',
    r'bluesky_app_password["\']?\s*[:=]\s*["\']?[^\s\'\"]{8,}["\']?'
]

def check_file(file_path):
    """Check a single file for potential secrets."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        issues = []
        line_number = 0
        
        for line_number, line in enumerate(content.split('\n'), 1):
            for pattern in SECRET_PATTERNS:
                matches = re.finditer(pattern, line, re.IGNORECASE)
                for match in matches:
                    # Skip matches in comments
                    if line.strip().startswith('#') or line.strip().startswith('//'):
                        continue
                    
                    # Skip matches that are likely variable assignments
                    if re.search(r'os\.getenv\(["\']', line) or "load_dotenv" in line:
                        continue
                    
                    # Skip README and similar files
                    if file_path.endswith(('README.md', '.gitignore', 'LICENSE')):
                        continue
                    
                    issues.append((line_number, match.group(0)))
        
        return issues
    except Exception as e:
        return [(0, f"Error reading file: {e}")]

def scan_directory(directory):
    """Scan a directory for potential secrets in all files."""
    file_extensions = ['.py', '.js', '.json', '.yml', '.yaml', '.env', '.ini', '.cfg', '.txt', '.md']
    issues_found = False
    
    for root, _, files in os.walk(directory):
        for file in files:
            if any(file.endswith(ext) for ext in file_extensions):
                file_path = os.path.join(root, file)
                
                # Skip the check_secrets.py script itself
                if os.path.basename(file_path) == 'check_secrets.py':
                    continue
                
                # Skip files in .git, __pycache__, etc.
                if '/.git/' in file_path or '/__pycache__/' in file_path or '/venv/' in file_path:
                    continue
                
                issues = check_file(file_path)
                if issues:
                    print(f"\n⚠️  Potential secrets found in {file_path}:")
                    for line_num, issue in issues:
                        print(f"  Line {line_num}: {issue}")
                    issues_found = True
    
    return issues_found

if __name__ == "__main__":
    print("🔍 Scanning for potential secrets...")
    
    # Default to current directory or accept a path as argument
    directory = sys.argv[1] if len(sys.argv) > 1 else '.'
    
    issues_found = scan_directory(directory)
    
    if issues_found:
        print("\n⛔ Potential secrets found! Please review the issues above before committing.")
        print("   Consider using environment variables or a secrets manager.")
        sys.exit(1)
    else:
        print("✅ No potential secrets found. Your code looks clean!")
        sys.exit(0)