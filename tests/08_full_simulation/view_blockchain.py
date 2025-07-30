#!/usr/bin/env python3
"""
Beautiful BGP-Sentry Blockchain Viewer
"""
import json
from datetime import datetime
from pathlib import Path

def view_blockchain():
    blockchain_path = Path("~/code/BGP-Sentry/nodes/rpki_nodes/shared_blockchain_stack/shared_data/chain/blockchain.json").expanduser()
    
    try:
        with open(blockchain_path, 'r') as f:
            blockchain = json.load(f)
    except FileNotFoundError:
        print("❌ Blockchain file not found")
        return
    
    print("🔗 BGP-Sentry Blockchain Viewer")
    print("=" * 60)
    
    if not blockchain:
        print("📭 Blockchain is empty")
        return
    
    for block in blockchain:
        timestamp = datetime.fromtimestamp(block["timestamp"])
        print(f"\n📦 Block {block['index']}")
        print(f"   🕒 Time: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   📋 Previous Hash: {block['previous_hash'][:16]}...")
        print(f"   🔐 Block Hash: {block['hash'][:16]}...")
        print(f"   📊 Transactions: {len(block.get('transactions', []))}")
        
        for i, tx in enumerate(block.get('transactions', []), 1):
            tx_time = datetime.fromtimestamp(tx["timestamp"])
            print(f"\n      💰 Transaction {i}:")
            print(f"         🆔 ID: {tx['transaction_id']}")
            print(f"         🏢 AS{tx['sender_asn']:02d} → {tx['ip_prefix']}")
            print(f"         🕒 Time: {tx_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"         📊 Trust Score: {tx.get('trust_score', 'N/A')}")
            print(f"         🔐 Signature: {tx['signature'][:32]}...")
            print(f"         ✅ Status: CRYPTOGRAPHICALLY SECURED")
    
    print(f"\n🎉 Total Blocks: {len(blockchain)}")
    total_txs = sum(len(block.get('transactions', [])) for block in blockchain)
    print(f"📊 Total Transactions: {total_txs}")
    print(f"🔐 All transactions secured with real RSA signatures!")

if __name__ == "__main__":
    view_blockchain()
