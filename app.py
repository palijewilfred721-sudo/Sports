
from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from pathlib import Path

app = Flask(__name__)
app.secret_key = "change-this-development-key"

DATABASE = Path(__file__).parent / "football.db"


# Connect to the database
def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


# Create database tables
def init_db():
    with get_db() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS teams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                jersey_number INTEGER,
                position TEXT NOT NULL,
                team_id INTEGER NOT NULL,
                FOREIGN KEY (team_id) REFERENCES teams(id)
                    ON DELETE RESTRICT
            );

            CREATE TABLE IF NOT EXISTS fixtures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                home_team INTEGER NOT NULL,
                away_team INTEGER NOT NULL,
                match_date TEXT NOT NULL,
                venue TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Scheduled',
                FOREIGN KEY (home_team) REFERENCES teams(id),
                FOREIGN KEY (away_team) REFERENCES teams(id),
                CHECK (home_team != away_team)
            );

            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fixture_id INTEGER NOT NULL UNIQUE,
                home_goals INTEGER NOT NULL,
                away_goals INTEGER NOT NULL,
                FOREIGN KEY (fixture_id) REFERENCES fixtures(id)
                    ON DELETE CASCADE,
                CHECK (home_goals >= 0),
                CHECK (away_goals >= 0)
            );
        """)


# Dashboard
@app.route("/")
def index():
    with get_db() as db:
        players_count = db.execute(
            "SELECT COUNT(*) FROM players"
        ).fetchone()[0]

        teams_count = db.execute(
            "SELECT COUNT(*) FROM teams"
        ).fetchone()[0]

        fixtures_count = db.execute(
            "SELECT COUNT(*) FROM fixtures"
        ).fetchone()[0]

        results_count = db.execute(
            "SELECT COUNT(*) FROM results"
        ).fetchone()[0]

        upcoming = db.execute("""
            SELECT f.*, h.name AS home_name, a.name AS away_name
            FROM fixtures f
            JOIN teams h ON f.home_team = h.id
            JOIN teams a ON f.away_team = a.id
            WHERE f.status = 'Scheduled'
            ORDER BY f.match_date
            LIMIT 5
        """).fetchall()

    return render_template(
        "index.html",
        players_count=players_count,
        teams_count=teams_count,
        fixtures_count=fixtures_count,
        results_count=results_count,
        upcoming=upcoming
    )


# Register and display players
@app.route("/players", methods=["GET", "POST"])
def players():
    with get_db() as db:
        if request.method == "POST":
            full_name = request.form.get("full_name", "").strip()
            position = request.form.get("position", "").strip()
            team_id = request.form.get("team_id", type=int)
            jersey_text = request.form.get("jersey_number", "").strip()

            try:
                jersey_number = int(jersey_text) if jersey_text else None

                if not full_name or not position or not team_id:
                    raise ValueError("Complete all required fields.")

                if jersey_number is not None and not 1 <= jersey_number <= 99:
                    raise ValueError("Jersey number must be between 1 and 99.")

                db.execute("""
                    INSERT INTO players
                    (full_name, jersey_number, position, team_id)
                    VALUES (?, ?, ?, ?)
                """, (full_name, jersey_number, position, team_id))

                db.commit()
                flash("Player registered successfully.", "success")

            except ValueError as error:
                flash(str(error), "error")
            except sqlite3.IntegrityError:
                flash("Invalid team or duplicate data.", "error")

            return redirect(url_for("players"))

        player_list = db.execute("""
            SELECT p.*, t.name AS team_name
            FROM players p
            JOIN teams t ON p.team_id = t.id
            ORDER BY p.full_name
        """).fetchall()

        team_list = db.execute(
            "SELECT * FROM teams ORDER BY name"
        ).fetchall()

    return render_template(
        "players.html",
        players=player_list,
        teams=team_list
    )


# Add and display teams
@app.route("/teams", methods=["GET", "POST"])
def teams():
    with get_db() as db:
        if request.method == "POST":
            name = request.form.get("name", "").strip()

            if not name:
                flash("Enter a team name.", "error")
            else:
                try:
                    db.execute(
                        "INSERT INTO teams (name) VALUES (?)",
                        (name,)
                    )
                    db.commit()
                    flash("Team added successfully.", "success")
                except sqlite3.IntegrityError:
                    flash("That team already exists.", "error")

            return redirect(url_for("teams"))

        team_list = db.execute("""
            SELECT t.*, COUNT(p.id) AS player_count
            FROM teams t
            LEFT JOIN players p ON t.id = p.team_id
            GROUP BY t.id
            ORDER BY t.name
        """).fetchall()

    return render_template("teams.html", teams=team_list)


# Create and display fixtures
@app.route("/fixtures", methods=["GET", "POST"])
def fixtures():
    with get_db() as db:
        team_list = db.execute(
            "SELECT * FROM teams ORDER BY name"
        ).fetchall()

        if request.method == "POST":
            home = request.form.get("home_team", type=int)
            away = request.form.get("away_team", type=int)
            match_date = request.form.get("match_date", "").strip()
            venue = request.form.get("venue", "").strip()

            if not home or not away or not match_date or not venue:
                flash("Complete all fixture fields.", "error")
            elif home == away:
                flash("A team cannot play against itself.", "error")
            else:
                try:
                    db.execute("""
                        INSERT INTO fixtures
                        (home_team, away_team, match_date, venue)
                        VALUES (?, ?, ?, ?)
                    """, (home, away, match_date, venue))

                    db.commit()
                    flash("Fixture scheduled successfully.", "success")
                except sqlite3.IntegrityError:
                    flash("Select valid teams.", "error")

            return redirect(url_for("fixtures"))

        fixture_list = db.execute("""
            SELECT f.*, h.name AS home_name, a.name AS away_name
            FROM fixtures f
            JOIN teams h ON f.home_team = h.id
            JOIN teams a ON f.away_team = a.id
            ORDER BY f.match_date DESC
        """).fetchall()

    return render_template(
        "fixtures.html",
        fixtures=fixture_list,
        teams=team_list
    )


# Record and display results
@app.route("/results", methods=["GET", "POST"])
def results():
    with get_db() as db:
        if request.method == "POST":
            fixture_id = request.form.get("fixture_id", type=int)
            home_goals = request.form.get("home_goals", type=int)
            away_goals = request.form.get("away_goals", type=int)

            if (
                not fixture_id
                or home_goals is None
                or away_goals is None
                or home_goals < 0
                or away_goals < 0
            ):
                flash("Enter a valid fixture and non-negative scores.", "error")
            else:
                try:
                    fixture = db.execute(
                        "SELECT * FROM fixtures WHERE id = ?",
                        (fixture_id,)
                    ).fetchone()

                    if fixture is None:
                        flash("Fixture not found.", "error")
                    else:
                        db.execute("""
                            INSERT INTO results
                            (fixture_id, home_goals, away_goals)
                            VALUES (?, ?, ?)
                            ON CONFLICT(fixture_id) DO UPDATE SET
                                home_goals = excluded.home_goals,
                                away_goals = excluded.away_goals
                        """, (fixture_id, home_goals, away_goals))

                        db.execute("""
                            UPDATE fixtures
                            SET status = 'Completed'
                            WHERE id = ?
                        """, (fixture_id,))

                        db.commit()
                        flash("Match result saved.", "success")

                except sqlite3.IntegrityError:
                    flash("Could not save the result.", "error")

            return redirect(url_for("results"))

        pending = db.execute("""
            SELECT f.id, f.match_date, h.name AS home_name,
                   a.name AS away_name
            FROM fixtures f
            JOIN teams h ON f.home_team = h.id
            JOIN teams a ON f.away_team = a.id
            LEFT JOIN results r ON f.id = r.fixture_id
            WHERE r.id IS NULL
            ORDER BY f.match_date
        """).fetchall()

        result_list = db.execute("""
            SELECT r.*, f.match_date,
                   h.name AS home_name, a.name AS away_name
            FROM results r
            JOIN fixtures f ON r.fixture_id = f.id
            JOIN teams h ON f.home_team = h.id
            JOIN teams a ON f.away_team = a.id
            ORDER BY f.match_date DESC
        """).fetchall()

    return render_template(
        "results.html",
        pending=pending,
        results=result_list
    )


# Calculate league standings
@app.route("/league")
def league():
    with get_db() as db:
        team_list = db.execute("""
            SELECT
                t.id,
                t.name,
                COUNT(r.id) AS played,
                SUM(CASE
                    WHEN r.id IS NOT NULL
                    AND (
                        (f.home_team = t.id AND r.home_goals > r.away_goals)
                        OR
                        (f.away_team = t.id AND r.away_goals > r.home_goals)
                    )
                    THEN 1 ELSE 0
                END) AS won,
                SUM(CASE
                    WHEN r.id IS NOT NULL
                    AND r.home_goals = r.away_goals
                    THEN 1 ELSE 0
                END) AS drawn,
                SUM(CASE
                    WHEN r.id IS NOT NULL
                    AND (
                        (f.home_team = t.id AND r.home_goals < r.away_goals)
                        OR
                        (f.away_team = t.id AND r.away_goals < r.home_goals)
                    )
                    THEN 1 ELSE 0
                END) AS lost,
                SUM(CASE
                    WHEN f.home_team = t.id THEN r.home_goals
                    WHEN f.away_team = t.id THEN r.away_goals
                    ELSE 0
                END) AS goals_for,
                SUM(CASE
                    WHEN f.home_team = t.id THEN r.away_goals
                    WHEN f.away_team = t.id THEN r.home_goals
                    ELSE 0
                END) AS goals_against
            FROM teams t
            LEFT JOIN fixtures f
                ON (f.home_team = t.id OR f.away_team = t.id)
            LEFT JOIN results r ON r.fixture_id = f.id
            GROUP BY t.id, t.name
        """).fetchall()

        standings = []

        for team in team_list:
            row = dict(team)
            row["won"] = row["won"] or 0
            row["drawn"] = row["drawn"] or 0
            row["lost"] = row["lost"] or 0
            row["goals_for"] = row["goals_for"] or 0
            row["goals_against"] = row["goals_against"] or 0
            row["goal_difference"] = (
                row["goals_for"] - row["goals_against"]
            )
            row["points"] = 3 * row["won"] + row["drawn"]
            standings.append(row)

        standings.sort(
            key=lambda x: (
                -x["points"],
                -x["goal_difference"],
                -x["goals_for"],
                x["name"].lower()
            )
        )

    return render_template("league.html", standings=standings)


if __name__ == "__main__":
    init_db()
    app.run(debug=True)

