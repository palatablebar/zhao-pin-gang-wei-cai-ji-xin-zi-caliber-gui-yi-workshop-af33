# jobnorm · 招聘岗位采集与薪资口径归一工坊

> 把「15-25K·14薪」「300/天」「20-30万/年」「面议」归一成同一把月薪口径的尺子，并给出城市 × 职能的 P25/P50/P75 薪资基准与质量门禁。

## 真实场景

- **模拟客户**：岗线数据（杭州，20 人），为 30 家 HR 客户提供岗位画像与薪资基准。
- **现有工作流**：分析师从 5 个招聘站采集岗位到 Excel，手工清洗薪资文本与岗位标题，再拼薪资报告。
- **三个痛点**：① 年薪/月薪/日结/13~16 薪口径混在一起，中位数互相矛盾；② 岗位标题归一大类靠肉眼；③ 兼职混入、上限小于下限、极端值等脏数据无标记。
- **上下游**：上游 5 个招聘站采集（seed 原始 JSON 代表已入湖数据）→ 本系统做「薪资解析 + 标题归一 + 基准报表 + 质量门禁」→ 下游 HR 薪资报告与招聘策略。

## 主要功能

- **采集源**：5 个源（拉勾/BOSS直聘/猎聘/企业官网/猎头），展示原始条数与同步状态；「模拟同步」由 Celery worker 异步投递到采集入库服务（自然键去重 + external_id 幂等）。
- **采集入库**：POST `/api/ingest/batches` 按「公司 + 城市 + 职位」自然键去重：同一岗位本次只保留最新薪酬，迟到旧版本（发布时间更早）只留冲突说明、不覆盖最新版本；人工修正过的岗位不被采集改写；面议/无法解析/缺字段/兼职/批内重复 external_id 等异常记录隔离为 `quarantined`，不进标准化表与基准样本。批次以 `batch_key` 幂等，重复运行同一批不新增岗位。页面展示新增/合并/忽略/失败数量、分源统计与合并前后来源，一键运行五渠道重送演示批。
- **原始队列**：按解析状态（已解析/待修正/解析失败/重复折叠/脏原文/人工修正/异常隔离）筛选；raw 原文 ↔ 归一结果对照面板（含冲突说明与「已被 raw #N 取代」）；人工修正薪资/城市并落库。
- **标准化结果表**：城市/职能/职级/质量标记筛选；细线刻度尺式薪资区间条；CSV 导出。
- **口径规则**：v1 历史基线（K/万/13~16 薪）与 v2 增补（面议识别、日结/时薪折算、中文千区间）版本化；按钮真实试跑命中率（v1 91.1% → v2 96.1%）；切版本重跑全部原始队列，人工修正条目不覆盖。
- **薪资基准报表**：按城市 × 职能用 numpy 线性插值计算 P25/P50/P75、样本量与分布；发布（admin）与 CSV 导出。
- **质量门禁**：12 条异常分类（面议 4 / 日结时薪 3 / 上下限倒置 2 / 兼职混入 2 / 极端值 1），逐条处置（disposed/ignored）并写审计。

## 快速启动

```bash
cp .env.example .env
docker compose config --quiet
docker compose up -d --build
# 等 5/5 healthy（首次构建约 2-4 分钟）
docker compose ps
```

- 前端：http://localhost:18239（采集入库页 `/ingest`）
- 后端 OpenAPI：http://localhost:19239/docs
- 健康检查：`GET /api/health`
- 手动 seed（容器启动时 `SEED_DEMO=true` 已自动跑一次，幂等）：
  ```bash
  docker compose exec -T backend python -m scripts.seed_demo
  # 输出一行：SEED_SUMMARY brand=jobnorm sources=5 raws=180 postings=150 rules=6 benchmarks=3 users=3
  ```

## 演示账号（密码统一 `Demo@2026`）

