import pg8000
import sqlalchemy
from google.cloud.sql.connector import Connector, IPTypes

from research_environment_api.modules.config import Config


def make_engine(config: Config) -> sqlalchemy.engine.base.Engine:
    connector = Connector(credentials=config.service_account_credentials)

    def getconn() -> pg8000.dbapi.Connection:
        conn: pg8000.dbapi.Connection = connector.connect(
            config.cloud_sql_instance_connection_name,
            "pg8000",
            user=config.database_user,
            password=config.database_password,
            db=config.database_name,
            ip_type=IPTypes.PUBLIC,
        )
        return conn

    if config.is_development():
        engine = sqlalchemy.create_engine(
            config.database_url,
            echo=True,
        )
    else:
        engine = sqlalchemy.create_engine(
            "postgresql+pg8000://",
            creator=getconn,
            echo=True,
        )
    return engine
