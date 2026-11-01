"""Football Manager - Flask + SQLite.

Runs three ways from the same code:
  * python app.py            -> development server in the browser
  * desktop.py (PyInstaller) -> Windows .exe in its own window
  * main.py (Buildozer)      -> Android .apk with a WebView
"""
import os
import secrets
import sqlite3
import sys
from contextlib import contextmanager
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, url_for


def resource_dir() -> Path:
    """Folder holding templates/static (inside the bundle when frozen)."""
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def data_dir() -> Path:
    """Writable folder for the database (never the PyInstaller temp folder)."""
    override = os.environ.get("FOOTBALL_DATA_DIR")
    if override:
        path = Path(override)
    elif os.environ.get("ANDROID_PRIVATE"):
        path = Path(os.environ["ANDROID_PRIVATE"])
    elif getattr(sys, "frozen", False):
        path = Path(os.environ.get("APPDATA") or Path.home()) / "FootballManager"
    else:
        path = Path(__file__).resolve().parent
    path.mkdir(parents=True, exist_ok=True)
    return path


DATA_DIR = data_dir()
DATABASE = DATA_DIR / "football.db"


def get_secret_key() -> str:
    env_key = os.environ.get("SECRET_KEY")
    if env_key:
        return env_key
    key_file = DATA_DIR / "secret.key"
    if not key_file.exists():
        key_file.write_text(secrets.token_hex(32))
    return key_file.read_text().strip()


app = Flask(
    __name__,
    template_folder=str(resource_dir() / "templates"),
    static_folder=str(resource_dir() / "static"),
)
app.secret_key = get_secret_key()

POSITIONS = ["Goalkeeper", "Defender", "Midfielder", "Forward"]


@contextmanager
def db():
    """Open a connection, commit on success, always close."""
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db():
    with db() as conn:
        conn.executescript("""
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
                FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE RESTRICT
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
                FOREIGN KEY (fixture_id) REFERENCES fixtures(id) ON DELETE CASCADE,
                CHECK (home_goals >= 0),
                CHECK (away_goals >= 0)
            );
        """)


# Create tables whenever the module is imported (exe, apk or flask run).
init_db()


@app.template_filter("fmt_date")
def fmt_date(value):
    return (value or "").replace("T", " ")


FIXTURE_SELECT = """
    SELECT f.*, h.name AS home_name, a.name AS away_name
    FROM fixtures f
    JOIN teams h ON f.home_team = h.id
    JOIN teams a ON f.away_team = a.id
"""


# ---------------------------------------------------------------- dashboard
@app.route("/")
def index():
    with db() as conn:
        counts = {
            name: conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
            for name in ("players", "teams", "fixtures", "results")
        }
        upcoming = conn.execute(
            FIXTURE_SELECT
            + " WHERE f.status = 'Scheduled' ORDER BY f.match_date LIMIT 5"
        ).fetchall()
        recent = conn.execute("""
            SELECT r.*, f.match_date, h.name AS home_name, a.name AS away_name
            FROM results r
            JOIN fixtures f ON r.fixture_id = f.id
            JOIN teams h ON f.home_team = h.id
            JOIN teams a ON f.away_team = a.id
            ORDER BY f.match_date DESC LIMIT 5
        """).fetchall()
    return render_template(
        "index.html",
        players_count=counts["players"],
        teams_count=counts["teams"],
        fixtures_count=counts["fixtures"],
        results_count=counts["results"],
        upcoming=upcoming,
        recent=recent,
    )


