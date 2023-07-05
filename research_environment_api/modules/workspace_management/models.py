from research_environment_api.modules.db import ScopedModel


class Workspace(ScopedModel):
    __abstract__ = True
    __table_prefix__ = "workspace_"
