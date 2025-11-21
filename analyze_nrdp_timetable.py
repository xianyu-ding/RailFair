import re
import os
import sys
import json
import argparse
import sqlite3
from pathlib import Path
from datetime import datetime, time, date
from collections import defaultdict, Counter
from statistics import median
from typing import Optional, List

def parse_cif_time(time_str):
    """解析CIF时间格式 (HHMM 或 HHMMH)"""
    if not time_str or time_str.strip() in ('', '0000'):
        return None
    
    time_str = time_str.strip()
    
    # 处理半分钟标记 (如 0841H)
    half_minute = time_str.endswith('H')
    if half_minute:
        time_str = time_str[:-1]
    
    # 验证是否为4位数字
    if not time_str.isdigit() or len(time_str) != 4:
        return None
    
    try:
        hour = int(time_str[:2])
        minute = int(time_str[2:4])
        
        if hour > 23 or minute > 59:
            return None
            
        return time(hour, minute, 30 if half_minute else 0)
    except (ValueError, IndexError):
        return None

def parse_cif_date(date_str):
    """解析CIF日期格式 (YYMMDD)"""
    if not date_str or len(date_str) != 6:
        return None
    
    try:
        year = int(date_str[0:2]) + 2000  # 假设是21世纪
        month = int(date_str[2:4])
        day = int(date_str[4:6])
        return datetime(year, month, day).date()
    except (ValueError, IndexError):
        return None

def parse_ddmmyy_date(date_str):
    """解析DDMMYY格式日期 (用于HD记录的Extract dates)"""
    if not date_str or len(date_str) != 6:
        return None
    
    try:
        day = int(date_str[0:2])
        month = int(date_str[2:4])
        year = int(date_str[4:6])
        # 年份00-50表示2000-2050，51-99表示1951-1999
        full_year = 2000 + year if year < 50 else 1900 + year
        return datetime(full_year, month, day).date()
    except (ValueError, IndexError):
        return None

def extract_timetable_date_range(cif_content):
    """
    根据NRDP规范从timetable数据中提取时间范围
    
    根据规范文档 RSPS5046:
    - HD记录: 位置49-54 = Extract start date (ddmmyy), 位置55-60 = Extract end date (ddmmyy)
    - BS记录: 位置10-15 = Date Runs From (yymmdd), 位置16-21 = Date Runs To (yymmdd)
    """
    date_range_info = {
        'start_date': None,
        'end_date': None,
        'validity_period': None,
        'source': None
    }
    
    all_start_dates = []
    all_end_dates = []
    
    # 查找HD记录（Header Record）
    for line in cif_content.split('\n'):
        line = line.rstrip('\r\n')
        if len(line) >= 60 and line[0:2] == 'HD':
            # 根据规范，HD记录格式：
            # 位置49-54: Extract start date (ddmmyy)
            # 位置55-60: Extract end date (ddmmyy)
            if len(line) >= 60:
                extract_start = line[48:54]  # 位置49-54 (0-indexed: 48-54)
                extract_end = line[54:60]    # 位置55-60 (0-indexed: 54-60)
                
                start_date = parse_ddmmyy_date(extract_start)
                end_date = parse_ddmmyy_date(extract_end)
                
                if start_date and end_date:
                    all_start_dates.append(start_date)
                    all_end_dates.append(end_date)
                    date_range_info['source'] = 'HD record (Extract dates)'
    
    # 从BS记录中提取所有服务的日期范围
    bs_dates_found = 0
    for line in cif_content.split('\n'):
        line = line.rstrip('\r\n')
        if len(line) >= 21 and line[0:2] == 'BS':
            # 根据规范，BS记录格式：
            # 位置10-15: Date Runs From (yymmdd)
            # 位置16-21: Date Runs To (yymmdd)
            date_from = line[9:15]   # 位置10-15 (0-indexed: 9-15)
            date_to = line[15:21]    # 位置16-21 (0-indexed: 15-21)
            
            start_date = parse_cif_date(date_from)
            end_date = parse_cif_date(date_to)
            
            if start_date and end_date:
                all_start_dates.append(start_date)
                all_end_dates.append(end_date)
                bs_dates_found += 1
    
    if bs_dates_found > 0:
        if not date_range_info['source']:
            date_range_info['source'] = f'BS records ({bs_dates_found} services)'
    
    # 确定最终的时间范围
    if all_start_dates and all_end_dates:
        min_start = min(all_start_dates)
        max_end = max(all_end_dates)
        
        date_range_info['start_date'] = min_start.strftime('%Y-%m-%d')
        date_range_info['end_date'] = max_end.strftime('%Y-%m-%d')
        
        days = (max_end - min_start).days + 1
        date_range_info['validity_period'] = f"{days} 天"
        
        if not date_range_info['source']:
            date_range_info['source'] = 'BS records'
    
    return date_range_info

