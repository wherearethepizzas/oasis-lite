#!/usr/bin/env python3
"""Load Oasis Lite music metadata and listening history into MySQL."""

from __future__ import annotations

import os
import re
import sys
from collections import Counter
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote_plus

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


MUSIC_INFO_PATH = Path("data/music_info.xlsx")
USER_HISTORY_PATH = Path("data/user_listening_history.xlsx")
AUDIO_FEATURE_COLUMNS = (
    "danceability",
    "energy",
    "speechiness",
    "acousticness",
    "instrumentalness",
    "liveness",
    "valence",
)


def build_database_url() -> str:
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = os.getenv("DB_PORT", "3306")
    user = quote_plus(os.getenv("DB_USER", "root"))
    password = quote_plus(os.getenv("DB_PASSWORD", ""))
    database = os.getenv("DB_NAME", "oasis_lite")
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4"


def get_connection() -> Engine:
    """Return a SQLAlchemy engine for the configured MySQL database."""
    return create_engine(build_database_url(), pool_pre_ping=True, future=True)


def clean_string(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    text_value = str(value).strip()
    if not text_value or text_value.lower() in {"nan", "none", "null", "n/a"}:
        return None
    return text_value


def safe_int(value: Any, *, min_value: int | None = None, max_value: int | None = None) -> int | None:
    if value is None or pd.isna(value):
        return None
    try:
        parsed = int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None
    if min_value is not None and parsed < min_value:
        return None
    if max_value is not None and parsed > max_value:
        return None
    return parsed


def safe_decimal(
    value: Any,
    *,
    places: int = 4,
    min_value: Decimal | None = None,
    max_value: Decimal | None = None,
) -> Decimal | None:
    if value is None or pd.isna(value):
        return None
    try:
        parsed = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None
    if min_value is not None and parsed < min_value:
        return None
    if max_value is not None and parsed > max_value:
        return None
    quantizer = Decimal("1").scaleb(-places)
    return parsed.quantize(quantizer, rounding=ROUND_HALF_UP)


def split_tags(value: Any) -> list[str]:
    """Split comma/pipe/semicolon/slash-delimited tags into unique names."""
    raw_value = clean_string(value)
    if raw_value is None:
        return []
    tags: list[str] = []
    seen: set[str] = set()
    for part in re.split(r"[,;|/]+", raw_value):
        tag = part.strip().strip("\"'")
        key = tag.casefold()
        if tag and key not in seen:
            seen.add(key)
            tags.append(tag)
    return tags


def _execute_many(conn: Any, sql: str, rows: Iterable[dict[str, Any]]) -> int:
    row_list = list(rows)
    if not row_list:
        return 0
    result = conn.execute(text(sql), row_list)
    return int(result.rowcount or 0)


def _fetch_id_map(conn: Any, table_name: str, id_column: str, name_column: str) -> dict[str, int]:
    rows = conn.execute(text(f"SELECT {id_column}, {name_column} FROM {table_name}")).mappings()
    return {row[name_column]: int(row[id_column]) for row in rows}


def refresh_user_taste_profiles(conn: Any) -> int:
    """Refresh play-count-weighted audio feature averages for all users with plays."""
    result = conn.execute(
        text(
            """
            INSERT INTO user_taste_profiles (
                user_id,
                danceability,
                energy,
                acousticness,
                instrumentalness,
                valence,
                tempo
            )
            SELECT
                p.user_id,
                ROUND(
                    SUM(CASE WHEN af.danceability IS NOT NULL THEN af.danceability * p.play_count ELSE 0 END)
                    / NULLIF(SUM(CASE WHEN af.danceability IS NOT NULL THEN p.play_count ELSE 0 END), 0),
                    4
                ) AS danceability,
                ROUND(
                    SUM(CASE WHEN af.energy IS NOT NULL THEN af.energy * p.play_count ELSE 0 END)
                    / NULLIF(SUM(CASE WHEN af.energy IS NOT NULL THEN p.play_count ELSE 0 END), 0),
                    4
                ) AS energy,
                ROUND(
                    SUM(CASE WHEN af.acousticness IS NOT NULL THEN af.acousticness * p.play_count ELSE 0 END)
                    / NULLIF(SUM(CASE WHEN af.acousticness IS NOT NULL THEN p.play_count ELSE 0 END), 0),
                    4
                ) AS acousticness,
                ROUND(
                    SUM(CASE WHEN af.instrumentalness IS NOT NULL THEN af.instrumentalness * p.play_count ELSE 0 END)
                    / NULLIF(SUM(CASE WHEN af.instrumentalness IS NOT NULL THEN p.play_count ELSE 0 END), 0),
                    4
                ) AS instrumentalness,
                ROUND(
                    SUM(CASE WHEN af.valence IS NOT NULL THEN af.valence * p.play_count ELSE 0 END)
                    / NULLIF(SUM(CASE WHEN af.valence IS NOT NULL THEN p.play_count ELSE 0 END), 0),
                    4
                ) AS valence,
                ROUND(
                    SUM(CASE WHEN af.tempo IS NOT NULL THEN af.tempo * p.play_count ELSE 0 END)
                    / NULLIF(SUM(CASE WHEN af.tempo IS NOT NULL THEN p.play_count ELSE 0 END), 0),
                    3
                ) AS tempo
            FROM user_track_plays p
            JOIN track_audio_features af ON af.track_id = p.track_id
            GROUP BY p.user_id
            ON DUPLICATE KEY UPDATE
                danceability = VALUES(danceability),
                energy = VALUES(energy),
                acousticness = VALUES(acousticness),
                instrumentalness = VALUES(instrumentalness),
                valence = VALUES(valence),
                tempo = VALUES(tempo),
                updated_at = CURRENT_TIMESTAMP
            """
        )
    )
    return int(result.rowcount or 0)


def load_music_info(engine: Engine, music_path: Path = MUSIC_INFO_PATH) -> Counter:
    if not music_path.exists():
        raise FileNotFoundError(f"Music metadata file not found: {music_path}")

    df = pd.read_excel(music_path, dtype=object)
    stats: Counter = Counter()
    artists: dict[str, dict[str, str]] = {}
    tracks: dict[str, dict[str, Any]] = {}
    features: dict[str, dict[str, Any]] = {}
    tags: dict[str, dict[str, str]] = {}
    track_artist_names: set[tuple[str, str]] = set()
    track_tag_names: set[tuple[str, str]] = set()

    for _, row in df.iterrows():
        track_id = clean_string(row.get("track_id"))
        track_name = clean_string(row.get("name"))
        if track_id is None or track_name is None:
            stats["music_rows_skipped"] += 1
            continue

        artist_name = clean_string(row.get("artist"))
        if artist_name:
            artists[artist_name] = {"artist_name": artist_name}
            track_artist_names.add((track_id, artist_name))

        tracks[track_id] = {
            "track_id": track_id,
            "spotify_id": clean_string(row.get("spotify_id")),
            "track_name": track_name,
            "spotify_preview_url": clean_string(row.get("spotify_preview_url")),
            "genre": clean_string(row.get("genre")),
            "release_year": safe_int(row.get("year")),
            "duration_ms": safe_int(row.get("duration_ms"), min_value=0),
        }

        features[track_id] = {
            "track_id": track_id,
            "danceability": safe_decimal(row.get("danceability"), min_value=Decimal("0"), max_value=Decimal("1")),
            "energy": safe_decimal(row.get("energy"), min_value=Decimal("0"), max_value=Decimal("1")),
            "musical_key": safe_int(row.get("key")),
            "loudness": safe_decimal(row.get("loudness"), places=3),
            "musical_mode": safe_int(row.get("mode")),
            "speechiness": safe_decimal(row.get("speechiness"), min_value=Decimal("0"), max_value=Decimal("1")),
            "acousticness": safe_decimal(row.get("acousticness"), min_value=Decimal("0"), max_value=Decimal("1")),
            "instrumentalness": safe_decimal(row.get("instrumentalness"), min_value=Decimal("0"), max_value=Decimal("1")),
            "liveness": safe_decimal(row.get("liveness"), min_value=Decimal("0"), max_value=Decimal("1")),
            "valence": safe_decimal(row.get("valence"), min_value=Decimal("0"), max_value=Decimal("1")),
            "tempo": safe_decimal(row.get("tempo"), places=3, min_value=Decimal("0")),
            "time_signature": safe_int(row.get("time_signature")),
        }

        for tag_name in split_tags(row.get("tags")):
            tags[tag_name] = {"tag_name": tag_name}
            track_tag_names.add((track_id, tag_name))

    with engine.begin() as conn:
        stats["artists_affected"] = _execute_many(
            conn,
            """
            INSERT INTO artists (artist_name)
            VALUES (:artist_name)
            ON DUPLICATE KEY UPDATE artist_name = VALUES(artist_name)
            """,
            artists.values(),
        )
        stats["tracks_affected"] = _execute_many(
            conn,
            """
            INSERT INTO tracks (
                track_id, spotify_id, track_name, spotify_preview_url, genre,
                release_year, duration_ms
            )
            VALUES (
                :track_id, :spotify_id, :track_name, :spotify_preview_url, :genre,
                :release_year, :duration_ms
            )
            ON DUPLICATE KEY UPDATE
                spotify_id = VALUES(spotify_id),
                track_name = VALUES(track_name),
                spotify_preview_url = VALUES(spotify_preview_url),
                genre = VALUES(genre),
                release_year = VALUES(release_year),
                duration_ms = VALUES(duration_ms),
                updated_at = CURRENT_TIMESTAMP
            """,
            tracks.values(),
        )

        stats["track_audio_features_affected"] = _execute_many(
            conn,
            """
            INSERT INTO track_audio_features (
                track_id, danceability, energy, musical_key, loudness, musical_mode,
                speechiness, acousticness, instrumentalness, liveness, valence,
                tempo, time_signature
            )
            VALUES (
                :track_id, :danceability, :energy, :musical_key, :loudness, :musical_mode,
                :speechiness, :acousticness, :instrumentalness, :liveness, :valence,
                :tempo, :time_signature
            )
            ON DUPLICATE KEY UPDATE
                danceability = VALUES(danceability),
                energy = VALUES(energy),
                musical_key = VALUES(musical_key),
                loudness = VALUES(loudness),
                musical_mode = VALUES(musical_mode),
                speechiness = VALUES(speechiness),
                acousticness = VALUES(acousticness),
                instrumentalness = VALUES(instrumentalness),
                liveness = VALUES(liveness),
                valence = VALUES(valence),
                tempo = VALUES(tempo),
                time_signature = VALUES(time_signature),
                updated_at = CURRENT_TIMESTAMP
            """,
            features.values(),
        )

        artist_ids = _fetch_id_map(conn, "artists", "artist_id", "artist_name")
        track_artists = [
            {"track_id": track_id, "artist_id": artist_ids[artist_name]}
            for track_id, artist_name in sorted(track_artist_names)
            if artist_name in artist_ids
        ]
        stats["track_artists_affected"] = _execute_many(
            conn,
            """
            INSERT INTO track_artists (track_id, artist_id)
            VALUES (:track_id, :artist_id)
            ON DUPLICATE KEY UPDATE artist_id = VALUES(artist_id)
            """,
            track_artists,
        )

        stats["tags_affected"] = _execute_many(
            conn,
            """
            INSERT INTO tags (tag_name)
            VALUES (:tag_name)
            ON DUPLICATE KEY UPDATE tag_name = VALUES(tag_name)
            """,
            tags.values(),
        )
        tag_ids = _fetch_id_map(conn, "tags", "tag_id", "tag_name")
        track_tags = [
            {"track_id": track_id, "tag_id": tag_ids[tag_name]}
            for track_id, tag_name in sorted(track_tag_names)
            if tag_name in tag_ids
        ]
        stats["track_tags_affected"] = _execute_many(
            conn,
            """
            INSERT INTO track_tags (track_id, tag_id)
            VALUES (:track_id, :tag_id)
            ON DUPLICATE KEY UPDATE tag_id = VALUES(tag_id)
            """,
            track_tags,
        )

    stats["artists_attempted"] = len(artists)
    stats["tracks_attempted"] = len(tracks)
    stats["track_audio_features_attempted"] = len(features)
    stats["track_artists_attempted"] = len(track_artists)
    stats["tags_attempted"] = len(tags)
    stats["track_tags_attempted"] = len(track_tags)
    return stats


def load_user_history(engine: Engine, history_path: Path = USER_HISTORY_PATH) -> Counter:
    if not history_path.exists():
        raise FileNotFoundError(f"Listening history file not found: {history_path}")

    df = pd.read_excel(history_path, dtype=object)
    play_column = "play_count" if "play_count" in df.columns else "playcount"
    if play_column not in df.columns:
        raise ValueError("Listening history must include either 'play_count' or 'playcount'.")

    stats: Counter = Counter()
    users: dict[str, dict[str, str]] = {}
    plays: dict[tuple[str, str], dict[str, Any]] = {}

    with engine.begin() as conn:
        track_ids = {
            row["track_id"]
            for row in conn.execute(text("SELECT track_id FROM tracks")).mappings()
        }

        for _, row in df.iterrows():
            user_id = clean_string(row.get("user_id"))
            track_id = clean_string(row.get("track_id"))
            play_count = safe_int(row.get(play_column), min_value=0)
            if user_id is None or track_id is None:
                stats["history_rows_skipped"] += 1
                continue
            if track_id not in track_ids:
                stats["history_rows_skipped_unmatched_track"] += 1
                continue
            users[user_id] = {"user_id": user_id}
            plays[(user_id, track_id)] = {
                "user_id": user_id,
                "track_id": track_id,
                "play_count": play_count if play_count is not None else 0,
            }

        stats["users_affected"] = _execute_many(
            conn,
            """
            INSERT INTO users (user_id)
            VALUES (:user_id)
            ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP
            """,
            users.values(),
        )
        stats["user_track_plays_affected"] = _execute_many(
            conn,
            """
            INSERT INTO user_track_plays (user_id, track_id, play_count)
            VALUES (:user_id, :track_id, :play_count)
            ON DUPLICATE KEY UPDATE
                play_count = VALUES(play_count),
                last_updated_at = CURRENT_TIMESTAMP
            """,
            plays.values(),
        )
        stats["user_taste_profiles_affected"] = refresh_user_taste_profiles(conn)

    stats["users_attempted"] = len(users)
    stats["user_track_plays_attempted"] = len(plays)
    return stats


def print_stats(title: str, stats: Counter) -> None:
    print(f"\n{title}")
    for key in sorted(stats):
        print(f"  {key}: {stats[key]}")


def main() -> int:
    try:
        engine = get_connection()
        music_stats = load_music_info(engine)
        history_stats = load_user_history(engine)
    except Exception as exc:
        print(f"Load failed: {exc}", file=sys.stderr)
        return 1

    print_stats("Music metadata load summary", music_stats)
    print_stats("Listening history load summary", history_stats)
    if history_stats.get("history_rows_skipped_unmatched_track"):
        print(
            "\nWarning: skipped listening-history rows whose track_id was not present in tracks: "
            f"{history_stats['history_rows_skipped_unmatched_track']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
