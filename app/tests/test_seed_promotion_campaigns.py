from datetime import date
from decimal import Decimal
import random

from db_setup.seed_promotion_campaigns import (
    MAX_TRACKS_PER_CAMPAIGN,
    MIN_TRACKS_PER_CAMPAIGN,
    generate_campaign_group,
    group_pairs_by_artist,
)


def _eligible_pair(artist_id: int, track_id: str):
    return {
        "track_id": track_id,
        "track_name": f"Track {track_id}",
        "genre": "Pop",
        "duration_ms": 180000,
        "artist_id": artist_id,
        "artist_name": f"Artist {artist_id}",
    }


def test_group_pairs_by_artist_only_keeps_artists_with_minimum_track_count():
    groups = group_pairs_by_artist(
        [
            _eligible_pair(1, "track-1"),
            _eligible_pair(1, "track-2"),
            _eligible_pair(2, "track-3"),
            _eligible_pair(2, "track-4"),
            _eligible_pair(2, "track-5"),
        ]
    )

    assert len(groups) == 1
    assert {pair["track_id"] for pair in groups[0]} == {"track-3", "track-4", "track-5"}


def test_generate_campaign_group_uses_three_to_fifteen_distinct_tracks():
    artist_pairs = [_eligible_pair(10, f"track-{index}") for index in range(20)]

    campaigns = generate_campaign_group(
        artist_pairs,
        active_ratio=0.75,
        rng=random.Random(42),
        today=date(2026, 6, 5),
    )

    assert MIN_TRACKS_PER_CAMPAIGN <= len(campaigns) <= MAX_TRACKS_PER_CAMPAIGN
    assert len({campaign["track_id"] for campaign in campaigns}) == len(campaigns)
    assert {campaign["artist_id"] for campaign in campaigns} == {10}
    assert {campaign["objective"] for campaign in campaigns} == {campaigns[0]["objective"]}
    assert {campaign["status"] for campaign in campaigns} == {campaigns[0]["status"]}
    assert {campaign["start_date"] for campaign in campaigns} == {campaigns[0]["start_date"]}
    assert {campaign["end_date"] for campaign in campaigns} == {campaigns[0]["end_date"]}
    assert all(isinstance(campaign["daily_budget"], Decimal) for campaign in campaigns)
