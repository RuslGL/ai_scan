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

-- SITES
CREATE TABLE IF NOT EXISTS sites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    site_url TEXT NOT NULL UNIQUE,
    api_key TEXT,
    category TEXT,
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
