#!/usr/bin/env python3
"""
Day 5: 元数据收集脚本
收集并管理TOC补偿规则、站点信息等补充数据
"""

import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

class MetadataManager:
    """元数据管理器"""
    
    def __init__(self, db_path: str = "data/railfair.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self._create_metadata_tables()
    
    def _create_metadata_tables(self):
        """创建元数据表"""
        
        # TOC元数据表
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS toc_metadata (
                toc_code TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                full_name TEXT,
                compensation_minutes INTEGER DEFAULT 30,
                compensation_percentage REAL DEFAULT 25.0,
                reliability_tier TEXT DEFAULT 'standard',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 站点元数据表
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS station_metadata (
                crs_code TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                full_name TEXT,
                latitude REAL,
                longitude REAL,
                zone INTEGER,
                is_major_hub INTEGER DEFAULT 0,
                interchange_time_minutes INTEGER DEFAULT 5,
                platform_count INTEGER,
                facilities TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 路线元数据表
        self.cursor.execute("""
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
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (origin_crs) REFERENCES station_metadata(crs_code),
                FOREIGN KEY (destination_crs) REFERENCES station_metadata(crs_code)
            )
        """)
        
        # 延误补偿规则表
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS compensation_rules (
                rule_id INTEGER PRIMARY KEY AUTOINCREMENT,
                toc_code TEXT,
                delay_threshold_minutes INTEGER NOT NULL,
                compensation_type TEXT NOT NULL, -- 'percentage' or 'fixed'
                compensation_value REAL NOT NULL,
                applies_to TEXT DEFAULT 'all', -- 'all', 'advance', 'anytime'
                conditions TEXT,
                effective_from DATE,
                effective_to DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (toc_code) REFERENCES toc_metadata(toc_code)
            )
        """)
        
        self.conn.commit()
    
    def load_toc_metadata(self) -> Dict:
        """加载TOC元数据"""
        
        # UK主要列车运营公司数据
        toc_data = {
            "VT": {
                "name": "Avanti West Coast",
                "full_name": "Avanti West Coast Trains",
                "compensation_minutes": 30,
                "compensation_percentage": 25.0,
                "reliability_tier": "premium",
                "notes": "Long distance services, London-Scotland routes"
            },
            "GW": {
                "name": "GWR", 
                "full_name": "Great Western Railway",
                "compensation_minutes": 30,
                "compensation_percentage": 25.0,
                "reliability_tier": "premium",
                "notes": "London-West England/Wales services"
            },
            "EM": {
                "name": "EMR",
                "full_name": "East Midlands Railway",
                "compensation_minutes": 30,
                "compensation_percentage": 25.0,
                "reliability_tier": "standard",
                "notes": "London-East Midlands services"
            },
            "TP": {
                "name": "TransPennine Express",
                "full_name": "TransPennine Express",
                "compensation_minutes": 30,
                "compensation_percentage": 25.0,
                "reliability_tier": "challenged",
                "notes": "North England cross-country services, known delays"
            },
            "XC": {
                "name": "CrossCountry",
                "full_name": "CrossCountry Trains",
                "compensation_minutes": 30,
                "compensation_percentage": 25.0,
                "reliability_tier": "standard",
                "notes": "Long distance cross-country services"
            },
            "LM": {
                "name": "London Midland",
                "full_name": "West Midlands Trains",
                "compensation_minutes": 30,
                "compensation_percentage": 25.0,
                "reliability_tier": "standard",
                "notes": "London-Birmingham services"
            },
            "SR": {
                "name": "ScotRail",
                "full_name": "ScotRail Trains",
                "compensation_minutes": 30,
                "compensation_percentage": 25.0,
                "reliability_tier": "standard",
                "notes": "Scotland domestic services"
            },
            "GR": {
                "name": "LNER",
                "full_name": "London North Eastern Railway",
                "compensation_minutes": 30,
                "compensation_percentage": 25.0,
                "reliability_tier": "premium",
                "notes": "East Coast Main Line services"
            },
            "HX": {
                "name": "Heathrow Express",
                "full_name": "Heathrow Express",
                "compensation_minutes": 15,
                "compensation_percentage": 50.0,
                "reliability_tier": "premium",
                "notes": "Premium airport service, higher compensation"
            },
            "SE": {
                "name": "Southeastern",
                "full_name": "Southeastern Railway",
                "compensation_minutes": 30,
                "compensation_percentage": 25.0,
                "reliability_tier": "standard",
                "notes": "London-Southeast England services"
            },
            "SN": {
                "name": "Southern",
                "full_name": "Southern Railway",
                "compensation_minutes": 30,
                "compensation_percentage": 25.0,
                "reliability_tier": "standard",
                "notes": "London-South coast services"
            },
            "SW": {
                "name": "SWR",
                "full_name": "South Western Railway",
                "compensation_minutes": 30,
                "compensation_percentage": 25.0,
                "reliability_tier": "standard",
                "notes": "London-Southwest England services"
            },
            "NT": {
                "name": "Northern",
                "full_name": "Northern Trains",
                "compensation_minutes": 30,
                "compensation_percentage": 25.0,
                "reliability_tier": "challenged",
                "notes": "North England regional services"
            },
            "AW": {
                "name": "TfW Rail",
                "full_name": "Transport for Wales Rail",
                "compensation_minutes": 30,
                "compensation_percentage": 25.0,
                "reliability_tier": "standard",
                "notes": "Wales and Borders services"
            },
            "CC": {
                "name": "c2c",
                "full_name": "c2c Rail",
                "compensation_minutes": 30,
                "compensation_percentage": 25.0,
                "reliability_tier": "good",
                "notes": "London-Essex commuter services, good performance"
            },
            "CH": {
                "name": "Chiltern",
                "full_name": "Chiltern Railways",
                "compensation_minutes": 30,
                "compensation_percentage": 25.0,
                "reliability_tier": "good",
                "notes": "London-Birmingham alternative route"
            },
            "GA": {
                "name": "Greater Anglia",
                "full_name": "Greater Anglia Railway",
                "compensation_minutes": 30,
                "compensation_percentage": 25.0,
                "reliability_tier": "standard",
                "notes": "London-East Anglia services"
            },
            "GX": {
                "name": "Gatwick Express",
                "full_name": "Gatwick Express",
                "compensation_minutes": 15,
                "compensation_percentage": 50.0,
                "reliability_tier": "premium",
                "notes": "Airport service, higher compensation"
            },
            "TL": {
                "name": "Thameslink",
                "full_name": "Thameslink Railway",
                "compensation_minutes": 30,
                "compensation_percentage": 25.0,
                "reliability_tier": "standard",
                "notes": "North-South London through services"
            },
            "ME": {
                "name": "Merseyrail",
                "full_name": "Merseyrail",
                "compensation_minutes": 30,
                "compensation_percentage": 25.0,
                "reliability_tier": "good",
                "notes": "Liverpool area services"
            }
        }
        
        # 插入或更新TOC数据
        inserted = 0
        updated = 0
        
        for toc_code, data in toc_data.items():
            existing = self.cursor.execute(
                "SELECT 1 FROM toc_metadata WHERE toc_code = ?", 
                (toc_code,)
            ).fetchone()
            
            if existing:
                self.cursor.execute("""
                    UPDATE toc_metadata 
                    SET name = ?, full_name = ?, compensation_minutes = ?,
                        compensation_percentage = ?, reliability_tier = ?,
                        notes = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE toc_code = ?
                """, (
                    data["name"], data["full_name"], 
                    data["compensation_minutes"], data["compensation_percentage"],
                    data["reliability_tier"], data["notes"], toc_code
                ))
                updated += 1
            else:
                self.cursor.execute("""
                    INSERT INTO toc_metadata (
                        toc_code, name, full_name, compensation_minutes,
                        compensation_percentage, reliability_tier, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    toc_code, data["name"], data["full_name"],
                    data["compensation_minutes"], data["compensation_percentage"],
                    data["reliability_tier"], data["notes"]
                ))
                inserted += 1
        
        self.conn.commit()
        
        return {
            "inserted": inserted,
            "updated": updated,
            "total": len(toc_data)
        }
    
    def load_station_metadata(self) -> Dict:
        """加载站点元数据"""
        
        # 主要站点数据（与路线相关的关键站点）
        station_data = {
            # London Terminals
            "EUS": {
                "name": "London Euston",
                "latitude": 51.5284, "longitude": -0.1337,
                "zone": 1, "is_major_hub": 1, "platform_count": 18,
                "interchange_time_minutes": 10
            },
            "KGX": {
                "name": "London King's Cross",
                "latitude": 51.5308, "longitude": -0.1238,
                "zone": 1, "is_major_hub": 1, "platform_count": 12,
                "interchange_time_minutes": 10
            },
            "PAD": {
                "name": "London Paddington",
                "latitude": 51.5154, "longitude": -0.1755,
                "zone": 1, "is_major_hub": 1, "platform_count": 14,
                "interchange_time_minutes": 10
            },
            "LST": {
                "name": "London Liverpool Street",
                "latitude": 51.5178, "longitude": -0.0823,
                "zone": 1, "is_major_hub": 1, "platform_count": 18,
                "interchange_time_minutes": 10
            },
            "VIC": {
                "name": "London Victoria",
                "latitude": 51.4952, "longitude": -0.1439,
                "zone": 1, "is_major_hub": 1, "platform_count": 19,
                "interchange_time_minutes": 10
            },
            "WAT": {
                "name": "London Waterloo",
                "latitude": 51.5031, "longitude": -0.1132,
                "zone": 1, "is_major_hub": 1, "platform_count": 22,
                "interchange_time_minutes": 10
            },
            "STP": {
                "name": "London St Pancras",
                "latitude": 51.5326, "longitude": -0.1252,
                "zone": 1, "is_major_hub": 1, "platform_count": 15,
                "interchange_time_minutes": 5
            },
            
            # Major Cities
            "MAN": {
                "name": "Manchester Piccadilly",
                "latitude": 53.4774, "longitude": -2.2309,
                "zone": None, "is_major_hub": 1, "platform_count": 14,
                "interchange_time_minutes": 8
            },
            "BHM": {
                "name": "Birmingham New Street",
                "latitude": 52.4778, "longitude": -1.9003,
                "zone": None, "is_major_hub": 1, "platform_count": 13,
                "interchange_time_minutes": 10
            },
            "EDR": {
                "name": "Edinburgh Waverley",
                "latitude": 55.9521, "longitude": -3.1899,
                "zone": None, "is_major_hub": 1, "platform_count": 20,
                "interchange_time_minutes": 8
            },
            "GLC": {
                "name": "Glasgow Central",
                "latitude": 55.8585, "longitude": -4.2579,
                "zone": None, "is_major_hub": 1, "platform_count": 17,
                "interchange_time_minutes": 8
            },
            "BRI": {
                "name": "Bristol Temple Meads",
                "latitude": 51.4491, "longitude": -2.5813,
                "zone": None, "is_major_hub": 1, "platform_count": 13,
                "interchange_time_minutes": 7
            },
            "LEE": {
                "name": "Leeds",
                "latitude": 53.7959, "longitude": -1.5480,
                "zone": None, "is_major_hub": 1, "platform_count": 17,
                "interchange_time_minutes": 8
            },
            "LIV": {
                "name": "Liverpool Lime Street",
                "latitude": 53.4075, "longitude": -2.9776,
                "zone": None, "is_major_hub": 1, "platform_count": 10,
                "interchange_time_minutes": 7
            },
            "NRW": {
                "name": "Norwich",
                "latitude": 52.6271, "longitude": 1.3069,
                "zone": None, "is_major_hub": 0, "platform_count": 6,
                "interchange_time_minutes": 5
            },
            "NCL": {
                "name": "Newcastle",
                "latitude": 54.9681, "longitude": -1.6174,
                "zone": None, "is_major_hub": 1, "platform_count": 12,
                "interchange_time_minutes": 7
            },
            "CDF": {
                "name": "Cardiff Central",
                "latitude": 51.4759, "longitude": -3.1785,
                "zone": None, "is_major_hub": 1, "platform_count": 7,
                "interchange_time_minutes": 6
            },
            "SHF": {
                "name": "Sheffield",
                "latitude": 53.3781, "longitude": -1.4621,
                "zone": None, "is_major_hub": 0, "platform_count": 8,
                "interchange_time_minutes": 6
            },
            "NTH": {
                "name": "Northampton",
                "latitude": 52.2377, "longitude": -0.9065,
                "zone": None, "is_major_hub": 0, "platform_count": 5,
                "interchange_time_minutes": 5
            },
            "BTN": {
                "name": "Brighton",
                "latitude": 50.8295, "longitude": -0.1412,
                "zone": None, "is_major_hub": 0, "platform_count": 8,
                "interchange_time_minutes": 5
            },
            "RDG": {
                "name": "Reading",
                "latitude": 51.4590, "longitude": -0.9724,
                "zone": None, "is_major_hub": 1, "platform_count": 15,
                "interchange_time_minutes": 8
            },
            "OXF": {
                "name": "Oxford",
                "latitude": 51.7535, "longitude": -1.2698,
                "zone": None, "is_major_hub": 0, "platform_count": 5,
                "interchange_time_minutes": 5
            }
        }
        
        # 插入或更新站点数据
        inserted = 0
        updated = 0
        
        for crs_code, data in station_data.items():
            existing = self.cursor.execute(
                "SELECT 1 FROM station_metadata WHERE crs_code = ?",
                (crs_code,)
            ).fetchone()
            
            if existing:
                self.cursor.execute("""
                    UPDATE station_metadata 
                    SET name = ?, latitude = ?, longitude = ?,
                        zone = ?, is_major_hub = ?, platform_count = ?,
                        interchange_time_minutes = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE crs_code = ?
                """, (
                    data["name"], data.get("latitude"), data.get("longitude"),
                    data.get("zone"), data.get("is_major_hub", 0),
                    data.get("platform_count"), data.get("interchange_time_minutes", 5),
                    crs_code
                ))
                updated += 1
            else:
                self.cursor.execute("""
                    INSERT INTO station_metadata (
                        crs_code, name, latitude, longitude, zone,
                        is_major_hub, platform_count, interchange_time_minutes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    crs_code, data["name"], data.get("latitude"),
                    data.get("longitude"), data.get("zone"),
                    data.get("is_major_hub", 0), data.get("platform_count"),
                    data.get("interchange_time_minutes", 5)
                ))
                inserted += 1
        
        self.conn.commit()
        
        return {
            "inserted": inserted,
            "updated": updated,
            "total": len(station_data)
        }
    
    def load_route_metadata(self) -> Dict:
        """加载路线元数据"""
        
        # 10条关键路线的元数据
        route_data = [
            {
                "route_id": "EUS-MAN",
                "origin": "EUS", "destination": "MAN",
                "distance_km": 296, "typical_duration_minutes": 127,
                "service_frequency": "2-3 per hour peak",
                "route_type": "intercity", "priority_tier": 1
            },
            {
                "route_id": "KGX-EDR",
                "origin": "KGX", "destination": "EDR",
                "distance_km": 632, "typical_duration_minutes": 270,
                "service_frequency": "2 per hour",
                "route_type": "long-distance", "priority_tier": 1
            },
            {
                "route_id": "PAD-BRI",
                "origin": "PAD", "destination": "BRI",
                "distance_km": 191, "typical_duration_minutes": 105,
                "service_frequency": "2 per hour",
                "route_type": "intercity", "priority_tier": 1
            },
            {
                "route_id": "LST-NRW",
                "origin": "LST", "destination": "NRW",
                "distance_km": 183, "typical_duration_minutes": 110,
                "service_frequency": "2 per hour",
                "route_type": "regional", "priority_tier": 2
            },
            {
                "route_id": "VIC-BHM",
                "origin": "VIC", "destination": "BHM",
                "distance_km": 171, "typical_duration_minutes": 120,
                "service_frequency": "1-2 per hour",
                "route_type": "intercity", "priority_tier": 2
            },
            {
                "route_id": "MAN-LIV",
                "origin": "MAN", "destination": "LIV",
                "distance_km": 50, "typical_duration_minutes": 45,
                "service_frequency": "3-4 per hour",
                "route_type": "regional", "priority_tier": 2
            },
            {
                "route_id": "BHM-MAN",
                "origin": "BHM", "destination": "MAN",
                "distance_km": 141, "typical_duration_minutes": 88,
                "service_frequency": "2 per hour",
                "route_type": "intercity", "priority_tier": 2
            },
            {
                "route_id": "BRI-BHM",
                "origin": "BRI", "destination": "BHM",
                "distance_km": 142, "typical_duration_minutes": 85,
                "service_frequency": "1-2 per hour",
                "route_type": "intercity", "priority_tier": 3
            },
            {
                "route_id": "EDR-GLC",
                "origin": "EDR", "destination": "GLC",
                "distance_km": 75, "typical_duration_minutes": 50,
                "service_frequency": "4 per hour",
                "route_type": "regional", "priority_tier": 3
            },
            {
                "route_id": "MAN-LEE",
                "origin": "MAN", "destination": "LEE",
                "distance_km": 64, "typical_duration_minutes": 55,
                "service_frequency": "2-3 per hour",
                "route_type": "regional", "priority_tier": 3
            }
        ]
        
        inserted = 0
        updated = 0
        
        for route in route_data:
            existing = self.cursor.execute(
                "SELECT 1 FROM route_metadata WHERE route_id = ?",
                (route["route_id"],)
            ).fetchone()
            
            if existing:
                self.cursor.execute("""
                    UPDATE route_metadata 
                    SET distance_km = ?, typical_duration_minutes = ?,
                        service_frequency = ?, route_type = ?,
                        priority_tier = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE route_id = ?
                """, (
                    route["distance_km"], route["typical_duration_minutes"],
                    route["service_frequency"], route["route_type"],
                    route["priority_tier"], route["route_id"]
                ))
                updated += 1
            else:
                self.cursor.execute("""
                    INSERT INTO route_metadata (
                        route_id, origin_crs, destination_crs, distance_km,
                        typical_duration_minutes, service_frequency,
                        route_type, priority_tier
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    route["route_id"], route["origin"], route["destination"],
                    route["distance_km"], route["typical_duration_minutes"],
                    route["service_frequency"], route["route_type"],
                    route["priority_tier"]
                ))
                inserted += 1
        
        self.conn.commit()
        
        return {
            "inserted": inserted,
            "updated": updated,
            "total": len(route_data)
        }
    
    def load_compensation_rules(self) -> Dict:
        """加载延误补偿规则"""
        
        # UK标准延误补偿规则
        rules = [
            # 15-29分钟延误规则
            {
                "delay_threshold_minutes": 15,
                "compensation_type": "percentage",
                "compensation_value": 25.0,
                "applies_to": "single",
                "conditions": "Single tickets, 15-29 minutes late"
            },
            {
                "delay_threshold_minutes": 15,
                "compensation_type": "percentage",
                "compensation_value": 12.5,
                "applies_to": "return",
                "conditions": "Return tickets, 15-29 minutes late"
            },
            # 30-59分钟延误规则
            {
                "delay_threshold_minutes": 30,
                "compensation_type": "percentage",
                "compensation_value": 50.0,
                "applies_to": "single",
                "conditions": "Single tickets, 30-59 minutes late"
            },
            {
                "delay_threshold_minutes": 30,
                "compensation_type": "percentage",
                "compensation_value": 25.0,
                "applies_to": "return",
                "conditions": "Return tickets, 30-59 minutes late"
            },
            # 60-119分钟延误规则
            {
                "delay_threshold_minutes": 60,
                "compensation_type": "percentage",
                "compensation_value": 100.0,
                "applies_to": "single",
                "conditions": "Single tickets, 60-119 minutes late"
            },
            {
                "delay_threshold_minutes": 60,
                "compensation_type": "percentage",
                "compensation_value": 50.0,
                "applies_to": "return",
                "conditions": "Return tickets, 60-119 minutes late"
            },
            # 120+分钟延误规则
            {
                "delay_threshold_minutes": 120,
                "compensation_type": "percentage",
                "compensation_value": 100.0,
                "applies_to": "return",
                "conditions": "Return tickets, 120+ minutes late"
            }
        ]
        
        inserted = 0
        
        for rule in rules:
            self.cursor.execute("""
                INSERT INTO compensation_rules (
                    delay_threshold_minutes, compensation_type,
                    compensation_value, applies_to, conditions
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                rule["delay_threshold_minutes"], rule["compensation_type"],
                rule["compensation_value"], rule["applies_to"],
                rule["conditions"]
            ))
            inserted += 1
        
        self.conn.commit()
        
        return {
            "inserted": inserted,
            "total": len(rules)
        }
    
    def enrich_existing_data(self):
        """使用元数据丰富现有数据"""
        
        # 先检查并添加列如果不存在
        self.cursor.execute("""
            SELECT COUNT(*) FROM pragma_table_info('hsp_service_details')
            WHERE name = 'location_name'
        """)
        
        has_location_name = self.cursor.fetchone()[0] > 0
        
        self.cursor.execute("""
            SELECT COUNT(*) FROM pragma_table_info('hsp_service_details')
            WHERE name = 'toc_name'
        """)
        
        has_toc_name = self.cursor.fetchone()[0] > 0
        
        # 添加缺失的列
        if not has_location_name:
            self.cursor.execute("""
                ALTER TABLE hsp_service_details
                ADD COLUMN location_name TEXT
            """)
        
        if not has_toc_name:
            self.cursor.execute("""
                ALTER TABLE hsp_service_details
                ADD COLUMN toc_name TEXT
            """)
        
        # 更新TOC名称
        self.cursor.execute("""
            UPDATE hsp_service_details
            SET toc_name = (
                SELECT name FROM toc_metadata 
                WHERE toc_metadata.toc_code = hsp_service_details.toc_code
            )
            WHERE EXISTS (
                SELECT 1 FROM toc_metadata 
                WHERE toc_metadata.toc_code = hsp_service_details.toc_code
            )
        """)
        
        # 更新站点名称
        self.cursor.execute("""
            UPDATE hsp_service_details
            SET location_name = (
                SELECT name FROM station_metadata 
                WHERE station_metadata.crs_code = hsp_service_details.location
            )
            WHERE EXISTS (
                SELECT 1 FROM station_metadata 
                WHERE station_metadata.crs_code = hsp_service_details.location
            )
        """)
        
        affected = self.cursor.rowcount
        self.conn.commit()
        
        return affected
    
    def generate_metadata_report(self) -> str:
        """生成元数据报告"""
        
        report = []
        report.append("=" * 60)
        report.append("METADATA SUMMARY REPORT")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 60)
        
        # TOC统计
        toc_count = self.cursor.execute(
            "SELECT COUNT(*) FROM toc_metadata"
        ).fetchone()[0]
        
        toc_tiers = self.cursor.execute("""
            SELECT reliability_tier, COUNT(*) 
            FROM toc_metadata 
            GROUP BY reliability_tier
        """).fetchall()
        
        report.append("\n🚂 TOC Metadata")
        report.append("-" * 40)
        report.append(f"Total TOCs: {toc_count}")
        for tier, count in toc_tiers:
            report.append(f"  {tier}: {count} TOCs")
        
        # 站点统计
        station_count = self.cursor.execute(
            "SELECT COUNT(*) FROM station_metadata"
        ).fetchone()[0]
        
        hub_count = self.cursor.execute(
            "SELECT COUNT(*) FROM station_metadata WHERE is_major_hub = 1"
        ).fetchone()[0]
        
        report.append("\n🚉 Station Metadata")
        report.append("-" * 40)
        report.append(f"Total Stations: {station_count}")
        report.append(f"Major Hubs: {hub_count}")
        
        # 路线统计
        route_count = self.cursor.execute(
            "SELECT COUNT(*) FROM route_metadata"
        ).fetchone()[0]
        
        route_tiers = self.cursor.execute("""
            SELECT priority_tier, COUNT(*) 
            FROM route_metadata 
            GROUP BY priority_tier
        """).fetchall()
        
        report.append("\n🛤️ Route Metadata")
        report.append("-" * 40)
        report.append(f"Total Routes: {route_count}")
        for tier, count in route_tiers:
            report.append(f"  Tier {tier}: {count} routes")
        
        # 补偿规则统计
        rule_count = self.cursor.execute(
            "SELECT COUNT(*) FROM compensation_rules"
        ).fetchone()[0]
        
        report.append("\n💷 Compensation Rules")
        report.append("-" * 40)
        report.append(f"Total Rules: {rule_count}")
        
        # 数据丰富统计
        enriched_toc = self.cursor.execute("""
            SELECT COUNT(DISTINCT toc_code)
            FROM hsp_service_details
            WHERE toc_name IS NOT NULL
        """).fetchone()[0]
        
        enriched_station = self.cursor.execute("""
            SELECT COUNT(DISTINCT location)
            FROM hsp_service_details
            WHERE location_name IS NOT NULL
        """).fetchone()[0]
        
        report.append("\n✅ Data Enrichment")
        report.append("-" * 40)
        report.append(f"TOCs with names: {enriched_toc}")
        report.append(f"Stations with names: {enriched_station}")
        
        return "\n".join(report)
    
    def close(self):
        """关闭数据库连接"""
        self.conn.close()


def main():
    """主函数"""
    print("🔧 Loading metadata into database...")
    print("=" * 60)
    
    # 创建data目录
    Path("data").mkdir(exist_ok=True)
    
    # 初始化管理器
    manager = MetadataManager()
    
    try:
        # 加载TOC元数据
        print("\n📌 Loading TOC metadata...")
        toc_result = manager.load_toc_metadata()
        print(f"  Inserted: {toc_result['inserted']}")
        print(f"  Updated: {toc_result['updated']}")
        print(f"  Total: {toc_result['total']}")
        
        # 加载站点元数据
        print("\n📌 Loading station metadata...")
        station_result = manager.load_station_metadata()
        print(f"  Inserted: {station_result['inserted']}")
        print(f"  Updated: {station_result['updated']}")
        print(f"  Total: {station_result['total']}")
        
        # 加载路线元数据
        print("\n📌 Loading route metadata...")
        route_result = manager.load_route_metadata()
        print(f"  Inserted: {route_result['inserted']}")
        print(f"  Updated: {route_result['updated']}")
        print(f"  Total: {route_result['total']}")
        
        # 加载补偿规则
        print("\n📌 Loading compensation rules...")
        comp_result = manager.load_compensation_rules()
        print(f"  Inserted: {comp_result['inserted']}")
        print(f"  Total: {comp_result['total']}")
        
        # 丰富现有数据
        print("\n📌 Enriching existing data...")
        affected = manager.enrich_existing_data()
        print(f"  Records enriched: {affected}")
        
        # 生成报告
        print("\n" + "=" * 60)
        report = manager.generate_metadata_report()
        print(report)
        
        # 保存报告
        report_file = "data/metadata_report.txt"
        with open(report_file, 'w') as f:
            f.write(report)
        print(f"\n📄 Report saved to: {report_file}")
        
    finally:
        manager.close()
    
    print("\n✅ Metadata loading complete!")


if __name__ == "__main__":
    main()
