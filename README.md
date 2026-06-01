# Oasis Lite Database Layer

Oasis Lite is a Spotify-style backend simulation for music promotion allocation
and recommendation. The database separates source music metadata, normalized
artists/tags, user listening history, synthetic promotion supply, and runtime
recommendation logs.

## 1. Start MySQL with Docker

```bash
docker run --name oasis-lite-mysql \
  -e MYSQL_ROOT_PASSWORD=oasis_password \
  -e MYSQL_DATABASE=oasis_lite \
  -p 3306:3306 \
  -d mysql:8.0
```

If the container already exists:

```bash
docker start oasis-lite-mysql
```

## 2. Run the schema migration

```bash
docker exec -it oasis-lite-mysql mysql -h 127.0.0.1 -P 3306 -u root -poasis_password oasis_lite < 001_create_music_schema.sql
```

The migration creates normalized tables for:

- artists and tracks
- track artists and tags
- audio features
- user listening history
- user taste profiles
- promotion campaigns
- promotion impressions and events


## 3. Install Python dependencies in the conda environment

Use the project conda environment:

```bash
conda install -n oasis-lite -c conda-forge sqlalchemy pymysql pandas openpyxl
```

## 4. Configure database environment variables

```bash
export DB_HOST=127.0.0.1
export DB_PORT=3306
export DB_USER=root
export DB_PASSWORD=oasis_password
export DB_NAME=oasis_lite
```

## 5. Load music and listening datasets

The loader expects:

- `data/music_info.xlsx`
- `data/user_listening_history.xlsx`

The data used for this project came from the [Million Song Dataset + Spotify + Last.fm](https://www.kaggle.com/datasets/undefinenull/million-song-dataset-spotify-lastfm) on Kaggle. 

Download `Music Info.csv` and `User Listening History.csv`, renaming and saving them as Excel workbooks `music_info.xlsx` and `user_listening_history.xlsx`.

The listening-history file may use either `playcount` or `play_count`.

```bash
conda run -n oasis-lite python load_datasets.py
```

The loader is safe to run multiple times. It upserts artists, tracks, audio
features, tags, users, and play counts, then refreshes `user_taste_profiles`.
Taste profiles are play-count-weighted averages of each user's listened track
audio features: `danceability`, `energy`, `acousticness`, `instrumentalness`,
`valence`, and `tempo`. Listening-history rows whose `track_id` does not exist
in `tracks` are skipped with a warning.

## 6. Seed synthetic promotion campaigns

`promotion_campaigns` represents the supply of tracks that are eligible to be
promoted by the recommendation backend. These rows are synthetic because the
source datasets contain music metadata and listening behavior, but no ad or
promotion campaign data.

```bash
conda run -n oasis-lite python seed_promotion_campaigns.py \
  --num-campaigns 500 \
  --active-ratio 0.75 \
  --seed 42
```

The seeder reads existing `tracks`, `artists`, and `track_artists`; it does not
create fake tracks or fake artists. It uses deterministic randomness when
`--seed` is provided and upserts campaign rows using MySQL's duplicate-key
handling.

The script does not seed `promotion_impressions` or `promotion_events`.
Those tables are runtime logs: the recommendation API should insert impressions
when promoted recommendations are served, and events when users click, stream,
skip, or save.
