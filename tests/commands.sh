#!/bin/bash
#========================================================
# BGP-Sentry Test Commands Reference
# File Location: tests/commands.sh
#========================================================
#
# This file contains all the important commands for running
# BGP-Sentry tests and simulations. Use it as a reference
# and quick execution script.
#
# Usage: 
#   source commands.sh    # Load functions into shell
#   ./commands.sh help    # Show this help
#========================================================

# Color codes for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Function to print colored headers
print_header() {
    echo -e "${CYAN}========================================${NC}"
    echo -e "${WHITE}$1${NC}"
    echo -e "${CYAN}========================================${NC}"
}

print_section() {
    echo -e "\n${YELLOW}📋 $1${NC}"
    echo -e "${YELLOW}$2${NC}"
}

# Help function
show_help() {
    print_header "BGP-Sentry Ultimate Test Commands Reference"
    
    print_section "CORE VALIDATION TESTS" "Quick system validation (30 seconds)"
    echo -e "${GREEN}# Basic validation with test data${NC}"
    echo "python3 enhanced_pre_simulation.py"
    echo ""
    echo -e "${GREEN}# Basic validation with original production data${NC}"
    echo "python3 enhanced_pre_simulation.py --data-source=original"
    
    print_section "EXTENDED COMPREHENSIVE TESTS" "Core + ALL individual test suites (2-5 minutes)"
    echo -e "${GREEN}# Extended tests: Core validation + ALL 18 test folders${NC}"
    echo "python3 enhanced_pre_simulation.py --run-extended-tests"
    echo ""
    echo -e "${GREEN}# Extended tests with original data${NC}"
    echo "python3 enhanced_pre_simulation.py --run-extended-tests --data-source=original"
    
    print_section "COMPLETE SETUP + VALIDATION" "Full blockchain setup + comprehensive testing"
    echo -e "${GREEN}# Complete setup: Reset → Start Hardhat → Deploy → Fund → Generate Data → Validate${NC}"
    echo "python3 enhanced_pre_simulation.py --setup"
    echo ""
    echo -e "${GREEN}# Complete setup + extended testing (EVERYTHING!)${NC}"
    echo "python3 enhanced_pre_simulation.py --setup --run-extended-tests"
    echo ""
    echo -e "${GREEN}# Complete setup with original data${NC}"
    echo "python3 enhanced_pre_simulation.py --setup --data-source=original"
    
    print_section "INDIVIDUAL TEST SUITES" "Run specific test categories"
    echo -e "${GREEN}# List all available test suites${NC}"
    echo "python3 run_test_suite.py --list"
    echo ""
    echo -e "${GREEN}# Run specific test suite${NC}"
    echo "python3 run_test_suite.py 00_directory_structure"
    echo "python3 run_test_suite.py 01_initialization_check"
    echo "python3 run_test_suite.py 04_staking"
    echo "python3 run_test_suite.py 08_trust_engine"
    echo "python3 run_test_suite.py 13_economic_tests"
    echo ""
    echo -e "${GREEN}# Run ALL individual test suites${NC}"
    echo "python3 run_test_suite.py"
    
    print_section "BLOCKCHAIN SETUP COMMANDS" "Manual blockchain operations"
    echo -e "${GREEN}# Start Hardhat node (run in separate terminal)${NC}"
    echo "cd ../smart_contract && npx hardhat node"
    echo ""
    echo -e "${GREEN}# Compile contracts${NC}"
    echo "cd ../smart_contract && npx hardhat compile"
    echo ""
    echo -e "${GREEN}# Deploy smart contracts${NC}"
    echo "cd ../smart_contract && npx hardhat run scripts/deploy.js --network localhost"
    echo ""
    echo -e "${GREEN}# Fund all wallets with staking amounts${NC}"
    echo "cd ../smart_contract && npx hardhat run scripts/deposit_from_all.js --network localhost"
    echo ""
    echo -e "${GREEN}# Check contract balance${NC}"
    echo "cd ../smart_contract && npx hardhat run scripts/check_balance.js --network localhost"
    
    print_section "DATA MANAGEMENT" "Working with test vs original data"
    echo -e "${GREEN}# File naming convention:${NC}"
    echo "  filename_test.json     # Self-generated test data (default)"
    echo "  filename_original.json # Original production data"
    echo ""
    echo -e "${GREEN}# Example data files:${NC}"
    echo "  bgpd_test.json / bgpd_original.json"
    echo "  trust_state_test.json / trust_state_original.json"
    echo "  rpki_verification_registry_test.json / rpki_verification_registry_original.json"
    echo ""
    echo -e "${GREEN}# Generate test data${NC}"
    echo "cd data_generator && python3 generate_test_data.py"
    
    print_section "DEVELOPMENT WORKFLOW" "Typical development commands"
    echo -e "${GREEN}# 1. Quick health check before coding${NC}"
    echo "python3 enhanced_pre_simulation.py"
    echo ""
    echo -e "${GREEN}# 2. Full system validation before major work${NC}"
    echo "python3 enhanced_pre_simulation.py --run-extended-tests"
    echo ""
    echo -e "${GREEN}# 3. Complete setup for fresh environment${NC}"
    echo "python3 enhanced_pre_simulation.py --setup --run-extended-tests"
    echo ""
    echo -e "${GREEN}# 4. Test specific component${NC}"
    echo "python3 run_test_suite.py 04_staking"
    echo ""
    echo -e "${GREEN}# 5. Validate with production data${NC}"
    echo "python3 enhanced_pre_simulation.py --run-extended-tests --data-source=original"
    
    print_section "DEBUGGING COMMANDS" "Troubleshooting and diagnostics"
    echo -e "${GREEN}# Check if Hardhat is running${NC}"
    echo "curl -X POST -H 'Content-Type: application/json' -d '{\"jsonrpc\":\"2.0\",\"method\":\"eth_blockNumber\",\"params\":[],\"id\":1}' http://localhost:8545"
    echo ""
    echo -e "${GREEN}# Kill existing Hardhat processes${NC}"
    echo "pkill -f hardhat"
    echo ""
    echo -e "${GREEN}# Check process status${NC}"
    echo "ps aux | grep hardhat"
    echo ""
    echo -e "${GREEN}# View detailed timing analysis${NC}"
    echo "cat ../timing_analysis.json | jq"
    echo ""
    echo -e "${GREEN}# Check system status${NC}"
    echo "./commands.sh status"
    
    print_section "QUICK COMMAND SHORTCUTS" "Fast access to common operations"
    echo -e "${GREEN}# Quick commands available:${NC}"
    echo "./commands.sh quick              # Quick validation test"
    echo "./commands.sh extended           # Extended comprehensive test"
    echo "./commands.sh setup              # Complete setup + validation"
    echo "./commands.sh setup-extended     # Complete setup + extended tests"
    echo "./commands.sh original           # Test with original data"
    echo "./commands.sh status             # System status check"
    echo "./commands.sh cleanup            # Kill Hardhat processes"
    echo "./commands.sh generate           # Generate test data"
    
    print_section "USEFUL ALIASES" "Add to your ~/.bashrc for quick access"
    echo -e "${GREEN}# Quick test aliases${NC}"
    echo "alias bgp-quick='cd ~/code/BGP-Sentry/tests && python3 enhanced_pre_simulation.py'"
    echo "alias bgp-extended='cd ~/code/BGP-Sentry/tests && python3 enhanced_pre_simulation.py --run-extended-tests'"
    echo "alias bgp-setup='cd ~/code/BGP-Sentry/tests && python3 enhanced_pre_simulation.py --setup'"
    echo "alias bgp-full='cd ~/code/BGP-Sentry/tests && python3 enhanced_pre_simulation.py --setup --run-extended-tests'"
    echo "alias bgp-original='cd ~/code/BGP-Sentry/tests && python3 enhanced_pre_simulation.py --data-source=original'"
    echo "alias bgp-help='cd ~/code/BGP-Sentry/tests && ./commands.sh help'"
    
    print_section "TEST SUITE BREAKDOWN" "Understanding the 18 individual test suites"
    echo -e "${GREEN}# Test Suite Categories:${NC}"
    echo "00_directory_structure    - Basic directory validation"
    echo "01_initialization_check   - System initialization tests"
    echo "02_blockchain_connectivity - Hardhat and blockchain tests"
    echo "03_sc_interface          - Smart contract interface tests"
    echo "04_staking               - Economic compensation tests"
    echo "05_data_registries       - Data generation and registry tests"
    echo "06_module_imports        - Python module import tests"
    echo "07_rpki_verification     - RPKI validation tests"
    echo "08_trust_engine          - Trust engine (RTE/ATE) tests"
    echo "09_trust_score_interface - Trust scoring tests"
    echo "10_bgp_data_validation   - BGP observation data tests"
    echo "11_bgp_attack_detection  - Attack detection algorithm tests"
    echo "12_consensus_readiness   - RPKI consensus preparation tests"
    echo "13_economic_tests        - Economic incentive tests"
    echo "14_blockchain_functionality - Full blockchain operation tests"
    echo "15_attack_scenarios      - Security attack simulation tests"
    echo "16_full_simulation       - End-to-end simulation tests"
    echo "17_setup_automation      - Setup utility tests"
    echo "18_master_runner         - Orchestration tests"
    
    print_section "LOG FILES AND OUTPUTS" "Important files to check"
    echo -e "${GREEN}# Timing and analysis files${NC}"
    echo "../timing_analysis.json          # Detailed performance metrics"
    echo ""
    echo -e "${GREEN}# Test data files${NC}"
    echo "../nodes/rpki_nodes/*/network_stack/bgpd_test.json"
    echo "../nodes/rpki_nodes/shared_blockchain_stack/shared_data/state/trust_state_test.json"
    echo "../nodes/rpki_nodes/shared_blockchain_stack/shared_data/shared_registry/*_test.json"
    echo ""
    echo -e "${GREEN}# Original data files${NC}"
    echo "../nodes/rpki_nodes/*/network_stack/bgpd_original.json"
    echo "../nodes/rpki_nodes/shared_blockchain_stack/shared_data/state/trust_state_original.json"
    echo "../nodes/rpki_nodes/shared_blockchain_stack/shared_data/shared_registry/*_original.json"
    
    echo -e "\n${CYAN}========================================${NC}"
    echo -e "${WHITE}💡 Tip: Run './commands.sh help' anytime to see this reference${NC}"
    echo -e "${WHITE}🎯 For comprehensive testing: './commands.sh setup-extended'${NC}"
    echo -e "${CYAN}========================================${NC}"
}

