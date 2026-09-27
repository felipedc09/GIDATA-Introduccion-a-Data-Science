-- =====================================================================
-- GIDATA - Introducción a Data Science
-- Proyecto final - Avance 1
-- Base de datos relacional para el histórico de los Mundiales FIFA
-- Motor: MySQL 8.0+
-- =====================================================================
-- Fuente de datos: https://github.com/jfjelstul/worldcup (Jason Fjelstul)
-- Las tablas normalizan la información cruda de esa fuente en las 15
-- entidades pedidas en el enunciado (Avance 1).
-- =====================================================================

DROP DATABASE IF EXISTS worldcup;
CREATE DATABASE worldcup CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE worldcup;

SET FOREIGN_KEY_CHECKS = 0;

-- ---------------------------------------------------------------------
-- Tablas de catálogo / dimensión (sin dependencias)
-- ---------------------------------------------------------------------

CREATE TABLE confederation (
    confederation_id            VARCHAR(10)   NOT NULL,
    confederation_name          VARCHAR(100)  NOT NULL,
    confederation_code          VARCHAR(10)   NOT NULL,
    confederation_wikipedia_link VARCHAR(255),
    PRIMARY KEY (confederation_id),
    UNIQUE KEY uq_confederation_code (confederation_code)
) ENGINE=InnoDB;

CREATE TABLE region (
    region_id    INT          NOT NULL AUTO_INCREMENT,
    region_name  VARCHAR(50)  NOT NULL,
    PRIMARY KEY (region_id),
    UNIQUE KEY uq_region_name (region_name)
) ENGINE=InnoDB;

CREATE TABLE federation (
    federation_id    INT           NOT NULL AUTO_INCREMENT,
    federation_name  VARCHAR(150)  NOT NULL,
    PRIMARY KEY (federation_id),
    UNIQUE KEY uq_federation_name (federation_name)
) ENGINE=InnoDB;

CREATE TABLE country (
    country_id    INT           NOT NULL AUTO_INCREMENT,
    country_name  VARCHAR(100)  NOT NULL,
    PRIMARY KEY (country_id),
    UNIQUE KEY uq_country_name (country_name)
) ENGINE=InnoDB;

CREATE TABLE position (
    position_id    INT          NOT NULL AUTO_INCREMENT,
    position_name  VARCHAR(50)  NOT NULL,
    position_code  VARCHAR(5)   NOT NULL,
    PRIMARY KEY (position_id),
    UNIQUE KEY uq_position_name (position_name),
    UNIQUE KEY uq_position_code (position_code)
) ENGINE=InnoDB;

CREATE TABLE award (
    award_id            VARCHAR(10)   NOT NULL,
    award_name          VARCHAR(100)  NOT NULL,
    award_description   VARCHAR(255),
    year_introduced     INT,
    PRIMARY KEY (award_id)
) ENGINE=InnoDB;

