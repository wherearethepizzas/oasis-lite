-- Oasis Lite music and promotion schema.
-- MySQL 8 compatible; designed for normalized music metadata, listening history,
-- synthetic promotion campaigns, and runtime recommendation logs.

CREATE TABLE IF NOT EXISTS artists (
    artist_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    artist_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_artists_artist_name (artist_name),
    KEY idx_artists_artist_name (artist_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS tracks (
    track_id VARCHAR(128) PRIMARY KEY,
    spotify_id VARCHAR(128) NULL,
    track_name VARCHAR(512) NOT NULL,
    spotify_preview_url TEXT NULL,
    genre VARCHAR(128) NULL,
    release_year SMALLINT NULL,
    duration_ms INT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_tracks_spotify_id (spotify_id),
    KEY idx_tracks_genre (genre),
    KEY idx_tracks_release_year (release_year),
    CONSTRAINT chk_tracks_duration_ms_nonnegative CHECK (duration_ms IS NULL OR duration_ms >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Many-to-many even though the current dataset has one artist string per row.
CREATE TABLE IF NOT EXISTS track_artists (
    track_id VARCHAR(128) NOT NULL,
    artist_id BIGINT NOT NULL,
    PRIMARY KEY (track_id, artist_id),
    KEY idx_track_artists_artist_id (artist_id),
    CONSTRAINT fk_track_artists_track
        FOREIGN KEY (track_id) REFERENCES tracks(track_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_track_artists_artist
        FOREIGN KEY (artist_id) REFERENCES artists(artist_id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS track_audio_features (
    track_id VARCHAR(128) PRIMARY KEY,
    danceability DECIMAL(5,4) NULL,
    energy DECIMAL(5,4) NULL,
    musical_key TINYINT NULL,
    loudness DECIMAL(7,3) NULL,
    musical_mode TINYINT NULL,
    speechiness DECIMAL(5,4) NULL,
    acousticness DECIMAL(5,4) NULL,
    instrumentalness DECIMAL(5,4) NULL,
    liveness DECIMAL(5,4) NULL,
    valence DECIMAL(5,4) NULL,
    tempo DECIMAL(8,3) NULL,
    time_signature TINYINT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_track_audio_features_track
        FOREIGN KEY (track_id) REFERENCES tracks(track_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT chk_track_audio_features_danceability CHECK (danceability IS NULL OR (danceability >= 0 AND danceability <= 1)),
    CONSTRAINT chk_track_audio_features_energy CHECK (energy IS NULL OR (energy >= 0 AND energy <= 1)),
    CONSTRAINT chk_track_audio_features_speechiness CHECK (speechiness IS NULL OR (speechiness >= 0 AND speechiness <= 1)),
    CONSTRAINT chk_track_audio_features_acousticness CHECK (acousticness IS NULL OR (acousticness >= 0 AND acousticness <= 1)),
    CONSTRAINT chk_track_audio_features_instrumentalness CHECK (instrumentalness IS NULL OR (instrumentalness >= 0 AND instrumentalness <= 1)),
    CONSTRAINT chk_track_audio_features_liveness CHECK (liveness IS NULL OR (liveness >= 0 AND liveness <= 1)),
    CONSTRAINT chk_track_audio_features_valence CHECK (valence IS NULL OR (valence >= 0 AND valence <= 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS tags (
    tag_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    tag_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_tags_tag_name (tag_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS track_tags (
    track_id VARCHAR(128) NOT NULL,
    tag_id BIGINT NOT NULL,
    PRIMARY KEY (track_id, tag_id),
    KEY idx_track_tags_tag_id (tag_id),
    CONSTRAINT fk_track_tags_track
        FOREIGN KEY (track_id) REFERENCES tracks(track_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_track_tags_tag
        FOREIGN KEY (tag_id) REFERENCES tags(tag_id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS users (
    user_id VARCHAR(128) PRIMARY KEY,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS user_track_plays (
    user_id VARCHAR(128) NOT NULL,
    track_id VARCHAR(128) NOT NULL,
    play_count INT NOT NULL DEFAULT 0,
    last_updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, track_id),
    KEY idx_user_track_plays_user_id (user_id),
    KEY idx_user_track_plays_track_id (track_id),
    CONSTRAINT fk_user_track_plays_user
        FOREIGN KEY (user_id) REFERENCES users(user_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_user_track_plays_track
        FOREIGN KEY (track_id) REFERENCES tracks(track_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT chk_user_track_plays_play_count_nonnegative CHECK (play_count >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Per-user audio taste vector derived from listening history. Each value is a
-- play-count-weighted average over the user's listened tracks.
CREATE TABLE IF NOT EXISTS user_taste_profiles (
    user_id VARCHAR(128) PRIMARY KEY,
    danceability DECIMAL(5,4) NULL,
    energy DECIMAL(5,4) NULL,
    acousticness DECIMAL(5,4) NULL,
    instrumentalness DECIMAL(5,4) NULL,
    valence DECIMAL(5,4) NULL,
    tempo DECIMAL(8,3) NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_user_taste_profiles_user
        FOREIGN KEY (user_id) REFERENCES users(user_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT chk_user_taste_profiles_danceability CHECK (danceability IS NULL OR (danceability >= 0 AND danceability <= 1)),
    CONSTRAINT chk_user_taste_profiles_energy CHECK (energy IS NULL OR (energy >= 0 AND energy <= 1)),
    CONSTRAINT chk_user_taste_profiles_acousticness CHECK (acousticness IS NULL OR (acousticness >= 0 AND acousticness <= 1)),
    CONSTRAINT chk_user_taste_profiles_instrumentalness CHECK (instrumentalness IS NULL OR (instrumentalness >= 0 AND instrumentalness <= 1)),
    CONSTRAINT chk_user_taste_profiles_valence CHECK (valence IS NULL OR (valence >= 0 AND valence <= 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Synthetic promotion supply. Impressions and events are runtime logs and are
-- intentionally stored separately.
CREATE TABLE IF NOT EXISTS promotion_campaigns (
    campaign_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    track_id VARCHAR(128) NOT NULL,
    artist_id BIGINT NOT NULL,
    objective ENUM('streams', 'saves', 'follows', 'discovery') NOT NULL,
    bid_weight DECIMAL(6,4) NOT NULL DEFAULT 0.0000,
    daily_budget DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    remaining_budget DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    budget_date DATE NULL,
    target_genre VARCHAR(128) NULL,
    max_impressions_per_user_per_day INT NOT NULL DEFAULT 3,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status ENUM('draft', 'active', 'paused', 'completed') NOT NULL DEFAULT 'draft',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_campaign_track_artist_objective_dates (track_id, artist_id, objective, start_date, end_date),
    KEY idx_promotion_campaigns_status (status),
    KEY idx_promotion_campaigns_track_id (track_id),
    KEY idx_promotion_campaigns_artist_id (artist_id),
    CONSTRAINT fk_promotion_campaigns_track
        FOREIGN KEY (track_id) REFERENCES tracks(track_id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_promotion_campaigns_artist
        FOREIGN KEY (artist_id) REFERENCES artists(artist_id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_promotion_campaigns_bid_weight_nonnegative CHECK (bid_weight >= 0),
    CONSTRAINT chk_promotion_campaigns_daily_budget_nonnegative CHECK (daily_budget >= 0),
    CONSTRAINT chk_promotion_campaigns_remaining_budget_nonnegative CHECK (remaining_budget >= 0),
    CONSTRAINT chk_promotion_campaigns_impression_cap_positive CHECK (max_impressions_per_user_per_day > 0),
    CONSTRAINT chk_promotion_campaigns_dates CHECK (end_date >= start_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS promotion_impressions (
    impression_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    campaign_id BIGINT NOT NULL,
    user_id VARCHAR(128) NOT NULL,
    track_id VARCHAR(128) NOT NULL,
    rank_position INT NOT NULL,
    relevance_score DECIMAL(8,6) NULL,
    campaign_score DECIMAL(8,6) NULL,
    diversity_bonus DECIMAL(8,6) NULL,
    fatigue_penalty DECIMAL(8,6) NULL,
    final_score DECIMAL(8,6) NULL,
    served_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_promotion_impressions_user_id (user_id),
    KEY idx_promotion_impressions_campaign_id (campaign_id),
    KEY idx_promotion_impressions_track_id (track_id),
    CONSTRAINT fk_promotion_impressions_campaign
        FOREIGN KEY (campaign_id) REFERENCES promotion_campaigns(campaign_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_promotion_impressions_user
        FOREIGN KEY (user_id) REFERENCES users(user_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_promotion_impressions_track
        FOREIGN KEY (track_id) REFERENCES tracks(track_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT chk_promotion_impressions_rank_positive CHECK (rank_position > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS promotion_events (
    event_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    impression_id BIGINT NOT NULL,
    event_type ENUM('click', 'stream', 'skip', 'save') NOT NULL,
    event_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_promotion_events_impression_id (impression_id),
    CONSTRAINT fk_promotion_events_impression
        FOREIGN KEY (impression_id) REFERENCES promotion_impressions(impression_id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- If promotion_campaigns already exists without the seeding idempotency key,
-- add it with:
-- ALTER TABLE promotion_campaigns
--   ADD UNIQUE KEY uq_campaign_track_artist_objective_dates
--   (track_id, artist_id, objective, start_date, end_date);
