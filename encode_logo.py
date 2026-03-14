#!/usr/bin/env python3
"""
Run this once locally to get the base64 string for LOGO_B64 env variable.
Usage: python encode_logo.py logo_cbis.png
"""
import base64
import sys

path = sys.argv[1] if len(sys.argv) > 1 else 'logo_cbis.png'
with open(path, 'rb') as f:
    b64 = base64.b64encode(f.read()).decode()

print(f'LOGO_B64={b64}')
print(f'\nLength: {len(b64)} chars')
print('Copy the LOGO_B64=... line to Railway/Render environment variables.')
