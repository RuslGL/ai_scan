-- USERS
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT,
    telegram_id TEXT,
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    source TEXT,
    auth_method TEXT,
    category TEXT,
    dashboard_token TEXT,
    dashboard_token_created_at TIMESTAMPTZ
);

-- PLANS
CREATE TABLE IF NOT EXISTS plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT,
    price INT,
    sites_limit INT,
    events_limit INT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- USER PLANS
CREATE TABLE IF NOT EXISTS user_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    plan_id UUID REFERENCES plans(id),
    valid_until TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

------------------------------------------------------------
--                         SITES
------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    site_url TEXT NOT NULL UNIQUE,
    api_key TEXT,
    category TEXT,

    -- TARGET ACTION (BUTTON TEXT)
    target_action_text TEXT,

    /*
      SITE TIMEZONE
      Формат: только IANA (пример: 'Europe/Moscow', 'America/Chicago', 'UTC')
      ❌ не допускаются строки вида '+03:00', 'MSK', 'GMT+3'
      Все timestamp продолжаем хранить в UTC
      Таймзона используется только для интерпретации суток и локальной даты
    */
    timezone TEXT NOT NULL DEFAULT 'UTC',

    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_scan_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- SITE STRUCTURE
CREATE TABLE IF NOT EXISTS site_structure (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    site_id UUID REFERENCES sites(id),
    url TEXT,
    tilda_id TEXT,
    element_type TEXT,
    text_current TEXT,
    position_index INT,
    is_active BOOLEAN DEFAULT TRUE,
    first_seen TIMESTAMPTZ DEFAULT NOW(),
    last_seen TIMESTAMPTZ DEFAULT NOW()
);

------------------------------------------------------------
--                EVENTS (ACTUAL SDK VERSION)
------------------------------------------------------------
CREATE TABLE IF NOT EXISTS events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- BASIC
    site_url TEXT NOT NULL,
    uid TEXT,
    session_id TEXT,
    event_type TEXT NOT NULL,
    event_time TIMESTAMPTZ NOT NULL,
    received_at TIMESTAMPTZ DEFAULT NOW(),

    -- SCROLL
    scroll_position_percent INT,

    -- CLICK
    button_text TEXT,
    button_id TEXT,
    button_class TEXT,

    -- DEVICE META
    device_type TEXT,
    os TEXT,
    browser TEXT,
    user_agent TEXT,

    -- NETWORK
    client_ip INET
);

------------------------------------------------------------
--              SESSION_SUMMARY (AGGREGATED VISITS)
------------------------------------------------------------
CREATE TABLE IF NOT EXISTS session_summary (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- IDENTIFIERS
    site_url TEXT NOT NULL,
    uid TEXT,
    session_id TEXT NOT NULL,

    -- VISIT TIME
    visit_start TIMESTAMPTZ NOT NULL,
    visit_end TIMESTAMPTZ NOT NULL,
    duration_seconds INT NOT NULL,

    -- GEO
    country TEXT,
    city TEXT,

    -- DEVICE
    device_type TEXT,
    os TEXT,
    browser TEXT,

    -- SCROLL SUMMARY
    max_scroll_depth INT,
    final_scroll_depth INT,
    scroll_stops JSONB,

    -- CLICKS SUMMARY
    click_buttons JSONB,

    -- AGGREGATES
    total_scroll_events INT,
    total_click_events INT,

    -- META
    created_at TIMESTAMPTZ DEFAULT NOW()
);

------------------------------------------------------------
--              DASHBOARD TOKENS (ONE TOKEN = ONE SITE)
------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dashboard_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- TOKEN
    token TEXT NOT NULL UNIQUE,

    -- OWNER
    user_id UUID REFERENCES users(id),

    -- ACCESS LEVEL (not scope)
    role TEXT NOT NULL CHECK (role IN ('user', 'admin')),

    -- HARD SITE BINDING
    site_url TEXT NOT NULL REFERENCES sites(site_url) ON DELETE CASCADE,

    -- LIFECYCLE
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    expires_at TIMESTAMPTZ,

    -- ROTATION
    rotated_from UUID REFERENCES dashboard_tokens(id),

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- INDEXES
CREATE INDEX IF NOT EXISTS idx_dashboard_tokens_site_url
ON dashboard_tokens(site_url);

------------------------------------------------------------
--              AGGREGATED SITE METRICS (DAILY)
------------------------------------------------------------
/*
Храним результаты суточной агрегации:
- daily        — показатели за текущие сутки
- baseline_7d  — бенчмарк (медиана/агрегаты за предыдущий период)
- stats        — результаты стат-тестов

Все timestamp остаются в UTC.
date_local — календарные сутки в таймзоне сайта (YYYY-MM-DD).
*/

CREATE TABLE IF NOT EXISTS site_daily_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- BINDING
    site_url TEXT NOT NULL REFERENCES sites(site_url) ON DELETE CASCADE,

    -- LOCAL DAY (NOT TIMESTAMP)
    date_local DATE NOT NULL,

    -- JSON BLOCKS (как отдаёт агрегатор)
    daily JSONB NOT NULL,
    baseline_7d JSONB,
    stats JSONB,

    -- META
    period_days INT NOT NULL DEFAULT 7,
    timezone TEXT NOT NULL,
    computed_at TIMESTAMPTZ DEFAULT NOW(),

    -- AI DELIVERY STATUS
    reported BOOLEAN NOT NULL DEFAULT FALSE,

    UNIQUE (site_url, date_local)
);

CREATE INDEX IF NOT EXISTS idx_site_daily_metrics_site_date
ON site_daily_metrics(site_url, date_local);

CREATE INDEX IF NOT EXISTS idx_site_daily_metrics_reported
ON site_daily_metrics(reported);

