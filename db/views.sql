CREATE OR REPLACE VIEW dashboard_session_summary AS
SELECT
    u.id                AS owner_user_id,
    u.email             AS owner_email,

    s.id                AS site_id,
    s.site_url,

    ss.id               AS session_summary_id,
    ss.session_id,
    ss.visit_start,
    ss.visit_end,
    ss.duration_seconds,

    ss.country,
    ss.city,
    ss.device_type,
    ss.os,
    ss.browser,

    ss.max_scroll_depth,
    ss.final_scroll_depth,
    ss.scroll_stops,
    ss.click_buttons,

    ss.total_scroll_events,
    ss.total_click_events,

    ss.created_at
FROM session_summary ss
JOIN sites s
    ON s.site_url = ss.site_url
JOIN users u
    ON u.id = s.user_id
WHERE s.is_active = TRUE;
