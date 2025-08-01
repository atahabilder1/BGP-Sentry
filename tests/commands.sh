#!/bin/bash
#========================================================
# BGP-Sentry Test Commands Reference
# File Location: tests/commands.sh
#========================================================

# Color codes for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m'

print_header() {
    echo -e "${CYAN}========================================${NC}"
    echo -e "${WHITE}$1${NC}"
    echo -e "${CYAN}========================================${NC}"
}

show_help() {
    print_header "BGP-Sentry Test Commands Reference"
    
    echo -e "${YELLOW}📋 BASIC PRE-SIMULATION TESTS${NC}"
    echo -e "${GREEN}# Basic test with self-generated data${NC}"
    echo "python3 enhanced_pre_simulation.py"
    echo ""
    echo -e "${GREEN}# Basic test with original production data${NC}"
    echo "python3 enhanced_pre_simulation.py --data-source=original"
    
    echo -e "\n${YELLOW}📋 EXTENDED PRE-SIMULATION TESTS${NC}"
    echo -e "${GREEN}# Extended tests with test data${NC}"
    echo "python3 enhanced_pre_simulation.py --run-extended-tests"
    echo ""
    echo -e "${GREEN}# Extended tests with original data${NC}"
    echo "python3 enhanced_pre_simulation.py --run-extended-tests --data-source=original"
    
    echo -e "\n${YELLOW}📋 BLOCKCHAIN SETUP${NC}"
    echo -e "${GREEN}# Start Hardhat node${NC}"
    echo "cd ../smart_contract && npx hardhat node"
    echo ""
    echo -e "${GREEN}# Fund all wallets${NC}"
    echo "cd ../smart_contract && npx hardhat run scripts/deposit_from_all.js --network localhost"
    
    echo -e "\n${YELLOW}📋 DATA GENERATION${NC}"
    echo -e "${GREEN}# Generate test data${NC}"
    echo "cd data_generator && python3 generate_test_data.py"
    
    echo -e "\n${YELLOW}📋 QUICK COMMANDS${NC}"
    echo "./commands.sh quick     # Quick test"
    echo "./commands.sh status    # Check system status"
    echo "./commands.sh cleanup   # Kill Hardhat processes"
    echo "./commands.sh generate  # Generate test data"
}

quick_test() {
    print_header "Running Quick Pre-Simulation Test"
    python3 enhanced_pre_simulation.py
}

generate_data() {
    print_header "Generating Test Data"
    if [ -d "data_generator" ]; then
        cd data_generator
        echo -e "${GREEN}Running data generator...${NC}"
        python3 generate_test_data.py
        cd ..
    else
        echo -e "${RED}❌ data_generator folder not found${NC}"
    fi
}

check_status() {
    print_header "System Status Check"
    echo -e "${BLUE}Checking Hardhat node...${NC}"
    if curl -s -X POST -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' http://localhost:8545 > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Hardhat node is running${NC}"
    else
        echo -e "${RED}❌ Hardhat node is not running${NC}"
    fi
    
    echo -e "\n${BLUE}Checking data_generator...${NC}"
    if [ -d "data_generator" ]; then
        echo -e "${GREEN}✅ data_generator folder exists${NC}"
    else
        echo -e "${RED}❌ data_generator folder missing${NC}"
    fi
    
    echo -e "\n${BLUE}Virtual environment status...${NC}"
    if [ -n "$VIRTUAL_ENV" ]; then
        echo -e "${GREEN}✅ Virtual environment active: $VIRTUAL_ENV${NC}"
    else
        echo -e "${YELLOW}⚠️  No virtual environment detected${NC}"
    fi
}

cleanup_blockchain() {
    print_header "Cleaning up Blockchain Processes"
    echo -e "${YELLOW}Killing all Hardhat processes...${NC}"
    pkill -f hardhat
    echo -e "${GREEN}Cleanup complete!${NC}"
}

case "$1" in
    "help"|"")
        show_help
        ;;
    "quick")
        quick_test
        ;;
    "generate")
        generate_data
        ;;
    "status")
        check_status
        ;;
    "cleanup")
        cleanup_blockchain
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo "Available: help, quick, generate, status, cleanup"
        ;;
esac