def parse_days_run(days_str):
    """解析运行日期模式 (1111100 = 周一到周五)"""
    if not days_str or len(days_str) != 7:
        return []
    
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    return [day_names[i] for i, char in enumerate(days_str) if char == '1']

def extract_service_times(cif_content):
    """从CIF内容中提取服务时间"""
    services = []
    current_service = None
    
    for line in cif_content.split('\n'):
        line = line.rstrip('\r\n')
        
        if len(line) < 2:
            continue
            
        record_type = line[0:2]
        
        # BS记录 - 基本服务信息
        if record_type == 'BS':
            if len(line) >= 80:
                transaction_type = line[2:3]
                train_uid = line[3:9].strip()
                start_date = line[9:15]
                end_date = line[15:21]
                days = line[21:28]
                train_status = line[29:30]
                train_category = line[30:32]
                train_identity = line[32:36].strip()
                
                current_service = {
                    'transaction_type': transaction_type,
                    'train_uid': train_uid,
                    'start_date': parse_cif_date(start_date),
                    'end_date': parse_cif_date(end_date),
                    'days_run': parse_days_run(days),
                    'train_status': train_status,
                    'train_category': train_category,
                    'train_identity': train_identity,
                    'origin_time': None,
                    'destination_time': None,
                    'origin_location': None,
                    'destination_location': None,
                    'intermediate_stops': []
                }
        
        # BX记录 - 扩展信息
        elif record_type == 'BX' and current_service:
            if len(line) >= 22:
                atoc_code = line[11:13]
                retail_service_id = line[14:22].strip()
                current_service['atoc_code'] = atoc_code
                current_service['retail_service_id'] = retail_service_id
        
        # LO记录 - 起点位置
        elif record_type == 'LO' and current_service:
            if len(line) >= 19:
                location = line[2:10].strip()
                scheduled_dep = line[10:15]
                public_dep = line[15:19]
                platform = line[19:22].strip() if len(line) >= 22 else ''
                
                current_service['origin_location'] = location
                
                # 优先使用public时间
                time_to_parse = public_dep if public_dep.strip() and public_dep.strip() != '0000' else scheduled_dep
                parsed_time = parse_cif_time(time_to_parse)
                
                if parsed_time:
                    current_service['origin_time'] = parsed_time
        
        # LI记录 - 中间站点
        elif record_type == 'LI' and current_service:
            if len(line) >= 29:
                location = line[2:10].strip()
                scheduled_arr = line[10:15]
                scheduled_dep = line[15:20]
                scheduled_pass = line[20:25]
                public_arr = line[25:29]
                public_dep = line[29:33] if len(line) >= 33 else ''
                platform = line[33:36].strip() if len(line) >= 36 else ''
                
                # 解析到达时间
                arr_time = None
                if public_arr.strip() and public_arr.strip() != '0000':
                    arr_time = parse_cif_time(public_arr)
                elif scheduled_arr.strip() and scheduled_arr.strip() != '0000':
                    arr_time = parse_cif_time(scheduled_arr)
                
                # 解析出发时间
                dep_time = None
                if public_dep.strip() and public_dep.strip() != '0000':
                    dep_time = parse_cif_time(public_dep)
                elif scheduled_dep.strip() and scheduled_dep.strip() != '0000':
                    dep_time = parse_cif_time(scheduled_dep)
                
                # 解析通过时间
                pass_time = None
                if scheduled_pass.strip() and scheduled_pass.strip() != '0000':
                    pass_time = parse_cif_time(scheduled_pass)
                
                stop_info = {
                    'location': location,
                    'arrival': arr_time,
                    'departure': dep_time,
                    'pass': pass_time,
                    'platform': platform
                }
                
                current_service['intermediate_stops'].append(stop_info)
        
        # LT记录 - 终点位置
        elif record_type == 'LT' and current_service:
            if len(line) >= 19:
                location = line[2:10].strip()
                scheduled_arr = line[10:15]
                public_arr = line[15:19]
                platform = line[19:22].strip() if len(line) >= 22 else ''
                
                current_service['destination_location'] = location
                
                time_to_parse = public_arr if public_arr.strip() and public_arr.strip() != '0000' else scheduled_arr
                parsed_time = parse_cif_time(time_to_parse)
                
                if parsed_time:
                    current_service['destination_time'] = parsed_time
                
                # 保存完整的服务记录
                if current_service['origin_time'] or current_service['destination_time']:
                    services.append(current_service.copy())
                
                current_service = None
    
    return services

