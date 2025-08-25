#!/usr/bin/env python3
"""
Installation script for PDF generation libraries.
This script helps install multiple PDF libraries for better certificate generation.
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
    print("🚀 Installing PDF generation libraries for certificate generation...")
    print("=" * 60)
    
    # Install PDF libraries
    packages = [
        "weasyprint==62.2",
        "pdfkit==1.0.0",
        "reportlab==4.0.4"
    ]
    
    success_count = 0
    for package in packages:
        if install_package(package):
            success_count += 1
    
    print(f"\n📊 Installation Summary:")
    print(f"✅ Successfully installed: {success_count}/{len(packages)} packages")
    
    if success_count == len(packages):
        print("\n🎉 All PDF libraries installed successfully!")
        print("\n📝 PDF Generation Methods Available:")
        print("   1. WeasyPrint - HTML to PDF with CSS support")
        print("   2. pdfkit - HTML to PDF using wkhtmltopdf")
        print("   3. ReportLab - Native PDF generation with proper text formatting")
        print("\n🔧 The certificate generator will automatically use the best available method.")
    else:
        print(f"\n⚠️  Some packages failed to install. The system will use available methods.")
    
    print("\n📋 System Dependencies (if needed):")
    print("   - For pdfkit: Install wkhtmltopdf from https://wkhtmltopdf.org/")
    print("   - For WeasyPrint: Install system dependencies if needed")
    print("   - ReportLab: No additional system dependencies required")
    
    print("\n🔧 If you encounter issues:")
    print("   1. Install system dependencies first")
    print("   2. Try installing packages individually")
    print("   3. Check your Python environment")

if __name__ == "__main__":
    main()