| 账号 | 角色 | 权限 | 典型动作 |
|---|---|---|---|
| `admin@jobnorm.io` | 数据主管 | 全部 | 激活规则版本、发布基准、触发采集源同步、看审计 |
| `analyst@jobnorm.io` | 标注分析 | 修正标准化结果、重跑解析、处置质量队列；**不能发布** | 修正 1 条、切 v2 重跑、处置门禁 |
| `client@jobnorm.io` | HR 客户（只读） | 只读 + 导出 CSV；**修正/发布 403** | 查看并导出基准报表 |

权限矩阵后端唯一事实源：`backend/src/constants/roles.py`；前端镜像：`frontend/src/constants/roles.ts`。

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | React 18 + TypeScript + Vite 5 + Zustand + React Router 6 |
| 后端 | Python 3.11 + FastAPI + SQLAlchemy 2.0 + Pydantic v2 |
| 异步 | Celery 5 + Redis（心跳 / 模拟同步任务） |
| 数据库 | MySQL 8.0（utf8mb4，Alembic 迁移） |
| 部署 | Docker Compose，5 服务（frontend/backend/worker/db/redis），Nginx 托管 dist |

## 核心算法（均为 Python 真算并落库）

### A. 薪资文本解析与月薪标准化 `backend/src/services/salary_parser.py`

- **输入**：`salary_raw` 文本（如 `15-25K·14薪`、`8千-1.2万`、`20-30万/年`、`300/天`、`45元/小时`、`面议`）。
- **输出**：`{min, max, median, unit_kind, annual_months, confidence, reason_code, flags, matched_rules}`。
- **公式口径**：K=千=1000、万=10000；周期折算月薪（月 ×1 / 年 ÷12 / 日 ×22 / 时 ×8×22）；`·14薪` 月薪 ×14/12；`13-16薪` 取上限 16；`median = (min+max)//2`；`15-25K·14薪` → min=17500 / max=29166 / median=23333 / annual_months=14。
- **失败态与校验**：面议 → 全 null + `negotiable`；无法解析 → 全 null + `unparsed` + reason；min>max 交换并标 `swapped`；月薪越界 [3000, 300000] 标 `outlier`。
- **可复现**：纯函数、无随机；规则版本 v1/v2 由 `SUPPORTED_PATTERNS` 决定。

### B. 岗位标题归一与职级/职能映射 `backend/src/services/title_normalizer.py`

- **输入**：`title_raw` + `experience_raw`。
- **输出**：`{canonical_title, function_type, seniority, confidence, matched_terms}`。
- **流程**：NFKC 全角→半角 → 去括号内容 → 去营销词（急招/高薪/包住…）→ 词典最大匹配分词（职能 60 词 / 职级 12 词）→ 权重最高定职能 → 职级词 + 年限（3-5 年）定 seniority → 拼 canonical_title。
- **相似合并**：字符 3-gram Jaccard ≥ 0.80 归并到已有 canonical，取频次最高写法（`batch_merge_titles`，规则页可跑演示）。
- **失败态**：无职能词命中时低置信度兜底并进入质量门禁 `needs_review`，不静默当成正确答案。

### 分位计算 `backend/src/services/percentile.py`

numpy `percentile(method="linear")` 计算 P25/P50/P75；基准生成排除质量标记与面议样本（`quality_flags` 为空且 `salary_median` 非空）。

## 目录结构

