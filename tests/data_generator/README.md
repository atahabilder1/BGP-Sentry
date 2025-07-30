# BGP Test Data Generator

## Overview
This tool generates BGP test data for RPKI nodes by reading configurations from the shared registry.

## Location
`/home/anik/code/BGP-Sentry/tests/data_generator/generatedata.py`

## Usage
```bash
cd /home/anik/code/BGP-Sentry/tests/data_generator/
python3 generatedata.py
```

## What it does
1. **Reads configurations** from `nodes/rpki_nodes/shared_blockchain_stack/shared_data/shared_registry/`
2. **Discovers RPKI node folders** in `nodes/rpki_nodes/`
3. **Shows generation plan** with target folders and settings
4. **Asks for confirmation** before writing data
5. **Generates BGP observations** for each RPKI router
6. **Writes bgpd.json files** to each AS network_stack directory

## Generated Data Structure
Each `bgpd.json` contains:
```json
{
  "bgp_announcements": [
    {
      "sender_asn": 2,
      "announced_prefix": "192.168.2.0/24",
      "as_path": [2],
      "timestamp": "2025-07-30T15:30:00Z"
    }
  ]
}
```

## Configuration Sources
- **AS relationships**: `as_relationships.json`
- **Prefix ownership**: `public_network_registry.json`
- **Network topology**: Extracted from existing configs

## Output Locations
Data is written to: `nodes/rpki_nodes/as{XX}/network_stack/bgpd.json`

## Safety Features
- Shows exactly what will be written before proceeding
- Requires explicit 'y' confirmation
- Reports success/failure for each AS
- Validates directory structure before writing
