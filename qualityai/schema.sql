PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS recipes (
    id                  TEXT PRIMARY KEY,
    name                TEXT NOT NULL,
    part_type           TEXT NOT NULL,
    description         TEXT NOT NULL DEFAULT '',
    root_path           TEXT NOT NULL UNIQUE,
    preprocessing_json  TEXT NOT NULL DEFAULT '{}',
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS app_settings (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dataset_versions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_id       TEXT NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    version_number  INTEGER NOT NULL,
    status          TEXT NOT NULL CHECK (status IN ('active', 'archived')),
    created_at      TEXT NOT NULL,
    closed_at       TEXT,
    UNIQUE (recipe_id, version_number)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_dataset_active_recipe
ON dataset_versions(recipe_id) WHERE status = 'active';

CREATE TABLE IF NOT EXISTS image_samples (
    id                  TEXT PRIMARY KEY,
    recipe_id           TEXT NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    dataset_version_id  INTEGER NOT NULL REFERENCES dataset_versions(id),
    label               TEXT NOT NULL CHECK (label IN ('ok', 'nok')),
    file_path           TEXT NOT NULL UNIQUE,
    source              TEXT NOT NULL CHECK (source IN ('camera', 'import', 'human_review', 'migration')),
    width               INTEGER,
    height              INTEGER,
    sha256              TEXT,
    captured_at         TEXT NOT NULL,
    deleted_at          TEXT
);

CREATE INDEX IF NOT EXISTS idx_images_recipe_label
ON image_samples(recipe_id, label, deleted_at);

CREATE TABLE IF NOT EXISTS training_runs (
    id                  TEXT PRIMARY KEY,
    recipe_id           TEXT NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    dataset_version_id  INTEGER NOT NULL REFERENCES dataset_versions(id),
    status              TEXT NOT NULL CHECK (status IN ('completed', 'failed', 'cancelled')),
    total_images        INTEGER NOT NULL,
    folds               INTEGER,
    metrics_json        TEXT NOT NULL DEFAULT '{}',
    started_at          TEXT,
    finished_at         TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS model_versions (
    id                  TEXT PRIMARY KEY,
    recipe_id           TEXT NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    dataset_version_id  INTEGER NOT NULL REFERENCES dataset_versions(id),
    training_run_id     TEXT REFERENCES training_runs(id),
    file_path           TEXT NOT NULL,
    model_type          TEXT NOT NULL,
    confidence_threshold REAL NOT NULL,
    metrics_json        TEXT NOT NULL DEFAULT '{}',
    active              INTEGER NOT NULL DEFAULT 0 CHECK (active IN (0, 1)),
    created_at          TEXT NOT NULL,
    archived_at         TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_model_active_recipe
ON model_versions(recipe_id) WHERE active = 1;

CREATE TABLE IF NOT EXISTS inspections (
    id               TEXT PRIMARY KEY,
    recipe_id        TEXT NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    model_id         TEXT REFERENCES model_versions(id),
    file_path        TEXT NOT NULL,
    predicted_label  TEXT NOT NULL CHECK (predicted_label IN ('ok', 'nok')),
    confidence       REAL NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    requires_review  INTEGER NOT NULL CHECK (requires_review IN (0, 1)),
    created_at       TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_inspections_recipe_created
ON inspections(recipe_id, created_at);

CREATE TABLE IF NOT EXISTS human_reviews (
    id                TEXT PRIMARY KEY,
    inspection_id     TEXT NOT NULL REFERENCES inspections(id) ON DELETE CASCADE,
    human_label       TEXT NOT NULL CHECK (human_label IN ('ok', 'nok')),
    corrected         INTEGER NOT NULL CHECK (corrected IN (0, 1)),
    dataset_image_id  TEXT REFERENCES image_samples(id),
    reviewed_at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_events (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_id     TEXT REFERENCES recipes(id) ON DELETE SET NULL,
    event_type    TEXT NOT NULL,
    details_json  TEXT NOT NULL DEFAULT '{}',
    created_at    TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_recipe_created
ON audit_events(recipe_id, created_at);

PRAGMA user_version = 1;
