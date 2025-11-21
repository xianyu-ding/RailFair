#!/usr/bin/env python3
"""
快速测试 API 连接脚本
用于验证前后端连接是否正常
"""

import requests
import json
import sys

API_BASE = "http://localhost:8000"

def test_health():
    """测试健康检查端点"""
    print("🔍 测试健康检查...")
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        if response.status_code == 200:
            print("✅ 健康检查通过")
            print(f"   状态: {response.json().get('status', 'unknown')}")
            return True
        else:
            print(f"❌ 健康检查失败: HTTP {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到API服务器")
        print("   请确保后端正在运行: python3 -m api.app")
        return False
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

def test_prediction():
    """测试预测端点"""
    print("\n🔍 测试预测API...")
    try:
        payload = {
            "origin": "EUS",
            "destination": "MAN",
            "departure_date": "2025-12-25",
            "departure_time": "09:30",
            "include_fares": True
        }
        response = requests.post(
            f"{API_BASE}/api/predict",
            json=payload,
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            print("✅ 预测API工作正常")
            if "prediction" in data:
                pred = data["prediction"]
                print(f"   预测延迟: {pred.get('predicted_delay_minutes', 'N/A')} 分钟")
                print(f"   置信度: {pred.get('confidence', 'N/A')}")
            if "fares" in data and data["fares"]:
                fares = data["fares"]
                print(f"   票价数据: 已获取")
                if fares.get("cheapest"):
                    print(f"   最便宜票价: £{fares['cheapest'].get('price', 'N/A')}")
            return True
        else:
            print(f"❌ 预测API失败: HTTP {response.status_code}")
            print(f"   响应: {response.text[:200]}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到API服务器")
        return False
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

def main():
    print("=" * 50)
    print("RailFair API 连接测试")
    print("=" * 50)
    print(f"API地址: {API_BASE}\n")
    
    health_ok = test_health()
    if not health_ok:
        print("\n⚠️  请先启动后端服务器:")
        print("   python3 -m api.app")
        print("   或")
        print("   ./start_api.sh")
        sys.exit(1)
    
    prediction_ok = test_prediction()
    
    print("\n" + "=" * 50)
    if health_ok and prediction_ok:
        print("✅ 所有测试通过！API 工作正常")
        print("\n📝 下一步:")
        print("   1. 确保前端配置指向 http://localhost:8000")
        print("   2. 启动前端服务器: ./start_frontend.sh")
        print("   3. 在浏览器中打开前端页面进行查询")
    else:
        print("❌ 部分测试失败，请检查后端日志")
    print("=" * 50)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n测试已取消")
        sys.exit(0)

