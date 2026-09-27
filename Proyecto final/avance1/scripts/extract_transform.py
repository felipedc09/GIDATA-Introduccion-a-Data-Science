"""
Extracción y transformación (E+T de un ETL) de los CSV crudos del
dataset histórico de Mundiales (fuente: jfjelstul/worldcup) hacia los
15 DataFrames normalizados que corresponden 1 a 1 con las tablas del
esquema definido en `sql/schema.sql`.

Este módulo NO toca la base de datos: solo lee `data/*.csv` con Pandas
y devuelve DataFrames limpios. La carga a MySQL vive en `load_data.py`.
"""

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

NOT_APPLICABLE = "not applicable"


# ---------------------------------------------------------------------
# Utilidades de limpieza
# ---------------------------------------------------------------------

def _read_csv(name: str) -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / name, encoding="utf-8")
    # Espacios sobrantes en encabezados y celdas de texto
    df.columns = [c.strip() for c in df.columns]
    text_cols = [c for c in df.columns if df[c].dtype.kind == "O"]
    for col in text_cols:
        df[col] = df[col].astype(str).str.strip()
        df[col] = df[col].replace({NOT_APPLICABLE: None, "nan": None, "": None})
    return df


def _to_bool_int(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0).astype(int)


def _to_nullable_int(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").astype("Int64")


# ---------------------------------------------------------------------
# Tablas de catálogo (sin dependencias)
# ---------------------------------------------------------------------

def build_confederation() -> pd.DataFrame:
    raw = _read_csv("confederations.csv")
    df = raw.rename(columns={
        "confederation_id": "confederation_id",
        "confederation_name": "confederation_name",
        "confederation_code": "confederation_code",
        "confederation_wikipedia_link": "confederation_wikipedia_link",
    })[["confederation_id", "confederation_name", "confederation_code",
        "confederation_wikipedia_link"]]
    return df.drop_duplicates(subset="confederation_id").reset_index(drop=True)


def build_region(teams_raw: pd.DataFrame) -> pd.DataFrame:
    names = sorted(teams_raw["region_name"].dropna().unique())
    df = pd.DataFrame({"region_name": names})
    df.insert(0, "region_id", range(1, len(df) + 1))
    return df


def build_federation(teams_raw: pd.DataFrame) -> pd.DataFrame:
    names = sorted(teams_raw["federation_name"].dropna().unique())
    df = pd.DataFrame({"federation_name": names})
    df.insert(0, "federation_id", range(1, len(df) + 1))
    return df


def build_country(stadiums_raw: pd.DataFrame, matches_raw: pd.DataFrame,
                   tournaments_raw: pd.DataFrame) -> pd.DataFrame:
    names = set(stadiums_raw["country_name"].dropna())
    names |= set(matches_raw["country_name"].dropna())
    names |= set(tournaments_raw["host_country"].dropna())
    df = pd.DataFrame({"country_name": sorted(names)})
    df.insert(0, "country_id", range(1, len(df) + 1))
    return df


def build_position(player_appearances_raw: pd.DataFrame) -> pd.DataFrame:
    df = (
        player_appearances_raw[["position_name", "position_code"]]
        .dropna()
        .drop_duplicates()
        .sort_values("position_name")
        .reset_index(drop=True)
    )
    df.insert(0, "position_id", range(1, len(df) + 1))
    return df


def build_award() -> pd.DataFrame:
    raw = _read_csv("awards.csv")
    df = raw.rename(columns={"award_id": "award_id"})[
        ["award_id", "award_name", "award_description", "year_introduced"]
    ]
    df["year_introduced"] = _to_nullable_int(df["year_introduced"])
    return df.drop_duplicates(subset="award_id").reset_index(drop=True)


def build_player() -> pd.DataFrame:
    raw = _read_csv("players.csv")
    df = raw[[
        "player_id", "family_name", "given_name", "birth_date", "female",
        "player_wikipedia_link",
    ]].copy()
    df["female"] = _to_bool_int(df["female"])
    df["birth_date"] = pd.to_datetime(df["birth_date"], errors="coerce").dt.date
    return df.drop_duplicates(subset="player_id").reset_index(drop=True)


# ---------------------------------------------------------------------
# Tablas de nivel 2
# ---------------------------------------------------------------------

def build_city(stadiums_raw: pd.DataFrame, matches_raw: pd.DataFrame,
               country_df: pd.DataFrame) -> pd.DataFrame:
    pairs = pd.concat([
        stadiums_raw[["city_name", "country_name", "city_wikipedia_link"]],
        matches_raw[["city_name", "country_name"]].assign(city_wikipedia_link=None),
    ], ignore_index=True)

    pairs = pairs.dropna(subset=["city_name", "country_name"])
    # Si una ciudad aparece con y sin link, nos quedamos con el link no nulo
    pairs = (
        pairs.sort_values("city_wikipedia_link")
        .drop_duplicates(subset=["city_name", "country_name"], keep="last")
        .reset_index(drop=True)
    )

    df = pairs.merge(country_df, left_on="country_name", right_on="country_name", how="left")
    df = df[["city_name", "country_id", "city_wikipedia_link"]]
    df = df.drop_duplicates(subset=["city_name", "country_id"]).reset_index(drop=True)
    df.insert(0, "city_id", range(1, len(df) + 1))
    return df


def build_team(teams_raw: pd.DataFrame, federation_df: pd.DataFrame,
               region_df: pd.DataFrame) -> pd.DataFrame:
    df = teams_raw.merge(federation_df, on="federation_name", how="left")
    df = df.merge(region_df, on="region_name", how="left")
    df = df[[
        "team_id", "team_name", "team_code", "mens_team", "womens_team",
        "federation_id", "region_id", "confederation_id",
        "mens_team_wikipedia_link", "womens_team_wikipedia_link",
    ]].copy()
    df["mens_team"] = _to_bool_int(df["mens_team"])
    df["womens_team"] = _to_bool_int(df["womens_team"])
    return df.drop_duplicates(subset="team_id").reset_index(drop=True)


# ---------------------------------------------------------------------
# Tablas de nivel 3
# ---------------------------------------------------------------------

def build_stadium(stadiums_raw: pd.DataFrame, city_df: pd.DataFrame,
                   country_df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza los estadios y los enlaza con su ciudad (city_id).

    Como el nombre de una ciudad puede repetirse en países distintos,
    el cruce se hace por (city_name, country_name) y no solo por nombre.
    """
    city_lookup = city_df.merge(country_df, on="country_id", how="left")
    merged = stadiums_raw.merge(
        city_lookup[["city_id", "city_name", "country_name"]],
        on=["city_name", "country_name"],
        how="left",
    )
    df = merged[[
        "stadium_id", "stadium_name", "city_id", "stadium_capacity",
        "stadium_wikipedia_link",
    ]].copy()
    df["stadium_capacity"] = _to_nullable_int(df["stadium_capacity"])
    return df.drop_duplicates(subset="stadium_id").reset_index(drop=True)


def build_tournament(country_df: pd.DataFrame, team_df: pd.DataFrame) -> pd.DataFrame:
    raw = _read_csv("tournaments.csv")
    df = raw.merge(
        country_df, left_on="host_country", right_on="country_name", how="left"
    )
    df = df.merge(
        team_df[["team_id", "team_name"]],
        left_on="winner", right_on="team_name", how="left",
        suffixes=("", "_winner"),
    )
    df = df.rename(columns={"country_id": "host_country_id", "team_id": "winner_team_id"})
    bool_cols = [
        "host_won", "group_stage", "second_group_stage", "final_round",
        "round_of_16", "quarter_finals", "semi_finals", "third_place_match",
        "final",
    ]
    for col in bool_cols:
        df[col] = _to_bool_int(df[col])
    df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce").dt.date
    df["end_date"] = pd.to_datetime(df["end_date"], errors="coerce").dt.date
    df["count_teams"] = _to_nullable_int(df["count_teams"])
    df["year"] = _to_nullable_int(df["year"])

    cols = [
        "tournament_id", "tournament_name", "year", "start_date", "end_date",
        "host_country_id", "winner_team_id", "host_won", "count_teams",
        "group_stage", "second_group_stage", "final_round", "round_of_16",
        "quarter_finals", "semi_finals", "third_place_match", "final",
    ]
    return df[cols].drop_duplicates(subset="tournament_id").reset_index(drop=True)


# ---------------------------------------------------------------------
# Tablas de nivel 4
# ---------------------------------------------------------------------

def build_matches(stadium_df: pd.DataFrame) -> pd.DataFrame:
    raw = _read_csv("matches.csv")
    df = raw.copy()
    df["match_time"] = df["match_time"].fillna("00:00")
    df["match_date"] = pd.to_datetime(df["match_date"], errors="coerce").dt.date

    bool_cols = ["extra_time", "penalty_shootout", "replayed", "replay"]
    for col in bool_cols:
        df[col] = _to_bool_int(df[col])

    for col in ["home_team_score", "away_team_score",
                "home_team_score_penalties", "away_team_score_penalties"]:
        df[col] = _to_nullable_int(df[col])

    # Solo conservamos estadios que sí quedaron normalizados
    valid_stadiums = set(stadium_df["stadium_id"])
    df["stadium_id"] = df["stadium_id"].where(df["stadium_id"].isin(valid_stadiums))

    cols = [
        "match_id", "tournament_id", "stage_name", "group_name", "match_date",
        "match_time", "stadium_id", "home_team_id", "away_team_id",
        "home_team_score", "away_team_score", "extra_time", "penalty_shootout",
        "home_team_score_penalties", "away_team_score_penalties", "result",
        "replayed", "replay",
    ]
    return df[cols].drop_duplicates(subset="match_id").reset_index(drop=True)


def build_goal() -> pd.DataFrame:
    raw = _read_csv("goals.csv")
    df = raw.copy()
    for col in ["minute_regulation", "minute_stoppage"]:
        df[col] = _to_nullable_int(df[col])
    for col in ["own_goal", "penalty"]:
        df[col] = _to_bool_int(df[col])

    cols = [
        "goal_id", "match_id", "team_id", "player_id", "minute_regulation",
        "minute_stoppage", "match_period", "own_goal", "penalty",
    ]
    return df[cols].drop_duplicates(subset="goal_id").reset_index(drop=True)


def build_player_appearance(position_df: pd.DataFrame) -> pd.DataFrame:
    raw = _read_csv("player_appearances.csv")
    df = raw.merge(position_df, on=["position_name", "position_code"], how="left")
    df["shirt_number"] = _to_nullable_int(df["shirt_number"])
    for col in ["starter", "substitute"]:
        df[col] = _to_bool_int(df[col])

    cols = ["match_id", "team_id", "player_id", "position_id", "shirt_number",
            "starter", "substitute"]
    return df[cols].drop_duplicates(
        subset=["match_id", "team_id", "player_id"]
    ).reset_index(drop=True)


def build_award_winner() -> pd.DataFrame:
    raw = _read_csv("award_winners.csv")
    df = raw.copy()
    df["shared"] = _to_bool_int(df["shared"])
    cols = ["tournament_id", "award_id", "player_id", "team_id", "shared"]
    return df[cols].drop_duplicates(
        subset=["tournament_id", "award_id", "player_id"]
    ).reset_index(drop=True)


# ---------------------------------------------------------------------
# Orquestación: arma TODOS los DataFrames normalizados en orden de FK
# ---------------------------------------------------------------------

def build_all() -> dict:
    teams_raw = _read_csv("teams.csv")
    stadiums_raw = _read_csv("stadiums.csv")
    matches_raw = _read_csv("matches.csv")
    tournaments_raw = _read_csv("tournaments.csv")
    player_appearances_raw = _read_csv("player_appearances.csv")

    confederation_df = build_confederation()
    region_df = build_region(teams_raw)
    federation_df = build_federation(teams_raw)
    country_df = build_country(stadiums_raw, matches_raw, tournaments_raw)
    position_df = build_position(player_appearances_raw)
    award_df = build_award()
    player_df = build_player()

    city_df = build_city(stadiums_raw, matches_raw, country_df)
    team_df = build_team(teams_raw, federation_df, region_df)

    stadium_df = build_stadium(stadiums_raw, city_df, country_df)
    tournament_df = build_tournament(country_df, team_df)

    matches_df = build_matches(stadium_df)
    goal_df = build_goal()
    player_appearance_df = build_player_appearance(position_df)
    award_winner_df = build_award_winner()

    return {
        "confederation": confederation_df,
        "region": region_df,
        "federation": federation_df,
        "country": country_df,
        "position": position_df,
        "award": award_df,
        "player": player_df,
        "city": city_df,
        "team": team_df,
        "stadium": stadium_df,
        "tournament": tournament_df,
        "matches": matches_df,
        "goal": goal_df,
        "player_appearance": player_appearance_df,
        "award_winner": award_winner_df,
    }


if __name__ == "__main__":
    tables = build_all()
    for name, frame in tables.items():
        print(f"{name:20s} -> {len(frame):6d} filas")
