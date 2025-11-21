#!/usr/bin/env python
"""
RailFair API 演示脚本
======================

演示FastAPI后端的核心功能：
1. 健康检查
2. 延误预测
3. 票价对比
4. 推荐生成
5. 反馈提交
6. 速率限制
7. 错误处理

运行: python api/demo.py 或 python -m api.demo
"""

import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any

# API配置
BASE_URL = "http://localhost:8000"
SESSION = requests.Session()


def print_section(title: str):
    """打印分节标题"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def print_json(data: Dict[Any, Any], indent: int = 2):
    """美化打印JSON"""
    print(json.dumps(data, indent=indent, ensure_ascii=False))


def health_check():
    """演示健康检查"""
    print_section("1. 健康检查")
    
    response = SESSION.get(f"{BASE_URL}/health")
    
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"服务状态: {data['status']}")
        print(f"版本: {data['version']}")
        print(f"时间戳: {data['timestamp']}")
        print(f"数据库: {'✅ 可用' if data.get('database', False) else '❌ 不可用'}")
        
        # 如果有其他字段，也显示出来
        if 'services' in data:
            print(f"\n服务状态:")
            for service, status in data['services'].items():
                print(f"  - {service}: {status}")
        if 'uptime_seconds' in data:
            print(f"运行时长: {data['uptime_seconds']:.2f}秒")
    else:
        print("❌ 健康检查失败")
        print_json(response.json())


def predict_delay():
    """演示延误预测"""
    print_section("2. 延误预测")
    
    # 明天的火车
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    payload = {
        "origin": "EUS",
        "destination": "MAN",
        "departure_date": tomorrow,
        "departure_time": "09:30",
        "include_fares": True
    }
    
    print("请求:")
    print_json(payload)
    
    print("\n发送请求...")
    start = time.time()
    response = SESSION.post(f"{BASE_URL}/api/predict", json=payload)
    duration = time.time() - start
    
    print(f"\n状态码: {response.status_code}")
    print(f"响应时间: {duration*1000:.2f}ms")
    
    if response.status_code == 200:
        data = response.json()
        
        print(f"\n📊 预测结果:")
        print(f"  请求ID: {data['request_id']}")
        
        pred = data['prediction']
        print(f"\n  延误预测:")
        print(f"    - 预测延误: {pred.get('delay_minutes', pred.get('predicted_delay_minutes', 'N/A'))} 分钟")
        print(f"    - 置信度: {pred['confidence']:.1%}")
        print(f"    - 延误等级: {pred.get('category', pred.get('delay_category', 'N/A'))}")
        print(f"    - 准点概率: {pred['on_time_probability']:.1%}")
        print(f"    - 历史数据: {pred.get('sample_size', pred.get('historical_data_points', 'N/A'))} 条")
        if pred.get('confidence_level'):
            print(f"    - 置信度等级: {pred['confidence_level']}")
        
        if data.get('fares'):
            fares = data['fares']
            print(f"\n  💰 票价对比:")
            
            # 检查是否有任何价格数据
            has_any_price = (fares.get('advance_price') or 
                           fares.get('off_peak_price') or 
                           fares.get('anytime_price') or
                           (fares.get('advance') and isinstance(fares['advance'], dict)) or
                           (fares.get('off_peak') and isinstance(fares['off_peak'], dict)) or
                           (fares.get('anytime') and isinstance(fares['anytime'], dict)))
            
            if not has_any_price:
                print(f"    ❌ 不可用（暂无真实票价数据）")
            else:
                # 支持两种格式：直接字段或嵌套对象
                if fares.get('advance_price'):
                    print(f"    - 提前票: £{fares['advance_price']:.2f}")
                elif fares.get('advance') and isinstance(fares['advance'], dict):
                    print(f"    - 提前票: £{fares['advance'].get('price', 'N/A'):.2f}")
                
                if fares.get('off_peak_price'):
                    print(f"    - 非高峰: £{fares['off_peak_price']:.2f}")
                elif fares.get('off_peak') and isinstance(fares['off_peak'], dict):
                    print(f"    - 非高峰: £{fares['off_peak'].get('price', 'N/A'):.2f}")
                
                if fares.get('anytime_price'):
                    print(f"    - 随时票: £{fares['anytime_price']:.2f}")
                elif fares.get('anytime') and isinstance(fares['anytime'], dict):
                    print(f"    - 随时票: £{fares['anytime'].get('price', 'N/A'):.2f}")
                    
                if fares.get('cheapest_type'):
                    cheapest_price = fares.get('cheapest_price')
                    if not cheapest_price:
                        # 尝试从各个票价中找最便宜的
                        prices = {}
                        if fares.get('advance_price'):
                            prices['advance'] = fares['advance_price']
                        if fares.get('off_peak_price'):
                            prices['off_peak'] = fares['off_peak_price']
                        if fares.get('anytime_price'):
                            prices['anytime'] = fares['anytime_price']
                        if prices:
                            cheapest_price = min(prices.values())
                    
                    print(f"\n    最便宜: {fares['cheapest_type']} (£{cheapest_price:.2f})" if cheapest_price else f"\n    最便宜: {fares['cheapest_type']}")
                    if fares.get('savings_amount'):
                        print(f"    可节省: £{fares['savings_amount']:.2f} ({fares.get('savings_percentage', 0):.1f}%)")
        else:
            print(f"\n  💰 票价对比:")
            print(f"    ❌ 不可用（暂无真实票价数据）")
        
        if data.get('recommendations'):
            print(f"\n  💡 推荐建议:")
            for i, rec in enumerate(data['recommendations'][:3], 1):
                rec_type = rec.get('type', rec.get('option', 'N/A'))
                print(f"\n    {i}. [{rec_type}] {rec['title']}")
                print(f"       {rec['description']}")
                score = rec.get('score', 0)
                # 支持0-10和0-100两种评分格式
                if score <= 10:
                    print(f"       评分: {score:.1f}/10")
                else:
                    print(f"       评分: {score:.0f}/100")
        
        print(f"\n  📈 元数据:")
        meta = data.get('metadata', {})
        if meta:
            if 'processing_time_ms' in meta:
                print(f"    - 处理时间: {meta['processing_time_ms']:.2f}ms")
            if 'cache_hit' in meta:
                print(f"    - 缓存命中: {meta['cache_hit']}")
            if 'client_fingerprint' in meta:
                print(f"    - 客户端指纹: {meta['client_fingerprint']}")
            if 'route' in meta:
                print(f"    - 路线: {meta['route']}")
            if 'api_version' in meta:
                print(f"    - API版本: {meta['api_version']}")
        
        # 返回request_id用于后续演示
        return data['request_id']
    else:
        print("❌ 预测失败")
        print_json(response.json())
        return None


def submit_feedback(request_id: str):
    """演示反馈提交"""
    print_section("3. 反馈提交")
    
    payload = {
        "request_id": request_id,
        "actual_delay_minutes": 15,
        "was_cancelled": False,
        "rating": 4,
        "comment": "预测相当准确，帮助我做出了正确的出行决策。"
    }
    
    print("请求:")
    print_json(payload)
    
    print("\n发送反馈...")
    response = SESSION.post(f"{BASE_URL}/api/feedback", json=payload)
    
    print(f"\n状态码: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 反馈提交成功!")
        print(f"  反馈ID: {data['feedback_id']}")
        print(f"  接收时间: {data['received_at']}")
        print(f"  消息: {data['message']}")
    else:
        print("❌ 反馈提交失败")
        print_json(response.json())


def test_validation_errors():
    """演示输入验证"""
    print_section("4. 输入验证测试")
    
    test_cases = [
        {
            "name": "无效的CRS代码（小写）",
            "payload": {
                "origin": "eus",  # 应该大写
                "destination": "MAN",
                "departure_date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
                "departure_time": "09:30"
            }
        },
        {
            "name": "过去的日期",
            "payload": {
                "origin": "EUS",
                "destination": "MAN",
                "departure_date": "2024-01-01",  # 过去
                "departure_time": "09:30"
            }
        },
        {
            "name": "无效的时间格式",
            "payload": {
                "origin": "EUS",
                "destination": "MAN",
                "departure_date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
                "departure_time": "9:30 AM"  # 应该24小时制
            }
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n测试 {i}: {test['name']}")
        response = SESSION.post(f"{BASE_URL}/api/predict", json=test['payload'])
        
        if response.status_code == 422:
            print("✅ 正确识别验证错误")
            errors = response.json()
            print(f"  错误详情: {errors['detail'][0]['msg']}")
        else:
            print(f"❌ 未预期的响应: {response.status_code}")


def test_rate_limiting():
    """演示速率限制"""
    print_section("5. 速率限制测试")
    
    print("⚠️  警告: 此测试将发送大量请求以触发速率限制")
    print("这可能需要几秒钟...\n")
    
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    payload = {
        "origin": "EUS",
        "destination": "MAN",
        "departure_date": tomorrow,
        "departure_time": "09:30",
        "include_fares": False  # 加快请求
    }
    
    # 发送请求直到被限制
    success_count = 0
    rate_limited = False
    
    print("发送请求中", end="", flush=True)
    
    for i in range(105):  # 超过100次限制
        response = SESSION.post(f"{BASE_URL}/api/predict", json=payload)
        
        if response.status_code == 200:
            success_count += 1
            if i % 20 == 0:
                print(".", end="", flush=True)
        elif response.status_code == 429:
            rate_limited = True
            print(f"\n\n✅ 速率限制触发!")
            print(f"  成功请求: {success_count}")
            print(f"  限制触发于: 第{i+1}次请求")
            error = response.json()
            print(f"  错误消息: {error['detail']}")
            break
    
    if not rate_limited:
        print(f"\n\n⚠️  未触发速率限制")
        print(f"  完成请求: {success_count}")


def test_statistics():
    """演示统计信息"""
    print_section("6. 统计信息")
    
    response = SESSION.get(f"{BASE_URL}/api/stats")
    
    if response.status_code == 200:
        data = response.json()
        print("📊 API使用统计:")
        print(f"  总请求数: {data.get('total_requests', 0)}")
        print(f"  唯一客户端: {data.get('unique_clients', 0)}")
        print(f"  总反馈数: {data.get('total_feedback', 0)}")
        if data.get('total_feedback', 0) > 0:
            print(f"  平均评分: {data.get('average_rating', 0):.1f}/5")
        print(f"  API版本: {data.get('api_version', data.get('version', 'N/A'))}")
        if data.get('timestamp'):
            print(f"  时间戳: {data['timestamp']}")
        
        # 兼容旧版本API的字段
        if 'total_errors' in data:
            print(f"  总错误数: {data['total_errors']}")
        if 'uptime_hours' in data:
            print(f"  运行时长: {data['uptime_hours']:.2f} 小时")
        if 'error_rate' in data:
            print(f"  错误率: {data['error_rate']:.2f}%")
    else:
        print("❌ 获取统计失败")
        print_json(response.json())


def test_documentation():
    """测试文档端点"""
    print_section("7. API文档")
    
    endpoints = {
        "Swagger UI": f"{BASE_URL}/docs",
        "ReDoc": f"{BASE_URL}/redoc",
        "OpenAPI Schema": f"{BASE_URL}/openapi.json"
    }
    
    print("📚 可用文档:")
    for name, url in endpoints.items():
        response = SESSION.get(url)
        if response.status_code == 200:
            print(f"  ✅ {name}: {url}")
        else:
            print(f"  ❌ {name}: 不可用")


def main():
    """主演示函数"""
    print("\n" + "="*60)
    print("  🚄 RailFair API 功能演示")
    print("="*60)
    print(f"\nAPI服务器: {BASE_URL}")
    print("请确保API服务器正在运行...")
    
    try:
        # 检查服务器是否运行
        response = SESSION.get(f"{BASE_URL}/health", timeout=2)
        if response.status_code != 200:
            print("\n❌ 服务器未正常运行")
            return
    except requests.exceptions.RequestException:
        print("\n❌ 无法连接到服务器")
        print("请先启动服务器: python api/app.py 或 python -m api.app")
        return
    
    print("✅ 服务器运行正常\n")
    
    # 检查速率限制状态，如果被限制则重置
    try:
        stats_response = SESSION.get(f"{BASE_URL}/api/stats")
        if stats_response.status_code == 200:
            stats = stats_response.json()
            if stats.get('total_requests', 0) >= 100:
                print("⚠️  检测到速率限制可能已触发，正在重置...")
                reset_response = SESSION.post(f"{BASE_URL}/api/reset-rate-limit")
                if reset_response.status_code == 200:
                    print("✅ 速率限制已重置\n")
                else:
                    print("⚠️  无法重置速率限制，可能需要等待1分钟\n")
    except Exception as e:
        print(f"⚠️  检查速率限制状态时出错: {e}\n")
    
    # 运行演示
    try:
        # 1. 健康检查
        health_check()
        time.sleep(1)
        
        # 2. 预测
        request_id = predict_delay()
        time.sleep(1)
        
        # 3. 反馈（如果有request_id）
        if request_id:
            submit_feedback(request_id)
            time.sleep(1)
        
        # 4. 验证错误
        test_validation_errors()
        time.sleep(1)
        
        # 5. 统计
        test_statistics()
        time.sleep(1)
        
        # 6. 文档
        test_documentation()
        time.sleep(1)
        
        # 7. 速率限制（可选，因为会发送很多请求）
        print("\n是否测试速率限制？(将发送100+请求) [y/N]: ", end="")
        if input().lower() == 'y':
            test_rate_limiting()
        else:
            print("\n⏭️  跳过速率限制测试")
        
        # 完成
        print_section("演示完成")
        print("✅ 所有功能演示成功!")
        print("\n📚 更多信息:")
        print(f"  - API文档: {BASE_URL}/docs")
        print(f"  - 健康检查: {BASE_URL}/health")
        print(f"  - 统计信息: {BASE_URL}/api/stats")
        print("\n感谢使用 RailFair API! 🚄")
        
    except KeyboardInterrupt:
        print("\n\n⏸️  演示被中断")
    except Exception as e:
        print(f"\n\n❌ 演示出错: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
