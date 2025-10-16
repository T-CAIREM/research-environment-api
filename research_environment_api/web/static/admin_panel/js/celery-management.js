$(document).ready(function() {
    let searchTimeout;
    let activeFilters = {
        status: '',
        worker: '',
        task_type: ''
    };
    let availableWorkers = [];
    let availableTaskTypes = [];

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

    function updateFilterDisplay() {
        const activeFilterCount = Object.values(activeFilters).filter(val => val !== '').length;

        if (activeFilterCount > 0) {
            $('#filter-badge').text(activeFilterCount).show();

            $('#active-filters').show();
            $('#filter-tags').empty();

            if (activeFilters.status) {
                addFilterTag('Status', activeFilters.status, 'status');
            }
            if (activeFilters.worker) {
                addFilterTag('Worker', activeFilters.worker, 'worker');
            }
            if (activeFilters.task_type) {
                addFilterTag('Task Type', activeFilters.task_type, 'task_type');
            }
        } else {
            $('#filter-badge').hide();
            $('#active-filters').hide();
        }
    }

    function addFilterTag(label, value, type) {
        const tag = $(`
            <span class="badge badge-info mr-2 mb-1 filter-tag">
                ${label}: ${value}
                <i class="fas fa-times ml-1 remove-filter" data-filter-type="${type}" style="cursor: pointer;"></i>
            </span>
        `);
        $('#filter-tags').append(tag);
    }

    function loadFilterOptions() {
        $.ajax({
            url: URLS.workers,
            type: 'GET',
            success: function(data) {
                availableWorkers = data.map(worker => worker.name);
                updateWorkerFilterOptions();
            }
        });

        $.ajax({
            url: URLS.celeryDashboardData,
            type: 'GET',
            data: { get_task_types: true },
            success: function(data) {
                if (data.task_types) {
                    availableTaskTypes = data.task_types;
                    updateTaskTypeFilterOptions();
                }
            }
        });
    }

    function updateWorkerFilterOptions() {
        const select = $('#worker-filter');
        select.find('option:not(:first)').remove();

        availableWorkers.forEach(function(worker) {
            select.append($('<option>', {
                value: worker,
                text: worker
            }));
        });

        if (activeFilters.worker && availableWorkers.includes(activeFilters.worker)) {
            select.val(activeFilters.worker);
        }
    }

    function updateTaskTypeFilterOptions() {
        const select = $('#task-type-filter');
        select.find('option:not(:first)').remove();

        availableTaskTypes.forEach(function(taskType) {
            const displayName = taskType.split('.').pop();
            select.append($('<option>', {
                value: taskType,
                text: displayName,
                title: taskType
            }));
        });

        if (activeFilters.task_type && availableTaskTypes.includes(activeFilters.task_type)) {
            select.val(activeFilters.task_type);
        }
    }

    function loadTaskTable(showLoading = true) {
        if (showLoading) {
            $('#tasks-table-body').html('<tr><td colspan="5" class="text-center"><i class="fas fa-spinner fa-spin fa-2x"></i><span class="ml-2">Loading tasks...</span></td></tr>');
            $('#search-button').prop('disabled', true);
            $('#search-icon').hide();
            $('#search-spinner').show();
        }

        const params = {
            q: $('#task-search').val(),
            status: activeFilters.status,
            worker: activeFilters.worker,
            task_type: activeFilters.task_type,
            limit: 20
        };

        $.ajax({
            url: URLS.celeryDashboardData,
            type: 'GET',
            data: params,
            success: function(data) {
                updateTaskTable(data.tasks);

                if (data.tasks && data.tasks.length > 0) {
                    const workers = [...new Set(data.tasks.map(task => task.worker).filter(Boolean))];
                    const taskTypes = [...new Set(data.tasks.map(task => task.name).filter(Boolean))];

                    if (workers.length > 0 && availableWorkers.length === 0) {
                        availableWorkers = workers;
                        updateWorkerFilterOptions();
                    }

                    if (taskTypes.length > 0 && availableTaskTypes.length === 0) {
                        availableTaskTypes = taskTypes;
                        updateTaskTypeFilterOptions();
                    }
                }
            },
            error: function() {
                $('#tasks-table-body').html('<tr><td colspan="5" class="text-center text-danger">Error loading tasks.</td></tr>');
            },
            complete: function() {
                if (showLoading) {
                    $('#search-button').prop('disabled', false);
                    $('#search-spinner').hide();
                    $('#search-icon').show();
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

                if (data.length > 0) {
                    availableWorkers = data.map(worker => worker.name);
                    updateWorkerFilterOptions();
                }
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
        $(document).on('click', '.dropdown-menu', function(e) {
            if ($(e.target).is('select, option, label, .form-group, .form-control')) {
                e.stopPropagation();
            }
        });

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

        $('#apply-filters').on('click', function() {
            activeFilters.status = $('#status-filter').val();
            activeFilters.worker = $('#worker-filter').val();
            activeFilters.task_type = $('#task-type-filter').val();

            updateFilterDisplay();
            loadTaskTable();
            $('.dropdown-menu').removeClass('show');
        });

        $('#reset-filters').on('click', function() {
            $('#status-filter, #worker-filter, #task-type-filter').val('');
            activeFilters = {
                status: '',
                worker: '',
                task_type: ''
            };

            updateFilterDisplay();
            loadTaskTable();
            $('.dropdown-menu').removeClass('show');
        });

        $(document).on('click', '.remove-filter', function() {
            const filterType = $(this).data('filter-type');
            activeFilters[filterType] = '';
            $(`#${filterType}-filter`).val('');

            updateFilterDisplay();
            loadTaskTable();
        });

        $('#clear-all-filters').on('click', function() {
            $('#status-filter, #worker-filter, #task-type-filter').val('');
            activeFilters = {
                status: '',
                worker: '',
                task_type: ''
            };

            updateFilterDisplay();
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
        loadFilterOptions();

        setInterval(loadTaskCounters, 120000);
    }

    init();
});
