"""
UK Rail Delay Predictor - Data Models
Day 2: Pydantic Models with Type Validation
Created: 2025-11-12
"""

from datetime import datetime, date, time
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, Field, validator, constr, condecimal
from enum import Enum


# ============================================
# Enums
# ============================================

class FareType(str, Enum):
    """票价类型枚举"""
    ANYTIME = "Anytime"
    OFF_PEAK = "Off-Peak"
    ADVANCE = "Advance"
    SEASON = "Season"


class TicketClass(str, Enum):
    """车票等级枚举"""
    STANDARD = "Standard"
    FIRST = "First"


class DelayCategory(str, Enum):
    """延误类型枚举"""
    WEATHER = "Weather"
    TECHNICAL = "Technical"
    STAFF = "Staff"
    PASSENGER = "Passenger"
    INFRASTRUCTURE = "Infrastructure"
    EXTERNAL = "External"
    OTHER = "Other"


class WeatherCondition(str, Enum):
    """天气状况枚举"""
    SUNNY = "Sunny"
    CLOUDY = "Cloudy"
    RAINY = "Rainy"
    SNOWY = "Snowy"
    FOGGY = "Foggy"
    STORMY = "Stormy"


class PowerType(str, Enum):
    """动力类型枚举"""
    ELECTRIC = "Electric"
    DIESEL = "Diesel"
    HYBRID = "Hybrid"


# ============================================
# Base Models
# ============================================

class BaseDBModel(BaseModel):
    """数据库模型基类"""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None,
            date: lambda v: v.isoformat() if v else None,
            time: lambda v: v.isoformat() if v else None,
        }


# ============================================
# Station Models
# ============================================

class StationBase(BaseModel):
    """车站基础模型"""
    station_code: constr(min_length=3, max_length=10) = Field(..., description="CRS代码")
    station_name: constr(min_length=1, max_length=100) = Field(..., description="车站名称")
    latitude: Optional[condecimal(max_digits=10, decimal_places=7)] = None
    longitude: Optional[condecimal(max_digits=10, decimal_places=7)] = None
    region: Optional[constr(max_length=50)] = None
    zone: Optional[int] = Field(None, ge=1, le=9, description="伦敦交通分区")
    is_active: bool = True
    
    @validator('station_code')
    def station_code_uppercase(cls, v):
        """车站代码自动转大写"""
        return v.upper()


class StationCreate(StationBase):
    """创建车站模型"""
    facilities: Optional[str] = None
    passenger_volume: Optional[int] = Field(None, ge=0)
    metro_area: Optional[str] = None


class Station(StationBase, BaseDBModel):
    """完整车站模型"""
    station_id: int
    facilities: Optional[str] = None
    passenger_volume: Optional[int] = None
    metro_area: Optional[str] = None


# ============================================
# Train Operator Models
# ============================================

class TrainOperatorBase(BaseModel):
    """列车运营商基础模型"""
    operator_code: constr(min_length=2, max_length=10) = Field(..., description="运营商代码")
    operator_name: constr(min_length=1, max_length=100) = Field(..., description="运营商名称")
    full_name: Optional[constr(max_length=200)] = None
    website: Optional[str] = None
    is_active: bool = True
    
    @validator('operator_code')
    def operator_code_uppercase(cls, v):
        """运营商代码自动转大写"""
        return v.upper()


class TrainOperatorCreate(TrainOperatorBase):
    """创建运营商模型"""
    parent_company: Optional[str] = None
    franchise_start_date: Optional[date] = None
    franchise_end_date: Optional[date] = None
    service_quality_rating: Optional[condecimal(max_digits=3, decimal_places=2)] = Field(
        None, ge=0, le=5
    )


class TrainOperator(TrainOperatorBase, BaseDBModel):
    """完整运营商模型"""
    operator_id: int
    parent_company: Optional[str] = None
    franchise_start_date: Optional[date] = None
    franchise_end_date: Optional[date] = None
    service_quality_rating: Optional[Decimal] = None


# ============================================
# Train Type Models
# ============================================

class TrainTypeBase(BaseModel):
    """列车类型基础模型"""
    type_code: constr(min_length=1, max_length=20) = Field(..., description="类型代码")
    type_name: constr(min_length=1, max_length=100) = Field(..., description="类型名称")
    manufacturer: Optional[str] = None
    max_speed: Optional[int] = Field(None, ge=0, le=400, description="最大速度 km/h")
    capacity: Optional[int] = Field(None, ge=0, description="座位数")
    comfort_rating: Optional[int] = Field(None, ge=1, le=5, description="舒适度评分")


