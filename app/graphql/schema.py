import strawberry
from strawberry.types import Info

from app.graphql.resolvers import resolve_create_client, resolve_health
from app.graphql.types import ClientType, CreateClientInput


@strawberry.type
class Query:
    health: str = strawberry.field(resolver=resolve_health)


@strawberry.type
class Mutation:
    @strawberry.mutation
    def create_client(self, info: Info, input: CreateClientInput) -> ClientType:
        return resolve_create_client(info, input)


schema = strawberry.Schema(query=Query, mutation=Mutation)
