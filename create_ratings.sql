CREATE TABLE IF NOT EXISTS dentist_ratings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    dentist_id INTEGER NOT NULL REFERENCES dentists(id) ON DELETE CASCADE,
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, dentist_id) -- Prevent multiple reviews per dentist by same user (optional but good practice)
);
