import csv
import io
import os
import re

from flask import Flask, make_response, redirect, render_template, request, url_for
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from db import db, init_app
from models import Game, Person, Player, Round, RoundScore

ROUND_LABELS = [
    "Ace",
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    "10",
    "Jack",
    "Queen",
    "King",
]

MIN_PLAYERS = 3
MAX_PLAYERS = 5
MAX_SCORE = 200

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")
init_app(app)


def round_label(index):
    if 1 <= index <= len(ROUND_LABELS):
        return ROUND_LABELS[index - 1]
    return f"Round {index}"


def compute_ranks(totals):
    if not totals:
        return {}
    unique_totals = sorted(set(totals.values()))
    rank_map = {total: idx + 1 for idx, total in enumerate(unique_totals)}
    return {player_id: rank_map[total] for player_id, total in totals.items()}


def normalize_person_name(name):
    return " ".join(name.split()).strip()


def get_person_names():
    return [person.display_name for person in Person.query.order_by(Person.display_name).all()]


def find_person_by_name(name):
    normalized = normalize_person_name(name)
    if not normalized:
        return None
    return Person.query.filter(func.lower(Person.display_name) == normalized.lower()).first()


def get_or_create_person(name):
    normalized = normalize_person_name(name)
    existing = find_person_by_name(normalized)
    if existing:
        return existing
    person = Person(display_name=normalized)
    db.session.add(person)
    db.session.flush()
    return person