```
gb-566/
├── docker-compose.yml          # 5 服务：frontend/backend/worker/db/redis
├── .env / .env.example
├── backend/
│   ├── Dockerfile / entrypoint.sh / alembic.ini / requirements.txt
│   ├── scripts/seed_demo.py        # 幂等 seed，打印 SEED_SUMMARY
│   ├── scripts/demo_ingest_batch.py # 五渠道重送演示批（合并/迟到旧版本/异常隔离）
│   ├── scripts/verify_ingest.py     # 采集入库验收脚本（SQLite，无需 Docker）
│   ├── scripts/verify_ingest_api.py # 采集入库 API 冒烟（TestClient）
│   ├── scripts/demo_corpus.py      # 180 条确定性演示语料
│   ├── scripts/worker_healthcheck.py
│   ├── migrations/                 # Alembic（0001 由 models metadata 建表，0002 采集入库表/去重列）
│   └── src/
│       ├── config/                 # settings / database / celery_app / app
│       ├── constants/              # enums / roles / error_codes / limits
│       ├── models/                 # User/Source/RawPosting/Posting/ParseRule/Benchmark/AuditLog/IngestBatch/IngestRecord
│       ├── schemas/                # Pydantic v2
│       ├── services/               # salary_parser / title_normalizer / percentile / 领域服务
│       ├── controllers/            # 路由处理函数
│       ├── routes/                 # APIRouter
│       ├── middlewares/            # auth / rbac / audit_logger / rate_limit / error_handler
│       └── utils/                  # jwt / errors / logger / pagination / cities
└── frontend/
    ├── Dockerfile / nginx.conf / vite.config.ts / package.json
    └── src/
        ├── api/ stores/ types/ hooks/ utils/ constants/
        ├── components/{common,layout}/
        └── pages/                  # Login/Sources/RawQueue/Postings/Rules/Benchmarks/Quality
```

## 环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `FRONTEND_PORT` | 18239 | 前端映射端口（容器内 80） |
| `BACKEND_PORT` | 19239 | 后端映射端口（容器内 8000） |
| `DB_PORT` | 17739 | MySQL 映射端口（容器内 3306） |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` | jobnorm | 应用库与账号 |
| `DB_ROOT_PASSWORD` | jobnorm_root_2026 | MySQL root 密码 |
| `JWT_SECRET` | 见 .env.example | HS256 签名密钥 |
| `REDIS_URL` | redis://redis:6379/0 | Celery broker/backend + 心跳 |
| `SEED_DEMO` | true | 后端启动时自动跑一次幂等 seed |
| `RATE_LIMIT_PER_MINUTE` | 900 | 按客户端 IP 的滑动窗口限流 |

## Docker 说明

- 恰好 5 服务且都有 healthcheck；`backend`/`worker` 依赖 `db`/`redis` 的 `service_healthy`，`frontend` 依赖 `backend` healthy。
- `worker` 复用 backend 镜像，`command` 切到 `celery -A src.config.celery_app worker -B`；健康检查读 Redis 心跳键。
- Nginx：`location /api/ { proxy_pass http://backend:8000/; }` + SPA 回落；后端同一份路由既挂 `/api/*` 也挂根路径。
- 命名卷：`db_data`、`redis_data`、`app_artifacts`。

## 采集入库验收

```bash
# 服务级：新版本覆盖 / 迟到旧版本不覆盖 / 异常隔离 / 同批幂等 / 人工修正保护
docker compose exec -T backend python -m scripts.verify_ingest
# API 级：路由 + 鉴权 + 台账 + 合并前后来源
docker compose exec -T backend python -m scripts.verify_ingest_api
```

两个脚本用 SQLite 内存库跑真实 service/路由，不需要 MySQL/Redis；容器内跑需要容器镜像自带 `httpx`（API 冒烟用 TestClient）。

## 共享枚举出现位置

| 枚举 | 后端定义 | 前端定义 | 使用位置 |
|---|---|---|---|
| roles | `backend/src/constants/roles.py` | `frontend/src/constants/roles.ts` | 鉴权依赖、审计、AppShell、登录页、按钮 disabled |
| function_type / seniority | `backend/src/constants/enums.py` | `frontend/src/constants/enums.ts` | Posting model、schema、基准生成、Postings/Benchmarks 页 |
| raw_status | 同上 | 同上 | RawPosting model、raw_service、RawQueue 状态抽屉 |
| quality_flag | 同上 | 同上 | posting_service/quality_service、Quality 页、ParseDiffPanel |
| rule_type / salary_unit | 同上 | 同上 | ParseRule/Posting model、Rules 页 |

## License

Demo 项目，仅用于教学与评审演示；演示数据均为构造数据。
