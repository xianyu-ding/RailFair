#!/bin/bash
# Day 3 - HSP Quick Start Guide

echo "=================================="
echo "HSP Data Fetcher - Quick Start"
echo "=================================="
echo ""

# Check Python version
echo "1. Checking Python..."
python3 --version
if [ $? -ne 0 ]; then
    echo "❌ Python 3 not found. Please install Python 3.8+"
    exit 1
fi
echo "✓ Python OK"
echo ""

# Check dependencies
echo "2. Checking dependencies..."
python3 -c "import requests, yaml, pytz" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠ Missing dependencies. Installing..."
    pip3 install requests pyyaml pytz
else
    echo "✓ Dependencies OK"
fi
echo ""

# Check environment variables
echo "3. Checking HSP credentials..."
if [ -z "$HSP_EMAIL" ] || [ -z "$HSP_PASSWORD" ]; then
    echo "⚠ HSP credentials not set!"
    echo ""
    echo "To use the HSP API, you need:"
    echo "  1. Register at: https://opendata.nationalrail.co.uk/"
    echo "  2. Check 'HSP' in subscription type"
    echo "  3. Set environment variables:"
    echo ""
    echo "     export HSP_EMAIL='your_email@example.com'"
    echo "     export HSP_PASSWORD='your_password'"
    echo ""
    echo "For now, running code structure tests only..."
    echo ""
else
    echo "✓ Credentials found"
    echo "  Email: ${HSP_EMAIL}"
    echo ""
fi

# Run tests
echo "4. Running tests..."
echo "=================================="
python3 test_hsp_fetch.py

if [ $? -eq 0 ]; then
    echo ""
    echo "=================================="
    echo "✅ All tests passed!"
    echo "=================================="
    echo ""
    
    if [ ! -z "$HSP_EMAIL" ]; then
        echo "Ready to fetch real data!"
        echo "Run: python3 fetch_hsp.py"
    else
        echo "Set HSP credentials to fetch real data."
    fi
else
    echo ""
    echo "=================================="
    echo "❌ Tests failed"
    echo "=================================="
fi

echo ""
echo "Quick Commands:"
echo "  python3 fetch_hsp.py          # Fetch EUS-MAN data"
echo "  python3 test_hsp_fetch.py     # Run tests"
echo "  cat DAY3_README.md            # Read documentation"
echo ""