def build_game_context(game):
    players = (
        Player.query.filter_by(game_id=game.id)
        .order_by(Player.sort_order)
        .all()
    )
    palette = ["#0f766e", "#f59e0b", "#2563eb", "#dc2626", "#16a34a"]
    player_style_map = {
        player.id: palette[index % len(palette)] for index, player in enumerate(players)
    }
    player_styles = [
        {"player": player, "color": player_style_map[player.id]} for player in players
    ]
    player_colors = [player_style_map[player.id] for player in players]
    rounds = (
        Round.query.options(joinedload(Round.scores))
        .filter_by(game_id=game.id)
        .order_by(Round.round_index)
        .all()
    )
    scores_by_round = {}
    totals = {player.id: 0 for player in players}
    cumulative_by_player = {player.id: [] for player in players}
    round_totals = []

    for round_item in rounds:
        score_map = {score.player_id: score for score in round_item.scores}
        round_total = 0
        for player in players:
            score_obj = score_map.get(player.id)
            score_value = score_obj.score if score_obj else 0
            totals[player.id] = totals.get(player.id, 0) + score_value
            cumulative_by_player[player.id].append(totals[player.id])
            round_total += score_value
        scores_by_round[round_item.id] = score_map
        round_totals.append(round_total)

    current_round = next(
        (round_item for round_item in rounds if round_item.round_index == game.current_round_index),
        None,
    )
    current_round_scores = scores_by_round.get(current_round.id, {}) if current_round else {}
    current_round_submitted = current_round is not None
    ranks = compute_ranks(totals)

    leader_ids = set()
    last_ids = set()
    if totals:
        min_total = min(totals.values())
        max_total = max(totals.values())
        leader_ids = {player_id for player_id, total in totals.items() if total == min_total}
        last_ids = {player_id for player_id, total in totals.items() if total == max_total}

    winners = []
    if game.finished and totals:
        min_total = min(totals.values())
        winners = [player for player in players if totals[player.id] == min_total]

    overall_total = sum(totals.values()) if totals else 0
    average_round_total = sum(round_totals) / len(round_totals) if round_totals else 0
    leader_total = min(totals.values()) if totals else 0
    last_total = max(totals.values()) if totals else 0
    leader_players = [player for player in players if player.id in leader_ids]
    last_players = [player for player in players if player.id in last_ids]
    score_spread = last_total - leader_total if totals else 0
    best_round = None
    worst_round = None
    best_round_total = 0
    worst_round_total = 0
    if round_totals:
        min_round_total = min(round_totals)
        max_round_total = max(round_totals)
        best_index = round_totals.index(min_round_total)
        worst_index = round_totals.index(max_round_total)
        best_round = rounds[best_index]
        worst_round = rounds[worst_index]
        best_round_total = min_round_total
        worst_round_total = max_round_total

    last_round = rounds[-1] if rounds else None
    last_round_scores = {}
    last_round_average = 0
    last_round_low = 0
    last_round_high = 0
    last_round_low_players = []
    last_round_high_players = []
    last_round_max_score = 1
    went_out_players = []

    if last_round and players:
        score_map = scores_by_round.get(last_round.id, {})
        last_round_scores = {
            player.id: score_map.get(player.id).score if score_map.get(player.id) else 0
            for player in players
        }
        score_values = [last_round_scores[player.id] for player in players]
        last_round_average = sum(score_values) / len(players) if players else 0
        last_round_low = min(score_values) if score_values else 0
        last_round_high = max(score_values) if score_values else 0
        last_round_low_players = [
            player for player in players if last_round_scores[player.id] == last_round_low
        ]
        last_round_high_players = [
            player for player in players if last_round_scores[player.id] == last_round_high
        ]
        went_out_players = [
            player
            for player in players
            if score_map.get(player.id) and score_map[player.id].went_out
        ]
        last_round_max_score = max(last_round_high, 1)

    trend_round_count = len(rounds)
    trend_labels = [f"R{round_item.round_index}" for round_item in rounds]
    trend_datasets = []
    for series in player_styles:
        player = series["player"]
        trend_datasets.append(
            {
                "label": player.name,
                "data": cumulative_by_player[player.id],
                "borderColor": series["color"],
                "backgroundColor": series["color"],
            }
        )

    last_round_labels = [player.name for player in players]
    last_round_values = [last_round_scores.get(player.id, 0) for player in players]

    return {
        "players": players,
        "rounds": rounds,
        "scores_by_round": scores_by_round,
        "totals": totals,
        "round_totals": round_totals,
        "current_round": current_round,
        "current_round_scores": current_round_scores,
        "current_round_label": round_label(game.current_round_index),
        "current_round_index": game.current_round_index,
        "current_round_submitted": current_round_submitted,
        "rounds_completed": len(rounds),
        "ranks": ranks,
        "leader_ids": leader_ids,
        "last_ids": last_ids,
        "winners": winners,
        "overall_total": overall_total,
        "average_round_total": average_round_total,
        "leader_players": leader_players,
        "last_players": last_players,
        "leader_total": leader_total,
        "last_total": last_total,
        "score_spread": score_spread,
        "best_round": best_round,
        "best_round_total": best_round_total,
        "worst_round": worst_round,
        "worst_round_total": worst_round_total,
        "player_style_map": player_style_map,
        "player_styles": player_styles,
        "player_colors": player_colors,
        "last_round": last_round,
        "last_round_scores": last_round_scores,
        "last_round_average": last_round_average,
        "last_round_low": last_round_low,
        "last_round_high": last_round_high,
        "last_round_low_players": last_round_low_players,
        "last_round_high_players": last_round_high_players,
        "last_round_max_score": last_round_max_score,
        "went_out_players": went_out_players,
        "trend_round_count": trend_round_count,
        "trend_labels": trend_labels,
        "trend_datasets": trend_datasets,
        "last_round_labels": last_round_labels,
        "last_round_values": last_round_values,
        "input_values": {},
        "person_names": get_person_names(),
    }


