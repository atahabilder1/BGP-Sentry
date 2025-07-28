#!/usr/bin/env python3
"""
Test Original Adaptive Trust Engine
"""

import sys
sys.path.append('../utils_common/trust_engine')
sys.path.append('../utils_common')

def test_original_ate():
    """Test the original ATE functionality"""
    
    print("🧪 Testing Original Adaptive Trust Engine...")
    
    try:
        # Import the original ATE
        from adaptive_trust_engine.adaptive_trust_engine import AdaptiveTrustEngine
        
        print("✅ Successfully imported AdaptiveTrustEngine")
        
        # Initialize ATE
        ate = AdaptiveTrustEngine()
        print("✅ Successfully initialized AdaptiveTrustEngine")
        
        # Test monthly evaluation
        print("🔄 Testing monthly evaluation...")
        ate.run_monthly_evaluation()
        print("✅ Monthly evaluation completed!")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False
    except Exception as e:
        print(f"⚠️  Execution error: {e}")
        print("🔧 ATE needs more configuration...")
        return False

if __name__ == "__main__":
    success = test_original_ate()
    if success:
        print("\n🎉 Original ATE is fully functional!")
    else:
        print("\n🔧 Need to fix remaining issues...")