CREATE TABLE player (
    player_id             VARCHAR(10)   NOT NULL,
    family_name           VARCHAR(100)  NOT NULL,
    given_name             VARCHAR(100)  NULL COMMENT 'NULL para jugadores conocidos por un solo nombre (p. ej. Pelé)',
    birth_date             DATE,
    female                  TINYINT(1)    NOT NULL DEFAULT 0,
    player_wikipedia_link  VARCHAR(255),
    PRIMARY KEY (player_id)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- Tablas de nivel 2 (dependen de las anteriores)
-- ---------------------------------------------------------------------

CREATE TABLE city (
    city_id             INT           NOT NULL AUTO_INCREMENT,
    city_name           VARCHAR(100)  NOT NULL,
    country_id          INT           NOT NULL,
    city_wikipedia_link VARCHAR(255),
    PRIMARY KEY (city_id),
    UNIQUE KEY uq_city_country (city_name, country_id),
    CONSTRAINT fk_city_country FOREIGN KEY (country_id)
        REFERENCES country (country_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE team (
    team_id                     VARCHAR(10)   NOT NULL,
    team_name                   VARCHAR(100)  NOT NULL,
    team_code                   CHAR(3)       NOT NULL,
    mens_team                   TINYINT(1)    NOT NULL DEFAULT 0,
    womens_team                 TINYINT(1)    NOT NULL DEFAULT 0,
    federation_id               INT,
    region_id                   INT,
    confederation_id            VARCHAR(10),
    mens_team_wikipedia_link    VARCHAR(255),
    womens_team_wikipedia_link  VARCHAR(255),
    PRIMARY KEY (team_id),
    CONSTRAINT fk_team_federation FOREIGN KEY (federation_id)
        REFERENCES federation (federation_id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT fk_team_region FOREIGN KEY (region_id)
        REFERENCES region (region_id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT fk_team_confederation FOREIGN KEY (confederation_id)
        REFERENCES confederation (confederation_id)
        ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- Tablas de nivel 3
-- ---------------------------------------------------------------------

CREATE TABLE stadium (
    stadium_id             VARCHAR(10)   NOT NULL,
    stadium_name           VARCHAR(150)  NOT NULL,
    city_id                INT           NOT NULL,
    stadium_capacity       INT,
    stadium_wikipedia_link VARCHAR(255),
    PRIMARY KEY (stadium_id),
    CONSTRAINT fk_stadium_city FOREIGN KEY (city_id)
        REFERENCES city (city_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE tournament (
    tournament_id       VARCHAR(10)   NOT NULL,
    tournament_name     VARCHAR(100)  NOT NULL,
    year                INT           NOT NULL,
    start_date          DATE,
    end_date            DATE,
    host_country_id     INT,
    winner_team_id      VARCHAR(10),
    host_won            TINYINT(1),
    count_teams         INT,
    group_stage         TINYINT(1),
    second_group_stage  TINYINT(1),
    final_round         TINYINT(1),
    round_of_16         TINYINT(1),
    quarter_finals      TINYINT(1),
    semi_finals         TINYINT(1),
    third_place_match   TINYINT(1),
    final               TINYINT(1),
    PRIMARY KEY (tournament_id),
    CONSTRAINT fk_tournament_country FOREIGN KEY (host_country_id)
        REFERENCES country (country_id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT fk_tournament_winner FOREIGN KEY (winner_team_id)
        REFERENCES team (team_id)
        ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- Tablas de nivel 4 (partidos, goles, convocatorias, premios)
-- ---------------------------------------------------------------------

CREATE TABLE matches (
    match_id                    VARCHAR(15)   NOT NULL,
    tournament_id                VARCHAR(10)   NOT NULL,
    stage_name                   VARCHAR(50)   NOT NULL,
    group_name                   VARCHAR(20),
    match_date                   DATE          NOT NULL,
    match_time                   TIME,
    stadium_id                   VARCHAR(10),
    home_team_id                 VARCHAR(10)   NOT NULL,
    away_team_id                 VARCHAR(10)   NOT NULL,
    home_team_score              INT           NOT NULL DEFAULT 0,
    away_team_score              INT           NOT NULL DEFAULT 0,
    extra_time                   TINYINT(1)    NOT NULL DEFAULT 0,
    penalty_shootout              TINYINT(1)    NOT NULL DEFAULT 0,
    home_team_score_penalties    INT,
    away_team_score_penalties    INT,
    result                        VARCHAR(30),
    replayed                     TINYINT(1)    NOT NULL DEFAULT 0,
    replay                        TINYINT(1)    NOT NULL DEFAULT 0,
    PRIMARY KEY (match_id),
    CONSTRAINT fk_matches_tournament FOREIGN KEY (tournament_id)
        REFERENCES tournament (tournament_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_matches_stadium FOREIGN KEY (stadium_id)
        REFERENCES stadium (stadium_id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT fk_matches_home_team FOREIGN KEY (home_team_id)
        REFERENCES team (team_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_matches_away_team FOREIGN KEY (away_team_id)
        REFERENCES team (team_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE goal (
    goal_id             VARCHAR(10)  NOT NULL,
    match_id            VARCHAR(15)  NOT NULL,
    team_id             VARCHAR(10)  NOT NULL,
    player_id           VARCHAR(10)  NOT NULL,
    minute_regulation   INT,
    minute_stoppage     INT,
    match_period        VARCHAR(50),
    own_goal            TINYINT(1)   NOT NULL DEFAULT 0,
    penalty             TINYINT(1)   NOT NULL DEFAULT 0,
    PRIMARY KEY (goal_id),
    CONSTRAINT fk_goal_match FOREIGN KEY (match_id)
        REFERENCES matches (match_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_goal_team FOREIGN KEY (team_id)
        REFERENCES team (team_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_goal_player FOREIGN KEY (player_id)
        REFERENCES player (player_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE player_appearance (
    player_appearance_id  INT           NOT NULL AUTO_INCREMENT,
    match_id               VARCHAR(15)   NOT NULL,
    team_id                 VARCHAR(10)   NOT NULL,
    player_id               VARCHAR(10)   NOT NULL,
    position_id             INT,
    shirt_number             INT,
    starter                  TINYINT(1)    NOT NULL DEFAULT 0,
    substitute               TINYINT(1)    NOT NULL DEFAULT 0,
    PRIMARY KEY (player_appearance_id),
    UNIQUE KEY uq_appearance (match_id, team_id, player_id),
    CONSTRAINT fk_appearance_match FOREIGN KEY (match_id)
        REFERENCES matches (match_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_appearance_team FOREIGN KEY (team_id)
        REFERENCES team (team_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_appearance_player FOREIGN KEY (player_id)
        REFERENCES player (player_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_appearance_position FOREIGN KEY (position_id)
        REFERENCES position (position_id)
        ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE award_winner (
    award_winner_id  INT           NOT NULL AUTO_INCREMENT,
    tournament_id     VARCHAR(10)   NOT NULL,
    award_id           VARCHAR(10)   NOT NULL,
    player_id           VARCHAR(10)   NOT NULL,
    team_id             VARCHAR(10)   NOT NULL,
    shared               TINYINT(1)    NOT NULL DEFAULT 0,
    PRIMARY KEY (award_winner_id),
    UNIQUE KEY uq_award_winner (tournament_id, award_id, player_id),
    CONSTRAINT fk_award_winner_tournament FOREIGN KEY (tournament_id)
        REFERENCES tournament (tournament_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_award_winner_award FOREIGN KEY (award_id)
        REFERENCES award (award_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_award_winner_player FOREIGN KEY (player_id)
        REFERENCES player (player_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_award_winner_team FOREIGN KEY (team_id)
        REFERENCES team (team_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

SET FOREIGN_KEY_CHECKS = 1;

-- ---------------------------------------------------------------------
-- Índices adicionales para consultas frecuentes
-- ---------------------------------------------------------------------
CREATE INDEX idx_matches_tournament ON matches (tournament_id);
CREATE INDEX idx_goal_match         ON goal (match_id);
CREATE INDEX idx_appearance_player  ON player_appearance (player_id);
CREATE INDEX idx_team_confederation ON team (confederation_id);