# Quick command functions
quick_test() {
    print_header "Running Quick Pre-Simulation Test"
    python3 enhanced_pre_simulation.py
}

extended_test() {
    print_header "Running Extended Comprehensive Test"
    echo -e "${YELLOW}This will run core validation + ALL 18 individual test suites${NC}"
    python3 enhanced_pre_simulation.py --run-extended-tests
}

setup_test() {
    print_header "Running Complete Setup + Validation"
    echo -e "${YELLOW}This will reset blockchain, start Hardhat, deploy contracts, fund wallets, generate data, and validate${NC}"
    python3 enhanced_pre_simulation.py --setup
}

setup_extended() {
    print_header "Running Complete Setup + Extended Testing"
    echo -e "${YELLOW}This will do EVERYTHING: Complete setup + comprehensive validation${NC}"
    echo -e "${YELLOW}This is the most thorough test possible!${NC}"
    python3 enhanced_pre_simulation.py --setup --run-extended-tests
}

test_original() {
    print_header "Testing with Original Data"
    python3 enhanced_pre_simulation.py --data-source=original
}

extended_original() {
    print_header "Extended Test with Original Data"
    python3 enhanced_pre_simulation.py --run-extended-tests --data-source=original
}

setup_blockchain() {
    print_header "Setting up Blockchain Environment"
    echo -e "${YELLOW}This will start Hardhat, deploy contracts, and fund wallets${NC}"
    echo -e "${YELLOW}Make sure no Hardhat process is running first!${NC}"
    read -p "Continue? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cd ../smart_contract
        echo -e "${GREEN}Starting Hardhat node in background...${NC}"
        npx hardhat node &
        HARDHAT_PID=$!
        echo "Hardhat PID: $HARDHAT_PID"
        
        sleep 5
        echo -e "${GREEN}Deploying contracts...${NC}"
        npx hardhat run scripts/deploy.js --network localhost
        
        echo -e "${GREEN}Funding wallets...${NC}"
        npx hardhat run scripts/deposit_from_all.js --network localhost
        
        echo -e "${GREEN}Setup complete! Hardhat running as PID $HARDHAT_PID${NC}"
        echo -e "${YELLOW}To stop: kill $HARDHAT_PID${NC}"
        cd ../tests
    fi
}