def build_explorer_context(selected_game_id=None):
    games = Game.query.order_by(Game.created_at.desc()).all()
    selected_game = None
    if selected_game_id:
        selected_game = next((game for game in games if game.id == selected_game_id), None)
        if not selected_game:
            selected_game = Game.query.get(selected_game_id)

    game_summaries = []
    for game in games:
        player_count = Player.query.filter_by(game_id=game.id).count()
        game_summaries.append(
            {
                "game": game,
                "player_count": player_count,
            }
        )

    if selected_game:
        players = (
            Player.query.filter_by(game_id=selected_game.id)
            .order_by(Player.sort_order)
            .all()
        )
        rounds = (
            Round.query.options(joinedload(Round.game))
            .filter_by(game_id=selected_game.id)
            .order_by(Round.round_index)
            .all()
        )
        scores = (
            RoundScore.query.options(
                joinedload(RoundScore.player),
                joinedload(RoundScore.round).joinedload(Round.game),
            )
            .join(Round)
            .filter(Round.game_id == selected_game.id)
            .order_by(Round.round_index)
            .all()
        )
    else:
        players = (
            Player.query.options(joinedload(Player.game))
            .order_by(Player.created_at.desc())
            .limit(50)
            .all()
        )
        rounds = (
            Round.query.options(joinedload(Round.game))
            .order_by(Round.created_at.desc())
            .limit(50)
            .all()
        )
        scores = (
            RoundScore.query.options(
                joinedload(RoundScore.player),
                joinedload(RoundScore.round).joinedload(Round.game),
            )
            .order_by(RoundScore.id.desc())
            .limit(50)
            .all()
        )

    return {
        "games": games,
        "game_summaries": game_summaries,
        "selected_game": selected_game,
        "players": players,
        "rounds": rounds,
        "scores": scores,
        "game_count": Game.query.count(),
        "active_games": Game.query.filter_by(archived=False).count(),
        "archived_games": Game.query.filter_by(archived=True).count(),
        "player_count": Player.query.count(),
        "round_count": Round.query.count(),
        "score_count": RoundScore.query.count(),
    }


def build_overall_scoreboard():
    rows = (
        db.session.query(
            Person.id,
            Person.display_name,
            func.coalesce(func.sum(RoundScore.score), 0).label("total_score"),
            func.count(func.distinct(Game.id)).label("games_played"),
            func.count(func.distinct(Round.id)).label("rounds_played"),
        )
        .join(Player, Player.person_id == Person.id)
        .join(RoundScore, RoundScore.player_id == Player.id)
        .join(Round, Round.id == RoundScore.round_id)
        .join(Game, Game.id == Round.game_id)
        .group_by(Person.id)
        .order_by(func.coalesce(func.sum(RoundScore.score), 0))
        .all()
    )

    overall_scores = []
    for index, row in enumerate(rows, start=1):
        rounds_played = row.rounds_played or 0
        average = (row.total_score / rounds_played) if rounds_played else 0
        overall_scores.append(
            {
                "rank": index,
                "name": row.display_name,
                "total_score": int(row.total_score or 0),
                "games_played": row.games_played or 0,
                "rounds_played": rounds_played,
                "avg_per_round": round(average, 1),
            }
        )
    return overall_scores


def collect_score_inputs(form, players):
    errors = []
    entries = []
    values = {}

    for player in players:
        raw_score = form.get(f"score_{player.id}", "").strip()
        went_out = form.get(f"went_out_{player.id}") == "on"
        values[player.id] = {"score": raw_score, "went_out": went_out}

        if raw_score == "":
            errors.append(f"Score required for {player.name}.")
            continue

        try:
            score_value = int(raw_score)
        except ValueError:
            errors.append(f"Score for {player.name} must be a number.")
            continue

        if score_value < 0 or score_value > MAX_SCORE:
            errors.append(
                f"Score for {player.name} must be between 0 and {MAX_SCORE}."
            )
            continue

        entries.append((player, score_value, went_out))

    return entries, errors, values


def slugify(value):
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip()).strip("-")
    return value.lower() or "game"


def is_htmx_request():
    return request.headers.get("HX-Request") is not None


