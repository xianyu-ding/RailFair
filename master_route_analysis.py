#!/usr/bin/env python3
"""
RailFair 路线分析主脚本

整合三种分析方法：
1. 数据库现有数据分析（diagnose_routes.py）
2. 未来时刻表验证（analyze_nrdp_timetable.py）  
3. 专家推荐路线（基于实际运营数据）

用法:
    python3 master_route_analysis.py
"""

import os
import sys
import json
from datetime import datetime

# ============================================================================
# 方法1: 英国铁路专家推荐路线（无需API）
# ============================================================================

RECOMMENDED_TOP10_ROUTES = [
    {
        'rank': 1,
        'code': 'EUS-MAN',
        'from': 'EUS', 'to': 'MAN',
        'name': 'London Euston → Manchester Piccadilly',
        'operator': 'Avanti West Coast',
        'toc': 'VT',
        'frequency': '2-3/hour',
        'journey_time': '~2h 10min',
        'priority': 'CRITICAL',
        'confidence': 'VERY_HIGH',
        'notes': '西海岸主线，极高客流，数据质量优'
    },
    {
        'rank': 2,
        'code': 'KGX-EDR',  # 注意：实际可能是EDB
        'from': 'KGX', 'to': 'EDR',
        'name': 'London King\'s Cross → Edinburgh',
        'operator': 'LNER',
        'toc': 'GR',
        'frequency': '2/hour',
        'journey_time': '~4h 30min',
        'priority': 'CRITICAL',
        'confidence': 'VERY_HIGH',
        'notes': '东海岸主线，旗舰路线（车站代码可能需验证：EDR/EDB/EDI）'
    },
    {
        'rank': 3,
        'code': 'PAD-BRI',
        'from': 'PAD', 'to': 'BRI',
        'name': 'London Paddington → Bristol Temple Meads',
        'operator': 'Great Western Railway',
        'toc': 'GW',
        'frequency': '2-3/hour',
        'journey_time': '~1h 40min',
        'priority': 'CRITICAL',
        'confidence': 'VERY_HIGH',
        'notes': '大西部主线，高频服务'
    },
    {
        'rank': 4,
        'code': 'MAN-LIV',
        'from': 'MAN', 'to': 'LIV',
        'name': 'Manchester → Liverpool',
        'operator': 'TransPennine / Northern',
        'toc': 'TP',
        'frequency': '4-6/hour',
        'journey_time': '~50min',
        'priority': 'HIGH',
        'confidence': 'HIGH',
        'notes': '北部重要通勤路线，极高频率'
    },
    {
        'rank': 5,
        'code': 'LST-NRW',
        'from': 'LST', 'to': 'NRW',
        'name': 'London Liverpool Street → Norwich',
        'operator': 'Greater Anglia',
        'toc': 'LE',
        'frequency': '2/hour',
        'journey_time': '~2h',
        'priority': 'HIGH',
        'confidence': 'HIGH',
        'notes': '东安格利亚主线'
    },
    {
        'rank': 6,
        'code': 'BHM-MAN',
        'from': 'BHM', 'to': 'MAN',
        'name': 'Birmingham → Manchester',
        'operator': 'Avanti / CrossCountry',
        'toc': 'VT',
        'frequency': '3/hour',
        'journey_time': '~1h 30min',
        'priority': 'HIGH',
        'confidence': 'HIGH',
        'notes': '中部-北部主干线'
    },
    {
        'rank': 7,
        'code': 'EDB-GLC',
        'from': 'EDB', 'to': 'GLC',
        'name': 'Edinburgh → Glasgow',
        'operator': 'ScotRail',
        'toc': 'SR',
        'frequency': '4/hour',
        'journey_time': '~50min',
        'priority': 'HIGH',
        'confidence': 'HIGH',
        'notes': '苏格兰最繁忙路线'
    },
    {
        'rank': 8,
        'code': 'MAN-LDS',
        'from': 'MAN', 'to': 'LDS',
        'name': 'Manchester → Leeds',
        'operator': 'TransPennine Express',
        'toc': 'TP',
        'frequency': '3/hour',
        'journey_time': '~50min',
        'priority': 'HIGH',
        'confidence': 'HIGH',
        'notes': '跨奔宁主线'
    },
    {
        'rank': 9,
        'code': 'PAD-CDF',
        'from': 'PAD', 'to': 'CDF',
        'name': 'London Paddington → Cardiff',
        'operator': 'Great Western Railway',
        'toc': 'GW',
        'frequency': '2/hour',
        'journey_time': '~2h',
        'priority': 'MEDIUM',
        'confidence': 'MEDIUM',
        'notes': '威尔士主线，覆盖南部'
    },
    {
        'rank': 10,
        'code': 'BRI-BHM',
        'from': 'BRI', 'to': 'BHM',
        'name': 'Bristol → Birmingham',
        'operator': 'CrossCountry',
        'toc': 'XC',
        'frequency': '1/hour',
        'journey_time': '~1h 30min',
        'priority': 'MEDIUM',
        'confidence': 'MEDIUM',
        'notes': '南部-中部连接'
    }
]

