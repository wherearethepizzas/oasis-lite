#!/usr/bin/env python3
"""Seed synthetic Oasis Lite promotion campaigns from real tracks/artists."""

from __future__ import annotations

import argparse
import os
import random
import sys
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Sequence
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


MIN_TRACKS_PER_CAMPAIGN = 3
MAX_TRACKS_PER_CAMPAIGN = 15
OBJECTIVE_WEIGHTS = {
    "streams": 0.45,
    "saves": 0.25,
    "discovery": 0.20,
    "follows": 0.10,
}
OBJECTIVE_BID_RANGES = {
    "streams": (Decimal("0.3000"), Decimal("1.0000")),
    "saves": (Decimal("0.2000"), Decimal("0.8500")),
    "discovery": (Decimal("0.1000"), Decimal("0.7000")),
    "follows": (Decimal("0.0500"), Decimal("0.6000")),
}


def build_database_url() -> str:
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = os.getenv("DB_PORT", "3306")
    user = quote_plus(os.getenv("DB_USER", "root"))
    password = quote_plus(os.getenv("DB_PASSWORD", ""))
    database = os.getenv("DB_NAME", "oasis_lite")
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4"


def get_engine() -> Engine:
    return create_engine(build_database_url(), pool_pre_ping=True, future=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed synthetic promotion campaign groups.")
    parser.add_argument(
        "--num-campaigns",
        type=int,
        default=500,
        help="Number of campaign groups to generate. Each group seeds 3 to 15 promoted tracks.",
    )
    parser.add_argument("--active-ratio", type=float, default=0.75)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if args.num_campaigns <= 0:
        parser.error("--num-campaigns must be a positive integer.")
    if not 0 <= args.active_ratio <= 1:
        parser.error("--active-ratio must be between 0 and 1.")
    return args


def fetch_eligible_track_artist_pairs(engine: Engine) -> list[dict[str, Any]]:
    """Return one artist per track, preferring tracks with richer metadata."""
    sql = """
        SELECT
            t.track_id,
            t.track_name,
            t.genre,
            t.duration_ms,
            first_artist.artist_id,
            a.artist_name
        FROM tracks t
        JOIN (
            SELECT track_id, MIN(artist_id) AS artist_id
            FROM track_artists
            GROUP BY track_id
        ) first_artist ON first_artist.track_id = t.track_id
        JOIN artists a ON a.artist_id = first_artist.artist_id
        ORDER BY
            CASE
                WHEN t.genre IS NOT NULL
                 AND t.duration_ms IS NOT NULL
                 AND t.track_name IS NOT NULL THEN 0
                ELSE 1
            END,
            t.track_id
    """
    with engine.connect() as conn:
        return [dict(row) for row in conn.execute(text(sql)).mappings()]


def fetch_existing_active_track_objectives(engine: Engine) -> set[tuple[str, str]]:
    sql = """
        SELECT track_id, objective
        FROM promotion_campaigns
        WHERE status = 'active'
    """
    with engine.connect() as conn:
        return {
            (str(row["track_id"]), str(row["objective"]))
            for row in conn.execute(text(sql)).mappings()
        }


def weighted_choice(weights: dict[str, float], rng: random.Random) -> str:
    total = sum(weights.values())
    threshold = rng.uniform(0, total)
    running = 0.0
    for value, weight in weights.items():
        running += weight
        if threshold <= running:
            return value
    return next(reversed(weights))


def _random_decimal(rng: random.Random, low: Decimal, high: Decimal, places: int) -> Decimal:
    span = high - low
    value = low + (span * Decimal(str(rng.random())))
    quantizer = Decimal("1").scaleb(-places)
    return value.quantize(quantizer, rounding=ROUND_HALF_UP)


def _choose_status(active_ratio: float, rng: random.Random) -> str:
    inactive_ratio = 1.0 - active_ratio
    return weighted_choice(
        {
            "active": active_ratio,
            "draft": inactive_ratio * 0.40,
            "paused": inactive_ratio * 0.40,
            "completed": inactive_ratio * 0.20,
        },
        rng,
    )


def _pair_weight(pair: dict[str, Any]) -> float:
    has_useful_metadata = bool(pair.get("genre") and pair.get("duration_ms") and pair.get("track_name"))
    return 3.0 if has_useful_metadata else 1.0


def group_pairs_by_artist(eligible_pairs: Sequence[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    pairs_by_artist: dict[Any, dict[str, dict[str, Any]]] = {}
    for pair in eligible_pairs:
        artist_tracks = pairs_by_artist.setdefault(pair["artist_id"], {})
        artist_tracks.setdefault(str(pair["track_id"]), pair)
    return [
        list(artist_tracks.values())
        for artist_tracks in pairs_by_artist.values()
        if len(artist_tracks) >= MIN_TRACKS_PER_CAMPAIGN
    ]


def _date_range_for_status(status: str, rng: random.Random, today: date) -> tuple[date, date]:
    if status == "active":
        start_date = today - timedelta(days=rng.randint(0, 30))
        end_date = today + timedelta(days=rng.randint(1, 60))
    elif status == "draft":
        start_date = today + timedelta(days=rng.randint(1, 30))
        end_date = start_date + timedelta(days=rng.randint(7, 90))
    elif status == "paused":
        start_date = today - timedelta(days=rng.randint(1, 60))
        end_date = today + timedelta(days=rng.randint(1, 45))
    else:
        start_date = today - timedelta(days=rng.randint(30, 120))
        end_date = today - timedelta(days=rng.randint(1, 29))
        if end_date < start_date:
            start_date, end_date = end_date - timedelta(days=rng.randint(7, 60)), end_date
    return start_date, end_date


def generate_campaign(
    pair: dict[str, Any],
    *,
    active_ratio: float,
    rng: random.Random,
    today: date | None = None,
    objective: str | None = None,
    status: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, Any]:
    """Generate one synthetic campaign using simple, explainable simulation choices."""
    current_date = today or date.today()
    objective = objective or weighted_choice(OBJECTIVE_WEIGHTS, rng)
    status = status or _choose_status(active_ratio, rng)
    if start_date is None or end_date is None:
        start_date, end_date = _date_range_for_status(status, rng, current_date)

    bid_low, bid_high = OBJECTIVE_BID_RANGES[objective]
    bid_weight = _random_decimal(rng, bid_low, bid_high, 4)

    # Squaring a uniform random value makes small daily budgets more common.
    daily_budget_float = 10.0 + ((rng.random() ** 2) * 490.0)
    daily_budget = Decimal(str(daily_budget_float)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    if status == "active":
        remaining_budget = daily_budget * _random_decimal(rng, Decimal("0.20"), Decimal("1.00"), 4)
    elif status == "paused":
        remaining_budget = daily_budget * _random_decimal(rng, Decimal("0.00"), Decimal("1.00"), 4)
    elif status == "completed":
        remaining_budget = Decimal("0.00")
    else:
        remaining_budget = daily_budget
    remaining_budget = remaining_budget.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    max_impressions = rng.randint(1, 4) if bid_weight >= Decimal("0.7500") else rng.randint(1, 5)

    return {
        "track_id": pair["track_id"],
        "artist_id": pair["artist_id"],
        "objective": objective,
        "bid_weight": bid_weight,
        "daily_budget": daily_budget,
        "remaining_budget": remaining_budget,
        "target_genre": pair.get("genre"),
        "max_impressions_per_user_per_day": max_impressions,
        "start_date": start_date,
        "end_date": end_date,
        "status": status,
    }


def generate_campaign_group(
    artist_pairs: Sequence[dict[str, Any]],
    *,
    active_ratio: float,
    rng: random.Random,
    today: date | None = None,
) -> list[dict[str, Any]]:
    """Generate one campaign group with 3-15 distinct tracks for the same artist."""
    unique_pairs = list({str(pair["track_id"]): pair for pair in artist_pairs}.values())
    if len(unique_pairs) < MIN_TRACKS_PER_CAMPAIGN:
        raise ValueError(f"Campaign groups require at least {MIN_TRACKS_PER_CAMPAIGN} distinct tracks.")

    current_date = today or date.today()
    track_count = rng.randint(MIN_TRACKS_PER_CAMPAIGN, min(MAX_TRACKS_PER_CAMPAIGN, len(unique_pairs)))
    selected_pairs = rng.sample(unique_pairs, k=track_count)
    objective = weighted_choice(OBJECTIVE_WEIGHTS, rng)
    status = _choose_status(active_ratio, rng)
    start_date, end_date = _date_range_for_status(status, rng, current_date)
    return [
        generate_campaign(
            pair,
            active_ratio=active_ratio,
            rng=rng,
            today=current_date,
            objective=objective,
            status=status,
            start_date=start_date,
            end_date=end_date,
        )
        for pair in selected_pairs
    ]


def upsert_campaigns(engine: Engine, campaigns: Sequence[dict[str, Any]]) -> int:
    if not campaigns:
        return 0
    sql = """
        INSERT INTO promotion_campaigns (
            track_id, artist_id, objective, bid_weight, daily_budget, remaining_budget,
            target_genre, max_impressions_per_user_per_day, start_date, end_date, status
        )
        VALUES (
            :track_id, :artist_id, :objective, :bid_weight, :daily_budget, :remaining_budget,
            :target_genre, :max_impressions_per_user_per_day, :start_date, :end_date, :status
        )
        ON DUPLICATE KEY UPDATE
            bid_weight = VALUES(bid_weight),
            daily_budget = VALUES(daily_budget),
            remaining_budget = VALUES(remaining_budget),
            target_genre = VALUES(target_genre),
            max_impressions_per_user_per_day = VALUES(max_impressions_per_user_per_day),
            status = VALUES(status),
            updated_at = CURRENT_TIMESTAMP
    """
    with engine.begin() as conn:
        result = conn.execute(text(sql), list(campaigns))
        return int(result.rowcount or 0)


def print_summary(
    *,
    eligible_count: int,
    eligible_artist_count: int,
    attempted_groups: int,
    attempted: int,
    affected: int,
    skipped: int,
    campaigns: Sequence[dict[str, Any]],
) -> None:
    status_counts = Counter(campaign["status"] for campaign in campaigns)
    objective_counts = Counter(campaign["objective"] for campaign in campaigns)
    print("Promotion campaign seed summary")
    print(f"  eligible_track_artist_pairs_found: {eligible_count}")
    print(f"  eligible_artists_with_3_plus_tracks: {eligible_artist_count}")
    print(f"  campaign_groups_attempted: {attempted_groups}")
    print(f"  campaign_track_rows_attempted: {attempted}")
    print(f"  rows_inserted_or_updated_mysql_affected: {affected}")
    print(f"  campaign_track_rows_skipped: {skipped}")
    print("  count_by_status:")
    for status, count in sorted(status_counts.items()):
        print(f"    {status}: {count}")
    print("  count_by_objective:")
    for objective, count in sorted(objective_counts.items()):
        print(f"    {objective}: {count}")


def main() -> int:
    args = parse_args()
    rng = random.Random(args.seed)
    engine = get_engine()

    try:
        eligible_pairs = fetch_eligible_track_artist_pairs(engine)
        if not eligible_pairs:
            print("No eligible track-artist pairs found. Load music data before seeding campaigns.", file=sys.stderr)
            return 1
        eligible_artist_groups = group_pairs_by_artist(eligible_pairs)
        if not eligible_artist_groups:
            print(
                f"No artists with at least {MIN_TRACKS_PER_CAMPAIGN} eligible tracks found. "
                "Load more music data before seeding campaigns.",
                file=sys.stderr,
            )
            return 1

        campaigns: list[dict[str, Any]] = []
        used_active_track_objectives = fetch_existing_active_track_objectives(engine)
        skipped = 0
        group_weights = [sum(_pair_weight(pair) for pair in artist_pairs) for artist_pairs in eligible_artist_groups]

        for artist_pairs in rng.choices(eligible_artist_groups, weights=group_weights, k=args.num_campaigns):
            campaign_group = generate_campaign_group(artist_pairs, active_ratio=args.active_ratio, rng=rng)
            available_group = [
                campaign
                for campaign in campaign_group
                if campaign["status"] != "active"
                or (campaign["track_id"], campaign["objective"]) not in used_active_track_objectives
            ]
            if len(available_group) < MIN_TRACKS_PER_CAMPAIGN:
                skipped += len(campaign_group)
                continue

            for campaign in available_group:
                if campaign["status"] == "active":
                    used_active_track_objectives.add((campaign["track_id"], campaign["objective"]))
                campaigns.append(campaign)

        affected = upsert_campaigns(engine, campaigns)
        print_summary(
            eligible_count=len(eligible_pairs),
            eligible_artist_count=len(eligible_artist_groups),
            attempted_groups=args.num_campaigns,
            attempted=len(campaigns),
            affected=affected,
            skipped=skipped,
            campaigns=campaigns,
        )
    except Exception as exc:
        print(f"Campaign seeding failed: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
