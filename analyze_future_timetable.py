#!/usr/bin/env python3
"""
未来时刻表分析工具
获取并分析未来2-4周的实际时刻表，识别真正有服务的路线

这个工具将帮助我们：
1. 发现哪些路线在未来有实际服务
2. 确认车站代码是否正确
3. 了解服务频率
4. 替换无效路线
"""

import os
import sys
import requests
import json
from datetime import datetime, timedelta
from collections import defaultdict
import time
from typing import Dict, List, Optional
import base64

# 目标路线（需要验证）
TARGET_ROUTES = {
    'EUS-MAN': {'from': 'EUS', 'to': 'MAN', 'name': 'London Euston → Manchester'},
    'KGX-EDB': {'from': 'KGX', 'to': 'EDB', 'name': 'London King\'s Cross → Edinburgh'},
    'PAD-BRI': {'from': 'PAD', 'to': 'BRI', 'name': 'London Paddington → Bristol'},
    'LST-NRW': {'from': 'LST', 'to': 'NRW', 'name': 'London Liverpool St → Norwich'},
    'MYB-BHM': {'from': 'MYB', 'to': 'BHM', 'name': 'London Marylebone → Birmingham'},
    'MAN-LIV': {'from': 'MAN', 'to': 'LIV', 'name': 'Manchester → Liverpool'},
    'BHM-MAN': {'from': 'BHM', 'to': 'MAN', 'name': 'Birmingham → Manchester'},
    'BRI-BHM': {'from': 'BRI', 'to': 'BHM', 'name': 'Bristol → Birmingham'},
    'EDB-GLC': {'from': 'EDB', 'to': 'GLC', 'name': 'Edinburgh → Glasgow'},
    'MAN-LDS': {'from': 'MAN', 'to': 'LDS', 'name': 'Manchester → Leeds'}
}

# 车站代码变体（用于测试）
STATION_VARIANTS = {
    'EDB': ['EDB', 'EDR', 'EDI'],
    'MAN': ['MAN', 'MCO', 'MCV'],
    'LDS': ['LDS', 'LEE'],
    'BHM': ['BHM', 'BHI', 'BHN'],
    'GLC': ['GLC', 'GLA', 'GLQ'],
    'BRI': ['BRI', 'BRS'],
    'LIV': ['LIV', 'LPY'],
}