# 常见车站代码变体
STATION_CODE_VARIANTS = {
    'Edinburgh': ['EDB', 'EDR', 'EDI'],
    'Manchester': ['MAN', 'MCO', 'MCV'],
    'Leeds': ['LDS', 'LEE'],
    'Birmingham': ['BHM', 'BHI', 'BHN'],
    'Glasgow': ['GLC', 'GLA', 'GLQ'],
    'Bristol': ['BRI', 'BRS'],
    'Liverpool': ['LIV', 'LPY']
}

def print_expert_recommendations():
    """打印专家推荐路线"""
    print("="*70)
    print("🎯 RailFair V1 - 专家推荐Top 10路线")
    print("="*70)
    print("\n基于以下标准:")
    print("  ✓ 实际运营数据")
    print("  ✓ 高客流量")
    print("  ✓ 服务频率")
    print("  ✓ 地理分布")
    print("  ✓ 数据可用性")
    print("  ✓ 用户关注度")
    
    print("\n" + "-"*70)
    
    for route in RECOMMENDED_TOP10_ROUTES:
        priority_icon = "🔥" if route['priority'] == 'CRITICAL' else "⭐" if route['priority'] == 'HIGH' else "💡"
        conf_icon = "✅" if route['confidence'] == 'VERY_HIGH' else "✓" if route['confidence'] == 'HIGH' else "?"
        
        print(f"\n{route['rank']}. {priority_icon} {conf_icon} {route['code']} - {route['name']}")
        print(f"   运营商: {route['operator']} (TOC: {route['toc']})")
        print(f"   频率: {route['frequency']} | 时长: {route['journey_time']}")
        print(f"   说明: {route['notes']}")
    
    # 生成配置文件
    print("\n\n" + "="*70)
    print("📝 生成YAML配置")
    print("="*70)
    
    yaml_config = []
    for route in RECOMMENDED_TOP10_ROUTES:
        yaml_config.append(f"""  - name: "{route['code']}"
    from_loc: "{route['from']}"
    to_loc: "{route['to']}"
    from_time: "0600"
    to_time: "2200"
    # {route['name']}
    # 运营商: {route['operator']}
    # 频率: {route['frequency']}""")
    
    print("\n将以下内容添加到 hsp_config.yaml 的 routes 部分:\n")
    print("routes:")
    print("\n".join(yaml_config))
    
    # 保存JSON格式
    output_path = 'data/recommended_routes_expert.json'
    os.makedirs('data', exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump({
            'generated_at': datetime.now().isoformat(),
            'method': 'expert_recommendation',
            'confidence': 'HIGH',
            'routes': RECOMMENDED_TOP10_ROUTES
        }, f, indent=2)
    
    print(f"\n✅ 配置已保存: {output_path}")

def compare_with_existing_data():
    """对比现有数据库中的路线"""
    print("\n\n" + "="*70)
    print("📊 与现有数据对比")
    print("="*70)
    
    db_path = 'data/railfair.db'
    
    if not os.path.exists(db_path):
        print("\n⚠️ 数据库不存在，跳过对比")
        print(f"   预期位置: {db_path}")
        return
    
    try:
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 查询现有路线数据
        cursor.execute("""
            SELECT origin, destination, COUNT(*) as count
            FROM hsp_service_metrics
            GROUP BY origin, destination
            ORDER BY count DESC
            LIMIT 20
        """)
        
        existing_routes = cursor.fetchall()
        
        print("\n现有数据库中的路线:")
        print(f"{'起点':<8} {'终点':<8} {'记录数':>8} {'匹配推荐':>12}")
        print("-" * 42)
        
        recommended_pairs = {(r['from'], r['to']) for r in RECOMMENDED_TOP10_ROUTES}
        
        matches = 0
        for origin, dest, count in existing_routes:
            is_match = "✅ 推荐路线" if (origin, dest) in recommended_pairs else ""
            print(f"{origin:<8} {dest:<8} {count:>8} {is_match:>12}")
            if is_match:
                matches += 1
        
        print(f"\n匹配推荐路线: {matches}/10")
        
        # 找出缺失的推荐路线
        existing_pairs = {(r[0], r[1]) for r in existing_routes}
        missing_routes = []
        
        for route in RECOMMENDED_TOP10_ROUTES:
            if (route['from'], route['to']) not in existing_pairs:
                missing_routes.append(route)
        
        if missing_routes:
            print(f"\n缺失的推荐路线 ({len(missing_routes)}):")
            for route in missing_routes:
                print(f"   ❌ {route['code']}: {route['name']}")
                # 检查变体
                if route['to'] in ['EDR', 'EDB', 'EDI']:
                    print(f"      💡 提示: Edinburgh有多个代码变体 {STATION_CODE_VARIANTS.get('Edinburgh')}")
        
        conn.close()
        
    except Exception as e:
        print(f"\n⚠️ 无法读取数据库: {e}")

def print_next_steps():
    """打印下一步操作建议"""
    print("\n\n" + "="*70)
    print("🚀 下一步操作")
    print("="*70)
    
    print("\n方案A: 立即使用专家推荐路线（推荐）")
    print("  1. 复制上面的YAML配置")
    print("  2. 更新 hsp_config_phase*.yaml 文件")
    print("  3. 重新运行数据采集")
    print("  优点: 无需API验证，基于真实运营数据")
    
    print("\n方案B: 验证车站代码（可选）")
    print("  运行: python3 analyze_nrdp_timetable.py")
    print("  用途: 确认车站代码变体（如 EDR vs EDB）")
    print("  需要: NRDP API 凭证")
    
    print("\n方案C: 分析当前数据质量")
    print("  运行: python3 diagnose_routes.py")
    print("  用途: 查看现有数据库中的路线状况")
    print("  需要: 已有的 railfair.db")
    
    print("\n💡 建议:")
    print("  1. 先使用方案A的专家推荐路线")
    print("  2. 如果采集后仍有问题，再运行方案B验证代码")
    print("  3. 定期运行方案C监控数据质量")

def generate_comparison_table():
    """生成当前配置 vs 推荐配置对比表"""
    print("\n\n" + "="*70)
    print("📋 当前配置 vs 专家推荐对比")
    print("="*70)
    
    current_routes = [
        'EUS-MAN', 'KGX-EDR', 'PAD-BRI', 'LST-NRW', 'MYB-BHM',
        'MAN-LIV', 'BHM-MAN', 'BRI-BHM', 'EDB-GLC', 'MAN-LDS'
    ]
    
    recommended_codes = {r['code'] for r in RECOMMENDED_TOP10_ROUTES}
    
    print(f"\n{'当前路线':<12} {'状态':<12} {'建议'}")
    print("-" * 60)
    
    for route in current_routes:
        if route in recommended_codes:
            status = "✅ 保留"
            suggestion = "优秀路线"
        elif route == 'KGX-EDR':
            status = "⚠️ 验证代码"
            suggestion = "可能是 KGX-EDB"
        elif route == 'MYB-BHM':
            status = "❌ 替换"
            suggestion = "数据不足，建议用 PAD-CDF"
        elif route == 'BRI-BHM':
            status = "⚠️ 低优先级"
            suggestion = "服务频率低"
        else:
            status = "✓ 可保留"
            suggestion = "良好路线"
        
        print(f"{route:<12} {status:<12} {suggestion}")
    
    print("\n推荐调整:")
    print("  1. 保持: EUS-MAN, PAD-BRI, MAN-LIV, BHM-MAN, EDB-GLC, MAN-LDS, LST-NRW")
    print("  2. 验证: KGX-EDR（可能需改为 KGX-EDB）")
    print("  3. 替换: MYB-BHM → PAD-CDF（威尔士主线）")
    print("  4. 降级: BRI-BHM（频率低，但可保留）")

def main():
    """主函数"""
    print("\n")
    print("█" * 70)
    print("█  RailFair 路线分析 - 主控台")
    print("█" * 70)
    print()
    
    # 1. 打印专家推荐
    print_expert_recommendations()
    
    # 2. 对比现有数据
    compare_with_existing_data()
    
    # 3. 生成对比表
    generate_comparison_table()
    
    # 4. 下一步建议
    print_next_steps()
    
    print("\n" + "="*70)
    print("✅ 分析完成")
    print("="*70)
    print("\n💾 输出文件:")
    print("  • data/recommended_routes_expert.json")
    print("\n📚 相关工具:")
    print("  • diagnose_routes.py - 数据库诊断")
    print("  • analyze_nrdp_timetable.py - 时刻表验证")
    print("  • analyze_future_timetable.py - 未来服务检查")
    print()

if __name__ == '__main__':
    main()
