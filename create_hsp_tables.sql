-- HSP Service Metrics Table
CREATE TABLE IF NOT EXISTS hsp_service_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    origin TEXT NOT NULL,
    destination TEXT NOT NULL,
    scheduled_departure TEXT,
    scheduled_arrival TEXT,
    toc_code TEXT NOT NULL,
    matched_services_count INTEGER,
    fetch_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(origin, destination, scheduled_departure, scheduled_arrival, toc_code)
);

-- HSP Service Details Table
CREATE TABLE IF NOT EXISTS hsp_service_details (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rid TEXT NOT NULL,
    date_of_service TEXT NOT NULL,
    toc_code TEXT NOT NULL,
    location TEXT NOT NULL,
    scheduled_departure TIMESTAMP,
    scheduled_arrival TIMESTAMP,
    actual_departure TIMESTAMP,
    actual_arrival TIMESTAMP,
    departure_delay_minutes INTEGER,
    arrival_delay_minutes INTEGER,
    cancellation_reason TEXT,
    fetch_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(rid, location)
);

-- Indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_hsp_metrics_route ON hsp_service_metrics(origin, destination);
CREATE INDEX IF NOT EXISTS idx_hsp_metrics_toc ON hsp_service_metrics(toc_code);
CREATE INDEX IF NOT EXISTS idx_hsp_details_rid ON hsp_service_details(rid);
CREATE INDEX IF NOT EXISTS idx_hsp_details_date ON hsp_service_details(date_of_service);
CREATE INDEX IF NOT EXISTS idx_hsp_details_location ON hsp_service_details(location);
CREATE INDEX IF NOT EXISTS idx_hsp_details_delay ON hsp_service_details(arrival_delay_minutes);
