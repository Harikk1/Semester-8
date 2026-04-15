-- CREATE DATABASE orders_db;
-- \c orders_db;

CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    amount FLOAT NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    paid BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