@app.route("/")
def index():
    games = Game.query.filter_by(archived=False).order_by(Game.created_at.desc()).all()
    template = "partials/game_setup_body.html" if is_htmx_request() else "game_setup.html"
    return render_template(
        template,
        games=games,
        overall_scores=build_overall_scoreboard(),
        person_names=get_person_names(),
        player_count=MIN_PLAYERS,
        player_names=["" for _ in range(MIN_PLAYERS)],
        game_name="",
        setup_errors=None,
    )


@app.get("/partials/player_fields")
def player_fields():
    try:
        count = int(request.args.get("player_count", MIN_PLAYERS))
    except ValueError:
        count = MIN_PLAYERS
    count = min(max(count, MIN_PLAYERS), MAX_PLAYERS)
    return render_template(
        "partials/player_fields.html",
        player_count=count,
        player_names=["" for _ in range(count)],
        person_names=get_person_names(),
    )


@app.post("/games")
def create_game():
    game_name = request.form.get("game_name", "").strip()
    player_names = [
        normalize_person_name(name) for name in request.form.getlist("player_names")
    ]
    player_count = len(player_names)
    setup_errors = []

    if not game_name:
        setup_errors.append("Game name is required.")

    if player_count < MIN_PLAYERS or player_count > MAX_PLAYERS:
        setup_errors.append("Please enter between 3 and 5 players.")

    if any(not name for name in player_names):
        setup_errors.append("All player names are required.")

    if setup_errors:
        games = (
            Game.query.filter_by(archived=False)
            .order_by(Game.created_at.desc())
            .all()
        )
        template = (
            "partials/game_setup_body.html" if is_htmx_request() else "game_setup.html"
        )
        return render_template(
            template,
            games=games,
            overall_scores=build_overall_scoreboard(),
            person_names=get_person_names(),
            setup_errors=setup_errors,
            player_count=max(MIN_PLAYERS, min(MAX_PLAYERS, player_count or MIN_PLAYERS)),
            player_names=player_names or ["" for _ in range(MIN_PLAYERS)],
            game_name=game_name,
        )

    game = Game(name=game_name, current_round_index=1, finished=False, archived=False)
    db.session.add(game)
    db.session.flush()

    for index, player_name in enumerate(player_names):
        person = get_or_create_person(player_name)
        db.session.add(
            Player(
                game_id=game.id,
                person_id=person.id,
                name=person.display_name,
                sort_order=index,
            )
        )

    db.session.commit()

    context = build_game_context(game)
    if is_htmx_request():
        response = make_response(
            render_template("partials/dashboard_body.html", game=game, **context)
        )
        response.headers["HX-Push-Url"] = url_for("game_view", game_id=game.id)
        return response
    return redirect(url_for("game_view", game_id=game.id))


@app.get("/game/<int:game_id>")
def game_view(game_id):
    game = Game.query.get_or_404(game_id)
    context = build_game_context(game)
    if is_htmx_request():
        return render_template("partials/dashboard_body.html", game=game, **context)
    return render_template("dashboard.html", game=game, **context)


@app.get("/explorer")
def explorer():
    selected_game_id = request.args.get("game_id", type=int)
    context = build_explorer_context(selected_game_id)
    if is_htmx_request():
        hx_target = request.headers.get("HX-Target")
        if hx_target == "explorer-body":
            return render_template("partials/explorer_content.html", **context)
        return render_template("partials/explorer_body.html", **context)
    return render_template("explorer.html", **context)


@app.post("/game/<int:game_id>/archive")
def archive_game(game_id):
    game = Game.query.get_or_404(game_id)
    game.archived = True
    db.session.commit()
    games = Game.query.filter_by(archived=False).order_by(Game.created_at.desc()).all()
    return render_template("partials/game_list.html", games=games)


