#!/usr/bin/env python3
"""
Installation script for WeasyPrint and its dependencies.
This script helps install WeasyPrint for HTML to PDF conversion.
"""

import subprocess
import sys
import os

def install_package(package):
    """Install a package using pip"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✅ Successfully installed {package}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install {package}: {e}")
        return False

def main():
    print("🚀 Installing WeasyPrint for certificate generation...")
    print("=" * 50)
    
    # Install WeasyPrint
    success = install_package("weasyprint==62.2")
    
    if success:
        print("\n✅ WeasyPrint installation completed successfully!")
        print("\n📝 Note: On some systems, you may need to install additional system dependencies:")
        print("   - Ubuntu/Debian: sudo apt-get install build-essential python3-dev python3-pip python3-setuptools python3-wheel python3-cffi libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info")
        print("   - CentOS/RHEL: sudo yum install redhat-rpm-config python3-devel python3-pip python3-setuptools python3-wheel python3-cffi libffi-devel cairo pango gdk-pixbuf2")
        print("   - macOS: brew install cairo pango gdk-pixbuf libffi")
        print("\n🔧 If you encounter issues, please install the system dependencies first.")
    else:
        print("\n❌ WeasyPrint installation failed!")
        print("Please try installing manually: pip install weasyprint==62.2")

if __name__ == "__main__":
    main()
