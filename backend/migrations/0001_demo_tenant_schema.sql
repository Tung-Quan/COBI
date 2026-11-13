CREATE TABLE IF NOT EXISTS applications (
    owner_user_id TEXT NOT NULL,
    application_id TEXT NOT NULL,
    data_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (owner_user_id, application_id)
);

CREATE TABLE IF NOT EXISTS audit_events (
    event_id BIGSERIAL PRIMARY KEY,
    owner_user_id TEXT NOT NULL,
    application_id TEXT NOT NULL,
    action TEXT NOT NULL,
    route TEXT,
    reason TEXT NOT NULL,
    actor TEXT NOT NULL DEFAULT 'Simulated credit officer',
    created_at TEXT NOT NULL,
    details_json TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY (owner_user_id, application_id)
        REFERENCES applications(owner_user_id, application_id)
);

CREATE TABLE IF NOT EXISTS calculation_results (
    owner_user_id TEXT NOT NULL,
    application_id TEXT NOT NULL,
    assessment_json TEXT NOT NULL,
    routing_json TEXT NOT NULL,
    computed_at TEXT NOT NULL,
    PRIMARY KEY (owner_user_id, application_id),
    FOREIGN KEY (owner_user_id, application_id)
        REFERENCES applications(owner_user_id, application_id)
);

CREATE INDEX IF NOT EXISTS audit_owner_application_action
    ON audit_events(owner_user_id, application_id, action);

CREATE OR REPLACE RULE audit_events_no_update AS
    ON UPDATE TO audit_events DO INSTEAD NOTHING;

CREATE OR REPLACE RULE audit_events_no_delete AS
    ON DELETE TO audit_events DO INSTEAD NOTHING;
