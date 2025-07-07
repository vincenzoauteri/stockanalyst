#!/usr/bin/env python3
"""
Test runner script for the Stock Analyst application.
Provides convenient commands for running different types of tests.
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print('='*60)
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ FAILED: {description}")
        print(f"Exit code: {e.returncode}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Run tests for Stock Analyst application")
    parser.add_argument('test_type', nargs='?', default='all', 
                       choices=['all', 'unit', 'integration', 'fast', 'slow', 'coverage', 'lint'],
                       help='Type of tests to run')
    parser.add_argument('--verbose', '-v', action='store_true', 
                       help='Verbose output')
    parser.add_argument('--parallel', '-p', action='store_true',
                       help='Run tests in parallel (requires pytest-xdist)')
    parser.add_argument('--coverage', '-c', action='store_true',
                       help='Generate coverage report')
    parser.add_argument('--html-coverage', action='store_true',
                       help='Generate HTML coverage report')
    parser.add_argument('--markers', '-m', type=str,
                       help='Run tests with specific markers (e.g., "not slow")')
    parser.add_argument('--file', '-f', type=str,
                       help='Run specific test file')
    parser.add_argument('--function', '-k', type=str,
                       help='Run tests matching pattern')
    parser.add_argument('--failfast', '-x', action='store_true',
                       help='Stop on first failure')
    parser.add_argument('--pdb', action='store_true',
                       help='Start debugger on failures')
    parser.add_argument('--durations', type=int, default=10,
                       help='Show N slowest test durations')
    
    args = parser.parse_args()
    
    # Check if we're in the right directory
    if not Path('tests').exists():
        print("❌ Error: 'tests' directory not found. Run from the project root.")
        sys.exit(1)
    
    # Base pytest command
    base_cmd = ['python', '-m', 'pytest']
    
    # Add verbosity
    if args.verbose:
        base_cmd.extend(['-v', '-s'])
    
    # Add parallel execution
    if args.parallel:
        base_cmd.extend(['-n', 'auto'])
    
    # Add fail fast
    if args.failfast:
        base_cmd.append('-x')
    
    # Add PDB
    if args.pdb:
        base_cmd.append('--pdb')
    
    # Add durations
    base_cmd.extend(['--durations', str(args.durations)])
    
    # Coverage options
    coverage_cmd = []
    if args.coverage or args.html_coverage or args.test_type == 'coverage':
        coverage_cmd = [
            '--cov=.',
            '--cov-report=term-missing',
            '--cov-branch'
        ]
        if args.html_coverage or args.test_type == 'coverage':
            coverage_cmd.append('--cov-report=html')
    
    # Test selection
    test_commands = []
    
    if args.test_type == 'all':
        test_commands.append({
            'cmd': base_cmd + coverage_cmd + ['tests/'],
            'description': 'All tests'
        })
    
    elif args.test_type == 'unit':
        test_commands.append({
            'cmd': base_cmd + coverage_cmd + ['-m', 'not integration and not slow', 'tests/'],
            'description': 'Unit tests only'
        })
    
    elif args.test_type == 'integration':
        test_commands.append({
            'cmd': base_cmd + coverage_cmd + ['-m', 'integration', 'tests/'],
            'description': 'Integration tests only'
        })
    
    elif args.test_type == 'fast':
        test_commands.append({
            'cmd': base_cmd + ['-m', 'not slow', 'tests/'],
            'description': 'Fast tests only'
        })
    
    elif args.test_type == 'slow':
        test_commands.append({
            'cmd': base_cmd + ['-m', 'slow', 'tests/'],
            'description': 'Slow tests only'
        })
    
    elif args.test_type == 'coverage':
        test_commands.append({
            'cmd': base_cmd + coverage_cmd + ['tests/'],
            'description': 'All tests with coverage report'
        })
    
    elif args.test_type == 'lint':
        # Run linting commands
        lint_commands = [
            {
                'cmd': ['python', '-m', 'flake8', '.', '--exclude=venv,__pycache__', '--max-line-length=120'],
                'description': 'Flake8 linting'
            },
            {
                'cmd': ['python', '-m', 'pylint', '--rcfile=.pylintrc', '*.py'],
                'description': 'Pylint analysis'
            }
        ]
        
        success = True
        for lint_cmd in lint_commands:
            if not run_command(lint_cmd['cmd'], lint_cmd['description']):
                success = False
        
        if success:
            print("\n✅ All linting checks passed!")
        else:
            print("\n❌ Some linting checks failed!")
        
        return 0 if success else 1
    
    # Add custom markers
    if args.markers:
        for cmd_info in test_commands:
            cmd_info['cmd'].extend(['-m', args.markers])
    
    # Add specific file
    if args.file:
        for cmd_info in test_commands:
            # Replace 'tests/' with specific file
            cmd_info['cmd'] = [c for c in cmd_info['cmd'] if c != 'tests/']
            cmd_info['cmd'].append(f'tests/{args.file}')
            cmd_info['description'] += f' (file: {args.file})'
    
    # Add function pattern
    if args.function:
        for cmd_info in test_commands:
            cmd_info['cmd'].extend(['-k', args.function])
            cmd_info['description'] += f' (pattern: {args.function})'
    
    # Run tests
    success = True
    total_commands = len(test_commands)
    
    for i, cmd_info in enumerate(test_commands, 1):
        print(f"\n🧪 Running test suite {i}/{total_commands}")
        
        if not run_command(cmd_info['cmd'], cmd_info['description']):
            success = False
            if args.failfast:
                break
    
    # Summary
    print(f"\n{'='*60}")
    if success:
        print("✅ ALL TESTS PASSED!")
        if args.coverage or args.html_coverage or args.test_type == 'coverage':
            print("\n📊 Coverage report generated:")
            if args.html_coverage or args.test_type == 'coverage':
                html_path = Path('htmlcov/index.html').absolute()
                print(f"   HTML: {html_path}")
                print(f"   Open with: open {html_path}")
    else:
        print("❌ SOME TESTS FAILED!")
    print('='*60)
    
    return 0 if success else 1

if __name__ == '__main__':
    # Set environment variables for testing
    os.environ['TESTING'] = 'true'
    os.environ['LOG_LEVEL'] = 'ERROR'
    
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n❌ Tests interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)