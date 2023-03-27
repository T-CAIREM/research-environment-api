from typing import Iterable

from google.cloud import datastore


def find_by(project_id: str, kind: str, **filters: dict) -> Iterable[datastore.Entity]:
    client = datastore.Client(project_id)
    query = client.query(kind=kind)
    filters = [datastore.query.PropertyFilter(k, "=", v) for k, v in filters.items()]
    for filter in filters:
        query.add_filter(filter=filter)

    return query.fetch()


def persist(project_id: str, kind: str, data: dict):
    client = datastore.Client(project_id)
    entity_key = client.key(kind)
    entity = datastore.Entity(key=entity_key)
    entity.update(data)
    client.put(entity)


def update(project_id: str, kind: str, data: dict):
    client = datastore.Client(project_id)
    entity_key = client.key(kind)
