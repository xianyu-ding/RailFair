#!/usr/bin/env python3
"""
测试有问题的路线，验证是否有数据
"""
import os
import sys
import json
import time
import random
import requests
from datetime import datetime, timedelta

def load_env_file(env_path='.env'):
    """从 .env 文件加载环境变量"""
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    os.environ[key] = value

def get_auth_header():
    """获取认证头"""
    load_env_file()
    email = os.environ.get('HSP_EMAIL') or os.environ.get('HSP_USERNAME')
    password = os.environ.get('HSP_PASSWORD')
    
    if not email or not password:
        raise ValueError("HSP_EMAIL/USERNAME and HSP_PASSWORD must be set")
    
    import base64
    credentials = f"{email}:{password}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return f"Basic {encoded}"

def test_route(from_loc, to_loc, from_date, to_date, days="WEEKDAY", 
               from_time="0000", to_time="2359", toc_filter=None, timeout=180):
    """测试单条路线"""
    url = "https://hsp-prod.rockshore.net/api/v1/serviceMetrics"
    headers = {
        "Authorization": get_auth_header(),
        "Content-Type": "application/json"
    }
    
    payload = {
        "from_loc": from_loc,
        "to_loc": to_loc,
        "from_date": from_date,
        "to_date": to_date,
        "from_time": from_time,
        "to_time": to_time,
        "days": days
    }
    
    if toc_filter:
        payload["toc_filter"] = toc_filter
    
    max_retries = 3
    retry_delay = 3
    
    time.sleep(random.uniform(1.0, 3.0))
    
    last_error = None
    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=timeout)
            if response.status_code == 200:
                data = response.json()
                services = data.get('Services', [])
                return len(services), None
            elif response.status_code in [502, 503, 504]:
                last_error = f"HTTP {response.status_code}: Proxy/Server Error"
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (attempt + 1) + random.uniform(0, 2)
                    time.sleep(wait_time)
                    continue
                else:
                    return 0, last_error
            else:
                return 0, f"HTTP {response.status_code}: {response.text[:200]}"
        except requests.exceptions.Timeout:
            last_error = "Request timeout"
            if attempt < max_retries - 1:
                wait_time = retry_delay * (attempt + 1) + random.uniform(0, 2)
                time.sleep(wait_time)
                continue
            else:
                return 0, last_error
        except Exception as e:
            last_error = str(e)
            if attempt < max_retries - 1:
                wait_time = retry_delay * (attempt + 1) + random.uniform(0, 2)
                time.sleep(wait_time)
                continue
            else:
                return 0, last_error
    
    return 0, last_error

# 问题路线
problematic_routes = [
    {
        "name": "VIC-BHM",
        "from_loc": "VIC",
        "to_loc": "BHM",
        "description": "London Victoria - Birmingham New Street",
        "toc_options": [
            None,  # 先试不带TOC
            ["LM"],  # West Midlands Trains
            ["XC"],  # CrossCountry
            ["LM", "XC"],  # 两者
            ["SN"],  # Southern (可能从Victoria出发)
            ["GX"],  # Gatwick Express
        ]
    },
    {
        "name": "MAN-LIV",
        "from_loc": "MAN",
        "to_loc": "LIV",
        "description": "Manchester Piccadilly - Liverpool Lime Street",
        "toc_options": [
            None,  # 先试不带TOC
            ["NT"],  # Northern Trains
            ["TP"],  # TransPennine Express
            ["NT", "TP"],  # 两者
            ["AW"],  # Transport for Wales
        ]
    },
    {
        "name": "KGX-EDB",
        "from_loc": "KGX",
        "to_loc": "EDB",
        "description": "London King's Cross - Edinburgh",
        "toc_options": [
            None,
            ["GR"],  # LNER
            ["LD"],  # Lumo
            ["GR", "LD"],
        ]
    },
    {
        "name": "EDB-GLC",
        "from_loc": "EDB",
        "to_loc": "GLC",
        "description": "Edinburgh - Glasgow Central",
        "toc_options": [
            None,
            ["SR"],  # ScotRail
        ]
    },
    {
        "name": "MAN-LDS",
        "from_loc": "MAN",
        "to_loc": "LDS",
        "description": "Manchester Piccadilly - Leeds",
        "toc_options": [
            None,
            ["TP"],  # TransPennine Express
            ["NT"],  # Northern Trains
            ["TP", "NT"],
        ]
    }
]

if __name__ == "__main__":
    print("=" * 80)
    print("测试问题路线数据可用性")
    print("=" * 80)
    print()
    
    # 测试日期：最近的一个工作日
    test_date = datetime.now() - timedelta(days=7)
    while test_date.weekday() >= 5:  # 跳过周末
        test_date -= timedelta(days=1)
    test_from_date = test_date.strftime('%Y-%m-%d')
    test_to_date = test_from_date  # 只测试一天
    
    print(f"测试日期: {test_from_date} (WEEKDAY)")
    print()
    
    for route in problematic_routes:
        print(f"🛤️  {route['name']}: {route['description']}")
        print("-" * 80)
        
        found_data = False
        for toc_option in route['toc_options']:
            toc_desc = "without TOC filter" if toc_option is None else f"with TOC {toc_option}"
            print(f"  测试: {toc_desc}...", end=" ", flush=True)
            
            count, error = test_route(
                route['from_loc'], route['to_loc'],
                test_from_date, test_to_date,
                days="WEEKDAY",
                from_time="0000", to_time="2359",
                toc_filter=toc_option,
                timeout=180
            )
            
            if error:
                print(f"❌ Error: {error}")
            elif count > 0:
                print(f"✅ Found {count} services!")
                found_data = True
                break  # 找到数据就停止
            else:
                print(f"⚠️  No services")
        
        if found_data:
            print(f"   ✅ {route['name']} 有数据！")
        else:
            print(f"   ❌ {route['name']} 没有找到数据")
        
        print()
        
        # 等待一下再测试下一条路线
        if route != problematic_routes[-1]:
            wait_time = random.uniform(2.0, 4.0)
            print(f"   等待 {wait_time:.1f}s...")
            time.sleep(wait_time)
            print()
    
    print("=" * 80)
    print("测试完成")
    print("=" * 80)
