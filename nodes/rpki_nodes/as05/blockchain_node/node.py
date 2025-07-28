# Updated node.py structure
from services.rpki_observer_service.observer_main import RPKIObserverService
from services.consensus_service.consensus_main import ConsensusService

def main():
    # Simple 2-service architecture
    observer = RPKIObserverService(as_number=5)
    consensus = ConsensusService(as_number=5)
    
    observer.start_service()
    consensus.start_service()
    
    # Both services now handle everything!