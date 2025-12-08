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
    site_url TEXT NOT NULL,
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

-- EVENTS (SDK, финальная структура)
CREATE TABLE IF NOT EXISTS events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    site_url TEXT NOT NULL,
    uid TEXT,
    session_id TEXT,

    event_type TEXT,
    event_time TIMESTAMPTZ DEFAULT NOW(),

    -- CLICK BUTTON
    button_text TEXT,
    button_id TEXT,
    button_class TEXT,
    button_type TEXT,

    -- FORMS
    form_selector TEXT,
    form_button_text TEXT,
    form_structure JSONB,

    -- HEARTBEAT (scroll + activity)
    hb_scroll_percent INT,
    hb_max_scroll INT,
    hb_scroll_y INT,
    hb_session_duration_ms BIGINT,
    hb_since_last_activity_ms BIGINT,

    -- DEVICE INFO
    device_type TEXT,
    os TEXT,
    browser TEXT,
    user_agent TEXT,
    viewport_width INT,
    viewport_height INT,
    screen_width INT,
    screen_height INT,

    -- GEO (через IP, считаем на бэке)
    ip_hash TEXT,
    country TEXT,
    city TEXT
);

-- SESSIONS (пока не трогаем, пусть лежит)
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    site_id UUID REFERENCES sites(id),
    url_start TEXT,
    user_agent TEXT,
    ip_hash TEXT,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ
);
