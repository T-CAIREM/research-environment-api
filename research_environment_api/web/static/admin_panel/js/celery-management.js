$(document).ready(function() {
    let searchTimeout;

    function loadTaskCounters() {
        loadActiveTasksCount();
        loadReservedTasksCount();
        loadScheduledTasksCount();
    }

    function loadActiveTasksCount() {
        $.ajax({
            url: URLS.celeryDashboardData,
            type: 'GET',
            data: { counter_type: 'active' },
            success: function(data) {
                $('.active-tasks-count').text(data.task_counts.active || 0);
            },
            error: function() {
                $('.active-tasks-count').html('<span class="text-danger">Error</span>');
            }
        });
    }

    function loadReservedTasksCount() {
        $.ajax({
            url: URLS.celeryDashboardData,
            type: 'GET',
            data: { counter_type: 'reserved' },
            success: function(data) {
                $('.reserved-tasks-count').text(data.task_counts.reserved || 0);
            },
            error: function() {
                $('.reserved-tasks-count').html('<span class="text-danger">Error</span>');
            }
        });
    }

    function loadScheduledTasksCount() {
        $.ajax({
            url: URLS.celeryDashboardData,
            type: 'GET',
            data: { counter_type: 'scheduled' },
            success: function(data) {
                $('.scheduled-tasks-count').text(data.task_counts.scheduled || 0);
            },
            error: function() {
                $('.scheduled-tasks-count').html('<span class="text-danger">Error</span>');
            }
        });
    }

    function loadTaskTable(showLoading = true) {
        if (showLoading) {
            $('#tasks-table-body').html('<tr><td colspan="5" class="text-center"><i class="fas fa-spinner fa-spin fa-2x"></i><span class="ml-2">Loading tasks...</span></td></tr>');
            $('#search-button').prop('disabled', true).find('#search-spinner').show();
            $('#search-button').find('#search-icon').hide();
        }

        const params = {
            q: $('#task-search').val(),
            status: $('#status-filter').val(),
            worker: $('#worker-filter').val(),
            task_type: $('#task-type-filter').val(),
            limit: 20
        };

        $.ajax({
            url: URLS.celeryDashboardData,
            type: 'GET',
            data: params,
            success: function(data) {
                updateTaskTable(data.tasks);
            },
            error: function() {
                $('#tasks-table-body').html('<tr><td colspan="5" class="text-center text-danger">Error loading tasks.</td></tr>');
            },
            complete: function() {
                if (showLoading) {
                    $('#search-button').prop('disabled', false).find('#search-spinner').hide();
                    $('#search-button').find('#search-icon').show();
                }
            }
        });
    }

    function loadWorkerStatus(showLoading = true) {
        if (showLoading) {
            $('#workers-table-body').html('<tr><td colspan="3" class="text-center"><i class="fas fa-spinner fa-spin"></i><span class="ml-2">Loading workers...</span></td></tr>');
        }

        $.ajax({
            url: URLS.workers,
            type: 'GET',
            success: function(data) {
                updateWorkerStats(data);
            },
            error: function() {
                $('#workers-table-body').html('<tr><td colspan="3" class="text-center text-danger">Error loading worker data.</td></tr>');
            }
        });
    }

    function updateTaskTable(tasks) {
        const tableBody = $('#tasks-table-body');
        tableBody.empty();
        if (tasks && tasks.length > 0) {
            tasks.forEach(function(task) {
                const statusBadge = getStatusBadge(task.status);
                const truncatedId = task.id.length > 12 ? task.id.substring(0, 12) + '...' : task.id;
                const row = `
                    <tr>
                        <td title="${task.id}">${truncatedId}</td>
                        <td>${task.name || 'N/A'}</td>
                        <td>${statusBadge}</td>
                        <td>${task.worker || 'N/A'}</td>
                        <td>
                            <button class="btn btn-sm btn-danger task-delete-btn" data-task-id="${task.id}"><i class="fas fa-trash"></i></button>
                        </td>
                    </tr>
                `;
                tableBody.append(row);
            });
        } else {
            tableBody.append('<tr><td colspan="5" class="text-center">No tasks found.</td></tr>');
        }
        attachActionHandlers();
    }

    function updateWorkerStats(workers) {
        const tableBody = $('#workers-table-body');
        tableBody.empty();
        if (workers && workers.length > 0) {
            workers.forEach(function(worker) {
                const row = `
                    <tr>
                        <td>${worker.name}</td>
                        <td><span class="badge badge-success">Online</span></td>
                        <td>${worker.active_tasks}</td>
                    </tr>
                `;
                tableBody.append(row);
            });
        } else {
            tableBody.append('<tr><td colspan="3" class="text-center">No worker data available.</td></tr>');
        }
    }

    function getStatusBadge(status) {
        if (status === 'SUCCESS') return '<span class="badge badge-success">' + status + '</span>';
        if (status === 'FAILURE') return '<span class="badge badge-danger">' + status + '</span>';
        if (['STARTED', 'RECEIVED'].includes(status)) return '<span class="badge badge-primary">' + status + '</span>';
        if (['PENDING', 'RETRY'].includes(status)) return '<span class="badge badge-warning">' + status + '</span>';
        if (status === 'REVOKED') return '<span class="badge badge-secondary">' + status + '</span>';
        return '<span class="badge badge-info">' + status + '</span>';
    }

    function attachActionHandlers() {

        $('.task-delete-btn').off('click').on('click', function() {
            const taskId = $(this).data('task-id');
            $('#delete-task-id').text(taskId);
            $('#confirmDeleteModal').modal('show');
        });
    }

    function initEventListeners() {
        $('#task-search').on('keyup', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(function() {
                loadTaskTable();
            }, 300);
        });

        $('#search-button').on('click', function() {
            clearTimeout(searchTimeout);
            loadTaskTable();
        });

        $('#purge-tasks').on('click', function() {
            if (confirm('Are you sure you want to purge all tasks?')) {
                $.post(URLS.purgeTasks)
                    .done(function(response) {
                        alert(response.purged_count + ' tasks purged.');
                        loadTaskTable();
                        loadTaskCounters();
                    }).fail(function() {
                        alert('Error purging tasks.');
                    });
            }
        });

        $('#confirm-delete-btn').on('click', function() {
            const taskId = $('#delete-task-id').text();
            $.ajax({
                url: URLS.deleteTasks,
                type: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({ task_ids: [taskId] }),
                success: function() {
                    $('#confirmDeleteModal').modal('hide');
                    loadTaskTable();
                    loadTaskCounters();
                },
                error: function() { alert('Error deleting task.'); }
            });
        });

        $('#refresh-counters').on('click', function() {
            loadTaskCounters();
        });
    }

    function init() {
        initEventListeners();

        loadTaskCounters();
        loadTaskTable();
        loadWorkerStatus();

        setInterval(loadTaskCounters, 10000);
    }

    init();
});
