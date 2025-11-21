"""
UK Rail Delay Predictor - Database Initialization
Day 2: Create and populate SQLite database
Created: 2025-11-12
"""

import sqlite3
import os
from pathlib import Path
from datetime import datetime


class DatabaseInitializer:
    """数据库初始化类"""
    
    def __init__(self, db_path: str = "data/railfair.db", schema_path: str = "database_schema.sql"):
        self.db_path = db_path
        self.schema_path = schema_path
        self.conn = None
        self.cursor = None
    
    def ensure_data_directory(self):
        """确保data目录存在"""
        data_dir = Path(self.db_path).parent
        if not data_dir.exists():
            data_dir.mkdir(parents=True, exist_ok=True)
            print(f"✅ 创建目录: {data_dir}")
        else:
            print(f"✓ 目录已存在: {data_dir}")
    
    def create_database(self):
        """创建数据库并执行Schema"""
        try:
            # 确保目录存在
            self.ensure_data_directory()
            
            # 如果数据库已存在,先备份
            if Path(self.db_path).exists():
                backup_path = f"{self.db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                os.rename(self.db_path, backup_path)
                print(f"⚠️  已备份现有数据库到: {backup_path}")
            
            # 连接数据库
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            print(f"✅ 数据库连接成功: {self.db_path}")
            
            # 读取并执行Schema
            if not Path(self.schema_path).exists():
                raise FileNotFoundError(f"Schema文件不存在: {self.schema_path}")
            
            with open(self.schema_path, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
            
            # 执行Schema (使用executescript以支持多条语句)
            self.cursor.executescript(schema_sql)
            self.conn.commit()
            print("✅ Schema创建成功")
            
            return True
            
        except Exception as e:
            print(f"❌ 创建数据库失败: {e}")
            if self.conn:
                self.conn.rollback()
            return False
    
    def verify_tables(self):
        """验证所有表是否创建成功"""
        expected_tables = [
            'stations',
            'train_operators',
            'train_types',
            'routes',
            'services',
            'service_stops',
            'fares',
            'delay_records',
            'weather_data',
            'query_history',
            'prediction_cache'
        ]
        
        try:
            self.cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            actual_tables = [row[0] for row in self.cursor.fetchall()]
            
            print("\n📋 表创建验证:")
            missing_tables = []
            
            for table in expected_tables:
                if table in actual_tables:
                    print(f"  ✅ {table}")
                else:
                    print(f"  ❌ {table} (缺失)")
                    missing_tables.append(table)
            
            if missing_tables:
                print(f"\n⚠️  缺失 {len(missing_tables)} 个表")
                return False
            else:
                print(f"\n✅ 所有 {len(expected_tables)} 个表创建成功")
                return True
                
        except Exception as e:
            print(f"❌ 验证表失败: {e}")
            return False
    
    def verify_indexes(self):
        """验证索引是否创建成功"""
        try:
            self.cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%' ORDER BY name"
            )
            indexes = [row[0] for row in self.cursor.fetchall()]
            
            print(f"\n🔍 索引验证: 共创建 {len(indexes)} 个索引")
            for idx in indexes[:10]:  # 只显示前10个
                print(f"  ✅ {idx}")
            if len(indexes) > 10:
                print(f"  ... 还有 {len(indexes) - 10} 个索引")
            
            return len(indexes) > 0
            
        except Exception as e:
            print(f"❌ 验证索引失败: {e}")
            return False
    
    def verify_views(self):
        """验证视图是否创建成功"""
        expected_views = ['popular_routes', 'delay_statistics']
        
        try:
            self.cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='view' ORDER BY name"
            )
            actual_views = [row[0] for row in self.cursor.fetchall()]
            
            print(f"\n👁️  视图验证:")
            for view in expected_views:
                if view in actual_views:
                    print(f"  ✅ {view}")
                else:
                    print(f"  ❌ {view} (缺失)")
            
            return len(actual_views) >= len(expected_views)
            
        except Exception as e:
            print(f"❌ 验证视图失败: {e}")
            return False
    
    def verify_triggers(self):
        """验证触发器是否创建成功"""
        try:
            self.cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='trigger' ORDER BY name"
            )
            triggers = [row[0] for row in self.cursor.fetchall()]
            
            print(f"\n⚡ 触发器验证: 共创建 {len(triggers)} 个触发器")
            for trigger in triggers:
                print(f"  ✅ {trigger}")
            
            return len(triggers) > 0
            
        except Exception as e:
            print(f"❌ 验证触发器失败: {e}")
            return False
    
    def test_insert_data(self):
        """测试数据插入"""
        print("\n🧪 测试数据插入:")
        
        try:
            # 测试查询示例数据
            self.cursor.execute("SELECT COUNT(*) FROM stations")
            station_count = self.cursor.fetchone()[0]
            print(f"  ✅ 车站表: {station_count} 条记录")
            
            self.cursor.execute("SELECT COUNT(*) FROM train_operators")
            operator_count = self.cursor.fetchone()[0]
            print(f"  ✅ 运营商表: {operator_count} 条记录")
            
            # 测试插入新数据
            test_station = ('TST', 'Test Station', 51.5, -0.1, 'Test Region', 1, 1)
            self.cursor.execute(
                """INSERT INTO stations 
                (station_code, station_name, latitude, longitude, region, zone, is_active) 
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                test_station
            )
            self.conn.commit()
            print("  ✅ 成功插入测试车站")
            
            # 删除测试数据
            self.cursor.execute("DELETE FROM stations WHERE station_code = 'TST'")
            self.conn.commit()
            print("  ✅ 成功删除测试车站")
            
            return True
            
        except Exception as e:
            print(f"  ❌ 数据插入测试失败: {e}")
            self.conn.rollback()
            return False
    
    def test_indexes(self):
        """测试索引效果"""
        print("\n⚡ 测试索引效果:")
        
        try:
            # 测试无索引查询
            import time
            
            # 插入更多测试数据
            test_data = [
                (f'T{i:02d}', f'Test Station {i}', 51.5 + i*0.01, -0.1 + i*0.01, 'Test', None, 1)
                for i in range(100)
            ]
            self.cursor.executemany(
                """INSERT INTO stations 
                (station_code, station_name, latitude, longitude, region, zone, is_active) 
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                test_data
            )
            self.conn.commit()
            
            # 测试索引查询
            start = time.time()
            self.cursor.execute("SELECT * FROM stations WHERE station_code = 'T50'")
            result = self.cursor.fetchone()
            elapsed = (time.time() - start) * 1000
            
            if result:
                print(f"  ✅ 索引查询成功 (用时: {elapsed:.2f}ms)")
            
            # 清理测试数据
            self.cursor.execute("DELETE FROM stations WHERE station_code LIKE 'T%'")
            self.conn.commit()
            
            return True
            
        except Exception as e:
            print(f"  ❌ 索引测试失败: {e}")
            self.conn.rollback()
            return False
    
    def get_database_info(self):
        """获取数据库信息"""
        print("\n📊 数据库信息:")
        
        try:
            # 数据库大小
            db_size = Path(self.db_path).stat().st_size
            print(f"  数据库大小: {db_size / 1024:.2f} KB")
            
            # SQLite版本
            self.cursor.execute("SELECT sqlite_version()")
            version = self.cursor.fetchone()[0]
            print(f"  SQLite版本: {version}")
            
            # PRAGMA信息
            self.cursor.execute("PRAGMA foreign_keys")
            fk_status = self.cursor.fetchone()[0]
            print(f"  外键约束: {'启用' if fk_status else '禁用'}")
            
            self.cursor.execute("PRAGMA journal_mode")
            journal = self.cursor.fetchone()[0]
            print(f"  日志模式: {journal}")
            
            return True
            
        except Exception as e:
            print(f"  ❌ 获取数据库信息失败: {e}")
            return False
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            print("\n✅ 数据库连接已关闭")
    
    def run_full_initialization(self):
        """运行完整的初始化流程"""
        print("=" * 60)
        print("🚀 UK Rail Delay Predictor - 数据库初始化")
        print("=" * 60)
        
        # 创建数据库
        if not self.create_database():
            self.close()
            return False
        
        # 验证表
        if not self.verify_tables():
            self.close()
            return False
        
        # 验证索引
        self.verify_indexes()
        
        # 验证视图
        self.verify_views()
        
        # 验证触发器
        self.verify_triggers()
        
        # 测试数据插入
        if not self.test_insert_data():
            self.close()
            return False
        
        # 测试索引
        self.test_indexes()
        
        # 获取数据库信息
        self.get_database_info()
        
        # 关闭连接
        self.close()
        
        print("\n" + "=" * 60)
        print("✅ 数据库初始化完成!")
        print("=" * 60)
        
        return True


def main():
    """主函数"""
    # 初始化数据库
    initializer = DatabaseInitializer()
    success = initializer.run_full_initialization()
    
    if success:
        print("\n✨ 数据库已准备就绪,可以开始开发了!")
        return 0
    else:
        print("\n❌ 数据库初始化失败,请检查错误信息")
        return 1


if __name__ == "__main__":
    exit(main())
