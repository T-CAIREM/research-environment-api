import pg8000
import sqlalchemy
from google.auth.credentials import Credentials
from google.cloud.sql.connector import Connector, IPTypes


def make_cloud_sql_engine(
    service_account_credentials: Credentials,
    instance_connection_name: str,
    database_user: str,
    database_password: str,
    database_name: str,
) -> sqlalchemy.engine.base.Engine:
    connector = Connector(credentials=service_account_credentials)

    def getconn() -> pg8000.dbapi.Connection:
        conn: pg8000.dbapi.Connection = connector.connect(
            instance_connection_name,
            "pg8000",
            user=database_user,
            password=database_password,
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


def make_engine(database_url: str) -> sqlalchemy.engine.base.Engine:
    return sqlalchemy.create_engine(
        database_url,
        echo=True,
    )