cleanup_blockchain() {
    print_header "Cleaning up Blockchain Processes"
    echo -e "${YELLOW}Killing all Hardhat processes...${NC}"
    pkill -f hardhat
    echo -e "${GREEN}Cleanup complete!${NC}"
}

generate_data() {
    print_header "Generating Test Data"
    if [ -d "data_generator" ]; then
        cd data_generator
        echo -e "${GREEN}Running data generator...${NC}"
        python3 generate_test_data.py
        cd ..
        echo -e "${GREEN}Test data generation complete!${NC}"
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
        echo -e "${YELLOW}   Start with: cd ../smart_contract && npx hardhat node${NC}"
    fi
    
    echo -e "\n${BLUE}Checking enhanced pre-simulation script...${NC}"
    if [ -f "enhanced_pre_simulation.py" ]; then
        echo -e "${GREEN}✅ Enhanced pre-simulation script available${NC}"
    else
        echo -e "${RED}❌ Enhanced pre-simulation script missing${NC}"
    fi
    
    echo -e "\n${BLUE}Checking test data files...${NC}"
    if [ -f "../nodes/rpki_nodes/as01/network_stack/bgpd.json" ]; then
        echo -e "${GREEN}✅ Test data files exist${NC}"
    else
        echo -e "${YELLOW}⚠️  Test data files not found${NC}"
        echo -e "${YELLOW}   Generate with: ./commands.sh generate${NC}"
    fi
    
    echo -e "\n${BLUE}Checking original data files...${NC}"
    if [ -f "../nodes/rpki_nodes/as01/network_stack/bgpd_original.json" ]; then
        echo -e "${GREEN}✅ Original data files exist${NC}"
    else
        echo -e "${YELLOW}⚠️  Original data files not found${NC}"
    fi
    
    echo -e "\n${BLUE}Virtual environment status...${NC}"
    if [ -n "$VIRTUAL_ENV" ]; then
        echo -e "${GREEN}✅ Virtual environment active: $VIRTUAL_ENV${NC}"
    else
        echo -e "${YELLOW}⚠️  No virtual environment detected${NC}"
    fi
    
    echo -e "\n${BLUE}Python packages...${NC}"
    python3 -c "
try:
    import requests, pytest
    print('✅ Required packages (requests, pytest) available')
except ImportError as e:
    print(f'❌ Missing packages: {e}')
"
    
    echo -e "\n${BLUE}Available test suites...${NC}"
    test_count=$(ls -d [0-9][0-9]_* 2>/dev/null | wc -l)
    echo -e "${GREEN}✅ ${test_count} individual test suites available${NC}"
}

# Main command dispatcher
case "$1" in
    "help"|"")
        show_help
        ;;
    "quick")
        quick_test
        ;;
    "extended")
        extended_test
        ;;
    "setup")
        setup_test
        ;;
    "setup-extended")
        setup_extended
        ;;
    "original")
        test_original
        ;;
    "extended-original")
        extended_original
        ;;
    "blockchain-setup")
        setup_blockchain
        ;;
    "cleanup")
        cleanup_blockchain
        ;;
    "generate")
        generate_data
        ;;
    "status")
        check_status
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo -e "${YELLOW}Available commands:${NC}"
        echo "  help, quick, extended, setup, setup-extended"
        echo "  original, extended-original, blockchain-setup"
        echo "  cleanup, generate, status"
        echo -e "${YELLOW}Run './commands.sh help' for detailed information${NC}"
        exit 1
        ;;
esac
