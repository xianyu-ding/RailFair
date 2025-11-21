#!/usr/bin/env python3
"""
RailFair Day 6 - Main Runner
统计预计算系统主运行脚本
"""

import sys
import os
import subprocess
from datetime import datetime

# 颜色
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    """打印标题"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text}{Colors.END}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.END}\n")

def print_step(step: int, text: str):
    """打印步骤"""
    print(f"{Colors.BLUE}Step {step}: {text}{Colors.END}")

def print_success(text: str):
    """打印成功"""
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")

def print_warning(text: str):
    """打印警告"""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")

def print_error(text: str):
    """打印错误"""
    print(f"{Colors.RED}❌ {text}{Colors.END}")

def run_command(command: list, description: str) -> bool:
    """运行命令"""
    print(f"\n{Colors.BLUE}▶ {description}{Colors.END}")
    try:
        result = subprocess.run(
            command,
            capture_output=False,
            text=True,
            check=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Command failed: {e}")
        return False
    except FileNotFoundError:
        print_error(f"Command not found: {command[0]}")
        return False

def check_prerequisites() -> bool:
    """检查前置条件"""
    print_step(1, "Checking prerequisites")
    
    checks = []
    
    # 检查数据库
    db_path = "data/railfair.db"
    if os.path.exists(db_path):
        print_success(f"Database found: {db_path}")
        checks.append(True)
    else:
        print_error(f"Database not found: {db_path}")
        print("       Please ensure you have run Day 4's data collection first")
        checks.append(False)
    
    # 检查Python脚本
    scripts = [
        'create_statistics_tables.sql',
        'calculate_stats.py',
        'query_stats.py',
        'test_statistics.py'
    ]
    
    for script in scripts:
        if os.path.exists(script):
            print_success(f"Script found: {script}")
            checks.append(True)
        else:
            print_error(f"Script not found: {script}")
            checks.append(False)
    
    # 检查Python版本
    import sys
    version = sys.version_info
    if version.major >= 3 and version.minor >= 7:
        print_success(f"Python version: {version.major}.{version.minor}.{version.micro}")
        checks.append(True)
    else:
        print_error(f"Python version too old: {version.major}.{version.minor}")
        print("       Python 3.7+ required")
        checks.append(False)
    
    return all(checks)

def create_statistics_tables() -> bool:
    """创建统计表"""
    print_step(2, "Creating statistics tables")
    
    # 这个步骤会在calculate_stats.py中自动执行
    print_success("Will be created in next step")
    return True

def calculate_statistics() -> bool:
    """计算统计数据"""
    print_step(3, "Calculating statistics")
    
    return run_command(
        ['python3', 'calculate_stats.py', 'data/railfair.db'],
        "Running statistics calculation"
    )

def run_tests() -> bool:
    """运行测试"""
    print_step(4, "Running tests")
    
    return run_command(
        ['python3', 'test_statistics.py', 'data/railfair.db'],
        "Testing statistics system"
    )

def generate_reports() -> bool:
    """生成报告"""
    print_step(5, "Generating reports")
    
    # 运行查询演示
    success = run_command(
        ['python3', 'query_stats.py', 'data/railfair.db'],
        "Generating statistics report"
    )
    
    if success:
        # 保存报告到文件
        print("\n💾 Saving reports...")
        
        try:
            result = subprocess.run(
                ['python3', 'query_stats.py', 'data/railfair.db'],
                capture_output=True,
                text=True
            )
            
            report_file = f"data/statistics_report_{datetime.now().strftime('%Y%m%d')}.txt"
            with open(report_file, 'w') as f:
                f.write(result.stdout)
            
            print_success(f"Report saved: {report_file}")
            return True
            
        except Exception as e:
            print_warning(f"Could not save report: {e}")
            return True  # 不阻止流程
    
    return success

def print_summary():
    """打印总结"""
    print_header("📊 Day 6 Completion Summary")
    
    print("✅ Tasks Completed:")
    print("   1. Statistics tables created")
    print("   2. Route statistics calculated")
    print("   3. TOC statistics calculated")
    print("   4. Query interface implemented")
    print("   5. Cache system ready")
    print("   6. Tests passed")
    print("   7. Reports generated")
    
    print("\n📁 Generated Files:")
    print("   - data/railfair.db (updated with statistics)")
    print("   - data/statistics_report_*.txt")
    
    print("\n📈 Next Steps:")
    print("   1. Review statistics in the database")
    print("   2. Set up CRON job for automatic updates")
    print("   3. Move to Week 2: Prediction Engine Development")
    
    print("\n🔧 Useful Commands:")
    print("   # View statistics")
    print("   python3 query_stats.py")
    print()
    print("   # Recalculate statistics")
    print("   python3 calculate_stats.py")
    print()
    print("   # Run tests")
    print("   python3 test_statistics.py")
    
    print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 Day 6 completed successfully!{Colors.END}")

def main():
    """主函数"""
    print_header("🚂 RailFair Day 6 - Statistics System Setup")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    steps = [
        ("Prerequisites", check_prerequisites),
        ("Create Tables", create_statistics_tables),
        ("Calculate Statistics", calculate_statistics),
        ("Run Tests", run_tests),
        ("Generate Reports", generate_reports)
    ]
    
    for i, (name, func) in enumerate(steps, 1):
        try:
            success = func()
            if not success:
                print_error(f"Step {i} failed: {name}")
                print("\nPlease fix the issues and run again:")
                print(f"  python3 run_day6.py")
                return 1
        except KeyboardInterrupt:
            print_error("\n\nInterrupted by user")
            return 1
        except Exception as e:
            print_error(f"Step {i} error: {e}")
            import traceback
            traceback.print_exc()
            return 1
    
    # 打印总结
    print_summary()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