@app.post("/game/<int:game_id>/players")
def update_players(game_id):
    game = Game.query.get_or_404(game_id)
    players = (
        Player.query.filter_by(game_id=game.id)
        .order_by(Player.sort_order)
        .all()
    )
    names = [normalize_person_name(name) for name in request.form.getlist("player_names")]

    player_errors = []
    if len(names) != len(players):
        player_errors.append("Please provide a name for every player.")
    if any(not name for name in names):
        player_errors.append("Player names cannot be empty.")

    player_saved = False
    if not player_errors:
        for player, new_name in zip(players, names):
            existing = find_person_by_name(new_name)
            if existing and existing.id != player.person_id:
                player.person_id = existing.id
                player.name = existing.display_name
            else:
                if player.person:
                    player.person.display_name = new_name
                else:
                    player.person = get_or_create_person(new_name)
                player.name = new_name
        db.session.commit()
        player_saved = True

    context = build_game_context(game)
    return render_template(
        "partials/updates_player_editor.html",
        game=game,
        player_errors=player_errors,
        player_saved=player_saved,
        **context,
    )


@app.post("/game/<int:game_id>/rounds")
def submit_round(game_id):
    game = Game.query.get_or_404(game_id)
    players = (
        Player.query.filter_by(game_id=game.id)
        .order_by(Player.sort_order)
        .all()
    )

    if game.finished:
        context = build_game_context(game)
        context.update(
            {
                "game": game,
                "round_errors": ["Game is finished. Unlock to continue."],
                "input_values": {},
                "current_round_submitted": True,
            }
        )
        return render_template("partials/round_entry.html", **context)

    submitted_index = request.form.get("round_index", "")
    if submitted_index and submitted_index.isdigit():
        submitted_index = int(submitted_index)
        if submitted_index != game.current_round_index:
            context = build_game_context(game)
            context.update(
                {
                    "game": game,
                    "round_errors": [
                        "This round is no longer current. Refresh and try again."
                    ],
                    "input_values": {},
                    "current_round_submitted": False,
                }
            )
            return render_template("partials/round_entry.html", **context)

    existing_round = Round.query.filter_by(
        game_id=game.id, round_index=game.current_round_index
    ).first()
    if existing_round:
        context = build_game_context(game)
        context.update(
            {
                "game": game,
                "round_errors": ["This round has already been submitted."],
                "input_values": {},
                "current_round_submitted": True,
            }
        )
        return render_template("partials/round_entry.html", **context)

    entries, round_errors, values = collect_score_inputs(request.form, players)
    if round_errors:
        context = build_game_context(game)
        context.update(
            {
                "game": game,
                "round_errors": round_errors,
                "input_values": values,
                "current_round_submitted": False,
            }
        )
        return render_template("partials/round_entry.html", **context)

    round_name = round_label(game.current_round_index)
    round_item = Round(
        game_id=game.id,
        round_index=game.current_round_index,
        round_name=round_name,
    )
    db.session.add(round_item)
    db.session.flush()

    for player, score_value, went_out in entries:
        db.session.add(
            RoundScore(
                round_id=round_item.id,
                player_id=player.id,
                score=score_value,
                went_out=went_out,
            )
        )

    if game.current_round_index >= len(ROUND_LABELS):
        game.finished = True
    else:
        game.current_round_index += 1

    db.session.commit()

    context = build_game_context(game)
    return render_template("partials/updates_round_entry.html", game=game, **context)


@app.get("/game/<int:game_id>/round_history")
def round_history(game_id):
    game = Game.query.get_or_404(game_id)
    context = build_game_context(game)
    return render_template("partials/round_history.html", game=game, **context)


@app.get("/game/<int:game_id>/round/<int:round_id>/edit")
def edit_round_form(game_id, round_id):
    game = Game.query.get_or_404(game_id)
    round_item = (
        Round.query.options(joinedload(Round.scores))
        .filter_by(id=round_id, game_id=game.id)
        .first_or_404()
    )
    players = (
        Player.query.filter_by(game_id=game.id)
        .order_by(Player.sort_order)
        .all()
    )
    scores_by_player = {score.player_id: score for score in round_item.scores}
    return render_template(
        "partials/round_edit_row.html",
        game=game,
        round_item=round_item,
        players=players,
        scores_by_player=scores_by_player,
        input_values={},
        edit_errors=None,
    )


