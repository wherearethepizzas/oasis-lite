from prometheus_client import Counter, Gauge, Histogram


recommendation_requests = Counter(
    "recommendation_requests",
    "Total number of promoted recommendation requests.",
)
recommendation_latency_seconds = Histogram(
    "recommendation_latency_seconds",
    "Latency for promoted recommendation requests in seconds.",
)
promoted_tracks_served = Counter(
    "promoted_tracks_served",
    "Total number of promoted tracks returned by recommendation responses.",
)
promotion_events = Counter(
    "promotion_events",
    "Total number of logged promotion interaction events.",
)
active_campaigns = Gauge(
    "active_campaigns_total",
    "Current active campaigns observed by the active campaigns endpoint.",
)
