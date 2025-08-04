#!/usr/bin/env python3
"""
Quick status checker for AI Mentor Application
"""

import requests
import json

def check_web_interface():
    """Check if web interface is running"""
    try:
        response = requests.get('http://localhost:8080/api/health', timeout=5)
        if response.status_code == 200:
            print("✅ Web Interface: Running on http://localhost:8080")
            return True
    except:
        pass
    
    # Try alternative ports
    for port in [8081, 8082, 5000]:
        try:
            response = requests.get(f'http://localhost:{port}/api/health', timeout=2)
            if response.status_code == 200:
                print(f"✅ Web Interface: Running on http://localhost:{port}")
                return True
        except:
            continue
    
    print("❌ Web Interface: Not accessible")
    return False

def check_ide_bridge():
    """Check if IDE bridge is running"""
    try:
        response = requests.get('http://localhost:8081/api/status', timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("✅ Universal IDE Bridge: Running on http://localhost:8081")
            print(f"   Active IDEs: {', '.join(data.get('active_ides', []))}")
            return True
    except:
        pass
    
    print("❌ Universal IDE Bridge: Not accessible")
    return False

def check_browser_extension():
    """Check browser extension availability"""
    import os
    base_dir = os.path.dirname(os.path.abspath(__file__))
    extension_dir = os.path.join(base_dir, 'browser_extension')
    manifest_path = os.path.join(extension_dir, 'manifest.json')
    
    if os.path.exists(manifest_path):
        print(f"✅ Browser Extension: Available at {extension_dir}")
        print("   Install via Chrome Extensions > Developer mode > Load unpacked")
        return True
    else:
        print("❌ Browser Extension: Not found")
        return False

def check_vscode_extension():
    """Check VS Code extension"""
    import os
    base_dir = os.path.dirname(os.path.abspath(__file__))
    extension_dir = os.path.join(base_dir, 'vscode_extension')
    
    if os.path.exists(extension_dir):
        print(f"✅ VS Code Extension: Available at {extension_dir}")
        return True
    else:
        print("❌ VS Code Extension: Not found")
        return False

def main():
    print("🔍 AI Mentor Application Status Check")
    print("=" * 50)
    
    services = 0
    
    if check_web_interface():
        services += 1
    
    if check_ide_bridge():
        services += 1
    
    if check_browser_extension():
        services += 1
    
    if check_vscode_extension():
        services += 1
    
    print("=" * 50)
    print(f"📊 Status: {services}/4 components available")
    
    if services >= 2:
        print("🎉 Application ready for use!")
        print("\n📖 Quick Start:")
        print("1. Install browser extension")
        print("2. Open any IDE (VS Code, IntelliJ, etc.)")
        print("3. Join a meeting")
        print("4. Use Ctrl+Alt+A for AI assistance")
    else:
        print("⚠️  Some components need attention")
    
    print("=" * 50)

if __name__ == "__main__":
    main()
