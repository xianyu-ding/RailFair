"""
RailFair V1 - 票价获取与缓存系统
=====================================

基于 National Rail Data Portal (NRDP) 官方API的票价数据获取系统

核心功能：
1. NRDP API 认证与数据下载
2. Fares 固定格式文件解析
3. 价格缓存机制（避免重复请求）
4. 多票种对比（Advance/Off-Peak/Anytime）
5. 价格变化追踪

数据来源：
- NRDP Fares API: https://opendata.nationalrail.co.uk/api/staticfeeds/2.0/fares
- 规范文档: RSPS5045 Fares and associated data feed interface specification

作者: Vanessa @ RailFair
日期: Day 9 - Week 2
"""

import requests
import logging
import json
import zipfile
import io
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import hashlib
import time

# 尝试导入 dotenv，如果失败则使用 os.getenv
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # 如果未安装 dotenv，使用 os.getenv 也可以

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================
# 数据模型
# ============================================

class TicketType(Enum):
    """
    票种类型
    
    Advance票：提前预订票，最便宜但不可退改，需要提前购买（通常提前数天到数周）
    Off-Peak票：非高峰票，中等价格，在非高峰时段使用（避开早晚高峰）
    Anytime票：随时票，最贵但最灵活，任何时段都可使用，可退改
    """
    ADVANCE = "advance"              # Advance票：提前预订票，最便宜但不可退改，需提前购买
    OFF_PEAK = "off_peak"            # Off-Peak票：非高峰票，中等价格，在非高峰时段使用
    ANYTIME = "anytime"              # Anytime票：随时票，最贵但最灵活，任何时段都可使用
    SUPER_OFF_PEAK = "super_off_peak"  # Super Off-Peak票：超级非高峰票，比Off-Peak更便宜
    SEASON = "season"                # Season票：季票，长期有效


class TicketClass(Enum):
    """座位等级"""
    STANDARD = "standard"  # 标准座
    FIRST = "first"        # 头等座


@dataclass
class FareInfo:
    """票价信息"""
    # 基本信息
    origin: str                  # 起点CRS/NLC
    destination: str             # 终点CRS/NLC
    ticket_type: TicketType      # 票种
    ticket_class: TicketClass    # 等级
    
    # 价格信息
    adult_fare: float            # 成人票价（便士）
    child_fare: Optional[float]  # 儿童票价（便士）
    
    # 有效期信息
    valid_from: datetime         # 有效起始日期
    valid_until: datetime        # 有效结束日期
    
    # 限制信息
    route_code: Optional[str]    # 路线代码
    restriction_code: Optional[str]  # 限制代码
    
    # TOC信息（票价制定者）
    toc_code: Optional[str] = None  # TOC代码（Train Operating Company，设置票价的铁路公司）
    toc_name: Optional[str] = None  # TOC名称
    
    # 元数据
    last_updated: datetime = None  # 最后更新时间
    data_source: str = "NRDP_REAL"  # 数据来源


@dataclass
class FareComparison:
    """票价对比结果"""
    origin: str
    destination: str
    departure_date: datetime
    
    # 各票种价格（便士）
    advance_price: Optional[float]
    off_peak_price: Optional[float]
    anytime_price: Optional[float]
    
    # 推荐信息
    cheapest_type: TicketType
    cheapest_price: float
    savings_amount: float        # 相对最贵票种的节省
    savings_percentage: float    # 节省百分比
    
    # 缓存信息
    cached: bool
    cache_age_hours: float
    data_source: str = "NRDP_SIMULATED"  # 数据来源


# ============================================
# NRDP API 客户端
# ============================================

