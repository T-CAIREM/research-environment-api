from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Dict, List, Any, Optional, Union


class TaskStatus(StrEnum):
    PENDING = "PENDING"
    RECEIVED = "RECEIVED"
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    REVOKED = "REVOKED"
    RETRY = "RETRY"
    REJECTED = "REJECTED"


@dataclass
class TaskResult:
    value: Any = None
    error: Optional[str] = None
    traceback: Optional[str] = None


@dataclass
class Task:
    id: str
    name: Optional[str] = None
    args: Optional[List[Any]] = None
    kwargs: Optional[Dict[str, Any]] = None
    status: Union[TaskStatus, str] = TaskStatus.PENDING
    worker: Optional[str] = None
    eta: Optional[str] = None
    date_done: Optional[datetime] = None
    result: Optional[TaskResult] = None
    ready: bool = False
    successful: bool = False
    failed: bool = False


@dataclass
class TaskOperationResult:
    task_id: str
    is_successful: bool
    task_type: Optional[str] = None
    worker: Optional[str] = None


@dataclass
class WorkerStats:
    name: str
    stats: Dict[str, Any] = field(default_factory=dict)
    active_tasks: int = 0
    registered_tasks: List[str] = field(default_factory=list)
