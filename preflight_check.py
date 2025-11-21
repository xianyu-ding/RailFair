#!/usr/bin/env python3
"""
Pre-flight Check Script for Day 4 Collection
Validates all files and configurations are ready
"""

import os
import sys
from pathlib import Path
import yaml

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

class Colors:
    GREEN = '\033[0;32m'
    RED = '\033[0;31m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color

def print_header(text):
    print(f"\n{Colors.BLUE}{'='*70}{Colors.NC}")
    print(f"{Colors.BLUE}{text:^70}{Colors.NC}")
    print(f"{Colors.BLUE}{'='*70}{Colors.NC}\n")

def check_file(filepath, required=True):
    """Check if file exists"""
    if os.path.exists(filepath):
        print(f"{Colors.GREEN}✅ Found: {filepath}{Colors.NC}")
        return True
    else:
        symbol = f"{Colors.RED}❌" if required else f"{Colors.YELLOW}⚠️"
        status = "REQUIRED" if required else "optional"
        print(f"{symbol} Missing ({status}): {filepath}{Colors.NC}")
        return not required

def check_python_module(module_name):
    """Check if Python module can be imported"""
    try:
        __import__(module_name)
        print(f"{Colors.GREEN}✅ Module available: {module_name}{Colors.NC}")
        return True
    except ImportError:
        print(f"{Colors.RED}❌ Module missing: {module_name}{Colors.NC}")
        return False

def check_env_variable(var_name, required=True):
    """Check if environment variable is set"""
    value = os.getenv(var_name)
    if value:
        # Don't show the actual value for security
        masked = value[:3] + "***" if len(value) > 3 else "***"
        print(f"{Colors.GREEN}✅ {var_name} = {masked}{Colors.NC}")
        return True
    else:
        symbol = f"{Colors.RED}❌" if required else f"{Colors.YELLOW}⚠️"
        status = "REQUIRED" if required else "optional"
        print(f"{symbol} {var_name} not set ({status}){Colors.NC}")
        return not required

def check_config_file(filepath):
    """Validate YAML configuration file"""
    try:
        with open(filepath, 'r') as f:
            config = yaml.safe_load(f)
        
        print(f"{Colors.GREEN}✅ Valid YAML: {filepath}{Colors.NC}")
        
        # Check key sections
        required_sections = ['api', 'data_collection', 'routes', 'database']
        for section in required_sections:
            if section not in config:
                print(f"   {Colors.YELLOW}⚠️  Missing section: {section}{Colors.NC}")
        
        # Show route count
        if 'routes' in config:
            route_count = len(config['routes'])
            print(f"   Routes configured: {route_count}")
            
        # Show date range
        if 'data_collection' in config:
            dc = config['data_collection']
            if 'from_date' in dc and 'to_date' in dc:
                print(f"   Date range: {dc['from_date']} to {dc['to_date']}")
        
        return True
    except Exception as e:
        print(f"{Colors.RED}❌ Invalid YAML: {filepath}{Colors.NC}")
        print(f"   Error: {e}")
        return False

def estimate_collection_time(config_file):
    """Estimate collection time based on configuration"""
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        routes = len(config.get('routes', []))
        
        # Parse dates
        from_date = config.get('data_collection', {}).get('from_date', '')
        to_date = config.get('data_collection', {}).get('to_date', '')
        
        # Rough estimate: 20-30 minutes per route
        avg_time_per_route = 25  # minutes
        total_time = routes * avg_time_per_route
        
        return {
            'routes': routes,
            'from_date': from_date,
            'to_date': to_date,
            'estimated_minutes': total_time,
            'estimated_hours': round(total_time / 60, 1)
        }
    except Exception as e:
        return None

