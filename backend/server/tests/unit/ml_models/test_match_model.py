from unittest import TestCase
from unittest.mock import Mock
import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import make_pipeline
from faker import Faker

from project.settings.common import BASE_DIR

from server.ml_models import MatchModel
from server.ml_models.match_model import MatchModelData

FAKE = Faker()

match_results_df = pd.read_csv(
    f"{BASE_DIR}/server/tests/fixtures/fitzroy_match_results.csv"
)
match_results_mock = Mock(return_value=match_results_df)


class TestMatchModel(TestCase):
    def setUp(self):
        teams = [FAKE.company()] * 10
        data_frame = pd.DataFrame(
            {
                "team": teams,
                "oppo_team": list(reversed(teams)),
                "round_type": ["Regular"] * 10,
                "year": ([2014] * 2) + ([2015] * 6) + ([2016] * 2),
                "score": np.random.randint(50, 150, 10),
                "oppo_score": np.random.randint(50, 150, 10),
                "round_number": 15,
            }
        )
        self.X = data_frame.drop("oppo_score", axis=1)
        self.y = data_frame["oppo_score"]
        pipeline = make_pipeline(
            ColumnTransformer(
                [
                    (
                        "onehot",
                        OneHotEncoder(sparse=False),
                        ["team", "oppo_team", "round_type"],
                    )
                ],
                remainder="passthrough",
            ),
            Ridge(),
        )
        self.model = MatchModel(pipeline=pipeline)

    def test_predict(self):
        self.model.fit(self.X, self.y)
        predictions = self.model.predict(self.X)

        self.assertIsInstance(predictions, np.ndarray)


class TestMatchModelData(TestCase):
    def setUp(self):
        self.data = MatchModelData(data_readers=[match_results_mock])

    def test_train_data(self):
        X_train, y_train = self.data.train_data()

        self.assertIsInstance(X_train, pd.DataFrame)
        self.assertIsInstance(y_train, pd.Series)
        self.assertNotIn("score", X_train.columns)
        self.assertNotIn("oppo_score", X_train.columns)
        self.assertNotIn("goals", X_train.columns)
        self.assertNotIn("oppo_goals", X_train.columns)
        self.assertNotIn("behinds", X_train.columns)
        self.assertNotIn("oppo_behinds", X_train.columns)
        self.assertNotIn("margin", X_train.columns)
        self.assertNotIn("result", X_train.columns)

        # Applying StandardScaler to integer columns raises a warning
        self.assertFalse(
            any([X_train[column].dtype == int for column in X_train.columns])
        )

    def test_test_data(self):
        X_test, y_test = self.data.test_data()

        self.assertIsInstance(X_test, pd.DataFrame)
        self.assertIsInstance(y_test, pd.Series)
        self.assertNotIn("score", X_test.columns)
        self.assertNotIn("oppo_score", X_test.columns)
        self.assertNotIn("goals", X_test.columns)
        self.assertNotIn("oppo_goals", X_test.columns)
        self.assertNotIn("behinds", X_test.columns)
        self.assertNotIn("oppo_behinds", X_test.columns)
        self.assertNotIn("result", X_test.columns)

        # Applying StandardScaler to integer columns raises a warning
        self.assertFalse(
            any([X_test[column].dtype == int for column in X_test.columns])
        )

    def test_train_test_data_compatibility(self):
        self.maxDiff = None

        X_train, _ = self.data.train_data()
        X_test, _ = self.data.test_data()

        self.assertCountEqual(list(X_train.columns), list(X_test.columns))