class NRDPClient:
    """
    National Rail Data Portal API 客户端
    
    实现NRDP的认证和数据下载功能
    """
    
    BASE_URL = "https://opendata.nationalrail.co.uk"
    AUTH_ENDPOINT = "/authenticate"
    FARES_ENDPOINT = "/api/staticfeeds/2.0/fares"
    
    def __init__(self, email: str, password: str):
        """
        初始化NRDP客户端
        
        Args:
            email: NRDP账户邮箱
            password: NRDP账户密码
        """
        self.email = email
        self.password = password
        self.token = None
        self.token_expiry = None
        
        logger.info(f"NRDP客户端初始化: {email}")
    
    
    def authenticate(self) -> str:
        """
        获取认证token
        
        Returns:
            认证token字符串
        """
        logger.info("开始NRDP认证...")
        
        auth_url = f"{self.BASE_URL}{self.AUTH_ENDPOINT}"
        
        payload = {
            "username": self.email,
            "password": self.password
        }
        
        try:
            response = requests.post(
                auth_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            response.raise_for_status()
            
            # Token格式: email:timestamp:hash
            self.token = response.headers.get('X-Auth-Token')
            
            if not self.token:
                # 有些实现返回在body中
                data = response.json()
                self.token = data.get('token')
            
            # Token有效期24小时
            self.token_expiry = datetime.now() + timedelta(hours=24)
            
            logger.info("✅ NRDP认证成功")
            return self.token
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ NRDP认证失败: {e}")
            raise
    
    
    def _ensure_authenticated(self):
        """确保有有效的token"""
        if not self.token or (self.token_expiry and datetime.now() >= self.token_expiry):
            self.authenticate()
    
    
    def download_fares_data(self, save_path: Optional[str] = None, check_update: bool = True) -> Tuple[bytes, Optional[str]]:
        """
        下载Fares数据ZIP文件
        
        根据文档建议：每天检查一次即可（不需要实时访问）
        Fares数据是静态数据，每周更新一次
        
        Args:
            save_path: 保存路径（可选，建议保存以便后续使用）
            check_update: 是否检查更新（通过Last-Modified头）
            
        Returns:
            (ZIP文件的字节内容, Last-Modified时间戳)
        """
        self._ensure_authenticated()
        
        logger.info("开始下载Fares数据...")
        logger.info("📌 注意：Fares数据是静态数据，每周更新，建议每天检查一次")
        
        fares_url = f"{self.BASE_URL}{self.FARES_ENDPOINT}"
        
        headers = {
            "X-Auth-Token": self.token,
            "Accept": "*/*"
        }
        
        try:
            response = requests.get(
                fares_url,
                headers=headers,
                timeout=300  # 5分钟超时（文件可能很大）
            )
            
            response.raise_for_status()
            
            zip_data = response.content
            
            # 获取文件名和更新时间
            last_modified = response.headers.get('Last-Modified', 'Unknown')
            filename = response.headers.get('Content-Disposition', '').split('filename=')[-1].strip('"')
            
            logger.info(f"✅ 下载成功: {filename} ({len(zip_data) / 1024 / 1024:.2f} MB)")
            logger.info(f"   最后更新: {last_modified}")
            
            # 可选：保存到文件（建议保存，避免重复下载）
            if save_path:
                os.makedirs(os.path.dirname(save_path) if os.path.dirname(save_path) else '.', exist_ok=True)
                with open(save_path, 'wb') as f:
                    f.write(zip_data)
                logger.info(f"   已保存到: {save_path}")
            
            return zip_data, last_modified
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ 下载Fares数据失败: {e}")
            raise


# ============================================
# Fares 数据解析器
# ============================================

class FaresParser:
    """
    Fares固定格式文件解析器
    
    根据RSPS5045规范解析Fares数据
    注意：实际文件格式非常复杂，这里实现核心功能
    """
    
    def __init__(self, zip_data: bytes):
        """
        初始化解析器
        
        Args:
            zip_data: ZIP文件字节数据
        """
        self.zip_data = zip_data
        if zip_data:
            self.zip_file = zipfile.ZipFile(io.BytesIO(zip_data))
            logger.info(f"Fares解析器初始化，ZIP包含 {len(self.zip_file.namelist())} 个文件")
        else:
            self.zip_file = None
            logger.info("Fares解析器初始化（模拟数据模式）")
    
    
    def get_dat_file(self) -> str:
        """
        获取DAT索引文件名
        
        Returns:
            DAT文件名
        """
        if not self.zip_file:
            raise ValueError("无ZIP数据")
            
        dat_files = [f for f in self.zip_file.namelist() if f.endswith('.DAT')]
        
        if not dat_files:
            raise ValueError("ZIP中未找到DAT索引文件")
        
        return dat_files[0]
    
    
    def extract_file(self, filename: str) -> str:
        """
        提取并读取文件内容
        
        Args:
            filename: 文件名
            
        Returns:
            文件内容（文本）
        """
        if not self.zip_file:
            raise ValueError("无ZIP数据")
            
        try:
            with self.zip_file.open(filename) as f:
                # 尝试不同编码
                try:
                    content = f.read().decode('utf-8')
                except UnicodeDecodeError:
                    content = f.read().decode('latin-1')
                
                return content
        except KeyError:
            logger.error(f"文件不存在: {filename}")
            raise
    
    
    def parse_all_fares(self) -> List[FareInfo]:
        """
        解析完整的Fares数据（从ZIP文件）
        
        根据RSPS5045规范解析固定宽度格式文件
        注意：完整实现需要详细的字段映射，这里实现基础解析
        
        Returns:
            票价信息列表
        """
        if not self.zip_file:
            logger.warning("⚠️  无ZIP数据，返回空列表")
            return []
        
        logger.info("开始解析Fares数据...")
        all_fares = []
        
        try:
            # 1. 读取DAT索引文件
            dat_file = self.get_dat_file()
            dat_content = self.extract_file(dat_file)
            
            logger.info(f"📋 索引文件: {dat_file}")
            logger.info(f"   包含 {len(dat_content.splitlines())} 个文件引用")
            
            # 2. 解析DAT文件，获取所有文件名
            file_list = []
            for line in dat_content.splitlines():
                line = line.strip()
                if line and not line.startswith('/!!'):
                    file_list.append(line)
            
            logger.info(f"📁 找到 {len(file_list)} 个数据文件")
            
            # 2.5. 解析Locations文件以获取CRS到NLC的映射
            crs_to_nlc, nlc_to_crs = self._parse_locations_file(file_list)
            if crs_to_nlc:
                logger.info(f"📋 加载了 {len(crs_to_nlc)} 个CRS到NLC映射")
            
            # 2.6. 解析TOC文件以获取TOC名称映射
            toc_mapping = self._parse_toc_file(file_list)
            if toc_mapping:
                logger.info(f"📋 加载了 {len(toc_mapping)} 个TOC信息")
            
            # 3. 解析主要票价文件（根据RSPS5045规范）
            # 主要文件类型：
            # - .FFL: Flow文件（最重要！包含点对点成人票价）
            # - .NDF: 非衍生票价文件
            # - .NFO: 非衍生票价覆盖文件
            
            fare_files = [f for f in file_list if f.upper().endswith('.FFL')]
            
            if not fare_files:
                logger.warning("⚠️  未找到.FFL票价文件，尝试解析其他文件")
                # 尝试其他票价文件
                fare_files = [f for f in file_list if any(f.upper().endswith(ext) 
                                                          for ext in ['.NFO', '.NDF'])]
            
            if not fare_files:
                logger.warning("⚠️  未找到票价文件，使用模拟数据")
                logger.info(f"   可用文件列表: {file_list[:10]}...")  # 显示前10个文件
                return self._generate_sample_fares()
            
            logger.info(f"📊 找到 {len(fare_files)} 个票价文件，开始解析...")
            
            # 4. 解析每个票价文件
            for fare_file in fare_files:
                try:
                    if fare_file.upper().endswith('.FFL'):
                        fares = self._parse_flow_file(fare_file, toc_mapping, crs_to_nlc, nlc_to_crs)
                    elif fare_file.upper().endswith('.NFO'):
                        fares = self._parse_ndo_file(fare_file, toc_mapping, crs_to_nlc, nlc_to_crs)
                    elif fare_file.upper().endswith('.NDF'):
                        fares = self._parse_ndf_file(fare_file)
                    else:
                        logger.warning(f"   ⚠️  未知文件类型: {fare_file}")
                        continue
                    
                    all_fares.extend(fares)
                    logger.info(f"   ✅ {fare_file}: 解析 {len(fares)} 条记录")
                except Exception as e:
                    logger.warning(f"   ⚠️  {fare_file}: 解析失败 - {e}")
                    import traceback
                    logger.debug(traceback.format_exc())
            
            logger.info(f"✅ 总共解析 {len(all_fares)} 条票价数据")
            
            if len(all_fares) == 0:
                logger.warning("⚠️  未能解析任何数据，使用模拟数据")
                return self._generate_sample_fares()
            
            return all_fares
            
        except Exception as e:
            logger.error(f"❌ 解析Fares数据失败: {e}")
            logger.info("⚠️  降级使用模拟数据")
            return self._generate_sample_fares()
    
    
    def _parse_locations_file(self, file_list: List[str]) -> Tuple[Dict[str, str], Dict[str, str]]:
        """
        解析Locations文件以获取CRS到NLC的映射
        
        根据RSPS5045规范4.19节，Location记录包含：
        - NLC_CODE: 位置37-40 (4字符)
        - CRS_CODE: 位置57-59 (3字符)
        
        Args:
            file_list: 文件列表
            
        Returns:
            (CRS到NLC的字典, NLC到CRS的字典)
        """
        crs_to_nlc = {}
        nlc_to_crs = {}
        
        # 查找LOC文件
        loc_files = [f for f in file_list if f.upper().endswith('.LOC')]
        
        if not loc_files:
            return crs_to_nlc, nlc_to_crs
        
        try:
            for loc_file in loc_files:
                content = self.extract_file(loc_file)
                
                for line in content.splitlines():
                    line = line.rstrip()
                    if not line or line.startswith('/!!'):
                        continue
                    
                    if len(line) >= 2:
                        record_type = line[1:2]
                        
                        if record_type == 'L':
                            # Location记录（根据RSPS5045 4.19.2节）
                            # NLC_CODE: 位置37-40 (4字符)
                            # CRS_CODE: 位置57-59 (3字符)
                            if len(line) >= 59:
                                nlc_code = line[36:40].strip()
                                crs_code = line[56:59].strip()
                                
                                if nlc_code and crs_code and len(nlc_code) == 4 and len(crs_code) == 3:
                                    crs_to_nlc[crs_code.upper()] = nlc_code
                                    nlc_to_crs[nlc_code] = crs_code.upper()
        
        except Exception as e:
            logger.warning(f"解析Locations文件失败: {e}")
        
        return crs_to_nlc, nlc_to_crs
    
    
    def _parse_toc_file(self, file_list: List[str]) -> Dict[str, str]:
        """
        解析TOC文件以获取TOC代码到名称的映射
        
        根据RSPS5045规范4.21节，TOC文件包含TOC记录和Fare TOC记录
        
        Args:
            file_list: 文件列表
            
        Returns:
            TOC代码到名称的字典
        """
        toc_mapping = {}
        
        # 查找TOC文件
        toc_files = [f for f in file_list if f.upper().endswith('.TOC')]
        
        if not toc_files:
            return toc_mapping
        
        try:
            for toc_file in toc_files:
                content = self.extract_file(toc_file)
                
                for line in content.splitlines():
                    line = line.rstrip()
                    if not line or line.startswith('/!!'):
                        continue
                    
                    if len(line) >= 2:
                        record_type = line[1:2]
                        
                        if record_type == 'F':
                            # Fare TOC记录（根据RSPS5045 4.21.3节）
                            # FARE_TOC_ID: 位置2-4 (3字符)
                            # FARE_TOC_NAME: 位置7-36 (30字符)
                            if len(line) >= 36:
                                fare_toc_id = line[1:4].strip()
                                fare_toc_name = line[6:36].strip()
                                if fare_toc_id and fare_toc_name:
                                    toc_mapping[fare_toc_id] = fare_toc_name
                        
                        elif record_type == 'T':
                            # TOC记录（根据RSPS5045 4.21.2节）
                            # TOC_ID: 位置2-3 (2字符)
                            # TOC_NAME: 位置4-33 (30字符)
                            if len(line) >= 33:
                                toc_id = line[1:3].strip()
                                toc_name = line[3:33].strip()
                                if toc_id and toc_name:
                                    # 注意：TOC_ID是2字符，FARE_TOC_ID是3字符
                                    # 这里存储2字符的TOC_ID，可能需要映射
                                    if len(toc_id) == 2:
                                        toc_mapping[toc_id] = toc_name
        
        except Exception as e:
            logger.warning(f"解析TOC文件失败: {e}")
        
        return toc_mapping
    
    
    def _parse_flow_file(self, filename: str, toc_mapping: Dict[str, str] = None, 
                        crs_to_nlc: Dict[str, str] = None, nlc_to_crs: Dict[str, str] = None) -> List[FareInfo]:
        """
        解析FLOW文件（.FFL）
        
        根据RSPS5045规范4.1节：
        - Flow记录：RECORD_TYPE = 'F'，包含起点、终点、路线等信息
        - Fare记录：RECORD_TYPE = 'T'，包含票价信息，通过FLOW_ID关联到Flow记录
        
        Args:
            filename: 文件名
            
        Returns:
            票价信息列表
        """
        try:
            content = self.extract_file(filename)
            fares = []
            
            # 存储Flow记录（key: FLOW_ID, value: Flow记录数据）
            flows = {}
            current_flow = None
            
            for line in content.splitlines():
                line = line.rstrip()  # 保留右侧空格（固定宽度格式）
                if not line or line.startswith('/!!'):
                    continue
                
                # 检查记录类型（第2个字符）
                if len(line) < 2:
                    continue
                
                record_type = line[1:2]
                update_marker = line[0:1] if len(line) > 0 else 'R'
                
                # 跳过删除记录
                if update_marker == 'D':
                    continue
                
                if record_type == 'F':
                    # Flow记录（根据RSPS5045 4.1.2节）
                    # 字段位置：
                    # ORIGIN_CODE: 位置3-6 (4字符NLC代码)
                    # DESTINATION_CODE: 位置7-10 (4字符NLC代码)
                    # ROUTE_CODE: 位置11-15 (5字符)
                    # STATUS_CODE: 位置16-18 (3字符，成人票价是'000')
                    # TOC: 位置37-39 (3字符，设置票价的TOC代码)
                    # FLOW_ID: 位置43-49 (7字符)
                    # START_DATE: 位置29-36 (8字符，格式ddmmyyyy)
                    # END_DATE: 位置21-28 (8字符，格式ddmmyyyy)
                    
                    if len(line) >= 49:
                        origin_nlc = line[2:6].strip()
                        dest_nlc = line[6:10].strip()
                        route_code = line[10:15].strip()
                        status_code = line[15:18].strip()
                        toc_code = line[36:39].strip()  # TOC代码（位置37-39）
                        flow_id = line[42:49].strip()
                        start_date_str = line[28:36].strip()
                        end_date_str = line[20:28].strip()
                        
                        # 只处理成人票价（STATUS_CODE = '000'）
                        if status_code == '000' and flow_id:
                            flows[flow_id] = {
                                'origin_nlc': origin_nlc,
                                'dest_nlc': dest_nlc,
                                'route_code': route_code,
                                'toc_code': toc_code,  # 添加TOC代码
                                'start_date': self._parse_date(start_date_str),
                                'end_date': self._parse_date(end_date_str),
                            }
                            current_flow = flow_id
                
                elif record_type == 'T':
                    # Fare记录（根据RSPS5045 4.1.3节）
                    # 字段位置：
                    # FLOW_ID: 位置3-9 (7字符)
                    # TICKET_CODE: 位置10-12 (3字符)
                    # FARE: 位置13-20 (8字符，便士)
                    # RESTRICTION_CODE: 位置21-22 (2字符)
                    
                    if len(line) >= 22:
                        flow_id = line[2:9].strip()
                        ticket_code = line[9:12].strip()
                        fare_str = line[12:20].strip()
                        restriction_code = line[20:22].strip()
                        
                        # 查找对应的Flow记录
                        if flow_id in flows:
                            flow = flows[flow_id]
                            
                            try:
                                fare_pence = int(fare_str) if fare_str else 0
                                
                                # 过滤异常价格：99999999表示无票价，> 100000便士（£1000）也视为异常
                                MAX_VALID_FARE = 100000  # 1000英镑 = 100000便士
                                if fare_pence > 0 and fare_pence < 99999999 and fare_pence <= MAX_VALID_FARE:
                                    # 根据ticket_code确定票种类型（需要参考TTY文件）
                                    ticket_type = self._determine_ticket_type(ticket_code)
                                    
                                    # 获取TOC名称
                                    toc_code = flow.get('toc_code')
                                    toc_name = None
                                    if toc_code and toc_mapping:
                                        toc_name = toc_mapping.get(toc_code)
                                    
                                    # 转换NLC到CRS（如果可能）
                                    origin_nlc = flow['origin_nlc']
                                    dest_nlc = flow['dest_nlc']
                                    origin_crs = nlc_to_crs.get(origin_nlc) if nlc_to_crs else None
                                    dest_crs = nlc_to_crs.get(dest_nlc) if nlc_to_crs else None
                                    
                                    # 优先使用CRS代码，如果没有则使用NLC代码
                                    origin_code = origin_crs if origin_crs else origin_nlc
                                    dest_code = dest_crs if dest_crs else dest_nlc
                                    
                                    fare = FareInfo(
                                        origin=origin_code,  # 使用CRS代码（如果可用）或NLC代码
                                        destination=dest_code,
                                        ticket_type=ticket_type,
                                        ticket_class=TicketClass.STANDARD,  # 默认标准座，需要从TTY文件确定
                                        adult_fare=fare_pence,
                                        child_fare=None,  # Flow文件只包含成人票价
                                        valid_from=flow['start_date'],
                                        valid_until=flow['end_date'],
                                        route_code=flow['route_code'],
                                        restriction_code=restriction_code if restriction_code else None,
                                        toc_code=toc_code,  # TOC代码（设置票价的铁路公司）
                                        toc_name=toc_name,  # TOC名称
                                        last_updated=datetime.now(),
                                        data_source="NRDP_REAL"
                                    )
                                    fares.append(fare)
                            except ValueError:
                                # 价格解析失败，跳过
                                continue
            
            logger.info(f"   解析了 {len(flows)} 个Flow记录，生成 {len(fares)} 条票价")
            return fares
            
        except Exception as e:
            logger.warning(f"解析FLOW文件 {filename} 失败: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return []
    
    
    def _parse_ndo_file(self, filename: str, toc_mapping: Dict[str, str] = None,
                       crs_to_nlc: Dict[str, str] = None, nlc_to_crs: Dict[str, str] = None) -> List[FareInfo]:
        """
        解析Non-Derivable Fares Overrides文件（.NFO）
        
        根据RSPS5045规范4.4节
        """
        try:
            content = self.extract_file(filename)
            fares = []
            
            for line in content.splitlines():
                line = line.rstrip()
                if not line or line.startswith('/!!'):
                    continue
                
                update_marker = line[0:1] if len(line) > 0 else 'R'
                if update_marker == 'D':
                    continue
                
                # 根据RSPS5045 4.4.3节
                # ORIGIN_CODE: 位置2-5 (4字符)
                # DESTINATION_CODE: 位置6-9 (4字符)
                # ROUTE_CODE: 位置10-14 (5字符)
                # TICKET_CODE: 位置18-20 (3字符)
                # ADULT_FARE: 位置47-54 (8字符，便士)
                # CHILD_FARE: 位置55-62 (8字符，便士)
                # START_DATE: 位置30-37 (8字符，格式ddmmyyyy)
                # END_DATE: 位置22-29 (8字符，格式ddmmyyyy)
                
                if len(line) >= 67:
                    origin_nlc = line[1:5].strip()
                    dest_nlc = line[5:9].strip()
                    route_code = line[9:14].strip()
                    ticket_code = line[17:20].strip()
                    adult_fare_str = line[46:54].strip()
                    child_fare_str = line[54:62].strip()
                    start_date_str = line[29:37].strip()
                    end_date_str = line[21:29].strip()
                    
                    try:
                        adult_fare = int(adult_fare_str) if adult_fare_str and adult_fare_str != '99999999' else None
                        child_fare = int(child_fare_str) if child_fare_str and child_fare_str != '99999999' else None
                        
                        # 过滤异常价格（> £1000）
                        MAX_VALID_FARE = 100000  # 1000英镑 = 100000便士
                        if adult_fare and adult_fare > 0 and adult_fare <= MAX_VALID_FARE:
                            ticket_type = self._determine_ticket_type(ticket_code)
                            
                            # 转换NLC到CRS（如果可能）
                            origin_crs = nlc_to_crs.get(origin_nlc) if nlc_to_crs else None
                            dest_crs = nlc_to_crs.get(dest_nlc) if nlc_to_crs else None
                            origin_code = origin_crs if origin_crs else origin_nlc
                            dest_code = dest_crs if dest_crs else dest_nlc
                            
                            fare = FareInfo(
                                origin=origin_code,  # 使用CRS代码（如果可用）或NLC代码
                                destination=dest_code,
                                ticket_type=ticket_type,
                                ticket_class=TicketClass.STANDARD,
                                adult_fare=adult_fare,
                                child_fare=child_fare,
                                valid_from=self._parse_date(start_date_str),
                                valid_until=self._parse_date(end_date_str),
                                route_code=route_code if route_code else None,
                                restriction_code=None,
                                last_updated=datetime.now(),
                                data_source="NRDP_REAL"
                            )
                            fares.append(fare)
                    except ValueError:
                        continue
            
            return fares
            
        except Exception as e:
            logger.warning(f"解析NFO文件 {filename} 失败: {e}")
            return []
    
    
    def _parse_ndf_file(self, filename: str) -> List[FareInfo]:
        """
        解析Non-Derivable Fares文件（.NDF）
        
        根据RSPS5045规范4.3节
        注意：这个文件现在基本废弃，只包含一条记录用于兼容
        """
        # NDF文件现在基本废弃，只返回空列表
        return []
    
    
    def _parse_date(self, date_str: str) -> datetime:
        """
        解析日期字符串（格式：ddmmyyyy）
        
        Args:
            date_str: 日期字符串（8字符，格式ddmmyyyy）
            
        Returns:
            datetime对象
        """
        try:
            if not date_str or len(date_str) != 8:
                return datetime.now()
            
            day = int(date_str[0:2])
            month = int(date_str[2:4])
            year = int(date_str[4:8])
            
            return datetime(year, month, day)
        except:
            return datetime.now()
    
    
    def _determine_ticket_type(self, ticket_code: str) -> TicketType:
        """
        根据ticket_code确定票种类型
        
        注意：这需要参考TTY（Ticket Types）文件来准确确定
        这里使用简化逻辑
        
        Args:
            ticket_code: 3字符票种代码
            
        Returns:
            TicketType枚举
        """
        if not ticket_code:
            return TicketType.ANYTIME
        
        # 简化判断逻辑（实际应该从TTY文件读取）
        ticket_code_upper = ticket_code.upper()
        
        # Advance票通常包含特定代码
        if any(code in ticket_code_upper for code in ['ADV', 'AP']):
            return TicketType.ADVANCE
        
        # Off-Peak票
        if any(code in ticket_code_upper for code in ['OFF', 'OP']):
            return TicketType.OFF_PEAK
        
        # 默认Anytime
        return TicketType.ANYTIME
    
    
    def _generate_sample_fares(self) -> List[FareInfo]:
        """生成示例票价数据（降级方案）"""
        logger.info("生成示例票价数据...")
        sample_fares = []
        
        common_routes = [
            ("EUS", "MAN"),  # 伦敦-曼彻斯特
            ("EUS", "BHM"),  # 伦敦-伯明翰
            ("PAD", "BRI"),  # 伦敦-布里斯托
            ("KGX", "EDN"),  # 伦敦-爱丁堡
            ("VIC", "BTN"),  # 伦敦-布莱顿
        ]
        
        for origin, dest in common_routes:
            # Advance票
            sample_fares.append(FareInfo(
                origin=origin,
                destination=dest,
                ticket_type=TicketType.ADVANCE,
                ticket_class=TicketClass.STANDARD,
                adult_fare=2500,  # £25.00 (便士)
                child_fare=1250,
                valid_from=datetime.now(),
                valid_until=datetime.now() + timedelta(days=90),
                route_code=None,
                restriction_code="ADV",
                last_updated=datetime.now(),
                data_source="NRDP_SIMULATED"
            ))
            
            # Off-Peak票
            sample_fares.append(FareInfo(
                origin=origin,
                destination=dest,
                ticket_type=TicketType.OFF_PEAK,
                ticket_class=TicketClass.STANDARD,
                adult_fare=4500,  # £45.00
                child_fare=2250,
                valid_from=datetime.now(),
                valid_until=datetime.now() + timedelta(days=90),
                route_code=None,
                restriction_code="OPK",
                last_updated=datetime.now(),
                data_source="NRDP_SIMULATED"
            ))
            
            # Anytime票
            sample_fares.append(FareInfo(
                origin=origin,
                destination=dest,
                ticket_type=TicketType.ANYTIME,
                ticket_class=TicketClass.STANDARD,
                adult_fare=8900,  # £89.00
                child_fare=4450,
                valid_from=datetime.now(),
                valid_until=datetime.now() + timedelta(days=90),
                route_code=None,
                restriction_code="ANY",
                last_updated=datetime.now(),
                data_source="NRDP_SIMULATED"
            ))
        
        logger.info(f"✅ 生成 {len(sample_fares)} 条示例票价数据")
        return sample_fares
    
    
    def parse_simplified_fares(self, limit: int = 1000) -> List[FareInfo]:
        """
        解析Fares数据（兼容旧接口）
        
        Args:
            limit: 最大解析记录数（已废弃，保留用于兼容）
            
        Returns:
            票价信息列表
        """
        if self.zip_file:
            # 有真实数据，解析完整数据
            all_fares = self.parse_all_fares()
            return all_fares[:limit] if limit else all_fares
        else:
            # 无数据，返回模拟数据
            return self._generate_sample_fares()


# ============================================
# 价格缓存系统
# ============================================

class FareCache:
    """
    票价缓存系统
    
    使用SQLite实现本地缓存，避免重复API调用
    """
    
    def __init__(self, db_path: str, crs_to_nlc: Dict[str, str] = None, nlc_to_crs: Dict[str, str] = None):
        """
        初始化缓存
        
        Args:
            db_path: 数据库路径
            crs_to_nlc: CRS到NLC的映射字典（可选）
            nlc_to_crs: NLC到CRS的映射字典（可选）
        """
        self.db_path = db_path
        self.crs_to_nlc = crs_to_nlc if crs_to_nlc is not None else {}
        self.nlc_to_crs = nlc_to_crs if nlc_to_crs is not None else {}
        self._init_cache_db()
        
        logger.info(f"票价缓存初始化: {db_path}")
        if self.crs_to_nlc:
            logger.info(f"   已加载 {len(self.crs_to_nlc)} 个CRS到NLC映射")
    
    
    def _init_cache_db(self):
        """初始化缓存数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建票价缓存表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fare_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                origin TEXT NOT NULL,
                destination TEXT NOT NULL,
                ticket_type TEXT NOT NULL,
                ticket_class TEXT NOT NULL,
                adult_fare REAL NOT NULL,
                child_fare REAL,
                valid_from TEXT NOT NULL,
                valid_until TEXT NOT NULL,
                route_code TEXT,
                restriction_code TEXT,
                data_source TEXT NOT NULL,
                cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                hits INTEGER DEFAULT 0,
                UNIQUE(origin, destination, ticket_type, ticket_class)
            )
        """)
        
        # 检查并添加valid_from和valid_until字段（数据库迁移）
        try:
            cursor.execute("SELECT COUNT(*) FROM pragma_table_info('fare_cache') WHERE name='valid_from'")
            if cursor.fetchone()[0] == 0:
                logger.info("📊 添加valid_from和valid_until字段到数据库...")
                cursor.execute("ALTER TABLE fare_cache ADD COLUMN valid_from TEXT")
                cursor.execute("ALTER TABLE fare_cache ADD COLUMN valid_until TEXT")
                # 为现有记录设置默认值
                cursor.execute("UPDATE fare_cache SET valid_from = '2000-01-01T00:00:00' WHERE valid_from IS NULL")
                cursor.execute("UPDATE fare_cache SET valid_until = '2099-12-31T23:59:59' WHERE valid_until IS NULL")
                conn.commit()
                logger.info("✅ valid_from和valid_until字段添加完成")
        except Exception as e:
            logger.warning(f"⚠️  添加valid_from/valid_until字段失败（可能已存在）: {e}")
        
        # 检查并添加TOC字段（数据库迁移）
        try:
            cursor.execute("SELECT COUNT(*) FROM pragma_table_info('fare_cache') WHERE name='toc_code'")
            if cursor.fetchone()[0] == 0:
                logger.info("📊 添加TOC字段到数据库...")
                cursor.execute("ALTER TABLE fare_cache ADD COLUMN toc_code TEXT")
                cursor.execute("ALTER TABLE fare_cache ADD COLUMN toc_name TEXT")
                conn.commit()
                logger.info("✅ TOC字段添加完成")
        except Exception as e:
            logger.warning(f"⚠️  添加TOC字段失败（可能已存在）: {e}")
        
        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_fare_route 
            ON fare_cache(origin, destination)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_fare_type 
            ON fare_cache(ticket_type)
        """)
        
        conn.commit()
        conn.close()
        
        logger.info("✅ 缓存数据库初始化完成")
    
    
    def cache_fares(self, fares: List[FareInfo]):
        """
        批量缓存票价数据
        
        Args:
            fares: 票价信息列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cached_count = 0
        
        for fare in fares:
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO fare_cache (
                        origin, destination, ticket_type, ticket_class,
                        adult_fare, child_fare, valid_from, valid_until,
                        route_code, restriction_code, toc_code, toc_name,
                        data_source, cached_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    fare.origin,
                    fare.destination,
                    fare.ticket_type.value,
                    fare.ticket_class.value,
                    fare.adult_fare,
                    fare.child_fare,
                    fare.valid_from.isoformat(),
                    fare.valid_until.isoformat(),
                    fare.route_code,
                    fare.restriction_code,
                    fare.toc_code,
                    fare.toc_name,
                    fare.data_source
                ))
                cached_count += 1
            except Exception as e:
                logger.warning(f"缓存失败 {fare.origin}->{fare.destination}: {e}")
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ 缓存 {cached_count}/{len(fares)} 条票价数据")
    
    
    def get_fare(
        self, 
        origin: str, 
        destination: str, 
        ticket_type: TicketType,
        ticket_class: TicketClass = TicketClass.STANDARD
    ) -> Optional[FareInfo]:
        """
        从缓存获取票价
        
        自动处理CRS和NLC代码的转换：
        - 如果输入是CRS代码，会尝试转换为NLC代码查询
        - 如果输入是NLC代码，直接查询
        - 会尝试两种格式以确保找到数据
        
        Args:
            origin: 起点（CRS或NLC代码）
            destination: 终点（CRS或NLC代码）
            ticket_type: 票种
            ticket_class: 等级
            
        Returns:
            票价信息，如果不存在返回None
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 尝试多种代码格式
        origin_variants = [origin]
        dest_variants = [destination]
        
        # 确保映射字典已初始化
        if not hasattr(self, 'crs_to_nlc'):
            self.crs_to_nlc = {}
        if not hasattr(self, 'nlc_to_crs'):
            self.nlc_to_crs = {}
        
        # 如果输入是CRS代码（3位字母），尝试转换为NLC
        if len(origin) == 3 and origin.isalpha() and origin.upper() in self.crs_to_nlc:
            origin_variants.append(self.crs_to_nlc[origin.upper()])
        
        # 如果输入是NLC代码（4位数字），尝试转换为CRS
        if len(origin) == 4 and origin.isdigit() and origin in self.nlc_to_crs:
            origin_variants.append(self.nlc_to_crs[origin])
        
        if len(destination) == 3 and destination.isalpha() and destination.upper() in self.crs_to_nlc:
            dest_variants.append(self.crs_to_nlc[destination.upper()])
        
        if len(destination) == 4 and destination.isdigit() and destination in self.nlc_to_crs:
            dest_variants.append(self.nlc_to_crs[destination])
        
        # 尝试所有组合，优先返回真实数据（NRDP_REAL）
        found_fares = []
        for orig in origin_variants:
            for dest in dest_variants:
                cursor.execute("""
                    SELECT * FROM fare_cache
                    WHERE origin = ? 
                      AND destination = ?
                      AND ticket_type = ?
                      AND ticket_class = ?
                        """, (orig, dest, ticket_type.value, ticket_class.value))
                
                rows = cursor.fetchall()
                for row in rows:
                    found_fares.append(row)
        
        # 只返回真实数据（NRDP_REAL），不返回模拟数据
        real_data_fares = [row for row in found_fares if row['data_source'] == 'NRDP_REAL']
        if real_data_fares:
            result = self._row_to_fare_info(real_data_fares[0], conn)
            conn.close()
            return result
        
        # 如果没有真实数据，返回None（不返回模拟数据）
        conn.close()
        return None
    
    
    def _row_to_fare_info(self, row: sqlite3.Row, conn: sqlite3.Connection) -> FareInfo:
        """将数据库行转换为FareInfo对象"""
        # 更新命中计数
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE fare_cache 
            SET hits = hits + 1 
            WHERE id = ?
        """, (row['id'],))
        conn.commit()
        
        # sqlite3.Row不支持.get()方法，需要安全地访问可能不存在的列
        try:
            toc_code = row['toc_code'] if row['toc_code'] else None
        except (KeyError, IndexError):
            toc_code = None
        
        try:
            toc_name = row['toc_name'] if row['toc_name'] else None
        except (KeyError, IndexError):
            toc_name = None
        
        fare = FareInfo(
            origin=row['origin'],
            destination=row['destination'],
            ticket_type=TicketType(row['ticket_type']),
            ticket_class=TicketClass(row['ticket_class']),
            adult_fare=row['adult_fare'],
            child_fare=row['child_fare'],
            valid_from=datetime.fromisoformat(row['valid_from']),
            valid_until=datetime.fromisoformat(row['valid_until']),
            route_code=row['route_code'],
            restriction_code=row['restriction_code'],
            toc_code=toc_code,
            toc_name=toc_name,
            last_updated=datetime.fromisoformat(row['cached_at']),
            data_source=row['data_source']
        )
        
        return fare
    
    
    def get_cache_stats(self) -> Dict:
        """
        获取缓存统计信息
        
        Returns:
            统计字典
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 总记录数
        cursor.execute("SELECT COUNT(*) FROM fare_cache")
        total_records = cursor.fetchone()[0]
        
        # 总命中数
        cursor.execute("SELECT SUM(hits) FROM fare_cache")
        total_hits = cursor.fetchone()[0] or 0
        
        # 按票种统计
        cursor.execute("""
            SELECT ticket_type, COUNT(*) as count
            FROM fare_cache
            GROUP BY ticket_type
        """)
        by_type = dict(cursor.fetchall())
        
        # 最热门路线
        cursor.execute("""
            SELECT origin, destination, SUM(hits) as total_hits
            FROM fare_cache
            GROUP BY origin, destination
            ORDER BY total_hits DESC
            LIMIT 5
        """)
        top_routes = cursor.fetchall()
        
        conn.close()
        
        # 计算命中率（避免除零错误，并处理小数精度）
        if total_records > 0:
            hit_rate = total_hits / total_records
        else:
            hit_rate = 0.0
        
        return {
            'total_records': total_records,
            'total_hits': total_hits,
            'hit_rate': hit_rate,
            'by_ticket_type': by_type,
            'top_routes': top_routes
        }


# ============================================
# 价格对比引擎
# ============================================

class FareComparator:
    """
    票价对比引擎
    
    结合缓存系统提供快速价格查询和对比
    """
    
    def __init__(self, cache: FareCache):
        """
        初始化对比引擎
        
        Args:
            cache: 票价缓存实例
        """
        self.cache = cache
        logger.info("票价对比引擎初始化完成")
    
    
    def compare_fares(
        self,
        origin: str,
        destination: str,
        departure_date: datetime,
        ticket_class: TicketClass = TicketClass.STANDARD
    ) -> Optional[FareComparison]:
        """
        对比不同票种的价格
        
        Args:
            origin: 起点
            destination: 终点
            departure_date: 出发日期
            ticket_class: 座位等级
            
        Returns:
            价格对比结果
        """
        logger.info(f"对比票价: {origin} -> {destination}")
        
        # 查询各票种价格
        advance = self.cache.get_fare(origin, destination, TicketType.ADVANCE, ticket_class)
        off_peak = self.cache.get_fare(origin, destination, TicketType.OFF_PEAK, ticket_class)
        anytime = self.cache.get_fare(origin, destination, TicketType.ANYTIME, ticket_class)
        
        # 提取价格，过滤异常价格（> £1000 或 < £0.01）
        # 重要：确保所有价格来自同一数据源（真实数据或模拟数据），避免混合
        MAX_VALID_FARE = 100000  # 1000英镑 = 100000便士
        MIN_VALID_FARE = 1  # 0.01英镑 = 1便士
        
        # 只使用真实数据（NRDP_REAL），忽略模拟数据
        data_source = 'NRDP_REAL'
        
        prices = {}
        # 只添加真实数据源的有效价格
        if advance and advance.data_source == 'NRDP_REAL' and MIN_VALID_FARE <= advance.adult_fare <= MAX_VALID_FARE:
            prices[TicketType.ADVANCE] = advance.adult_fare
        elif advance and advance.data_source != 'NRDP_REAL':
            logger.debug(f"跳过Advance价格（非真实数据: {advance.data_source}）")
        elif advance:
            logger.debug(f"过滤异常Advance价格: £{advance.adult_fare/100:.2f}")
        
        if off_peak and off_peak.data_source == 'NRDP_REAL' and MIN_VALID_FARE <= off_peak.adult_fare <= MAX_VALID_FARE:
            prices[TicketType.OFF_PEAK] = off_peak.adult_fare
        elif off_peak and off_peak.data_source != 'NRDP_REAL':
            logger.debug(f"跳过Off-Peak价格（非真实数据: {off_peak.data_source}）")
        elif off_peak:
            logger.debug(f"过滤异常Off-Peak价格: £{off_peak.adult_fare/100:.2f}")
        
        if anytime and anytime.data_source == 'NRDP_REAL' and MIN_VALID_FARE <= anytime.adult_fare <= MAX_VALID_FARE:
            prices[TicketType.ANYTIME] = anytime.adult_fare
        elif anytime and anytime.data_source != 'NRDP_REAL':
            logger.debug(f"跳过Anytime价格（非真实数据: {anytime.data_source}）")
        elif anytime:
            logger.debug(f"过滤异常Anytime价格: £{anytime.adult_fare/100:.2f}")
        
        # 如果没有真实数据，返回 None（由调用者处理）
        if not prices:
            logger.info(f"未找到真实票价数据: {origin} -> {destination}（只有模拟数据）")
            return None
        
        # 找出最便宜和最贵
        cheapest_type = min(prices.keys(), key=lambda k: prices[k])
        cheapest_price = prices[cheapest_type]
        most_expensive = max(prices.values())
        
        # 计算节省
        savings = most_expensive - cheapest_price
        savings_pct = (savings / most_expensive * 100) if most_expensive > 0 else 0
        
        # 计算缓存年龄
        cache_age = 0
        if advance:
            cache_age = (datetime.now() - advance.last_updated).total_seconds() / 3600
        
        return FareComparison(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            advance_price=prices.get(TicketType.ADVANCE),
            off_peak_price=prices.get(TicketType.OFF_PEAK),
            anytime_price=prices.get(TicketType.ANYTIME),
            cheapest_type=cheapest_type,
            cheapest_price=cheapest_price,
            savings_amount=savings,
            savings_percentage=savings_pct,
            cached=True,
            cache_age_hours=cache_age,
            data_source='NRDP_REAL'
        )
    
    
    def format_price(self, pence: float) -> str:
        """
        格式化价格显示
        
        Args:
            pence: 便士价格
            
        Returns:
            格式化字符串（如"£25.00"）
        """
        pounds = pence / 100
        return f"£{pounds:.2f}"


# ============================================
# 辅助函数
# ============================================

def _should_update_fares_data(cache: FareCache, zip_path: str, max_age_days: int = 30) -> bool:
    """
    检查是否需要更新票价数据
    
    根据要求：票价数据每月更新一次（NRDP每周更新，我们每月检查一次）
    这里实现：如果ZIP文件存在且未超过30天，则不需要重新下载
    
    Args:
        cache: 票价缓存实例
        zip_path: ZIP文件路径
        max_age_days: 最大缓存天数（默认1天）
        
    Returns:
        True如果需要更新，False如果可以使用现有数据
    """
    # 1. 检查数据库是否有数据
    stats = cache.get_cache_stats()
    if stats['total_records'] == 0:
        logger.info("📊 数据库为空，需要下载数据")
        return True
    
    # 2. 检查ZIP文件是否存在
    if not os.path.exists(zip_path):
        logger.info("📊 ZIP文件不存在，需要下载")
        return True
    
    # 3. 检查ZIP文件修改时间
    try:
        zip_mtime = datetime.fromtimestamp(os.path.getmtime(zip_path))
        age_days = (datetime.now() - zip_mtime).days
        
        if age_days >= max_age_days:
            logger.info(f"📊 ZIP文件已存在 {age_days} 天（超过 {max_age_days} 天），需要更新")
            return True
        else:
            logger.info(f"📊 ZIP文件存在且新鲜（{age_days} 天前），使用现有数据")
            return False
    except Exception as e:
        logger.warning(f"⚠️  检查ZIP文件时间失败: {e}，将重新下载")
        return True


# ============================================
# 便捷接口
# ============================================

def initialize_fares_system(
    db_path: str,
    nrdp_email: Optional[str] = None,
    nrdp_password: Optional[str] = None
) -> Tuple[FareCache, FareComparator]:
    """
    初始化票价系统（仅使用真实NRDP数据）
    
    Args:
        db_path: 数据库路径
        nrdp_email: NRDP账户邮箱（如果为None，则从.env文件读取）
        nrdp_password: NRDP密码（如果为None，则从.env文件读取）
        
    Returns:
        (缓存实例, 对比引擎)
        
    Raises:
        ValueError: 如果没有提供NRDP凭据
    """
    logger.info("=" * 60)
    logger.info("初始化RailFair票价系统（仅真实数据）")
    logger.info("=" * 60)
    
    # 从环境变量读取凭据（如果未提供）
    if not nrdp_email:
        nrdp_email = os.getenv('NRDP_EMAIL')
    if not nrdp_password:
        nrdp_password = os.getenv('NRDP_PASSWORD')
    
    # 必须提供NRDP凭据
    if not nrdp_email or not nrdp_password:
        raise ValueError(
            "❌ 未提供NRDP凭据。请在.env文件中设置NRDP_EMAIL和NRDP_PASSWORD，"
            "或作为参数传入。系统仅支持真实数据，不支持模拟数据。"
        )
    
    # 创建缓存（暂时不加载映射，稍后在解析数据时加载）
    cache = FareCache(db_path)
    
    # 使用NRDP真实数据
    logger.info("🔐 使用NRDP真实数据")
    logger.info(f"   账户: {nrdp_email}")
    
    try:
        # 检查是否需要更新数据（每月更新一次）
        zip_path = os.path.join(os.path.dirname(db_path) if os.path.dirname(db_path) else '.', "fares_data.zip")
        needs_update = _should_update_fares_data(cache, zip_path, max_age_days=30)
        
        if not needs_update:
            logger.info("✅ 使用现有缓存数据（数据未超过30天）")
            stats = cache.get_cache_stats()
            if stats['total_records'] > 0:
                logger.info(f"   缓存中有 {stats['total_records']} 条票价记录")
            else:
                logger.warning("   缓存为空，需要重新下载")
                needs_update = True
        
        if needs_update:
            client = NRDPClient(nrdp_email, nrdp_password)
            
            # 下载完整数据（建议保存到本地，避免重复下载）
            zip_data, last_modified = client.download_fares_data(save_path=zip_path)
            
            logger.info("📦 开始解析完整Fares数据...")
            parser = FaresParser(zip_data)
            
            # 解析所有票价数据（不再使用简化版本）
            fares = parser.parse_all_fares()
            
            logger.info(f"💾 将 {len(fares)} 条票价数据存储到数据库...")
            cache.cache_fares(fares)
            
            # 加载CRS到NLC映射到缓存（用于查询转换）
            dat_file = parser.get_dat_file()
            dat_content = parser.extract_file(dat_file)
            file_list = [line.strip() for line in dat_content.splitlines() 
                       if line.strip() and not line.strip().startswith('/!!')]
            crs_to_nlc, nlc_to_crs = parser._parse_locations_file(file_list)
            if crs_to_nlc:
                cache.crs_to_nlc = crs_to_nlc
                cache.nlc_to_crs = nlc_to_crs
                logger.info(f"📋 加载了 {len(crs_to_nlc)} 个CRS到NLC映射到缓存")
            
            logger.info(f"✅ 数据更新完成，最后更新: {last_modified}")
        else:
            logger.info("📊 跳过数据下载，使用现有缓存")
            
            # 即使使用现有缓存，也需要加载CRS到NLC映射以便查询
            # 尝试从ZIP文件加载映射
            if os.path.exists(zip_path):
                try:
                    with open(zip_path, 'rb') as f:
                        zip_data = f.read()
                    parser = FaresParser(zip_data)
                    dat_file = parser.get_dat_file()
                    dat_content = parser.extract_file(dat_file)
                    file_list = [line.strip() for line in dat_content.splitlines() 
                               if line.strip() and not line.strip().startswith('/!!')]
                    crs_to_nlc, nlc_to_crs = parser._parse_locations_file(file_list)
                    if crs_to_nlc:
                        cache.crs_to_nlc = crs_to_nlc
                        cache.nlc_to_crs = nlc_to_crs
                        logger.info(f"📋 从ZIP文件加载了 {len(crs_to_nlc)} 个CRS到NLC映射")
                except Exception as e:
                    logger.warning(f"⚠️  加载CRS映射失败: {e}")
        
    except Exception as e:
        logger.error(f"❌ NRDP数据下载失败: {e}")
        logger.error("❌ 无法获取真实票价数据，系统将无法提供票价查询服务")
        # 不降级到模拟数据，让系统继续运行但票价查询会返回None
        # 这样API会显示"不可用"而不是显示模拟数据
    
    # 创建对比引擎
    comparator = FareComparator(cache)
    
    # 显示缓存统计
    stats = cache.get_cache_stats()
    logger.info(f"📊 缓存统计: {stats['total_records']} 条记录")
    
    logger.info("✅ 票价系统初始化完成")
    
    return cache, comparator


# ============================================
# 演示/测试
# ============================================

if __name__ == "__main__":
    print("RailFair 票价系统测试")
    print("=" * 60)
    
    # 初始化系统（自动从.env读取凭据，使用真实API）
    cache, comparator = initialize_fares_system(
        "railfair_fares.db"
    )
    
    # 测试价格查询
    print("\n测试价格查询:")
    print("-" * 60)
    
    test_routes = [
        ("EUS", "MAN", "伦敦到曼彻斯特"),
        ("PAD", "BRI", "伦敦到布里斯托"),
    ]
    
    for origin, dest, name in test_routes:
        result = comparator.compare_fares(
            origin, dest, datetime.now()
        )
        
        print(f"\n{name} ({origin} -> {dest}):")
        
        # 获取详细票价信息（包含TOC）
        advance_fare = cache.get_fare(origin, dest, TicketType.ADVANCE) if result.advance_price else None
        offpeak_fare = cache.get_fare(origin, dest, TicketType.OFF_PEAK) if result.off_peak_price else None
        anytime_fare = cache.get_fare(origin, dest, TicketType.ANYTIME) if result.anytime_price else None
        
        if result.advance_price and result.advance_price > 0:
            advance_price_str = comparator.format_price(result.advance_price)
        else:
            advance_price_str = "不可用"
        print(f"  Advance:  {advance_price_str}", end="")
        if advance_fare and advance_fare.toc_name:
            print(f" (由 {advance_fare.toc_name} 制定)")
        elif advance_fare and advance_fare.toc_code:
            print(f" (TOC: {advance_fare.toc_code})")
        else:
            print()
        
        if result.off_peak_price and result.off_peak_price > 0:
            offpeak_price_str = comparator.format_price(result.off_peak_price)
        else:
            offpeak_price_str = "不可用"
        print(f"  Off-Peak: {offpeak_price_str}", end="")
        if offpeak_fare and offpeak_fare.toc_name:
            print(f" (由 {offpeak_fare.toc_name} 制定)")
        elif offpeak_fare and offpeak_fare.toc_code:
            print(f" (TOC: {offpeak_fare.toc_code})")
        else:
            print()
        
        if result.anytime_price and result.anytime_price > 0:
            anytime_price_str = comparator.format_price(result.anytime_price)
        else:
            anytime_price_str = "不可用"
        print(f"  Anytime:  {anytime_price_str}", end="")
        if anytime_fare and anytime_fare.toc_name:
            print(f" (由 {anytime_fare.toc_name} 制定)")
        elif anytime_fare and anytime_fare.toc_code:
            print(f" (TOC: {anytime_fare.toc_code})")
        else:
            print()
        
        print(f"  💰 最便宜: {result.cheapest_type.value} "
              f"{comparator.format_price(result.cheapest_price)}")
        print(f"  💸 节省: {comparator.format_price(result.savings_amount)} "
              f"({result.savings_percentage:.1f}%)")
        
        # 显示数据来源说明
        if advance_fare and advance_fare.data_source == "NRDP_REAL":
            print(f"  📊 数据来源: NRDP官方数据（真实票价）")
    
    # 缓存统计
    print("\n" + "=" * 60)
    print("缓存统计:")
    stats = cache.get_cache_stats()
    print(f"  总记录: {stats['total_records']}")
    print(f"  总命中: {stats['total_hits']}")
    # 命中率显示：如果很小则显示更多小数位
    if stats['hit_rate'] < 0.01:
        print(f"  命中率: {stats['hit_rate']:.4%} ({stats['total_hits']}/{stats['total_records']})")
    else:
        print(f"  命中率: {stats['hit_rate']:.1%}")