class TrainTypeCreate(TrainTypeBase):
    """创建列车类型模型"""
    year_introduced: Optional[int] = Field(None, ge=1800, le=2100)
    power_type: Optional[PowerType] = None
    bi_mode: bool = False
    wheelchair_spaces: Optional[int] = Field(None, ge=0)
    bike_spaces: Optional[int] = Field(None, ge=0)
    wifi_available: bool = False
    power_sockets: bool = False


class TrainType(TrainTypeBase, BaseDBModel):
    """完整列车类型模型"""
    train_type_id: int
    year_introduced: Optional[int] = None
    power_type: Optional[str] = None
    bi_mode: bool = False
    wheelchair_spaces: Optional[int] = None
    bike_spaces: Optional[int] = None
    wifi_available: bool = False
    power_sockets: bool = False


# ============================================
# Route Models
# ============================================

class RouteBase(BaseModel):
    """路线基础模型"""
    route_code: constr(min_length=1, max_length=20) = Field(..., description="路线代码")
    route_name: constr(min_length=1, max_length=200) = Field(..., description="路线名称")
    origin_station_id: int = Field(..., gt=0)
    destination_station_id: int = Field(..., gt=0)
    distance_km: Optional[condecimal(max_digits=8, decimal_places=2)] = Field(None, ge=0)
    typical_duration_minutes: Optional[int] = Field(None, ge=0)
    operator_id: Optional[int] = None
    is_express: bool = False
    
    @validator('destination_station_id')
    def stations_must_differ(cls, v, values):
        """起点和终点不能相同"""
        if 'origin_station_id' in values and v == values['origin_station_id']:
            raise ValueError('起点和终点车站不能相同')
        return v


class RouteCreate(RouteBase):
    """创建路线模型"""
    scenic_rating: Optional[int] = Field(None, ge=1, le=5)
    difficulty_level: Optional[int] = Field(None, ge=1, le=5)
    main_line: Optional[str] = None
    electrified: bool = False


class Route(RouteBase, BaseDBModel):
    """完整路线模型"""
    route_id: int
    scenic_rating: Optional[int] = None
    difficulty_level: Optional[int] = None
    main_line: Optional[str] = None
    electrified: bool = False


# ============================================
# Service Models
# ============================================

class ServiceBase(BaseModel):
    """车次基础模型"""
    service_code: constr(min_length=1, max_length=20) = Field(..., description="车次代码")
    route_id: int = Field(..., gt=0)
    operator_id: int = Field(..., gt=0)
    train_type_id: Optional[int] = None
    departure_time: time = Field(..., description="出发时间")
    arrival_time: time = Field(..., description="到达时间")
    scheduled_duration_minutes: Optional[int] = Field(None, ge=0)
    frequency: Optional[str] = None


class ServiceCreate(ServiceBase):
    """创建车次模型"""
    weekday_only: bool = False
    saturday_service: bool = True
    sunday_service: bool = True
    bank_holiday_service: bool = False
    reservation_required: bool = False
    first_class_available: bool = True
    catering_available: bool = False


class Service(ServiceBase, BaseDBModel):
    """完整车次模型"""
    service_id: int
    weekday_only: bool = False
    saturday_service: bool = True
    sunday_service: bool = True
    bank_holiday_service: bool = False
    reservation_required: bool = False
    first_class_available: bool = True
    catering_available: bool = False


# ============================================
# Service Stop Models
# ============================================

class ServiceStopBase(BaseModel):
    """车站停靠基础模型"""
    service_id: int = Field(..., gt=0)
    station_id: int = Field(..., gt=0)
    stop_sequence: int = Field(..., ge=1, description="停靠顺序")
    arrival_time: Optional[time] = None
    departure_time: Optional[time] = None
    platform: Optional[constr(max_length=10)] = None
    dwell_time_minutes: Optional[int] = Field(None, ge=0)
    is_pickup: bool = True
    is_dropoff: bool = True


class ServiceStopCreate(ServiceStopBase):
    """创建停靠站模型"""
    typical_delay_minutes: Optional[int] = None
    delay_risk_level: Optional[int] = Field(None, ge=1, le=5)


class ServiceStop(ServiceStopBase, BaseDBModel):
    """完整停靠站模型"""
    stop_id: int
    typical_delay_minutes: Optional[int] = None
    delay_risk_level: Optional[int] = None


