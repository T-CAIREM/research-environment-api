import threading

import pg8000
import sqlalchemy
from google.auth.credentials import Credentials
from google.cloud.sql.connector import Connector, IPTypes

lock = threading.Lock()


def create_cloud_sql_engine(
    service_account_credentials: Credentials,
    instance_connection_name: str,
    database_name: str,
) -> sqlalchemy.engine.base.Engine:
    def getconn() -> pg8000.dbapi.Connection:
        # The connector needs to be inside of `getconn` to work with Celery workers/threads.
        # Otherwise, the connector is not initialized properly and tasks hang on the connection indefinitely.
        connector = Connector(
            credentials=service_account_credentials, enable_iam_auth=True
        )
        iam_service_account_user = (
            service_account_credentials.service_account_email.removesuffix(
                ".gserviceaccount.com"
            )
        )
        # The connector needs to refresh the SA token every now and then.
        # The refresh is not thread-safe and leads to malformed SSL exchanges.
        with lock:
            conn: pg8000.dbapi.Connection = connector.connect(
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
    )
    return engine


def create_sql_engine(database_url: str) -> sqlalchemy.engine.base.Engine:
    return sqlalchemy.create_engine(
        database_url,
        echo=True,
    )
