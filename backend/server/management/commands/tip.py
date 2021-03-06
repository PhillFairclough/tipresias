"""Module for 'tip' command that updates predictions for upcoming AFL matches"""

import os
from functools import partial, reduce
from pydoc import locate
from datetime import datetime
from typing import List, Optional
from mypy_extensions import TypedDict
from django.core.management.base import BaseCommand
from django import utils
import pandas as pd
import numpy as np
from sklearn.externals import joblib

from project.settings.common import BASE_DIR
from server.data_readers import FootywireDataReader
from server.models import Match, TeamMatch, Team, MLModel, Prediction
from server.ml_models import (
    BettingModel,
    MatchModel,
    PlayerModel,
    AllModel,
    EnsembleModel,
)
from server.ml_models.betting_model import BettingModelData
from server.ml_models.match_model import MatchModelData
from server.ml_models.player_model import PlayerModelData
from server.ml_models.all_model import AllModelData

FixtureData = TypedDict(
    "FixtureData",
    {
        "date": pd.Timestamp,
        "season": int,
        "season_game": int,
        "round": int,
        "home_team": str,
        "away_team": str,
        "venue": str,
    },
)

NO_SCORE = 0
ML_MODELS = [
    (BettingModel(name="betting_data"), BettingModelData),
    (MatchModel(name="match_data"), MatchModelData),
    (PlayerModel(name="player_data"), PlayerModelData),
    (AllModel(name="all_data"), AllModelData),
    (EnsembleModel(name="avg_predictions"), AllModelData),
]


