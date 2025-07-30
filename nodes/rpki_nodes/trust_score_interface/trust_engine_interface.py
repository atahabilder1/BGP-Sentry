#!/usr/bin/env python3
"""
Trust Engine Interface - Working Version
"""

import sys
import os

# Add trust engine path
TRUST_ENGINE_PATH = "/home/anik/code/BGP-Sentry/trust_engine"
sys.path.insert(0, TRUST_ENGINE_PATH)
sys.path.insert(0, os.path.join(TRUST_ENGINE_PATH, 'reactive_trust_engine'))
sys.path.insert(0, os.path.join(TRUST_ENGINE_PATH, 'adaptive_trust_engine'))

class TrustEngineInterface:
    """Working interface for trust engines"""
    
    def __init__(self):
        self.rte = None
        self.ate = None
        self.coordinator = None
        self._initialize_engines()
    
    def _initialize_engines(self):
        """Initialize engines with fixed imports"""
        
        # Load RTE
        try:
            from reactive_trust_engine_fixed import ReactiveTrustEngine
            self.rte = ReactiveTrustEngine()
            print("✅ Reactive Trust Engine loaded")
        except Exception as e:
            print(f"❌ RTE loading failed: {e}")
        
        # Load ATE
        try:
            from adaptive_trust_engine_fixed import AdaptiveTrustEngine
            self.ate = AdaptiveTrustEngine()
            print("✅ Adaptive Trust Engine loaded")
        except Exception as e:
            print(f"❌ ATE loading failed: {e}")
        
        # Load Coordinator
        try:
            from main_trust_coordinator_fixed import TrustCoordinator
            self.coordinator = TrustCoordinator()
            print("✅ Trust Coordinator loaded")
        except Exception as e:
            print(f"❌ Coordinator loading failed: {e}")
    
    def test_rte_separately(self):
        """Test RTE functionality independently"""
        print("\n🔧 Testing Reactive Trust Engine Separately:")
        
        if not self.rte:
            print("  ❌ RTE not available")
            return False
        
        try:
            # Test violation processing
            test_cases = [
                {'as': 65001, 'type': 'prefix_hijacking'},
                {'as': 65002, 'type': 'subprefix_hijacking'},
                {'as': 65003, 'type': 'route_leak'}
            ]
            
            for case in test_cases:
                result = self.rte.process_violation(case['as'], case['type'])
                status = "✅ Success" if result else "❌ Failed"
                print(f"  {status}: AS{case['as']} - {case['type']}")
            
            # Test status
            status = self.rte.get_status()
            print(f"  📊 RTE Status: {status}")
            
            return True
            
        except Exception as e:
            print(f"  ❌ RTE testing failed: {e}")
            return False
    
    def test_ate_separately(self):
        """Test ATE functionality independently"""
        print("\n🔧 Testing Adaptive Trust Engine Separately:")
        
        if not self.ate:
            print("  ❌ ATE not available")
            return False
        
        try:
            # Test trust score evaluation
            test_as_numbers = [65001, 65002, 65003]
            
            for as_number in test_as_numbers:
                score = self.ate.evaluate_trust_score(as_number)
                print(f"  ✅ AS{as_number} trust score: {score}")
            
            # Test behavioral metrics
            metrics = self.ate.calculate_behavioral_metrics(65001)
            print(f"  📊 Behavioral metrics: {metrics}")
            
            # Test status
            status = self.ate.get_status()
            print(f"  📊 ATE Status: {status}")
            
            return True
            
        except Exception as e:
            print(f"  ❌ ATE testing failed: {e}")
            return False
    
    def test_coordinator(self):
        """Test coordinator functionality"""  
        print("\n🔧 Testing Trust Coordinator:")
        
        if not self.coordinator:
            print("  ❌ Coordinator not available")
            return False
        
        try:
            # Test violation processing through coordinator
            result = self.coordinator.process_violation(65001, 'prefix_hijacking')
            print(f"  ✅ Coordinator violation processing: {result}")
            
            # Test trust score evaluation through coordinator
            score = self.coordinator.evaluate_trust_score(65001)
            print(f"  ✅ Coordinator trust evaluation: {score}")
            
            # Test getting cached score
            cached_score = self.coordinator.get_trust_score(65001)
            print(f"  ✅ Cached trust score: {cached_score}")
            
            # Test system status
            status = self.coordinator.get_system_status()
            print(f"  📊 System Status: {status}")
            
            return True
            
        except Exception as e:
            print(f"  ❌ Coordinator testing failed: {e}")
            return False

def main():
    print("=== Trust Engine Interface Test ===")
    
    interface = TrustEngineInterface()
    
    # Test each engine separately
    rte_ok = interface.test_rte_separately()
    ate_ok = interface.test_ate_separately()  
    coord_ok = interface.test_coordinator()
    
    print(f"\n=== Test Results ===")
    print(f"RTE: {'✅ Working' if rte_ok else '❌ Failed'}")
    print(f"ATE: {'✅ Working' if ate_ok else '❌ Failed'}")
    print(f"Coordinator: {'✅ Working' if coord_ok else '❌ Failed'}")

if __name__ == "__main__":
    main()