@app.get("/game/<int:game_id>/round/<int:round_id>/row")
def round_row(game_id, round_id):
    game = Game.query.get_or_404(game_id)
    round_item = (
        Round.query.options(joinedload(Round.scores))
        .filter_by(id=round_id, game_id=game.id)
        .first_or_404()
    )
    context = build_game_context(game)
    context.update(
        {
            "game": game,
            "round_item": round_item,
            "score_map": context["scores_by_round"].get(round_item.id, {}),
        }
    )
    return render_template("partials/round_history_row.html", **context)


@app.post("/game/<int:game_id>/round/<int:round_id>/edit")
def edit_round(game_id, round_id):
    game = Game.query.get_or_404(game_id)
    round_item = (
        Round.query.options(joinedload(Round.scores))
        .filter_by(id=round_id, game_id=game.id)
        .first_or_404()
    )
    players = (
        Player.query.filter_by(game_id=game.id)
        .order_by(Player.sort_order)
        .all()
    )
    scores_by_player = {score.player_id: score for score in round_item.scores}

    entries, edit_errors, values = collect_score_inputs(request.form, players)
    if edit_errors:
        return render_template(
            "partials/round_edit_row.html",
            game=game,
            round_item=round_item,
            players=players,
            scores_by_player=scores_by_player,
            input_values=values,
            edit_errors=edit_errors,
        )

    for player, score_value, went_out in entries:
        score_obj = scores_by_player.get(player.id)
        if score_obj:
            score_obj.score = score_value
            score_obj.went_out = went_out
        else:
            db.session.add(
                RoundScore(
                    round_id=round_item.id,
                    player_id=player.id,
                    score=score_value,
                    went_out=went_out,
                )
            )

    db.session.commit()
    context = build_game_context(game)
    context.update(
        {
            "game": game,
            "round_item": round_item,
            "score_map": context["scores_by_round"].get(round_item.id, {}),
        }
    )
    return render_template("partials/updates_round_row.html", **context)


@app.post("/game/<int:game_id>/rounds/undo")
def undo_round(game_id):
    game = Game.query.get_or_404(game_id)
    last_round = (
        Round.query.filter_by(game_id=game.id)
        .order_by(Round.round_index.desc())
        .first()
    )

    history_message = None
    if not last_round:
        history_message = "There are no rounds to undo yet."
    else:
        last_index = last_round.round_index
        db.session.delete(last_round)

        game.finished = False
        if last_index <= 1:
            game.current_round_index = 1
        else:
            game.current_round_index = last_index

        db.session.commit()

    context = build_game_context(game)
    return render_template(
        "partials/updates_round_history.html",
        game=game,
        history_message=history_message,
        **context,
    )


@app.post("/game/<int:game_id>/unlock")
def unlock_game(game_id):
    game = Game.query.get_or_404(game_id)
    game.finished = False
    db.session.commit()
    context = build_game_context(game)
    return render_template(
        "partials/updates_round_entry.html",
        game=game,
        **context,
    )


@app.get("/game/<int:game_id>/export.csv")
def export_csv(game_id):
    game = Game.query.get_or_404(game_id)
    players = (
        Player.query.filter_by(game_id=game.id)
        .order_by(Player.sort_order)
        .all()
    )
    rounds = (
        Round.query.options(joinedload(Round.scores))
        .filter_by(game_id=game.id)
        .order_by(Round.round_index)
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Round", "Player", "Score", "Went Out"])

    for round_item in rounds:
        score_map = {score.player_id: score for score in round_item.scores}
        for player in players:
            score_obj = score_map.get(player.id)
            writer.writerow(
                [
                    round_item.round_name,
                    player.name,
                    score_obj.score if score_obj else "",
                    "yes" if score_obj and score_obj.went_out else "",
                ]
            )

    filename = f"{slugify(game.name)}-scores.csv"
    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv"
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response
