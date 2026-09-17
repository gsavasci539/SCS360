-- Create canteen_wallet_transactions table
CREATE TABLE IF NOT EXISTS canteen_wallet_transactions (
    id TEXT PRIMARY KEY,
    student_id TEXT NOT NULL,
    amount REAL NOT NULL,
    transaction_type TEXT NOT NULL,
    payment_method TEXT,
    reference_number TEXT,
    processed_by TEXT,
    status TEXT DEFAULT 'COMPLETED',
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id),
    FOREIGN KEY (processed_by) REFERENCES users(id)
);
