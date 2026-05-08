CREATE TABLE IF NOT EXISTS users (
    id         BIGINT PRIMARY KEY,
    username   TEXT,
    first_name TEXT,
    language   VARCHAR(2) NOT NULL DEFAULT 'uk',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS activity_types (
    id             SERIAL PRIMARY KEY,
    slug           VARCHAR(50) UNIQUE NOT NULL,
    name_uk        TEXT NOT NULL,
    name_ru        TEXT NOT NULL,
    description_uk TEXT,
    description_ru TEXT,
    is_active      BOOLEAN NOT NULL DEFAULT TRUE,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id               SERIAL PRIMARY KEY,
    user_id          BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    activity_type_id INTEGER NOT NULL REFERENCES activity_types(id),
    reminder_time    TIME NOT NULL,
    timezone         VARCHAR(50) NOT NULL DEFAULT 'Europe/Kyiv',
    is_active        BOOLEAN NOT NULL DEFAULT TRUE,
    subscribed_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, activity_type_id)
);

CREATE TABLE IF NOT EXISTS sessions (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    activity_type_id INTEGER NOT NULL REFERENCES activity_types(id),
    session_date     DATE NOT NULL,
    started_at       TIMESTAMPTZ,
    completed_at     TIMESTAMPTZ,
    is_complete      BOOLEAN NOT NULL DEFAULT FALSE,
    responses        JSONB,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, activity_type_id, session_date)
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_date ON sessions(user_id, session_date DESC);
CREATE INDEX IF NOT EXISTS idx_subscriptions_active ON subscriptions(is_active, user_id);

INSERT INTO activity_types (slug, name_uk, name_ru, description_uk, description_ru)
VALUES (
    'thinking_pattern',
    'Паттерн мислення',
    'Паттерн мышления',
    'Щоденний аналіз важливої події: роздратування → збудження → відчуття → почуття → емоція → враження → смисл → ідея',
    'Ежедневный анализ важного события: раздражение → возбуждение → ощущение → чувство → эмоция → впечатление → смысл → идея'
) ON CONFLICT (slug) DO NOTHING;