# ------------------------------------------------------------------ players
@app.route("/players", methods=["GET", "POST"])
def players():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        position = request.form.get("position", "").strip()
        team_id = request.form.get("team_id", type=int)
        jersey_text = request.form.get("jersey_number", "").strip()
        try:
            jersey = int(jersey_text) if jersey_text else None
        except ValueError:
            flash("Jersey number must be a whole number.", "error")
            return redirect(url_for("players"))

        with db() as conn:
            try:
                if not full_name or position not in POSITIONS or not team_id:
                    raise ValueError("Complete all required fields.")
                if jersey is not None and not 1 <= jersey <= 99:
                    raise ValueError("Jersey number must be between 1 and 99.")
                if jersey is not None and conn.execute(
                    "SELECT 1 FROM players WHERE team_id = ? AND jersey_number = ?",
                    (team_id, jersey),
                ).fetchone():
                    raise ValueError("That jersey number is already taken in this team.")
                conn.execute(
                    "INSERT INTO players (full_name, jersey_number, position, team_id)"
                    " VALUES (?, ?, ?, ?)",
                    (full_name, jersey, position, team_id),
                )
                flash("Player registered successfully.", "success")
            except ValueError as error:
                flash(str(error), "error")
            except sqlite3.IntegrityError:
                flash("Select a valid team.", "error")
        return redirect(url_for("players"))

    team_filter = request.args.get("team", type=int)
    with db() as conn:
        query = """
            SELECT p.*, t.name AS team_name
            FROM players p JOIN teams t ON p.team_id = t.id
        """
        params = ()
        if team_filter:
            query += " WHERE p.team_id = ?"
            params = (team_filter,)
        player_list = conn.execute(query + " ORDER BY t.name, p.full_name", params).fetchall()
        team_list = conn.execute("SELECT * FROM teams ORDER BY name").fetchall()
    return render_template(
        "players.html",
        players=player_list,
        teams=team_list,
        positions=POSITIONS,
        team_filter=team_filter,
    )


@app.post("/players/<int:player_id>/delete")
def delete_player(player_id):
    with db() as conn:
        conn.execute("DELETE FROM players WHERE id = ?", (player_id,))
    flash("Player removed.", "success")
    return redirect(url_for("players"))


# -------------------------------------------------------------------- teams
@app.route("/teams", methods=["GET", "POST"])
def teams():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Enter a team name.", "error")
        else:
            with db() as conn:
                try:
                    conn.execute("INSERT INTO teams (name) VALUES (?)", (name,))
                    flash("Team added successfully.", "success")
                except sqlite3.IntegrityError:
                    flash("That team already exists.", "error")
        return redirect(url_for("teams"))

    with db() as conn:
        team_list = conn.execute("""
            SELECT t.*, COUNT(p.id) AS player_count
            FROM teams t LEFT JOIN players p ON t.id = p.team_id
            GROUP BY t.id ORDER BY t.name
        """).fetchall()
    return render_template("teams.html", teams=team_list)


@app.post("/teams/<int:team_id>/delete")
def delete_team(team_id):
    with db() as conn:
        try:
            conn.execute("DELETE FROM teams WHERE id = ?", (team_id,))
            flash("Team removed.", "success")
        except sqlite3.IntegrityError:
            flash("Remove this team's players and fixtures first.", "error")
    return redirect(url_for("teams"))


# ----------------------------------------------------------------- fixtures
@app.route("/fixtures", methods=["GET", "POST"])
def fixtures():
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
            with db() as conn:
                try:
                    conn.execute(
                        "INSERT INTO fixtures (home_team, away_team, match_date, venue)"
                        " VALUES (?, ?, ?, ?)",
                        (home, away, match_date, venue),
                    )
                    flash("Fixture scheduled successfully.", "success")
                except sqlite3.IntegrityError:
                    flash("Select valid teams.", "error")
        return redirect(url_for("fixtures"))

    with db() as conn:
        team_list = conn.execute("SELECT * FROM teams ORDER BY name").fetchall()
        fixture_list = conn.execute(
            FIXTURE_SELECT + " ORDER BY f.match_date DESC"
        ).fetchall()
    return render_template("fixtures.html", fixtures=fixture_list, teams=team_list)