# ============================================
# Fare Models
# ============================================

class FareBase(BaseModel):
    """票价基础模型"""
    origin_station_id: int = Field(..., gt=0)
    destination_station_id: int = Field(..., gt=0)
    fare_type: FareType = Field(..., description="票价类型")
    ticket_class: TicketClass = Field(..., description="车票等级")
    adult_fare: condecimal(max_digits=10, decimal_places=2) = Field(..., gt=0)
    child_fare: Optional[condecimal(max_digits=10, decimal_places=2)] = Field(None, ge=0)
    railcard_discount: Optional[condecimal(max_digits=5, decimal_places=2)] = Field(
        None, ge=0, le=100
    )
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    
    @validator('destination_station_id')
    def stations_must_differ(cls, v, values):
        """起点和终点不能相同"""
        if 'origin_station_id' in values and v == values['origin_station_id']:
            raise ValueError('起点和终点车站不能相同')
        return v


class FareCreate(FareBase):
    """创建票价模型"""
    restrictions: Optional[str] = None
    refundable: bool = False
    exchangeable: bool = False
    route_restriction: Optional[str] = None
    operator_restriction: Optional[int] = None
    peak_time_surcharge: Optional[condecimal(max_digits=10, decimal_places=2)] = None


class Fare(FareBase, BaseDBModel):
    """完整票价模型"""
    fare_id: int
    restrictions: Optional[str] = None
    refundable: bool = False
    exchangeable: bool = False
    route_restriction: Optional[str] = None
    operator_restriction: Optional[int] = None
    peak_time_surcharge: Optional[Decimal] = None


# ============================================
# Delay Record Models
# ============================================

class DelayRecordBase(BaseModel):
    """延误记录基础模型"""
    service_id: int = Field(..., gt=0)
    station_id: int = Field(..., gt=0)
    scheduled_time: datetime = Field(..., description="计划时间")
    actual_time: Optional[datetime] = None
    delay_minutes: Optional[int] = Field(None, description="延误分钟数")
    cancellation: bool = False
    delay_reason: Optional[constr(max_length=200)] = None
    delay_category: Optional[DelayCategory] = None


class DelayRecordCreate(DelayRecordBase):
    """创建延误记录模型"""
    weather_condition: Optional[WeatherCondition] = None
    temperature: Optional[condecimal(max_digits=5, decimal_places=2)] = None
    precipitation: Optional[condecimal(max_digits=5, decimal_places=2)] = Field(None, ge=0)
    wind_speed: Optional[condecimal(max_digits=5, decimal_places=2)] = Field(None, ge=0)
    day_of_week: Optional[int] = Field(None, ge=1, le=7)
    is_peak_hour: bool = False
    is_holiday: bool = False
    passenger_count: Optional[int] = Field(None, ge=0)


class DelayRecord(DelayRecordBase, BaseDBModel):
    """完整延误记录模型"""
    delay_id: int
    weather_condition: Optional[str] = None
    temperature: Optional[Decimal] = None
    precipitation: Optional[Decimal] = None
    wind_speed: Optional[Decimal] = None
    day_of_week: Optional[int] = None
    is_peak_hour: bool = False
    is_holiday: bool = False
    passenger_count: Optional[int] = None


# ============================================
# Weather Data Models
# ============================================

class WeatherDataBase(BaseModel):
    """天气数据基础模型"""
    station_id: int = Field(..., gt=0)
    record_time: datetime = Field(..., description="记录时间")
    temperature: Optional[condecimal(max_digits=5, decimal_places=2)] = None
    feels_like: Optional[condecimal(max_digits=5, decimal_places=2)] = None
    humidity: Optional[int] = Field(None, ge=0, le=100)
    pressure: Optional[condecimal(max_digits=7, decimal_places=2)] = Field(None, ge=0)
    wind_speed: Optional[condecimal(max_digits=5, decimal_places=2)] = Field(None, ge=0)
    wind_direction: Optional[int] = Field(None, ge=0, le=360)
    precipitation: Optional[condecimal(max_digits=5, decimal_places=2)] = Field(None, ge=0)
    visibility: Optional[int] = Field(None, ge=0)
    weather_condition: Optional[WeatherCondition] = None


class WeatherDataCreate(WeatherDataBase):
    """创建天气数据模型"""
    uv_index: Optional[int] = Field(None, ge=0, le=15)
    cloud_cover: Optional[int] = Field(None, ge=0, le=100)
    dew_point: Optional[condecimal(max_digits=5, decimal_places=2)] = None


