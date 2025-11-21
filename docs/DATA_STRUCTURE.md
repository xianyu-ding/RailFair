# 项目数据结构总览

本文档整理 `uk-rail-delay-predictor` 项目的整体结构，涵盖：
- 仓库目录与关键文件
- 数据与配置存储位置
- 代码模块职责划分
- 现有数据库表结构

旨在帮助团队快速了解数据流向、依赖关系与扩展入口。

---

## 1. 仓库目录速览

```
uk-rail-delay-predictor/
├── configs/            # YAML 等运行配置
├── data/               # 自动生成的本地数据（raw/processed/cache、SQLite）
├── docs/               # 文档（架构、日记、数据结构）
├── logs/               # 运行日志（按日期滚动）
├── models/             # 训练产出及实验
├── notebooks/          # 探索性分析 / 原型
├── scripts/            # 工具脚本（连通性检测、验证等）
├── src/                # 可复用核心代码（API、数据管道、模型、工具）
├── tests/              # `pytest` 测试（unit + integration）
├── fetch_hsp.py        # HSP 数据抓取主脚本
├── hsp_processor.py    # HSP 数据处理逻辑
├── hsp_validator.py    # HSP 数据校验逻辑
├── retry_handler.py    # 重试与错误分类工具
├── models.py           # 模型训练入口（WIP）
├── init_database.py    # 数据库初始化脚本
├── create_hsp_tables.sql
├── requirements.txt
└── README.md / QUICKSTART.md / docs/...
```

说明：
- 可执行脚本大多位于根目录或 `scripts/`。
- `src/` 封装库化模块，便于测试与复用。
- `docs/DAY1_SUMMARY.md`、`logs/` 等记录每日进展与运行情况。

---

## 2. 代码模块职责（`src/`）

| 子目录 | 说明 | 关键文件 |
| ------ | ---- | -------- |
| `src/api/` | 预留对外 API 层，当前为空，未来用于暴露 REST/GraphQL 接口。 | —— |
| `src/data_collection/` | 外部数据源客户端封装，目前包括 HSP API。 | `hsp_client.py` |
| `src/models/` | 模型训练与预测逻辑（占位，随模型迭代补充）。 | —— |
| `src/preprocessing/` | 特征工程与数据清洗（待完善）。 | —— |
| `src/utils/` | 通用工具，例如配置加载、日志初始化、目录保障。 | `config.py`, `logger.py` |

辅助模块：
- `hsp_processor.py`：位于根目录，提供 `HSPDataProcessor`，负责将原始 API 响应转换成结构化记录。
- `retry_handler.py`：为 API 调用提供带指数退避的重试装饰器。

---

## 3. 脚本与工作流

- `fetch_hsp.py`：Day3 主流程，负责按 `configs/hsp_config.yaml` 抓取数据 → 处理 → 验证 → 落库。
- `test_hsp_fetch.py`：集成测试脚本；支持离线结构测试（无凭据时）与线上 API 验证。
- `init_database.py` / `create_hsp_tables.sql`：手动初始化数据库所需的 SQL。
- `scripts/validate_setup.py`、`scripts/test_api_connection.py`：环境自检与 API 连通性测试。
- `quick_start.sh`：自动化启动脚本。

> CLI 脚本会优先读取环境变量，若 `.env` 无法访问则给出警告，不阻断执行。

---

## 4. 数据目录结构

数据库在 `fetch_hsp.py` 首次写入时自动初始化，表结构来自 `create_hsp_tables.sql`。主要表如下：

### `hsp_service_metrics`
- `id` (`INTEGER`, PK, AUTOINCREMENT)
- `origin` (`TEXT`, 非空)：出发站 CRS 码
- `destination` (`TEXT`, 非空)：到达站 CRS 码
- `scheduled_departure` (`TEXT`，可空)：计划出发时间（HHMM 或 ISO 日期时间）
- `scheduled_arrival` (`TEXT`，可空)：计划到达时间
- `toc_code` (`TEXT`, 非空)：列车运营公司代码
- `matched_services_count` (`INTEGER`，可空)：匹配到的服务次数
- `fetch_timestamp` (`TIMESTAMP`，默认 `CURRENT_TIMESTAMP`)
- 复合唯一键：`(origin, destination, scheduled_departure, scheduled_arrival, toc_code)`
- 索引：`idx_hsp_metrics_route(origin, destination)`、`idx_hsp_metrics_toc(toc_code)`