@app.post("/fixtures/<int:fixture_id>/delete")
def delete_fixture(fixture_id):
    with db() as conn:
        conn.execute("DELETE FROM fixtures WHERE id = ?", (fixture_id,))
    flash("Fixture removed.", "success")
    return redirect(url_for("fixtures"))


# ------------------------------------------------------------------ results
@app.route("/results", methods=["GET", "POST"])
def results():
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
            with db() as conn:
                fixture = conn.execute(
                    "SELECT id FROM fixtures WHERE id = ?", (fixture_id,)
                ).fetchone()
                if fixture is None:
                    flash("Fixture not found.", "error")
                else:
                    conn.execute("""
                        INSERT INTO results (fixture_id, home_goals, away_goals)
                        VALUES (?, ?, ?)
                        ON CONFLICT(fixture_id) DO UPDATE SET
                            home_goals = excluded.home_goals,
                            away_goals = excluded.away_goals
                    """, (fixture_id, home_goals, away_goals))
                    conn.execute(
                        "UPDATE fixtures SET status = 'Completed' WHERE id = ?",
                        (fixture_id,),
                    )
                    flash("Match result saved.", "success")
        return redirect(url_for("results"))

    with db() as conn:
        pending = conn.execute(
            FIXTURE_SELECT
            + " LEFT JOIN results r ON f.id = r.fixture_id"
            " WHERE r.id IS NULL ORDER BY f.match_date"
        ).fetchall()
        result_list = conn.execute("""
            SELECT r.*, f.match_date, h.name AS home_name, a.name AS away_name
            FROM results r
            JOIN fixtures f ON r.fixture_id = f.id
            JOIN teams h ON f.home_team = h.id
            JOIN teams a ON f.away_team = a.id
            ORDER BY f.match_date DESC
        """).fetchall()
    return render_template("results.html", pending=pending, results=result_list)


@app.post("/results/<int:result_id>/delete")
def delete_result(result_id):
    with db() as conn:
        row = conn.execute(
            "SELECT fixture_id FROM results WHERE id = ?", (result_id,)
        ).fetchone()
        if row:
            conn.execute("DELETE FROM results WHERE id = ?", (result_id,))
            conn.execute(
                "UPDATE fixtures SET status = 'Scheduled' WHERE id = ?",
                (row["fixture_id"],),
            )
    flash("Result removed; the fixture is open again.", "success")
    return redirect(url_for("results"))


# ------------------------------------------------------------------- league
@app.route("/league")
def league():
    with db() as conn:
        teams_rows = conn.execute("SELECT id, name FROM teams").fetchall()
        match_rows = conn.execute("""
            SELECT f.home_team, f.away_team, r.home_goals, r.away_goals
            FROM results r JOIN fixtures f ON r.fixture_id = f.id
        """).fetchall()

    table = {
        t["id"]: {
            "id": t["id"], "name": t["name"], "played": 0, "won": 0, "drawn": 0,
            "lost": 0, "goals_for": 0, "goals_against": 0,
        }
        for t in teams_rows
    }
    for m in match_rows:
        for team_id, scored, conceded in (
            (m["home_team"], m["home_goals"], m["away_goals"]),
            (m["away_team"], m["away_goals"], m["home_goals"]),
        ):
            row = table[team_id]
            row["played"] += 1
            row["goals_for"] += scored
            row["goals_against"] += conceded
            if scored > conceded:
                row["won"] += 1
            elif scored == conceded:
                row["drawn"] += 1
            else:
                row["lost"] += 1

    standings = list(table.values())
    for row in standings:
        row["goal_difference"] = row["goals_for"] - row["goals_against"]
        row["points"] = 3 * row["won"] + row["drawn"]
    standings.sort(key=lambda x: (-x["points"], -x["goal_difference"],
                                  -x["goals_for"], x["name"].lower()))
    return render_template("league.html", standings=standings)


if __name__ == "__main__":
    app.run(debug=True)