def save_parsed_data(services, date_range_info, output_file='data/timetable_parsed.json', source_files=None):
    """保存解析后的数据到JSON文件"""
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    range_info = (date_range_info or {}).copy()
    
    if source_files:
        range_info['files'] = [Path(p).name for p in source_files]
        range_info['file_count'] = len(source_files)
    
    # 转换数据为可序列化格式
    serializable_services = []
    for service in services:
        serializable_service = {
            'train_uid': service['train_uid'],
            'atoc_code': service.get('atoc_code', ''),
            'retail_service_id': service.get('retail_service_id', ''),
            'start_date': service['start_date'].isoformat() if service['start_date'] else None,
            'end_date': service['end_date'].isoformat() if service['end_date'] else None,
            'days_run': service['days_run'],
            'train_category': service['train_category'],
            'origin_location': service['origin_location'],
            'origin_time': service['origin_time'].isoformat() if service['origin_time'] else None,
            'destination_location': service['destination_location'],
            'destination_time': service['destination_time'].isoformat() if service['destination_time'] else None,
            'intermediate_stops_count': len(service['intermediate_stops'])
        }
        serializable_services.append(serializable_service)
    
    data = {
        'parsed_at': datetime.now().isoformat(),
        'date_range': range_info,
        'total_services': len(services),
        'services': serializable_services
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    return output_path

def load_parsed_data(input_file='data/timetable_parsed.json'):
    """从JSON文件加载已解析的数据"""
    input_path = Path(input_file)
    if not input_path.exists():
        return None, None
    
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 转换回原始格式
    services = []
    for s in data['services']:
        # 解析日期
        start_date = None
        if s['start_date']:
            try:
                start_date = datetime.fromisoformat(s['start_date']).date()
            except (ValueError, TypeError):
                # 尝试其他日期格式
                try:
                    start_date = datetime.strptime(s['start_date'], '%Y-%m-%d').date()
                except (ValueError, TypeError):
                    pass
        
        end_date = None
        if s['end_date']:
            try:
                end_date = datetime.fromisoformat(s['end_date']).date()
            except (ValueError, TypeError):
                try:
                    end_date = datetime.strptime(s['end_date'], '%Y-%m-%d').date()
                except (ValueError, TypeError):
                    pass
        
        # 解析时间（使用time.fromisoformat或手动解析）
        origin_time = None
        if s['origin_time']:
            try:
                origin_time = time.fromisoformat(s['origin_time'])
            except (ValueError, TypeError):
                try:
                    # 手动解析 HH:MM:SS 格式
                    parts = s['origin_time'].split(':')
                    if len(parts) >= 2:
                        origin_time = time(int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 0)
                except (ValueError, TypeError, IndexError):
                    pass
        
        destination_time = None
        if s['destination_time']:
            try:
                destination_time = time.fromisoformat(s['destination_time'])
            except (ValueError, TypeError):
                try:
                    # 手动解析 HH:MM:SS 格式
                    parts = s['destination_time'].split(':')
                    if len(parts) >= 2:
                        destination_time = time(int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 0)
                except (ValueError, TypeError, IndexError):
                    pass
        
        service = {
            'train_uid': s['train_uid'],
            'atoc_code': s.get('atoc_code', ''),
            'retail_service_id': s.get('retail_service_id', ''),
            'start_date': start_date,
            'end_date': end_date,
            'days_run': s['days_run'],
            'train_category': s['train_category'],
            'origin_location': s['origin_location'],
            'origin_time': origin_time,
            'destination_location': s['destination_location'],
            'destination_time': destination_time,
            'intermediate_stops': [],
            'intermediate_stops_count': s.get('intermediate_stops_count', 0)  # 确保包含中间站点数量
        }
        services.append(service)
    
    return services, data.get('date_range', {})

def parse_iso_date(value: str) -> Optional[date]:
    """Parse YYYY-MM-DD strings into date objects"""
    if not value:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        return None

def get_cache_age_days(parsed_data: dict) -> Optional[int]:
    """Return cache age in days if parsed_at is present"""
    parsed_at = parsed_data.get('parsed_at')
    if not parsed_at:
        return None
    try:
        parsed_dt = datetime.fromisoformat(parsed_at)
    except ValueError:
        try:
            parsed_dt = datetime.strptime(parsed_at, '%Y-%m-%dT%H:%M:%S')
        except ValueError:
            return None
    delta = datetime.now() - parsed_dt
    return delta.days

def parse_date_string(value: Optional[str], label: str = "日期") -> Optional[date]:
    """Parse CLI date string in YYYY-MM-DD format"""
    if not value:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        print(f"✗ 无效的{label}: {value} (请使用 YYYY-MM-DD 格式)")
        sys.exit(1)

def filter_services_by_date_range(services, start_date: Optional[date] = None, end_date: Optional[date] = None):
    """Filter services within optional [start_date, end_date]"""
    if not start_date and not end_date:
        return services
    
    filtered = []
    for service in services:
        svc_start = service.get('start_date')
        svc_end = service.get('end_date') or svc_start
        
        if start_date and svc_end and svc_end < start_date:
            continue
        if end_date and svc_start and svc_start > end_date:
            continue
        filtered.append(service)
    
    return filtered

def calculate_duration_minutes(service) -> Optional[int]:
    """Calculate duration in minutes between origin and destination times"""
    origin_time = service.get('origin_time')
    destination_time = service.get('destination_time')
    
    if not origin_time or not destination_time:
        return None
    
    start_minutes = origin_time.hour * 60 + origin_time.minute + origin_time.second / 60
    end_minutes = destination_time.hour * 60 + destination_time.minute + destination_time.second / 60
    
    duration = end_minutes - start_minutes
    if duration < 0:
        duration += 24 * 60  # 跨午夜
    
    return round(duration)

def aggregate_route_metrics(services):
    """Aggregate timetable services into route-level metrics"""
    route_stats = {}
    
    for service in services:
        origin = service.get('origin_location')
        destination = service.get('destination_location')
        if not origin or not destination:
            continue
        
        key = (origin, destination)
        if key not in route_stats:
            route_stats[key] = {
                'origin': origin,
                'destination': destination,
                'total_services': 0,
                'start_date': None,
                'end_date': None,
                'durations': [],
                'hour_counter': Counter(),
                'total_stops': 0,
                'stop_samples': 0
            }
        
        entry = route_stats[key]
        entry['total_services'] += 1
        
        duration = calculate_duration_minutes(service)
        if duration is not None:
            entry['durations'].append(duration)
        
        svc_start = service.get('start_date')
        svc_end = service.get('end_date') or svc_start
        
        if svc_start and (entry['start_date'] is None or svc_start < entry['start_date']):
            entry['start_date'] = svc_start
        if svc_end and (entry['end_date'] is None or svc_end > entry['end_date']):
            entry['end_date'] = svc_end
        
        origin_time = service.get('origin_time')
        if isinstance(origin_time, time):
            entry['hour_counter'][origin_time.hour] += 1
        
        stops = service.get('intermediate_stops_count')
        if isinstance(stops, int):
            entry['total_stops'] += stops
            entry['stop_samples'] += 1
    
    aggregated = []
    for (origin, destination), entry in route_stats.items():
        durations = entry['durations']
        typical_duration = round(median(durations)) if durations else None
        avg_stops = entry['total_stops'] / entry['stop_samples'] if entry['stop_samples'] else 0
        
        start_date = entry['start_date']
        end_date = entry['end_date']
        total_days = (end_date - start_date).days + 1 if start_date and end_date else None
        services_per_day = entry['total_services'] / total_days if total_days else None
        
        if services_per_day:
            service_frequency = f"{services_per_day:.1f} per day"
        else:
            service_frequency = f"{entry['total_services']} services"
        
        peak_hours = [f"{hour:02d}:00" for hour, _ in entry['hour_counter'].most_common(3)]
        peak_times = ", ".join(peak_hours)
        
        if typical_duration and typical_duration >= 150:
            route_type = "long_distance"
        elif avg_stops >= 8:
            route_type = "intercity"
        else:
            route_type = "regional"
        
        if services_per_day and services_per_day >= 8:
            priority_tier = 1
        elif services_per_day and services_per_day >= 4:
            priority_tier = 2
        else:
            priority_tier = 3
        
        coverage_note = None
        if start_date and end_date:
            coverage_note = f"Timetable coverage {start_date} → {end_date} ({entry['total_services']} services)"
        
        aggregated.append({
            "route_id": f"{origin}-{destination}",
            "origin": origin,
            "destination": destination,
            "typical_duration_minutes": typical_duration,
            "service_frequency": service_frequency,
            "peak_times": peak_times,
            "route_type": route_type,
            "priority_tier": priority_tier,
            "notes": coverage_note,
            "start_date": start_date,
            "end_date": end_date
        })
    
    return aggregated

def sync_route_metadata_to_db(route_records, db_path: str):
    """Persist aggregated route metrics into route_metadata table"""
    if not route_records:
        print("⚠️ 没有可同步的路线数据")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 确保表存在（与collect_metadata保持一致）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS route_metadata (
            route_id TEXT PRIMARY KEY,
            origin_crs TEXT NOT NULL,
            destination_crs TEXT NOT NULL,
            distance_km REAL,
            typical_duration_minutes INTEGER,
            service_frequency TEXT,
            peak_times TEXT,
            route_type TEXT,
            priority_tier INTEGER DEFAULT 3,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    for record in route_records:
        cursor.execute("""
            INSERT INTO route_metadata (
                route_id,
                origin_crs,
                destination_crs,
                typical_duration_minutes,
                service_frequency,
                peak_times,
                route_type,
                priority_tier,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(route_id) DO UPDATE SET
                origin_crs=excluded.origin_crs,
                destination_crs=excluded.destination_crs,
                typical_duration_minutes=excluded.typical_duration_minutes,
                service_frequency=excluded.service_frequency,
                peak_times=excluded.peak_times,
                route_type=excluded.route_type,
                priority_tier=excluded.priority_tier,
                notes=excluded.notes,
                updated_at=CURRENT_TIMESTAMP
        """, (
            record["route_id"],
            record["origin"],
            record["destination"],
            record["typical_duration_minutes"],
            record["service_frequency"],
            record["peak_times"],
            record["route_type"],
            record["priority_tier"],
            record["notes"]
        ))
    
    conn.commit()
    conn.close()
    print(f"💾 已同步 {len(route_records)} 条路线到 route_metadata （数据库: {db_path}）")

def analyze_services(services):
    """分析服务数据"""
    print("\n" + "="*80)
    print("服务分析统计")
    print("="*80)
    
    # 按TOC统计
    toc_stats = defaultdict(int)
    route_stats = defaultdict(int)
    
    for service in services:
        toc = service.get('atoc_code', 'Unknown')
        toc_stats[toc] += 1
        
        origin = service.get('origin_location', 'Unknown')
        dest = service.get('destination_location', 'Unknown')
        route = f"{origin} → {dest}"
        route_stats[route] += 1
    
    print(f"\n总服务数: {len(services)}")
    
    print("\n按运营商统计:")
    for toc, count in sorted(toc_stats.items(), key=lambda x: x[1], reverse=True):
        print(f"  {toc}: {count} 个服务")
    
    print("\n热门路线 (前10):")
    for route, count in sorted(route_stats.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {route}: {count} 个服务")
    
    # 时间段分析
    hour_stats = defaultdict(int)
    for service in services:
        if service.get('origin_time'):
            hour = service['origin_time'].hour
            hour_stats[hour] += 1
    
    print("\n出发时间分布 (按小时):")
    for hour in sorted(hour_stats.keys()):
        count = hour_stats[hour]
        bar = '█' * (count // 5)  # 每个█代表5个服务
        print(f"  {hour:02d}:00 - {hour:02d}:59 | {bar} ({count})")

def main():
    parser = argparse.ArgumentParser(
        description='NRDP Timetable 数据分析工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 从本地目录读取MCA文件
  python analyze_nrdp_timetable.py --dir data/nrdp_timetable
  
  # 从指定的MCA文件读取
  python analyze_nrdp_timetable.py --file data/nrdp_timetable/RJTTF652.MCA
        """
    )
    parser.add_argument(
        '--dir',
        type=str,
        help='从本地目录读取MCA文件（会自动查找.MCA文件）'
    )
    parser.add_argument(
        '--file',
        type=str,
        help='从指定的MCA文件读取'
    )
    parser.add_argument(
        '--use-cached',
        action='store_true',
        help='优先使用已保存的解析数据，即便超过缓存有效期'
    )
    parser.add_argument(
        '--save',
        action='store_true',
        default=True,
        help='保存解析后的数据（默认开启）'
    )
    parser.add_argument(
        '--cache-ttl-days',
        type=int,
        default=30,
        help='缓存有效天数，默认30天'
    )
    parser.add_argument(
        '--force-parse',
        action='store_true',
        help='忽略缓存强制重新解析'
    )
    parser.add_argument(
        '--start-date',
        type=str,
        help='仅保留该日期（含）之后的服务，格式 YYYY-MM-DD'
    )
    parser.add_argument(
        '--end-date',
        type=str,
        help='仅保留该日期（含）之前的服务，格式 YYYY-MM-DD'
    )
    parser.add_argument(
        '--sync-db',
        action='store_true',
        help='将聚合后的路线指标写入 route_metadata 表'
    )
    parser.add_argument(
        '--db-path',
        type=str,
        default='data/railfair.db',
        help='SQLite 数据库路径（默认: data/railfair.db）'
    )
    
    args = parser.parse_args()
    
    # 检查是否使用已保存的数据
    parsed_data_file = Path('data/timetable_parsed.json')
    source_files: List[str] = []
    services = None
    date_range_info = None
    
    cache_metadata = None
    cache_age_days = None
    if parsed_data_file.exists():
        try:
            with open(parsed_data_file, 'r', encoding='utf-8') as f:
                cache_metadata = json.load(f)
                cache_age_days = get_cache_age_days(cache_metadata)
        except Exception:
            cache_metadata = None
            cache_age_days = None
    
    use_cache = False
    if cache_metadata and not args.force_parse:
        if args.use_cached:
            use_cache = True
        elif cache_age_days is not None and cache_age_days <= args.cache_ttl_days:
            use_cache = True
    
    if use_cache and parsed_data_file.exists():
        if cache_age_days is not None:
            print(f"📂 缓存命中: {parsed_data_file} （{cache_age_days} 天前生成）")
        else:
            print(f"📂 使用缓存: {parsed_data_file}")
        services, date_range_info = load_parsed_data(str(parsed_data_file))
        if services:
            print(f"✓ 加载成功: {len(services):,} 个服务")
            if isinstance(date_range_info, dict):
                source_files = date_range_info.get('files', [])
        else:
            print("✗ 缓存加载失败，将重新解析")
            services = None
            date_range_info = None
    elif cache_metadata and not args.force_parse and cache_age_days is not None and cache_age_days > args.cache_ttl_days:
        print(f"⚠️ 缓存已超过 {args.cache_ttl_days} 天（当前 {cache_age_days} 天），将重新解析")
    
    # 如果需要重新解析
    if services is None:
        cif_file_paths: List[Path] = []
        
        if args.dir:
            dir_path = Path(args.dir)
            if not dir_path.exists():
                print(f"✗ 错误: 目录不存在 {dir_path}")
                return
            mca_files = list(dir_path.glob('*.MCA')) + list(dir_path.glob('*.mca'))
            if not mca_files:
                print(f"✗ 错误: 在目录 {dir_path} 中未找到MCA文件")
                return
            cif_file_paths = sorted(mca_files)
            print(f"📂 从目录读取: {dir_path}")
            print(f"   找到 {len(cif_file_paths)} 个MCA文件")
        
        elif args.file:
            cif_file_path = Path(args.file)
            if not cif_file_path.exists():
                print(f"✗ 错误: 文件不存在 {cif_file_path}")
                return
            cif_file_paths = [cif_file_path]
        else:
            default_dir = Path('data/nrdp_timetable')
            if default_dir.exists():
                mca_files = list(default_dir.glob('*.MCA')) + list(default_dir.glob('*.mca'))
                if mca_files:
                    cif_file_paths = sorted(mca_files)
                    print(f"📂 使用默认目录: {default_dir}")
                    print(f"   找到 {len(cif_file_paths)} 个MCA文件")
                else:
                    print("✗ 错误: 请使用 --dir 或 --file 参数指定文件路径")
                    parser.print_help()
                    return
            else:
                print("✗ 错误: 请使用 --dir 或 --file 参数指定文件路径")
                parser.print_help()
                return
        
        if not cif_file_paths:
            print("✗ 未找到任何MCA文件")
            return
        
        services = []
        combined_start = None
        combined_end = None
        combined_sources = set()
        
        for idx, cif_file_path in enumerate(cif_file_paths, start=1):
            print(f"\n[{idx}/{len(cif_file_paths)}] 正在读取CIF文件: {cif_file_path}")
            try:
                with open(cif_file_path, 'r', encoding='latin-1', errors='ignore') as f:
                    cif_content = f.read()
                print(f"✓ 文件读取成功，大小: {len(cif_content):,} 字节")
            except FileNotFoundError:
                print(f"✗ 错误: 找不到文件 {cif_file_path}")
                return
            except Exception as e:
                print(f"✗ 读取文件时出错: {e}")
                return
            
            print("正在解析CIF数据...")
            file_date_range = extract_timetable_date_range(cif_content)
            file_services = extract_service_times(cif_content)
            services.extend(file_services)
            source_files.append(str(cif_file_path))
            
            file_start = parse_iso_date(file_date_range.get('start_date'))
            file_end = parse_iso_date(file_date_range.get('end_date'))
            if file_start and (combined_start is None or file_start < combined_start):
                combined_start = file_start
            if file_end and (combined_end is None or file_end > combined_end):
                combined_end = file_end
            if file_date_range.get('source'):
                combined_sources.add(file_date_range['source'])
            
            print(f"   解析完成: {len(file_services):,} 个服务（累计 {len(services):,}）")
        
        validity_days = (combined_end - combined_start).days + 1 if combined_start and combined_end else None
        date_range_info = {
            'start_date': combined_start.strftime('%Y-%m-%d') if combined_start else None,
            'end_date': combined_end.strftime('%Y-%m-%d') if combined_end else None,
            'validity_period': f"{validity_days} 天" if validity_days else None,
            'source': " | ".join(sorted(combined_sources)) if combined_sources else None,
            'file_count': len(source_files),
            'files': [Path(p).name for p in source_files]
        }
        
        if args.save:
            saved_path = save_parsed_data(services, date_range_info, source_files=source_files)
            print(f"💾 数据已保存到: {saved_path}")
    
    # 根据需要过滤日期
    filter_start = parse_date_string(args.start_date, "开始日期") if args.start_date else None
    filter_end = parse_date_string(args.end_date, "结束日期") if args.end_date else None
    if filter_start and filter_end and filter_start > filter_end:
        print("✗ 开始日期不能晚于结束日期")
        return
    
    filter_labels = []
    if filter_start:
        filter_labels.append(f">= {filter_start}")
    if filter_end:
        filter_labels.append(f"<= {filter_end}")
    active_filter_label = " & ".join(filter_labels) if filter_labels else "全部解析范围"

    original_count = len(services)
    services = filter_services_by_date_range(services, filter_start, filter_end)
    
    if original_count != len(services):
        print(f"🔍 已过滤: {original_count:,} → {len(services):,} 个服务（{active_filter_label}）")
    
    # 分析服务数据
    print("正在分析数据...")
    toc_stats = defaultdict(int)
    route_stats = defaultdict(int)  # 路线频率统计
    route_distance_stats = defaultdict(lambda: {'count': 0, 'total_stops': 0, 'avg_stops': 0})  # 路线距离统计（按中间站点数）
    hour_stats = defaultdict(int)
    
    for service in services:
        toc = service.get('atoc_code', 'Unknown')
        toc_stats[toc] += 1
        
        origin = service.get('origin_location', 'Unknown')
        dest = service.get('destination_location', 'Unknown')
        route = f"{origin} → {dest}"
        route_stats[route] += 1
        
        # 计算中间站点数量（用于判断长途路线）
        intermediate_stops_count = service.get('intermediate_stops_count', 0)
        if route not in route_distance_stats:
            route_distance_stats[route] = {'count': 0, 'total_stops': 0, 'avg_stops': 0}
        route_distance_stats[route]['count'] += 1
        route_distance_stats[route]['total_stops'] += intermediate_stops_count
        
        if service.get('origin_time'):
            hour = service['origin_time'].hour
            hour_stats[hour] += 1
    
    # 计算平均中间站点数
    for route in route_distance_stats:
        if route_distance_stats[route]['count'] > 0:
            route_distance_stats[route]['avg_stops'] = route_distance_stats[route]['total_stops'] / route_distance_stats[route]['count']
    
    # 显示总结
    print("\n" + "="*80)
    print("📊 分析总结")
    print("="*80)
    print(f"\n📎 数据范围: {active_filter_label}")
    
    # 时间范围信息
    if date_range_info['start_date'] and date_range_info['end_date']:
        print(f"\n📅 时刻表有效期:")
        print(f"   开始日期: {date_range_info['start_date']}")
        print(f"   结束日期: {date_range_info['end_date']}")
        print(f"   有效期: {date_range_info['validity_period']}")
        
        today = datetime.now().date()
        end_date = datetime.strptime(date_range_info['end_date'], '%Y-%m-%d').date()
        if end_date < today:
            days_old = (today - end_date).days
            print(f"   状态: ⚠️ 已过期 {days_old} 天")
        elif end_date >= today:
            days_remaining = (end_date - today).days
            print(f"   状态: ✅ 有效（剩余 {days_remaining} 天）")
    else:
        print(f"\n📅 时刻表有效期: ⚠️ 未能提取")
    
    # 服务统计
    print(f"\n🚂 服务统计:")
    print(f"   总服务数: {len(services):,}")
    print(f"   运营商数: {len(toc_stats)}")
    print(f"   路线数: {len(route_stats)}")
    
    # Top运营商
    print(f"\n📈 Top 5 运营商:")
    for toc, count in sorted(toc_stats.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"   {toc}: {count:,} 个服务")
    
    # Top路线（按频率）
    print(f"\n🛤️  Top 20 热门路线 (按服务频率):")
    for idx, (route, count) in enumerate(sorted(route_stats.items(), key=lambda x: x[1], reverse=True)[:20], 1):
        avg_stops = route_distance_stats.get(route, {}).get('avg_stops', 0)
        print(f"   {idx:2d}. {route}: {count:,} 个服务 (平均 {avg_stops:.1f} 个中间站点)")
    
    # Top长途路线（按中间站点数）
    print(f"\n🚄 Top 20 长途路线 (按平均中间站点数):")
    # 只考虑至少有10个服务的路线，避免单次服务的影响
    long_distance_routes = [
        (route, stats['avg_stops'], stats['count'])
        for route, stats in route_distance_stats.items()
        if stats['count'] >= 10 and stats['avg_stops'] > 0
    ]
    long_distance_routes.sort(key=lambda x: x[1], reverse=True)  # 按平均站点数排序
    
    for idx, (route, avg_stops, count) in enumerate(long_distance_routes[:20], 1):
        print(f"   {idx:2d}. {route}: 平均 {avg_stops:.1f} 个中间站点 ({count:,} 个服务)")
    
    # Top中频热门路线（热门但非超长途）
    print(f"\n⭐ Top 20 中频热门路线 (热门但非超长途):")
    # 过滤条件：平均中间站点数 <= 20（排除超长途），服务数 >= 20（确保热门）
    medium_distance_routes = [
        (route, count, route_distance_stats.get(route, {}).get('avg_stops', 0))
        for route, count in route_stats.items()
        if count >= 20 and route_distance_stats.get(route, {}).get('avg_stops', 0) <= 20
    ]
    medium_distance_routes.sort(key=lambda x: x[1], reverse=True)  # 按服务频率排序
    
    for idx, (route, count, avg_stops) in enumerate(medium_distance_routes[:20], 1):
        print(f"   {idx:2d}. {route}: {count:,} 个服务 (平均 {avg_stops:.1f} 个中间站点)")
    
    # 出发时间分布（只显示高峰时段）
    if hour_stats:
        print(f"\n⏰ 出发时间分布 (高峰时段):")
        peak_hours = sorted([h for h in hour_stats.keys() if 6 <= h <= 22])
        for hour in peak_hours[:10]:  # 只显示前10个
            count = hour_stats[hour]
            bar = '█' * min(count // 50, 20)  # 每个█代表50个服务，最多20个
            print(f"   {hour:02d}:00 - {hour:02d}:59 | {bar} {count:,}")
    
    if args.sync_db:
        print("\n🔄 正在同步路线元数据...")
        route_records = aggregate_route_metrics(services)
        sync_route_metadata_to_db(route_records, args.db_path)
    
    print("\n" + "="*80)

if __name__ == "__main__":
    main()