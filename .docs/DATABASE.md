# 数据库文档

---

## 1. MySQL 表设计（sql/init.sql）

```sql
CREATE TABLE report_info (
    id            BIGINT PRIMARY KEY AUTO_INCREMENT,
    session_id    VARCHAR(64)  NOT NULL UNIQUE,
    file_name     VARCHAR(255) NOT NULL,
    file_path     VARCHAR(512) NOT NULL,
    company_name  VARCHAR(128) DEFAULT NULL,     -- 解析阶段回填
    report_year   INT          DEFAULT NULL,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_session (session_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE financial_metric (
    id            BIGINT PRIMARY KEY AUTO_INCREMENT,
    session_id    VARCHAR(64) NOT NULL,
    metric_name   VARCHAR(64)  NOT NULL,   -- 净利润/营业收入/毛利率/资产负债率/经营现金流...
    metric_value  DECIMAL(18,4) DEFAULT NULL,
    period        VARCHAR(32)  NOT NULL,   -- 如 2024FY / 2025H1 / 2025Q3
    yoy           DECIMAL(10,4) DEFAULT NULL,  -- 同比，由风险校验Agent回填
    qoq           DECIMAL(10,4) DEFAULT NULL,  -- 环比
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_session_period (session_id, period)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE analysis_report (
    id            BIGINT PRIMARY KEY AUTO_INCREMENT,
    report_id     VARCHAR(64) NOT NULL UNIQUE,   -- 对外暴露的下载 ID
    session_id    VARCHAR(64) NOT NULL,
    title         VARCHAR(255) NOT NULL,
    content_md    LONGTEXT     NOT NULL,          -- Markdown 全文
    file_path     VARCHAR(512) NOT NULL,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_session (session_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 表说明

| 表名 | 职责 | 写入时机 |
|---|---|---|
| `report_info` | 财报基础信息（文件名、路径、公司名、年份） | 上传接口写入基础字段；PDF解析Agent回填 company_name / report_year |
| `financial_metric` | 结构化财务指标（净利润、营收、毛利率等） | 指标提取Agent逐条写入；风险校验Agent回填 yoy / qoq |
| `analysis_report` | 生成的 Markdown 分析报告 | 报告生成Agent完成后写入 |

---

## 2. Redis 会话持久化设计（核心扩展点）

ADK 原生 `InMemorySessionService` 重启即丢；自定义 `RedisSessionService` 继承 `BaseSessionService`，在 `create_session / get_session / append_event` 等钩子里同步读写 Redis。

### Key 设计

| Key | 类型 | 内容 | TTL |
|---|---|---|---|
| `session:{sid}:status` | String | pending/running/success/failed + error | 7 天 |
| `session:{sid}:events` | List | ADK 事件 JSONL（逐条 rpush，可截断保留最近 N=200 条） | 7 天 |
| `session:{sid}:state` | Hash | Agent 间传递的状态快照（parser→metric→risk→report 各阶段产出摘要） | 7 天 |
| `session:{sid}:chat` | List | 多轮问答 [{role, content}]（保留最近 20 轮） | 7 天 |

### 中断恢复

服务启动时扫描所有 `status=running` 的 session：重新执行流水线（PDF 已落盘，Milvus 切片按 `session_id` 分区先删后插，保证幂等）。

### 多轮问答

chat 接口先从 `session:{sid}:chat` 读取历史拼入 prompt（或恢复 ADK Session），回答完成后 rpush 追加，防止上下文无限膨胀。
