CREATE TABLE IF NOT EXISTS sku_master (
    id BIGSERIAL PRIMARY KEY,
    sku TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL,
    pins_per_kettle DOUBLE PRECISION NOT NULL
        CHECK (pins_per_kettle > 0),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS planned_usage (
    id BIGSERIAL PRIMARY KEY,
    production_date DATE NOT NULL,
    sku TEXT NOT NULL,
    kettles_planned DOUBLE PRECISION NOT NULL DEFAULT 0
        CHECK (kettles_planned >= 0),
    expected_pins DOUBLE PRECISION NOT NULL DEFAULT 0
        CHECK (expected_pins >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (production_date, sku),
    FOREIGN KEY (sku)
        REFERENCES sku_master(sku)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS actual_usage (
    id BIGSERIAL PRIMARY KEY,
    production_date DATE NOT NULL,
    sku TEXT NOT NULL,
    actual_pins DOUBLE PRECISION NOT NULL DEFAULT 0
        CHECK (actual_pins >= 0),
    yield_percent DOUBLE PRECISION NOT NULL DEFAULT 100
        CHECK (yield_percent >= 0 AND yield_percent <= 100),
    notes TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (production_date, sku),
    FOREIGN KEY (sku)
        REFERENCES sku_master(sku)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_planned_date
ON planned_usage(production_date);

CREATE INDEX IF NOT EXISTS idx_actual_date
ON actual_usage(production_date);
