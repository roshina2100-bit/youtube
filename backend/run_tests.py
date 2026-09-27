#!/usr/bin/env python
"""
Test runner script for Cinematic Video Studio.
Run tests with various options.
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_tests(args):
    """Run pytest with the given arguments."""
    backend_dir = Path(__file__).parent
    test_dir = backend_dir / "tests"
    
    cmd = ["python", "-m", "pytest"]
    
    # Add test directory
    cmd.append(str(test_dir))
    
    # Add verbosity
    if args.verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")
    
    # Add coverage
    if args.coverage:
        cmd.extend(["--cov=app", "--cov-report=term-missing", "--cov-report=html"])
    
    # Add markers
    if args.markers:
        cmd.extend(["-m", args.markers])
    
    # Add parallel execution
    if args.parallel:
        cmd.extend(["-n", "auto"])
    
    # Add timeout
    if args.timeout:
        cmd.extend(["--timeout", str(args.timeout)])
    
    # Add HTML report
    if args.html:
        cmd.extend(["--html=report.html", "--self-contained-html"])
    
    # Add JSON report
    if args.json:
        cmd.extend(["--json-report", "--json-report-file=report.json"])
    
    # Add specific test file or pattern
    if args.test_file:
        cmd.append(args.test_file)
    
    # Add keyword filter
    if args.keyword:
        cmd.extend(["-k", args.keyword])
    
    # Run tests
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=backend_dir)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="Run Cinematic Video Studio tests")
    
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("-c", "--coverage", action="store_true", help="Run with coverage")
    parser.add_argument("-m", "--markers", help="Run tests with specific markers (e.g., 'unit', 'integration', 'e2e')")
    parser.add_argument("-p", "--parallel", action="store_true", help="Run tests in parallel")
    parser.add_argument("-t", "--timeout", type=int, help="Timeout in seconds")
    parser.add_argument("--html", action="store_true", help="Generate HTML report")
    parser.add_argument("--json", action="store_true", help="Generate JSON report")
    parser.add_argument("-f", "--test-file", help="Run specific test file")
    parser.add_argument("-k", "--keyword", help="Run tests matching keyword")
    
    args = parser.parse_args()
    
    return run_tests(args)


if __name__ == "__main__":
    sys.exit(main())