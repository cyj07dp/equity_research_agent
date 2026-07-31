CREATE TABLE agent_users (
    id UUID PRIMARY KEY,
    display_name VARCHAR(100) NOT NULL,
    auth_provider VARCHAR(50) NOT NULL DEFAULT 'local',
    external_subject VARCHAR(255),
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE UNIQUE INDEX idx_agent_users_provider_subject
ON agent_users(auth_provider, external_subject);

CREATE TABLE agent_user_preferences (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES agent_users(id) ON DELETE CASCADE,
    preferred_locale VARCHAR(32) NOT NULL DEFAULT 'zh-CN',
    default_market VARCHAR(32),
    risk_tolerance VARCHAR(32),
    time_horizon VARCHAR(32),
    report_style VARCHAR(32),
    preferred_sectors TEXT NOT NULL DEFAULT '[]',
    excluded_sectors TEXT NOT NULL DEFAULT '[]',
    preferred_assets TEXT NOT NULL DEFAULT '[]',
    notes TEXT,
    memory_source VARCHAR(32) NOT NULL DEFAULT 'USER_PROVIDED',
    confidence NUMERIC(5,4) NOT NULL DEFAULT 1.0000,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE UNIQUE INDEX idx_agent_user_preferences_user_id
ON agent_user_preferences(user_id);

CREATE INDEX idx_agent_user_preferences_enabled
ON agent_user_preferences(enabled);
