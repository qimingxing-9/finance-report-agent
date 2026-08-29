CREATE TABLE IF NOT EXISTS report_info (
    id            BIGINT PRIMARY KEY AUTO_INCREMENT,
    session_id    VARCHAR(64)  NOT NULL UNIQUE,
    file_name     VARCHAR(255) NOT NULL,
    file_path     VARCHAR(512) NOT NULL,
    company_name  VARCHAR(128) DEFAULT NULL,
    report_year   INT          DEFAULT NULL,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_session (session_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS financial_metric (
    id            BIGINT PRIMARY KEY AUTO_INCREMENT,
    session_id    VARCHAR(64) NOT NULL,
    metric_name   VARCHAR(64)  NOT NULL,
    metric_value  DECIMAL(18,4) DEFAULT NULL,
    period        VARCHAR(32)  NOT NULL,
    yoy           DECIMAL(10,4) DEFAULT NULL,
    qoq           DECIMAL(10,4) DEFAULT NULL,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_session_period (session_id, period)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS analysis_report (
    id            BIGINT PRIMARY KEY AUTO_INCREMENT,
    report_id     VARCHAR(64) NOT NULL UNIQUE,
    session_id    VARCHAR(64) NOT NULL,
    title         VARCHAR(255) NOT NULL,
    content_md    LONGTEXT     NOT NULL,
    file_path     VARCHAR(512) NOT NULL,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_session (session_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
