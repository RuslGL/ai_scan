-- USERS
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,
    email TEXT,
    telegram_id TEXT,
    joined_at TIMESTAMP,
    source TEXT,
    auth_method TEXT,
    category TEXT,
    dashboard_token TEXT,
    dashboard_token_created_at TIMESTAMP
);

-- PLANS
CREATE TABLE IF NOT EXISTS plans (
    id UUID PRIMARY KEY,
    name TEXT,
    price INT,
    sites_limit INT,
    events_limit INT,
    created_at TIMESTAMP
);

-- USER PLANS
CREATE TABLE IF NOT EXISTS user_plans (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    plan_id UUID REFERENCES plans(id),
    valid_until TIMESTAMP,
    is_active BOOLEAN,
    created_at TIMESTAMP
);

-- SITES
CREATE TABLE IF NOT EXISTS sites (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    site_url TEXT,
    api_key TEXT,
    category TEXT,
    created_at TIMESTAMP,
    last_scan_at TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- SITE STRUCTURE
CREATE TABLE IF NOT EXISTS site_structure (
    id UUID PRIMARY KEY,
    site_id UUID REFERENCES sites(id),
    url TEXT,
    tilda_id TEXT,
    element_type TEXT,
    text_current TEXT,
    position_index INT,
    is_active BOOLEAN,
    first_seen TIMESTAMP,
    last_seen TIMESTAMP
);

-- EVENTS (новая структура под SDK-tracking)
CREATE TABLE IF NOT EXISTS events (
    id UUID PRIMARY KEY,
    site_id UUID REFERENCES sites(id),
    uid TEXT,
    session_id UUID,
    event_type TEXT,
    event_time TIMESTAMP,

    -- CLICK
    click_text TEXT,
    click_block_title TEXT,

    -- SCROLL
    scroll_percent INT,
    scroll_max INT,
    scroll_milestone INT
);

-- SESSIONS
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY,
    site_id UUID REFERENCES sites(id),
    url_start TEXT,
    user_agent TEXT,
    ip_hash TEXT,
    started_at TIMESTAMP,
    ended_at TIMESTAMP
);
