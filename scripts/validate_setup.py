#!/usr/bin/env python3
"""Quick environment validation script for Day 1."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test that all core packages can be imported."""
    print("🔍 Testing package imports...")
    
    packages = [
        ("pandas", "Data processing"),
        ("numpy", "Numerical computing"),
        ("requests", "HTTP client"),
        ("dotenv", "Environment variables"),
        ("loguru", "Logging"),
        ("stomp", "STOMP protocol (Darwin API)"),
    ]
    
    failed = []
    for package, description in packages:
        try:
            __import__(package)
            print(f"  ✅ {package:15} - {description}")
        except ImportError:
            print(f"  ❌ {package:15} - {description} (MISSING)")
            failed.append(package)
    
    if failed:
        print(f"\n❌ Missing packages: {', '.join(failed)}")
        print("   Run: pip install -r requirements.txt")
        return False
    
    print("\n✅ All core packages installed!")
    return True


def test_project_structure():
    """Verify project directory structure."""
    print("\n🔍 Testing project structure...")
    
    required_dirs = [
        "data/raw/hsp",
        "data/raw/darwin",
        "data/processed",
        "data/cache",
        "src/data_collection",
        "src/utils",
        "models/saved_models",
        "logs",
        "configs"
    ]
    
    missing = []
    for dir_path in required_dirs:
        full_path = project_root / dir_path
        if full_path.exists():
            print(f"  ✅ {dir_path}")
        else:
            print(f"  ❌ {dir_path} (MISSING)")
            missing.append(dir_path)
    
    if missing:
        print(f"\n❌ Missing directories: {len(missing)}")
        return False
    
    print("\n✅ Project structure verified!")
    return True


def test_configuration():
    """Test configuration loading."""
    print("\n🔍 Testing configuration...")
    
    try:
        from src.utils import Config
        
        print(f"  ✅ Config module loaded")
        print(f"  📁 Project root: {Config.get_summary()['project_root']}")
        print(f"  🔗 HSP URL: {Config.HSP_SERVICE_METRICS_URL}")
        
        # Check credentials
        creds = Config.validate()
        print(f"\n  🔑 Credentials status:")
        for service, status in creds.items():
            icon = "✅" if status else "⚠️ "
            print(f"     {icon} {service}")
        
        if not any(creds.values()):
            print("\n  ⚠️  No API credentials configured yet")
            print("     Edit .env file with your National Rail API credentials")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Configuration error: {e}")
        return False


def main():
    """Run all validation tests."""
    print("=" * 60)
    print("  UK Rail Delay Predictor - Day 1 Validation")
    print("=" * 60)
    
    results = [
        test_imports(),
        test_project_structure(),
        test_configuration()
    ]
    
    print("\n" + "=" * 60)
    if all(results):
        print("  ✅ Day 1 Setup Complete!")
        print("=" * 60)
        print("\n📋 Next Steps:")
        print("  1. Edit .env file with your National Rail API credentials")
        print("  2. Run: python scripts/test_api_connection.py")
        print("  3. Start Day 2: Data collection pipeline")
        return 0
    else:
        print("  ❌ Setup Incomplete")
        print("=" * 60)
        print("\n  Please fix the issues above and run again.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
