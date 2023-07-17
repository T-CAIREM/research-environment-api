import google.auth.transport.requests
import pg8000
import sqlalchemy
from google.auth.credentials import Credentials
from google.cloud.sql.connector import Connector, IPTypes


def _generate_credentials_token(credentials: Credentials) -> str:
    cloud_sql_scopes = ["https://www.googleapis.com/auth/sqlservice.admin"]
    scoped_credentials = credentials.with_scopes(cloud_sql_scopes)

    request = google.auth.transport.requests.Request()
    scoped_credentials.refresh(request)

    return scoped_credentials.token


def _generate_credentials_user(credentials: Credentials) -> str:
    return credentials.service_account_email.removesuffix(".gserviceaccount.com")


def create_cloud_sql_engine(
    service_account_credentials: Credentials,
    instance_connection_name: str,
    database_name: str,
) -> sqlalchemy.engine.base.Engine:
    connector = Connector(credentials=service_account_credentials)

    def getconn() -> pg8000.dbapi.Connection:
        iam_service_account_user = _generate_credentials_user(
            service_account_credentials
        )
        iam_service_account_password = _generate_credentials_token(
            service_account_credentials
        )
        conn: pg8000.dbapi.Connection = connector.connect(
            instance_connection_name,
            "pg8000",
            user=iam_service_account_user,
            password=iam_service_account_password,
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
