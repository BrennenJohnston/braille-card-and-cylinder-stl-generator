#!/usr/bin/env python3
"""
Test script for JavaScript liblouis integration in vercel_backend.py
"""

import sys
import os
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from vercel_backend import translate_with_liblouis_js, convert_liblouis_output_to_unicode
    print("✅ Successfully imported vercel_backend functions")
    
    # Test basic translation
    print("\n🧪 Testing basic translation...")
    try:
        result = translate_with_liblouis_js("Hello", "g2")
        print(f"✅ 'Hello' → '{result}'")
    except Exception as e:
        print(f"❌ Basic translation failed: {e}")
    
    # Test liblouis output conversion
    print("\n🧪 Testing liblouis output conversion...")
    try:
        result = convert_liblouis_output_to_unicode(",br5n5", "g2")
        print(f"✅ ',br5n5' → '{result}'")
    except Exception as e:
        print(f"❌ Output conversion failed: {e}")
    
    print("\n🎯 Test completed!")
    
except ImportError as e:
    print(f"❌ Failed to import vercel_backend: {e}")
    print("Make sure vercel_backend.py is in the same directory")
except Exception as e:
    print(f"❌ Unexpected error: {e}")
