"""
BGP Attack Detection Module

This module provides comprehensive BGP security analysis including:
- Prefix hijacking detection
- Subprefix hijacking detection  
- Route leak detection
- RPKI validation
- IRR validation
"""

from .attack_detector import BGPSecurityAnalyzer

__version__ = "1.0.0"
__all__ = ['BGPSecurityAnalyzer']