### `hsp_service_details`
- `id` (`INTEGER`, PK, AUTOINCREMENT)
- `rid` (`TEXT`, 非空)：RTTI Service ID
- `date_of_service` (`TEXT`, 非空)：服务日期
- `toc_code` (`TEXT`, 非空)
- `location` (`TEXT`, 非空)：站点 CRS 码
- `scheduled_departure` (`TIMESTAMP`，可空)
- `scheduled_arrival` (`TIMESTAMP`，可空)
- `actual_departure` (`TIMESTAMP`，可空)
- `actual_arrival` (`TIMESTAMP`，可空)
- `departure_delay_minutes` (`INTEGER`，可空)
- `arrival_delay_minutes` (`INTEGER`，可空)
- `cancellation_reason` (`TEXT`，可空)
- `fetch_timestamp` (`TIMESTAMP`，默认 `CURRENT_TIMESTAMP`)
- 复合唯一键：`(rid, location)`
- 索引：`idx_hsp_details_rid(rid)`、`idx_hsp_details_date(date_of_service)`、`idx_hsp_details_location(location)`、`idx_hsp_details_delay(arrival_delay_minutes)`

> 当 `create_hsp_tables.sql` 不存在时，系统会回退到脚本内的最小建表语句，确保上述两张表存在。

---

## 5. SQLite 数据库（`data/railfair.db`）

根目录下的 `data/` 文件夹被 `src/utils/config.py` 自动创建，并包含以下子目录：

```
data/
├── cache/        # 短期缓存文件（可选）
├── processed/    # 处理后的数据输出
├── railfair.db   # 项目主 SQLite 数据库
└── raw/
    ├── darwin/   # Darwin Push Port 原始数据
    ├── hsp/      # HSP API 原始响应（JSON 等）
    ├── kb/       # National Rail Knowledgebase 数据
    └── weather/  # 天气数据
```

---

## 6. 配置与敏感信息管理

### 运行参数
- `configs/hsp_config.yaml`：HSP 抓取脚本的核心配置，包含 API 基础信息、日期范围、重试策略、日志设置等。
  - 若 `auth.username` / `auth.password` 填写，则在环境变量缺失时作为兜底凭据。

### 环境变量
- `.env`（可选）：如果存在，`fetch_hsp.py` 和 `test_hsp_fetch.py` 会尝试加载，其中可设置：
  - `HSP_EMAIL` 或 `HSP_USERNAME`
  - `HSP_PASSWORD`
  - 其他 API/数据库密钥

---

## 7. 测试与质量保障

- `tests/unit/`：单元测试（覆盖核心处理与验证逻辑）。
- `tests/integration/`：端到端或跨模块集成测试。
- `test_hsp_fetch.py`：脚本级别的手动/自动测试入口。
- `retry_handler.py` 日志方便排查 API 失败与重试情况。
- 运行 `pytest` 前确保虚拟环境与依赖安装齐全（`requirements.txt`）。

---

## 8. 模型与实验（占位说明）

- `models/`：保存训练好的模型与实验配置。`models/experiments/` 用于记录实验，`models/saved_models/` 用于持久化模型文件。
- `models.py`：未来统一的模型训练入口（目前为草稿或待完善状态）。
- `notebooks/`：Jupyter Notebook，适合探索性数据分析（EDA）、特征试验。

---

## 9. 维护建议

- 数据库结构变更：优先修改 `create_hsp_tables.sql`，并同步更新 `_initialize_database` 回退逻辑。
- 新数据源：在 `src/data_collection/` 新增客户端，在 `src/utils/config.py` 暴露配置与目录。
- 配置同步：更新 `configs/` 时请在文档中注明默认值与覆盖策略。
- 文档更新：新增重要模块/目录后，记得补充本文件以方便团队成员快速熟悉项目。

