from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    Date,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    PrimaryKeyConstraint,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.mysql import TIMESTAMP, TINYINT
from sqlalchemy.orm import declarative_base, relationship


Base = declarative_base()


class Artist(Base):
    __tablename__ = "artists"

    artist_id = Column(BigInteger, primary_key=True, autoincrement=True)
    artist_name = Column(String(255), nullable=False, unique=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(
        TIMESTAMP,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        server_onupdate=text("CURRENT_TIMESTAMP"),
    )

    track_links = relationship("TrackArtist", back_populates="artist", cascade="all, delete-orphan")
    campaigns = relationship("PromotionCampaign", back_populates="artist")

    __table_args__ = (Index("idx_artists_artist_name", "artist_name"),)


class Track(Base):
    __tablename__ = "tracks"

    track_id = Column(String(128), primary_key=True)
    spotify_id = Column(String(128), nullable=True)
    track_name = Column(String(512), nullable=False)
    spotify_preview_url = Column(Text, nullable=True)
    genre = Column(String(128), nullable=True)
    release_year = Column(SmallInteger, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(
        TIMESTAMP,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        server_onupdate=text("CURRENT_TIMESTAMP"),
    )

    audio_features = relationship(
        "TrackAudioFeature",
        back_populates="track",
        cascade="all, delete-orphan",
        uselist=False,
    )
    artist_links = relationship("TrackArtist", back_populates="track", cascade="all, delete-orphan")
    tag_links = relationship("TrackTag", back_populates="track", cascade="all, delete-orphan")
    user_plays = relationship("UserTrackPlay", back_populates="track", cascade="all, delete-orphan")
    campaigns = relationship("PromotionCampaign", back_populates="track")
    impressions = relationship("PromotionImpression", back_populates="track")

    __table_args__ = (
        Index("idx_tracks_spotify_id", "spotify_id"),
        Index("idx_tracks_genre", "genre"),
        Index("idx_tracks_release_year", "release_year"),
        CheckConstraint(
            "duration_ms IS NULL OR duration_ms >= 0",
            name="chk_tracks_duration_ms_nonnegative",
        ),
    )


class TrackArtist(Base):
    __tablename__ = "track_artists"

    track_id = Column(
        String(128),
        ForeignKey("tracks.track_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    artist_id = Column(
        BigInteger,
        ForeignKey("artists.artist_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )

    track = relationship("Track", back_populates="artist_links")
    artist = relationship("Artist", back_populates="track_links")

    __table_args__ = (
        PrimaryKeyConstraint("track_id", "artist_id"),
        Index("idx_track_artists_artist_id", "artist_id"),
    )


class TrackAudioFeature(Base):
    __tablename__ = "track_audio_features"

    track_id = Column(
        String(128),
        ForeignKey("tracks.track_id", ondelete="CASCADE", onupdate="CASCADE"),
        primary_key=True,
    )
    danceability = Column(Numeric(5, 4), nullable=True)
    energy = Column(Numeric(5, 4), nullable=True)
    musical_key = Column(TINYINT, nullable=True)
    loudness = Column(Numeric(7, 3), nullable=True)
    musical_mode = Column(TINYINT, nullable=True)
    speechiness = Column(Numeric(5, 4), nullable=True)
    acousticness = Column(Numeric(5, 4), nullable=True)
    instrumentalness = Column(Numeric(5, 4), nullable=True)
    liveness = Column(Numeric(5, 4), nullable=True)
    valence = Column(Numeric(5, 4), nullable=True)
    tempo = Column(Numeric(8, 3), nullable=True)
    time_signature = Column(TINYINT, nullable=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(
        TIMESTAMP,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        server_onupdate=text("CURRENT_TIMESTAMP"),
    )

    track = relationship("Track", back_populates="audio_features")

    __table_args__ = (
        CheckConstraint(
            "danceability IS NULL OR (danceability >= 0 AND danceability <= 1)",
            name="chk_track_audio_features_danceability",
        ),
        CheckConstraint(
            "energy IS NULL OR (energy >= 0 AND energy <= 1)",
            name="chk_track_audio_features_energy",
        ),
        CheckConstraint(
            "speechiness IS NULL OR (speechiness >= 0 AND speechiness <= 1)",
            name="chk_track_audio_features_speechiness",
        ),
        CheckConstraint(
            "acousticness IS NULL OR (acousticness >= 0 AND acousticness <= 1)",
            name="chk_track_audio_features_acousticness",
        ),
        CheckConstraint(
            "instrumentalness IS NULL OR (instrumentalness >= 0 AND instrumentalness <= 1)",
            name="chk_track_audio_features_instrumentalness",
        ),
        CheckConstraint(
            "liveness IS NULL OR (liveness >= 0 AND liveness <= 1)",
            name="chk_track_audio_features_liveness",
        ),
        CheckConstraint(
            "valence IS NULL OR (valence >= 0 AND valence <= 1)",
            name="chk_track_audio_features_valence",
        ),
    )


class Tag(Base):
    __tablename__ = "tags"

    tag_id = Column(BigInteger, primary_key=True, autoincrement=True)
    tag_name = Column(String(255), nullable=False, unique=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(
        TIMESTAMP,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        server_onupdate=text("CURRENT_TIMESTAMP"),
    )

    track_links = relationship("TrackTag", back_populates="tag", cascade="all, delete-orphan")


class TrackTag(Base):
    __tablename__ = "track_tags"

    track_id = Column(
        String(128),
        ForeignKey("tracks.track_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    tag_id = Column(
        BigInteger,
        ForeignKey("tags.tag_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )

    track = relationship("Track", back_populates="tag_links")
    tag = relationship("Tag", back_populates="track_links")

    __table_args__ = (
        PrimaryKeyConstraint("track_id", "tag_id"),
        Index("idx_track_tags_tag_id", "tag_id"),
    )


class User(Base):
    __tablename__ = "users"

    user_id = Column(String(128), primary_key=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(
        TIMESTAMP,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        server_onupdate=text("CURRENT_TIMESTAMP"),
    )

    track_plays = relationship("UserTrackPlay", back_populates="user", cascade="all, delete-orphan")
    taste_profile = relationship(
        "UserTasteProfile",
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )
    impressions = relationship("PromotionImpression", back_populates="user", cascade="all, delete-orphan")


class UserTrackPlay(Base):
    __tablename__ = "user_track_plays"

    user_id = Column(
        String(128),
        ForeignKey("users.user_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    track_id = Column(
        String(128),
        ForeignKey("tracks.track_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    play_count = Column(Integer, nullable=False, server_default=text("0"))
    last_updated_at = Column(
        TIMESTAMP,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        server_onupdate=text("CURRENT_TIMESTAMP"),
    )

    user = relationship("User", back_populates="track_plays")
    track = relationship("Track", back_populates="user_plays")

    __table_args__ = (
        PrimaryKeyConstraint("user_id", "track_id"),
        Index("idx_user_track_plays_user_id", "user_id"),
        Index("idx_user_track_plays_track_id", "track_id"),
        CheckConstraint("play_count >= 0", name="chk_user_track_plays_play_count_nonnegative"),
    )


class UserTasteProfile(Base):
    __tablename__ = "user_taste_profiles"

    user_id = Column(
        String(128),
        ForeignKey("users.user_id", ondelete="CASCADE", onupdate="CASCADE"),
        primary_key=True,
    )
    danceability = Column(Numeric(5, 4), nullable=True)
    energy = Column(Numeric(5, 4), nullable=True)
    acousticness = Column(Numeric(5, 4), nullable=True)
    instrumentalness = Column(Numeric(5, 4), nullable=True)
    valence = Column(Numeric(5, 4), nullable=True)
    tempo = Column(Numeric(8, 3), nullable=True)
    updated_at = Column(
        TIMESTAMP,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        server_onupdate=text("CURRENT_TIMESTAMP"),
    )

    user = relationship("User", back_populates="taste_profile")

    __table_args__ = (
        CheckConstraint(
            "danceability IS NULL OR (danceability >= 0 AND danceability <= 1)",
            name="chk_user_taste_profiles_danceability",
        ),
        CheckConstraint(
            "energy IS NULL OR (energy >= 0 AND energy <= 1)",
            name="chk_user_taste_profiles_energy",
        ),
        CheckConstraint(
            "acousticness IS NULL OR (acousticness >= 0 AND acousticness <= 1)",
            name="chk_user_taste_profiles_acousticness",
        ),
        CheckConstraint(
            "instrumentalness IS NULL OR (instrumentalness >= 0 AND instrumentalness <= 1)",
            name="chk_user_taste_profiles_instrumentalness",
        ),
        CheckConstraint(
            "valence IS NULL OR (valence >= 0 AND valence <= 1)",
            name="chk_user_taste_profiles_valence",
        ),
    )


class PromotionCampaign(Base):
    __tablename__ = "promotion_campaigns"

    campaign_id = Column(BigInteger, primary_key=True, autoincrement=True)
    track_id = Column(
        String(128),
        ForeignKey("tracks.track_id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
    )
    artist_id = Column(
        BigInteger,
        ForeignKey("artists.artist_id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
    )
    objective = Column(Enum("streams", "saves", "follows", "discovery"), nullable=False)
    bid_weight = Column(Numeric(6, 4), nullable=False, server_default=text("0.0000"))
    daily_budget = Column(Numeric(10, 2), nullable=False, server_default=text("0.00"))
    remaining_budget = Column(Numeric(10, 2), nullable=False, server_default=text("0.00"))
    target_genre = Column(String(128), nullable=True)
    max_impressions_per_user_per_day = Column(Integer, nullable=False, server_default=text("3"))
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(Enum("draft", "active", "paused", "completed"), nullable=False, server_default=text("'draft'"))
    created_at = Column(TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(
        TIMESTAMP,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        server_onupdate=text("CURRENT_TIMESTAMP"),
    )

    track = relationship("Track", back_populates="campaigns")
    artist = relationship("Artist", back_populates="campaigns")
    impressions = relationship("PromotionImpression", back_populates="campaign", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint(
            "track_id",
            "artist_id",
            "objective",
            "start_date",
            "end_date",
            name="uq_campaign_track_artist_objective_dates",
        ),
        Index("idx_promotion_campaigns_status", "status"),
        Index("idx_promotion_campaigns_track_id", "track_id"),
        Index("idx_promotion_campaigns_artist_id", "artist_id"),
        CheckConstraint("bid_weight >= 0", name="chk_promotion_campaigns_bid_weight_nonnegative"),
        CheckConstraint("daily_budget >= 0", name="chk_promotion_campaigns_daily_budget_nonnegative"),
        CheckConstraint("remaining_budget >= 0", name="chk_promotion_campaigns_remaining_budget_nonnegative"),
        CheckConstraint(
            "max_impressions_per_user_per_day > 0",
            name="chk_promotion_campaigns_impression_cap_positive",
        ),
        CheckConstraint("end_date >= start_date", name="chk_promotion_campaigns_dates"),
    )


class PromotionImpression(Base):
    __tablename__ = "promotion_impressions"

    impression_id = Column(BigInteger, primary_key=True, autoincrement=True)
    campaign_id = Column(
        BigInteger,
        ForeignKey("promotion_campaigns.campaign_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    user_id = Column(
        String(128),
        ForeignKey("users.user_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    track_id = Column(
        String(128),
        ForeignKey("tracks.track_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    rank_position = Column(Integer, nullable=False)
    relevance_score = Column(Numeric(8, 6), nullable=True)
    campaign_score = Column(Numeric(8, 6), nullable=True)
    diversity_bonus = Column(Numeric(8, 6), nullable=True)
    fatigue_penalty = Column(Numeric(8, 6), nullable=True)
    final_score = Column(Numeric(8, 6), nullable=True)
    served_at = Column(TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    campaign = relationship("PromotionCampaign", back_populates="impressions")
    user = relationship("User", back_populates="impressions")
    track = relationship("Track", back_populates="impressions")
    events = relationship("PromotionEvent", back_populates="impression", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_promotion_impressions_user_id", "user_id"),
        Index("idx_promotion_impressions_campaign_id", "campaign_id"),
        Index("idx_promotion_impressions_track_id", "track_id"),
        CheckConstraint("rank_position > 0", name="chk_promotion_impressions_rank_positive"),
    )


class PromotionEvent(Base):
    __tablename__ = "promotion_events"

    event_id = Column(BigInteger, primary_key=True, autoincrement=True)
    impression_id = Column(
        BigInteger,
        ForeignKey("promotion_impressions.impression_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    event_type = Column(Enum("click", "stream", "skip", "save"), nullable=False)
    event_timestamp = Column(TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    impression = relationship("PromotionImpression", back_populates="events")

    __table_args__ = (Index("idx_promotion_events_impression_id", "impression_id"),)
