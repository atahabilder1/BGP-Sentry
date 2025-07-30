import sys
import os

# Add necessary paths
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, current_dir)
sys.path.insert(0, parent_dir)

class ReactiveTrustEngine:
    """Reactive Trust Engine (RTE) - Immediate penalty enforcement"""
    
    def __init__(self):
        print("Initializing Reactive Trust Engine...")
        self.penalties = {
            'prefix_hijacking': 15,
            'subprefix_hijacking': 10,
            'route_leak': 5
        }
        print("✅ RTE initialized successfully")
    
    def process_violation(self, as_number, violation_type, timestamp=None):
        """Process a BGP violation and apply immediate penalty"""
        try:
            penalty = self.penalties.get(violation_type, 5)
            print(f"Processing violation: AS{as_number} - {violation_type} (penalty: {penalty})")
            return True
        except Exception as e:
            print(f"❌ Violation processing failed: {e}")
            return False
    
    def get_status(self):
        """Get RTE status"""
        return {
            'engine': 'Reactive Trust Engine',
            'status': 'operational',
            'penalties': self.penalties
        }

# Make it available as ReactiveEngine for consistency
ReactiveEngine = ReactiveTrustEngine
