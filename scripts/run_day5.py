#!/usr/bin/env python3
"""
Day 5: 数据验证与元数据收集 - 主运行脚本
"""

import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime
import time

def print_header(title):
    """打印格式化标题"""
    print("\n" + "=" * 70)
    print(f"🚆 {title}")
    print("=" * 70)

def run_command(cmd, description):
    """运行命令并显示状态"""
    print(f"\n📌 {description}...")
    print(f"   Command: {' '.join(cmd)}")
    
    try:
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        elapsed = time.time() - start_time
        
        if result.stdout:
            print(result.stdout)
        
        print(f"✅ {description} completed in {elapsed:.1f}s")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed!")
        if e.stderr:
            print(f"   Error: {e.stderr}")
        return False
    except FileNotFoundError:
        print(f"❌ Command not found: {cmd[0]}")
        return False

def check_database_exists():
    """检查数据库是否存在"""
    db_path = Path("data/railfair.db")
    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        print("   Please run data collection first (Day 3-4 scripts)")
        return False
    
    # 获取数据库大小
    size_mb = db_path.stat().st_size / (1024 * 1024)
    print(f"✅ Database found: {db_path} ({size_mb:.1f} MB)")
    return True

def check_dependencies():
    """检查Python依赖"""
    required_modules = ['sqlite3', 'json', 'datetime', 'pathlib']
    missing = []
    
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing.append(module)
    
    if missing:
        print(f"❌ Missing Python modules: {', '.join(missing)}")
        return False
    
    print("✅ All required Python modules available")
    return True

def main():
    """主函数"""
    print_header("Day 5: Data Validation & Metadata Collection")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 检查前置条件
    print("\n🔍 Pre-flight checks...")
    print("-" * 40)
    
    if not check_database_exists():
        sys.exit(1)
    
    if not check_dependencies():
        sys.exit(1)
    
    # 确保data目录存在
    Path("data").mkdir(exist_ok=True)
    
    # 步骤1: 运行数据验证
    print_header("Step 1: Data Validation")
    
    validation_success = run_command(
        [sys.executable, "validate_data.py", 
         "--db", "data/railfair.db",
         "--output", "data/validation_report_day5.txt",
         "--json", "data/validation_results_day5.json"],
        "Running comprehensive data validation"
    )
    
    if not validation_success:
        print("⚠️ Validation failed, but continuing with metadata collection...")
    
    # 步骤2: 收集元数据
    print_header("Step 2: Metadata Collection")
    
    metadata_success = run_command(
        [sys.executable, "collect_metadata.py"],
        "Loading TOC, station, and route metadata"
    )
    
    if not metadata_success:
        print("⚠️ Metadata collection had issues")
    
    # 步骤3: 重新验证（包含元数据）
    if metadata_success:
        print_header("Step 3: Re-validation with Metadata")
        
        run_command(
            [sys.executable, "validate_data.py",
             "--db", "data/railfair.db",
             "--output", "data/validation_report_enriched.txt",
             "--json", "data/validation_results_enriched.json"],
            "Re-validating with enriched metadata"
        )
    
    # 生成最终总结
    print_header("Day 5 Summary")
    
    # 读取验证结果
    validation_report_path = Path("data/validation_report_day5.txt")
    if validation_report_path.exists():
        with open(validation_report_path, 'r') as f:
            lines = f.readlines()
            # 提取关键指标
            for line in lines:
                if "Total Records:" in line or "Quality Score:" in line or "Success Rate:" in line:
                    print(line.strip())
    
    # 显示生成的文件
    print("\n📁 Generated Files:")
    print("-" * 40)
    
    output_files = [
        "data/validation_report_day5.txt",
        "data/validation_results_day5.json",
        "data/metadata_report.txt",
        "data/validation_report_enriched.txt"
    ]
    
    for file_path in output_files:
        if Path(file_path).exists():
            size_kb = Path(file_path).stat().st_size / 1024
            print(f"  ✅ {file_path} ({size_kb:.1f} KB)")
        else:
            print(f"  ❌ {file_path} (not created)")
    
    # 最终状态
    print("\n" + "=" * 70)
    
    if validation_success and metadata_success:
        print("✅ Day 5 COMPLETED SUCCESSFULLY!")
        print("\n🎯 Week 1 Milestones Check:")
        print("  ✅ Database with historical records")
        print("  ✅ Route coverage analysis complete") 
        print("  ✅ Data quality validation complete")
        print("  ✅ Metadata enrichment complete")
        print("\n📊 Next Steps (Day 6-7):")
        print("  1. Create statistics pre-calculation tables")
        print("  2. Calculate route performance metrics")
        print("  3. Build caching layer for fast queries")
        print("  4. Generate performance dashboard")
    else:
        print("⚠️ Day 5 completed with warnings")
        print("   Please review the reports for details")
    
    print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)


if __name__ == "__main__":
    main()
