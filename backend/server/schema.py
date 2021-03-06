import graphene
from graphene_django.types import DjangoObjectType

from server.models import Prediction, MLModel, TeamMatch, Match, Team


class TeamType(DjangoObjectType):
    class Meta:
        model = Team


class MatchType(DjangoObjectType):
    class Meta:
        model = Match

    winner = graphene.Field(TeamType, id=graphene.Int(), name=graphene.String())
    year = graphene.Int()


class TeamMatchType(DjangoObjectType):
    class Meta:
        model = TeamMatch


class MLModelType(DjangoObjectType):
    class Meta:
        model = MLModel


class PredictionType(DjangoObjectType):
    class Meta:
        model = Prediction

    is_correct = graphene.Boolean()


class Query(graphene.ObjectType):
    predictions = graphene.List(PredictionType, year=graphene.Int(default_value=None))

    def resolve_predictions(self, _info, year=None):  # pylint: disable=R0201
        if year is None:
            return Prediction.objects.all()

        return Prediction.objects.filter(match__start_date_time__year=year)


schema = graphene.Schema(query=Query)
