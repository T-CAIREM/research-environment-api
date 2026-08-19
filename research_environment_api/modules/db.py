import functools

import pg8000
import sqlalchemy
from google.auth.credentials import Credentials
from google.cloud.sql.connector import Connector, IPTypes


# HACK: The connector needs to be instantiated lazily due to issues with it's internal asyncio loop
# hanging indefinitely when it's instantiated in the main thread in Celery.
@functools.cache
def cloud_sql_connector(credentials: Credentials) -> Connector:
    return Connector(credentials=credentials, enable_iam_auth=True)


def create_cloud_sql_engine(
    service_account_credentials: Credentials,
    instance_connection_name: str,
    database_name: str,
) -> sqlalchemy.engine.base.Engine:
    def getconn() -> pg8000.dbapi.Connection:
        iam_service_account_user = (
            service_account_credentials.service_account_email.removesuffix(
                ".gserviceaccount.com"
            )
        )
        conn: pg8000.dbapi.Connection = cloud_sql_connector(
            service_account_credentials
        ).connect(
            instance_connection_name,
            "pg8000",
            user=iam_service_account_user,
            db=database_name,
            ip_type=IPTypes.PUBLIC,
        )
        return conn

    engine = sqlalchemy.create_engine(
        "postgresql+pg8000://",
        creator=getconn,
        echo=True,
        # Cloud SQL closes pooled connections out from under us: IAM auth tokens
        # expire after roughly an hour, and idle sockets get reaped by the network
        # in between. Without these two options SQLAlchemy hands the dead socket to
        # the next request, which surfaces as `SSLEOFError` -> `pg8000
        # InterfaceError: network error` and a 500 rather than a retry.
        # pre_ping validates on checkout and transparently replaces a dead
        # connection; recycle retires connections before the token can expire.
        pool_pre_ping=True,
        pool_recycle=1800,
    )
    return engine


def create_sql_engine(database_url: str) -> sqlalchemy.engine.base.Engine:
    return sqlalchemy.create_engine(
        database_url,
        echo=True,
        pool_pre_ping=True,
        pool_recycle=1800,
    )
