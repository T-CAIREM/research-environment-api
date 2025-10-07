#!/usr/bin/env python
# helper command line to test celery tasks management
"""
Command-line interface for Celery management operations.
"""

import argparse
import json
import sys
from typing import List, Dict, Any, Optional

from research_environment_api.background import celery_management
from research_environment_api.modules.celery_management import services
from dataclasses import is_dataclass, asdict


def _to_serializable(obj):
    if is_dataclass(obj):
        return asdict(obj)
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "__dict__"):
        return {k: v for k, v in obj.__dict__.items()}
    return str(obj)

def format_output(data: Any, output_format: str = 'json') -> str:
    """Format the output data according to the specified format."""
    if output_format.lower() == 'json':
        return json.dumps(data, indent=2, default=_to_serializable)
    elif output_format.lower() == 'pretty':
        if isinstance(data, list):
            result = []
            for item in data:
                # normalize item to dict if it's a dataclass or object
                if not isinstance(item, dict):
                    item = _to_serializable(item)
                if isinstance(item, dict):
                    result.append("\n".join([f"{k}: {v}" for k, v in item.items()]))
                else:
                    result.append(str(item))
                result.append("-" * 50)
            return "\n".join(result)
        elif isinstance(data, dict):
            # convert nested dataclasses/objects if present
            normalized = {k: _to_serializable(v) for k, v in data.items()}
            return "\n".join([f"{k}: {v}" for k, v in normalized.items()])
        else:
            return str(_to_serializable(data))
    return str(_to_serializable(data))



def search_tasks(args):
    """Search tasks by name."""
    tasks = celery_management.search_tasks_by_name(args.name)
    print(format_output(tasks, args.format))


def filter_tasks(args):
    """Filter tasks by criteria."""
    tasks = celery_management.filter_tasks(
        status=args.status,
        task_type=args.type,
        worker=args.worker
    )
    print(format_output(tasks, args.format))


def purge_tasks(args):
    """Purge all pending tasks."""
    count = celery_management.purge_tasks()
    print(f"Purged {count} tasks from the queue.")


def get_task_details(args):
    """Get detailed information about a task."""
    details = celery_management.get_task_details(args.task_id)
    print(format_output(details, args.format))


def get_worker_stats(args):
    """Get statistics about Celery workers."""
    stats = celery_management.get_worker_stats()
    print(format_output(stats, args.format))


def list_backend(args):
    """List tasks stored in the backend."""
    tasks = celery_management.list_backend_tasks(limit=args.limit, pattern=args.pattern)
    print(f"Found {len(tasks)} tasks in the backend:")
    print(format_output(tasks, args.format))


def list_scheduled(args):
    """List scheduled tasks across all workers."""
    tasks = celery_management.list_scheduled_tasks()
    print(f"Found {len(tasks)} scheduled tasks:")
    print(format_output(tasks, args.format))

# ----------------------------------------------------------------------------------
# Permanent deletion commands
# ----------------------------------------------------------------------------------

def delete_task_id(args):
    """Permanently delete a task by ID from broker + backend."""
    result = celery_management.delete_task_by_id(args.task_id)
    print(format_output(result, args.format))


def delete_task_id_new(args):
    """Permanently delete a task by ID from broker + backend."""
    task_ids = args.task_ids if isinstance(args.task_ids, list) else [args.task_ids]
    result = services.delete_tasks(task_ids)
    print(format_output(result, args.format))

def delete_tasks_pattern(args):
    """Delete tasks whose name matches a pattern (glob or substring)."""
    result = celery_management.delete_tasks_by_name_pattern(
        pattern=args.pattern,
        use_glob=not args.substring,
        limit=args.limit
    )
    print(format_output(result, args.format))

# ----------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Celery Task Management CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Common arguments
    format_parser = argparse.ArgumentParser(add_help=False)
    format_parser.add_argument(
        "--format", "-f", choices=["json", "pretty"], default="pretty",
        help="Output format (default: pretty)"
    )

    # Search tasks
    search_parser = subparsers.add_parser(
        "search", help="Search for tasks by name", parents=[format_parser]
    )
    search_parser.add_argument(
        "name", help="Name fragment to search for in task names"
    )
    search_parser.set_defaults(func=search_tasks)

    # Filter tasks
    filter_parser = subparsers.add_parser(
        "filter", help="Filter tasks by criteria", parents=[format_parser]
    )
    filter_parser.add_argument(
        "--status", "-s", choices=["ACTIVE", "RESERVED", "SCHEDULED"],
        help="Filter by task status"
    )
    filter_parser.add_argument(
        "--type", "-t", help="Filter by task type/name"
    )
    filter_parser.add_argument(
        "--worker", "-w", help="Filter by worker name"
    )
    filter_parser.set_defaults(func=filter_tasks)

    # Purge tasks
    purge_parser = subparsers.add_parser("purge", help="Purge all pending tasks")
    purge_parser.set_defaults(func=purge_tasks)

    # Task details
    details_parser = subparsers.add_parser(
        "details", help="Get detailed information about a task",
        parents=[format_parser]
    )
    details_parser.add_argument("task_id", help="ID of the task to get details for")
    details_parser.set_defaults(func=get_task_details)

    # Worker stats
    stats_parser = subparsers.add_parser(
        "stats", help="Get statistics about Celery workers",
        parents=[format_parser]
    )
    stats_parser.set_defaults(func=get_worker_stats)

    # List backend tasks
    list_backend_parser = subparsers.add_parser(
        "list-backend", help="List tasks stored in the result backend",
        parents=[format_parser]
    )
    list_backend_parser.add_argument(
        "--limit", "-l", type=int, default=100,
        help="Maximum number of tasks to return"
    )
    list_backend_parser.add_argument(
        "--pattern", "-p", help="Filter tasks by pattern"
    )
    list_backend_parser.set_defaults(func=list_backend)

    # List scheduled tasks
    list_scheduled_parser = subparsers.add_parser(
        "list-scheduled", help="List scheduled tasks across all workers",
        parents=[format_parser]
    )
    list_scheduled_parser.set_defaults(func=list_scheduled)

    # Delete task by ID (permanent)
    delete_id_parser = subparsers.add_parser(
        "delete", help="Permanently delete a task by ID from broker and backend",
        parents=[format_parser]
    )
    delete_id_parser.add_argument(
        "task_ids",
        nargs="+",
        help="ID(s) of the task(s) to delete (provide one or more)"
    )
    delete_id_parser.set_defaults(func=delete_task_id_new)


    # Delete tasks by pattern
    delete_pattern_parser = subparsers.add_parser(
        "delete-pattern", help="Delete tasks whose names match a pattern",
        parents=[format_parser]
    )
    delete_pattern_parser.add_argument("pattern", help="Pattern to match task names against")
    delete_pattern_parser.add_argument(
        "--substring", "-s", action="store_true",
        help="Treat pattern as substring (default: glob pattern)"
    )
    delete_pattern_parser.add_argument(
        "--limit", "-l", type=int, default=100,
        help="Maximum number of tasks to delete (default: 100)"
    )
    delete_pattern_parser.set_defaults(func=delete_tasks_pattern)

    # Parse arguments
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Execute the appropriate function
    args.func(args)


if __name__ == "__main__":
    main()