class Command(BaseCommand):
    """manage.py command for 'tip' that updates predictions for upcoming AFL matches"""

    help = """
    Check if there are upcoming AFL matches and make predictions on results
    for all unplayed matches in the upcoming/current round.
    """

    def __init__(self, *args, data_reader=FootywireDataReader(), **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.data_reader = data_reader
        # Fixture data uses UTC
        self.right_now = datetime.now()
        self.current_year = self.right_now.year

    def handle(self, *_args, verbose=1, **_kwargs) -> None:  # pylint: disable=W0221
        """Run 'tip' command"""

        self.verbose = verbose  # pylint: disable=W0201

        fixture_data_frame = self.__fetch_fixture_data(self.current_year)

        if fixture_data_frame is None:
            raise ValueError("Could not fetch data.")

        fixture_rounds = fixture_data_frame["round"]
        upcoming_round = fixture_rounds[
            fixture_data_frame["date"] > self.right_now
        ].min()
        saved_match_count = Match.objects.filter(
            start_date_time__gt=self.right_now
        ).count()

        if self.verbose == 1:
            if saved_match_count == 0:
                print(
                    f"No existing match records found for round {upcoming_round}. "
                    "Creating new match and prediction records...\n"
                )
            else:
                print(
                    f"{saved_match_count} unplayed match records found for round {upcoming_round}. "
                    "Updating associated prediction records with new model predictions."
                )

        upcoming_fixture = fixture_data_frame[
            (fixture_data_frame["round"] == upcoming_round)
            & (fixture_data_frame["date"] > self.right_now)
        ]

        if self.verbose == 1:
            print(f"Saving Match and TeamMatch records for round {upcoming_round}...\n")

        self.__create_matches(upcoming_fixture.to_dict("records"))

        upcoming_round_year = fixture_data_frame["date"].map(lambda x: x.year).max()

        self.__make_predictions(upcoming_round_year, round_number=upcoming_round)

        if self.verbose == 1:
            print("Match and prediction data were updated!\n")

        return None

    def __fetch_fixture_data(self, year: int) -> pd.DataFrame:
        if self.verbose == 1:
            print(f"Fetching fixture for {year}...\n")

        fixture_data_frame = self.data_reader.get_fixture(
            year_range=(year, year + 1), fresh_data=True
        )
        latest_match = fixture_data_frame["date"].max()

        if self.right_now > latest_match:
            print(
                f"No unplayed matches found in {year}. We will try to fetch "
                f"fixture for {year + 1}.\n"
            )

            fixture_data_frame = self.data_reader.get_fixture(
                year_range=(year + 1, year + 2), fresh_data=True
            )
            latest_match = fixture_data_frame["date"].max()

            if self.right_now > latest_match:
                raise ValueError(
                    f"No unplayed matches found in {year + 1}, and we're not going "
                    "to keep trying. Please try a season that hasn't been completed.\n"
                )

        return fixture_data_frame

    def __create_matches(self, fixture_data: List[FixtureData]) -> None:
        if not any(fixture_data):
            raise ValueError("No fixture data found.")

        round_number = set([match_data["round"] for match_data in fixture_data]).pop()
        year = set([match_data["season"] for match_data in fixture_data]).pop()

        team_match_lists = [
            self.__build_match(match_data) for match_data in fixture_data
        ]

        compacted_team_match_lists = [
            team_match_list
            for team_match_list in team_match_lists
            if team_match_list is not None
        ]

        team_matches_to_save: List[TeamMatch] = reduce(
            lambda acc_list, curr_list: acc_list + curr_list,
            compacted_team_match_lists,
            [],
        )

        team_match_count = TeamMatch.objects.filter(
            match__start_date_time__year=year, match__round_number=round_number
        ).count()

        if not any(team_matches_to_save) and team_match_count == 0:
            raise ValueError("Something went wrong, and no team matches were saved.\n")

        TeamMatch.objects.bulk_create(team_matches_to_save)

        if self.verbose == 1:
            print("Match data saved!\n")

    def __build_match(self, match_data: FixtureData) -> Optional[List[TeamMatch]]:
        raw_date = match_data["date"].to_pydatetime()

        # 'make_aware' raises error if datetime already has a timezone
        if raw_date.tzinfo is None or raw_date.tzinfo.utcoffset(raw_date) is None:
            match_date = utils.timezone.make_aware(raw_date)
        else:
            match_date = raw_date

        match, was_created = Match.objects.get_or_create(
            start_date_time=match_date,
            round_number=int(match_data["round"]),
            venue=match_data["venue"],
        )

        if was_created:
            match.full_clean()

        return self.__build_team_match(match, match_data)

    def __make_predictions(
        self,
        year: int,
        ml_models: Optional[List[MLModel]] = None,
        round_number: Optional[int] = None,
    ) -> None:
        matches_to_predict = Match.objects.filter(
            start_date_time__gt=self.right_now, round_number=round_number
        )

        ml_models = ml_models or MLModel.objects.all()

        if ml_models is None:
            raise ValueError(
                "Could not find any ML models in DB to make predictions.\n"
            )

        make_model_predictions = partial(
            self.__make_model_predictions,
            year,
            matches_to_predict,
            round_number=round_number,
        )

        prediction_lists = [make_model_predictions(ml_model) for ml_model in ml_models]
        predictions: List[Optional[Prediction]] = reduce(
            lambda acc_list, curr_list: acc_list + curr_list, prediction_lists, []
        )
        predictions_to_save = [pred for pred in predictions if pred is not None]

        Prediction.objects.bulk_create(predictions_to_save)

        if self.verbose == 1:
            print("Predictions saved!\n")

    def __make_model_predictions(
        self,
        year: int,
        matches: List[Match],
        ml_model_record: MLModel,
        round_number: Optional[int] = None,
    ) -> List[Optional[Prediction]]:
        loaded_model = joblib.load(os.path.join(BASE_DIR, ml_model_record.filepath))
        data_class = locate(ml_model_record.data_class_path)
        data = data_class(test_years=(year, year))

        X_test, _ = data.test_data(test_round=round_number)
        y_pred = loaded_model.predict(X_test)

        data_row_slice = (slice(None), year, slice(round_number, round_number))
        prediction_data = data.data.loc[data_row_slice, :].assign(
            predicted_margin=y_pred
        )

        build_match_prediction = partial(
            self.__build_match_prediction, ml_model_record, prediction_data
        )

        return [build_match_prediction(match) for match in matches]

    @staticmethod
    def __build_match_prediction(
        ml_model_record: MLModel, prediction_data: pd.DataFrame, match: Match
    ) -> Optional[Prediction]:
        home_team = match.teammatch_set.get(at_home=True).team
        away_team = match.teammatch_set.get(at_home=False).team

        predicted_home_margin = prediction_data.xs(home_team.name, level=0)[
            "predicted_margin"
        ].iloc[0]
        predicted_away_margin = prediction_data.xs(away_team.name, level=0)[
            "predicted_margin"
        ].iloc[0]

        # predicted_margin is always positive as its always associated with predicted_winner
        predicted_margin = np.mean(
            np.abs([predicted_home_margin, predicted_away_margin])
        )

        if predicted_home_margin > predicted_away_margin:
            predicted_winner = home_team
        elif predicted_away_margin > predicted_home_margin:
            predicted_winner = away_team
        else:
            raise ValueError(
                "Predicted home and away margins are equal, which is basically impossible, "
                "so figure out what's going on:\n"
                f"home_team = {home_team.name}\n"
                f"away_team = {away_team.name}\n"
                f"data = {prediction_data}"
            )

        prediction_attributes = {"match": match, "ml_model": ml_model_record}

        try:
            prediction = Prediction.objects.get(**prediction_attributes)

            prediction.predicted_margin = predicted_margin
            prediction.predicted_winner = predicted_winner

            prediction.clean_fields()
            prediction.clean()
            prediction.save()

            return None
        except Prediction.DoesNotExist:
            prediction = Prediction(
                predicted_margin=predicted_margin,
                predicted_winner=predicted_winner,
                **prediction_attributes,
            )

            return prediction

    @staticmethod
    def __build_team_match(
        match: Match, match_data: FixtureData
    ) -> Optional[List[TeamMatch]]:
        team_match_count = match.teammatch_set.count()

        if team_match_count == 2:
            return None

        if team_match_count == 1 or team_match_count > 2:
            model_string = "TeamMatches" if team_match_count > 1 else "TeamMatch"
            raise ValueError(
                f"{match} has {team_match_count} associated {model_string}, which shouldn't "
                "happen. Figure out what's up."
            )
        home_team = Team.objects.get(name=match_data["home_team"])
        away_team = Team.objects.get(name=match_data["away_team"])

        home_team_match = TeamMatch(
            team=home_team, match=match, at_home=True, score=NO_SCORE
        )
        away_team_match = TeamMatch(
            team=away_team, match=match, at_home=False, score=NO_SCORE
        )

        home_team_match.clean_fields()
        home_team_match.clean()
        away_team_match.clean_fields()
        away_team_match.clean()

        return [home_team_match, away_team_match]