def main():
    print_header("Day 4 Pre-flight Check")
    
    all_checks_passed = True

    # Attempt to load environment variables from .env
    if load_dotenv is not None:
        env_candidates = [
            Path(".env"),
            Path("configs") / ".env",
            Path("config") / ".env",
        ]
        for env_path in env_candidates:
            if env_path.exists():
                try:
                    load_dotenv(dotenv_path=env_path, override=False)
                    print(f"{Colors.GREEN}Loaded environment variables from {env_path}{Colors.NC}")
                    break
                except Exception as exc:
                    print(f"{Colors.YELLOW}Warning: could not load {env_path}: {exc}{Colors.NC}")
    
    # Check Python version
    print(f"\n{Colors.YELLOW}Python Version:{Colors.NC}")
    version = sys.version_info
    print(f"   Python {version.major}.{version.minor}.{version.micro}")
    if version.major >= 3 and version.minor >= 7:
        print(f"{Colors.GREEN}✅ Python version OK (3.7+){Colors.NC}")
    else:
        print(f"{Colors.RED}❌ Python version too old (need 3.7+){Colors.NC}")
        all_checks_passed = False
    
    # Check required files
    print_header("Required Files")
    
    required_files = [
        'fetch_hsp_batch.py',
        'hsp_processor.py',
        'hsp_validator.py',
        'retry_handler.py',
        'validate_hsp_data.py',
        'configs/hsp_config_phase1.yaml',
        'configs/hsp_config_phase2.yaml',
        'configs/hsp_config_phase3.yaml',
    ]
    
    for filepath in required_files:
        if not check_file(filepath):
            all_checks_passed = False
    
    # Check optional files
    print(f"\n{Colors.YELLOW}Optional Files:{Colors.NC}")
    optional_files = [
        'run_collection.sh',
        'DAY4_DOCUMENTATION.md',
    ]
    
    for filepath in optional_files:
        check_file(filepath, required=False)
    
    # Check Python modules
    print_header("Python Modules")
    
    required_modules = [
        'yaml',
        'requests',
        'sqlite3',
    ]
    
    for module in required_modules:
        if not check_python_module(module):
            all_checks_passed = False
    
    # Check environment variables
    print_header("Environment Variables")
    
    has_email = check_env_variable('HSP_EMAIL', required=False)
    has_username = check_env_variable('HSP_USERNAME', required=False)
    has_password = check_env_variable('HSP_PASSWORD', required=True)
    
    if not (has_email or has_username):
        print(f"{Colors.RED}❌ Need either HSP_EMAIL or HSP_USERNAME{Colors.NC}")
        all_checks_passed = False
    
    if not has_password:
        all_checks_passed = False
    
    # Check configuration files
    print_header("Configuration Validation")
    
    config_files = [
        'configs/hsp_config_phase1.yaml',
        'configs/hsp_config_phase2.yaml',
        'configs/hsp_config_phase3.yaml',
    ]
    
    for config_file in config_files:
        if os.path.exists(config_file):
            if not check_config_file(config_file):
                all_checks_passed = False
    
    # Check directories
    print_header("Directory Structure")
    
    required_dirs = [
        'data',
        'logs',
    ]
    
    for dirname in required_dirs:
        if os.path.exists(dirname):
            print(f"{Colors.GREEN}✅ Directory exists: {dirname}{Colors.NC}")
        else:
            print(f"{Colors.YELLOW}⚠️  Will create: {dirname}{Colors.NC}")
            try:
                os.makedirs(dirname, exist_ok=True)
                print(f"{Colors.GREEN}   Created successfully{Colors.NC}")
            except Exception as e:
                print(f"{Colors.RED}   Failed to create: {e}{Colors.NC}")
                all_checks_passed = False
    
    # Estimate collection times
    print_header("Collection Estimates")
    
    phases = [
        ('Phase 1 (Winter)', 'configs/hsp_config_phase1.yaml'),
        ('Phase 2 (Recent)', 'configs/hsp_config_phase2.yaml'),
        ('Phase 3 (Summer)', 'configs/hsp_config_phase3.yaml'),
    ]
    
    total_hours = 0
    for phase_name, config_file in phases:
        if os.path.exists(config_file):
            estimate = estimate_collection_time(config_file)
            if estimate:
                print(f"\n{Colors.BLUE}{phase_name}:{Colors.NC}")
                print(f"   Routes: {estimate['routes']}")
                print(f"   Period: {estimate['from_date']} to {estimate['to_date']}")
                print(f"   Estimated time: {estimate['estimated_hours']} hours")
                total_hours += estimate['estimated_hours']
    
    if total_hours > 0:
        print(f"\n{Colors.BLUE}Total estimated time: {total_hours} hours{Colors.NC}")
    
    # Final summary
    print_header("Pre-flight Summary")
    
    if all_checks_passed:
        print(f"{Colors.GREEN}✅ All checks passed!{Colors.NC}")
        print(f"\n{Colors.GREEN}Ready to start collection:{Colors.NC}")
        print(f"   ./run_collection.sh all")
        print(f"   OR")
        print(f"   python3 fetch_hsp_batch.py hsp_config_phase1.yaml --phase \"Phase 1\"")
        return 0
    else:
        print(f"{Colors.RED}❌ Some checks failed{Colors.NC}")
        print(f"\n{Colors.YELLOW}Please fix the issues above before starting collection{Colors.NC}")
        print(f"\nCommon fixes:")
        print(f"   1. Set credentials:")
        print(f"      export HSP_EMAIL='your_email@example.com'")
        print(f"      export HSP_PASSWORD='your_password'")
        print(f"   2. Install missing modules:")
        print(f"      pip install pyyaml requests")
        print(f"   3. Copy missing files from project repository")
        return 1

if __name__ == '__main__':
    sys.exit(main())