class FutureTimetableAnalyzer:
    """未来时刻表分析器"""
    
    def __init__(self):
        self.email = os.environ.get('HSP_EMAIL') or os.environ.get('HSP_USERNAME')
        self.password = os.environ.get('HSP_PASSWORD')
        
        if not self.email or not self.password:
            print("⚠️ 警告: HSP_EMAIL/HSP_PASSWORD 未设置")
            print("   某些功能可能不可用")
        
        self.base_url = "https://hsp-prod.rockshore.net/api/v1"
        self.results = defaultdict(dict)
    
    def _get_auth_header(self) -> str:
        """生成认证header"""
        credentials = f"{self.email}:{self.password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"
    
    def check_route_future_services(
        self, 
        from_code: str, 
        to_code: str,
        date: str = None,
        time_window: str = "0600-0900"
    ) -> Dict:
        """
        检查未来某天某路线是否有服务
        
        Args:
            from_code: 起点站代码
            to_code: 终点站代码
            date: 日期 (YYYY-MM-DD)，默认明天
            time_window: 时间窗口，如 "0600-0900"
        """
        if not date:
            date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        from_time, to_time = time_window.split('-')
        
        url = f"{self.base_url}/serviceMetrics"
        params = {
            'from_loc': from_code,
            'to_loc': to_code,
            'from_time': from_time,
            'to_time': to_time,
            'from_date': date,
            'to_date': date,
            'days': 'WEEKDAY' if datetime.strptime(date, '%Y-%m-%d').weekday() < 5 else 'WEEKEND'
        }
        
        try:
            response = requests.get(
                url,
                params=params,
                headers={'Authorization': self._get_auth_header()},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                services = data.get('Services', [])
                return {
                    'success': True,
                    'count': len(services),
                    'services': services[:5],  # 只返回前5个作为样本
                    'date': date,
                    'from': from_code,
                    'to': to_code
                }
            else:
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}",
                    'date': date,
                    'from': from_code,
                    'to': to_code
                }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'date': date,
                'from': from_code,
                'to': to_code
            }
    
    def test_route_variants(
        self,
        route_key: str,
        route_info: Dict,
        future_days: int = 7
    ) -> Dict:
        """
        测试一条路线的所有变体
        
        Args:
            route_key: 路线标识
            route_info: 路线信息
            future_days: 测试未来几天
        """
        print(f"\n{'='*70}")
        print(f"🔍 测试路线: {route_key} - {route_info['name']}")
        print(f"{'='*70}")
        
        from_code = route_info['from']
        to_code = route_info['to']
        
        # 获取所有可能的代码变体
        from_variants = STATION_VARIANTS.get(from_code, [from_code])
        to_variants = STATION_VARIANTS.get(to_code, [to_code])
        
        results = []
        
        # 测试未来几天
        for day_offset in range(1, future_days + 1):
            test_date = (datetime.now() + timedelta(days=day_offset)).strftime('%Y-%m-%d')
            
            # 测试不同的车站代码组合
            for from_var in from_variants:
                for to_var in to_variants:
                    if from_var == to_var:
                        continue
                    
                    print(f"   📅 {test_date}: {from_var} → {to_var}...", end=' ')
                    
                    result = self.check_route_future_services(
                        from_var, to_var, test_date
                    )
                    
                    if result['success']:
                        count = result['count']
                        if count > 0:
                            print(f"✅ {count} 个服务")
                            results.append({
                                'date': test_date,
                                'from': from_var,
                                'to': to_var,
                                'count': count,
                                'sample_services': result['services']
                            })
                        else:
                            print("⚠️ 0 个服务")
                    else:
                        print(f"❌ {result.get('error', 'Unknown error')}")
                    
                    time.sleep(1)  # Rate limiting
        
        # 汇总结果
        if results:
            total_services = sum(r['count'] for r in results)
            avg_per_day = total_services / len(results)
            
            print(f"\n✅ 路线验证成功!")
            print(f"   总服务数: {total_services}")
            print(f"   平均每天: {avg_per_day:.1f}")
            print(f"   有效代码组合: {set((r['from'], r['to']) for r in results)}")
            
            # 显示样本服务
            if results[0]['sample_services']:
                print(f"\n   📋 服务样本 (第一天):")
                for svc in results[0]['sample_services'][:3]:
                    print(f"      • {svc.get('serviceAttributesMetrics', {}).get('origin_departure_time')} "
                          f"→ {svc.get('serviceAttributesMetrics', {}).get('destination_arrival_time')}")
        else:
            print(f"\n❌ 路线无服务或代码错误")
            print(f"   建议:")
            print(f"   1. 检查车站代码是否正确")
            print(f"   2. 验证路线是否存在")
            print(f"   3. 考虑替换为其他路线")
        
        return {
            'route_key': route_key,
            'results': results,
            'total_services': sum(r['count'] for r in results) if results else 0,
            'is_valid': len(results) > 0
        }
    
    def analyze_all_routes(self, future_days: int = 3) -> Dict:
        """
        分析所有目标路线
        
        Args:
            future_days: 测试未来几天（建议3-7天）
        """
        print("="*70)
        print("🚂 RailFair 未来时刻表分析")
        print("="*70)
        print(f"📅 分析范围: 未来 {future_days} 天")
        print(f"🛤️ 目标路线: {len(TARGET_ROUTES)} 条")
        print("="*70)
        
        all_results = {}
        valid_routes = []
        invalid_routes = []
        
        for route_key, route_info in TARGET_ROUTES.items():
            result = self.test_route_variants(route_key, route_info, future_days)
            all_results[route_key] = result
            
            if result['is_valid']:
                valid_routes.append((route_key, result['total_services']))
            else:
                invalid_routes.append(route_key)
            
            time.sleep(2)  # 路线间延迟
        
        # 生成总结报告
        print("\n" + "="*70)
        print("📊 分析总结")
        print("="*70)
        
        print(f"\n✅ 有效路线 ({len(valid_routes)}/{len(TARGET_ROUTES)}):")
        valid_routes.sort(key=lambda x: x[1], reverse=True)
        for route_key, total in valid_routes:
            avg = total / future_days
            status = "🔥" if avg > 20 else "✓"
            print(f"   {status} {route_key}: {total} 服务 (平均 {avg:.1f}/天)")
        
        if invalid_routes:
            print(f"\n❌ 无效/无数据路线 ({len(invalid_routes)}):")
            for route_key in invalid_routes:
                print(f"   • {route_key}: {TARGET_ROUTES[route_key]['name']}")
        
        # 生成建议
        print("\n" + "="*70)
        print("💡 建议")
        print("="*70)
        
        if len(valid_routes) < 10:
            print(f"\n⚠️ 只有 {len(valid_routes)} 条路线有效，需要替换 {10 - len(valid_routes)} 条")
            print("\n推荐操作:")
            print("1. 使用 diagnose_routes.py 查看数据库中的高流量替代路线")
            print("2. 更新 hsp_config.yaml 中的路线配置")
            print("3. 重新运行数据采集")
        
        if len(valid_routes) >= 10:
            print("\n✅ 路线配置良好，可以继续数据采集")
        
        # 保存报告
        report = {
            'generated_at': datetime.now().isoformat(),
            'analysis_days': future_days,
            'total_routes': len(TARGET_ROUTES),
            'valid_routes': len(valid_routes),
            'invalid_routes': len(invalid_routes),
            'route_details': all_results
        }
        
        report_path = 'data/future_timetable_analysis.json'
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 详细报告已保存: {report_path}")
        
        return report

def main():
    """主函数"""
    print("🚂 RailFair - 未来时刻表分析工具")
    print("=" * 70)
    
    # 检查API凭证
    if not os.environ.get('HSP_EMAIL') and not os.environ.get('HSP_USERNAME'):
        print("❌ 错误: HSP_EMAIL 或 HSP_USERNAME 环境变量未设置")
        print("\n请设置:")
        print("  export HSP_EMAIL='your_email@example.com'")
        print("  export HSP_PASSWORD='your_password'")
        sys.exit(1)
    
    if not os.environ.get('HSP_PASSWORD'):
        print("❌ 错误: HSP_PASSWORD 环境变量未设置")
        sys.exit(1)
    
    # 创建分析器
    analyzer = FutureTimetableAnalyzer()
    
    # 运行分析（默认3天，可以改为7天更全面但更慢）
    future_days = 3
    if len(sys.argv) > 1:
        try:
            future_days = int(sys.argv[1])
        except ValueError:
            print("⚠️ 参数应为整数，使用默认值 3 天")
    
    print(f"\n开始分析未来 {future_days} 天的时刻表...")
    print("⏱️ 预计耗时: ~{} 分钟\n".format(future_days * len(TARGET_ROUTES) // 2))
    
    try:
        report = analyzer.analyze_all_routes(future_days)
        
        print("\n" + "="*70)
        print("✅ 分析完成!")
        print("="*70)
        print("\n下一步:")
        print("1. 查看报告: cat data/future_timetable_analysis.json")
        print("2. 更新路线配置")
        print("3. 重新运行数据采集")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