class WeatherData(WeatherDataBase, BaseDBModel):
    """完整天气数据模型"""
    weather_id: int
    uv_index: Optional[int] = None
    cloud_cover: Optional[int] = None
    dew_point: Optional[Decimal] = None


# ============================================
# Query History Models
# ============================================

class QueryHistoryBase(BaseModel):
    """查询历史基础模型"""
    session_id: Optional[constr(max_length=100)] = None
    origin_station_id: Optional[int] = None
    destination_station_id: Optional[int] = None
    departure_date: Optional[date] = None
    departure_time: Optional[time] = None
    passengers: int = Field(1, ge=1, le=99)
    railcard_type: Optional[str] = None


class QueryHistoryCreate(QueryHistoryBase):
    """创建查询历史模型"""
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    response_time_ms: Optional[int] = Field(None, ge=0)
    results_count: Optional[int] = Field(None, ge=0)


class QueryHistory(QueryHistoryBase, BaseDBModel):
    """完整查询历史模型"""
    query_id: int
    search_timestamp: datetime
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    response_time_ms: Optional[int] = None
    results_count: Optional[int] = None


# ============================================
# Prediction Cache Models
# ============================================

class PredictionCacheBase(BaseModel):
    """预测缓存基础模型"""
    service_id: int = Field(..., gt=0)
    station_id: int = Field(..., gt=0)
    prediction_date: date = Field(..., description="预测日期")
    prediction_time: time = Field(..., description="预测时间")
    predicted_delay_minutes: Optional[int] = None
    confidence_score: Optional[condecimal(max_digits=5, decimal_places=4)] = Field(
        None, ge=0, le=1
    )
    model_version: Optional[str] = None
    features_used: Optional[str] = None


class PredictionCacheCreate(PredictionCacheBase):
    """创建预测缓存模型"""
    weather_factor: Optional[condecimal(max_digits=5, decimal_places=4)] = Field(
        None, ge=0, le=1
    )
    time_factor: Optional[condecimal(max_digits=5, decimal_places=4)] = Field(
        None, ge=0, le=1
    )
    historical_factor: Optional[condecimal(max_digits=5, decimal_places=4)] = Field(
        None, ge=0, le=1
    )
    expires_at: Optional[datetime] = None


class PredictionCache(PredictionCacheBase, BaseDBModel):
    """完整预测缓存模型"""
    cache_id: int
    weather_factor: Optional[Decimal] = None
    time_factor: Optional[Decimal] = None
    historical_factor: Optional[Decimal] = None
    expires_at: Optional[datetime] = None


# ============================================
# Journey Search Models (用于API)
# ============================================

class JourneySearch(BaseModel):
    """行程搜索请求模型"""
    origin: constr(min_length=3, max_length=10) = Field(..., description="起点车站代码")
    destination: constr(min_length=3, max_length=10) = Field(..., description="终点车站代码")
    departure_date: date = Field(..., description="出发日期")
    departure_time: Optional[time] = None
    arrival_time: Optional[time] = None
    passengers: int = Field(1, ge=1, le=9)
    railcard: Optional[str] = None
    ticket_class: TicketClass = TicketClass.STANDARD
    
    @validator('destination')
    def stations_must_differ(cls, v, values):
        """起点和终点不能相同"""
        if 'origin' in values and v.upper() == values['origin'].upper():
            raise ValueError('起点和终点车站不能相同')
        return v.upper()
    
    @validator('origin')
    def origin_uppercase(cls, v):
        """起点代码自动转大写"""
        return v.upper()


class JourneyOption(BaseModel):
    """行程选项响应模型"""
    service_code: str
    operator_name: str
    departure_time: time
    arrival_time: time
    duration_minutes: int
    changes: int
    fare: Decimal
    predicted_delay: Optional[int] = None
    delay_confidence: Optional[float] = None
    train_type: Optional[str] = None
    
    class Config:
        json_encoders = {
            time: lambda v: v.strftime('%H:%M'),
            Decimal: lambda v: float(v),
        }


# ============================================
# 工具函数
# ============================================

def validate_station_code(code: str) -> bool:
    """验证车站代码格式"""
    return len(code) == 3 and code.isalpha() and code.isupper()


def validate_time_range(start: time, end: time) -> bool:
    """验证时间范围"""
    return start < end
