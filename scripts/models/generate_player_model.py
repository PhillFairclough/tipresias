"""Script for generating the pickle file for the PlayerXGB estimator"""

import os
import sys

PROJECT_PATH: str = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../')
)

if PROJECT_PATH not in sys.path:
    sys.path.append(PROJECT_PATH)

from server.ml_models import PlayerXGB
from server.ml_models.player_xgb import PlayerXGBData


def main():
    data = PlayerXGBData()
    estimator = PlayerXGB()
    estimator.fit(*data.train_data())
    estimator.save()


if __name__ == '__main__':
    main()
