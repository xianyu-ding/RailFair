#!/bin/bash
# Quick start script for HSP batch collection
# Usage: ./run_collection.sh [phase1|phase2|phase3|all]

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  HSP Data Collection - Quick Start${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 not found${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Python 3 found${NC}"

# Check required files
REQUIRED_FILES=(
    "fetch_hsp_batch.py"
    "hsp_processor.py"
    "hsp_validator.py"
    "retry_handler.py"
    "hsp_config_phase1.yaml"
    "hsp_config_phase2.yaml"
    "hsp_config_phase3.yaml"
)

echo ""
echo -e "${YELLOW}Checking required files...${NC}"
for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$SCRIPT_DIR/$file" ]; then
        echo -e "${RED}❌ Missing: $file${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Found: $file${NC}"
done

# Check environment variables
echo ""
echo -e "${YELLOW}Checking credentials...${NC}"
if [ -z "$HSP_EMAIL" ] && [ -z "$HSP_USERNAME" ]; then
    echo -e "${RED}❌ HSP_EMAIL or HSP_USERNAME not set${NC}"
    echo "   Please set credentials:"
    echo "   export HSP_EMAIL='your_email@example.com'"
    echo "   export HSP_PASSWORD='your_password'"
    exit 1
fi

if [ -z "$HSP_PASSWORD" ]; then
    echo -e "${RED}❌ HSP_PASSWORD not set${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Credentials configured${NC}"

# Create necessary directories
echo ""
echo -e "${YELLOW}Creating directories...${NC}"
mkdir -p data/raw/hsp/phase{1,2,3}
mkdir -p logs
echo -e "${GREEN}✅ Directories created${NC}"

# Determine which phase to run
PHASE=${1:-all}

echo ""
echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  Starting Collection: $PHASE${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

run_phase() {
    local phase_num=$1
    local phase_name=$2
    local config_file="hsp_config_phase${phase_num}.yaml"
    local log_file="logs/collection_phase${phase_num}_$(date +%Y%m%d_%H%M%S).log"
    
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}  Phase ${phase_num}: ${phase_name}${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "   Config: ${config_file}"
    echo -e "   Log:    ${log_file}"
    echo ""
    
    # Run collection
    if python3 "$SCRIPT_DIR/fetch_hsp_batch.py" \
        "$SCRIPT_DIR/$config_file" \
        --phase "Phase ${phase_num}: ${phase_name}" \
        2>&1 | tee "$log_file"; then
        echo ""
        echo -e "${GREEN}✅ Phase ${phase_num} completed successfully${NC}"
        return 0
    else
        echo ""
        echo -e "${RED}❌ Phase ${phase_num} failed${NC}"
        return 1
    fi
}

# Run phases based on argument
case $PHASE in
    phase1|1)
        run_phase 1 "Winter Historical Data (Dec 2024 - Jan 2025)"
        ;;
    phase2|2)
        run_phase 2 "Recent Operational Data (Sep-Oct 2025)"
        ;;
    phase3|3)
        run_phase 3 "Summer Baseline Data (Jun-Aug 2025)"
        ;;
    all)
        echo -e "${BLUE}Running all phases sequentially...${NC}"
        echo ""
        
        if run_phase 1 "Winter Historical Data"; then
            echo ""
            echo -e "${YELLOW}⏳ Waiting 30 seconds before Phase 2...${NC}"
            sleep 30
            
            if run_phase 2 "Recent Operational Data"; then
                echo ""
                echo -e "${YELLOW}⏳ Waiting 30 seconds before Phase 3...${NC}"
                sleep 30
                
                run_phase 3 "Summer Baseline Data"
            fi
        fi
        ;;
    *)
        echo -e "${RED}❌ Invalid phase: $PHASE${NC}"
        echo "   Usage: $0 [phase1|phase2|phase3|all]"
        exit 1
        ;;
esac

# Run validation
echo ""
echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  Running Data Validation${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

if [ -f "$SCRIPT_DIR/validate_hsp_data.py" ]; then
    REPORT_FILE="data/validation_report_$(date +%Y%m%d_%H%M%S).txt"
    JSON_FILE="data/statistics_$(date +%Y%m%d_%H%M%S).json"
    
    python3 "$SCRIPT_DIR/validate_hsp_data.py" \
        --db data/railfair.db \
        --output "$REPORT_FILE" \
        --json "$JSON_FILE"
    
    echo ""
    echo -e "${GREEN}✅ Validation report: $REPORT_FILE${NC}"
    echo -e "${GREEN}✅ Statistics JSON: $JSON_FILE${NC}"
else
    echo -e "${YELLOW}⚠️  Validation script not found${NC}"
fi

echo ""
echo -e "${BLUE}================================================${NC}"
echo -e "${GREEN}  ✅ Collection Complete!${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo "Next steps:"
echo "  1. Review validation report in data/"
echo "  2. Check logs in logs/"
echo "  3. Query database: sqlite3 data/railfair.db"
echo ""
