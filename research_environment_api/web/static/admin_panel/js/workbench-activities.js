$(document).ready(function() {
  let selectedActivities = [];

  if (typeof $().tooltip === 'function') {
    $('[data-toggle="tooltip"]').tooltip();
  }

  function updateSelectedCount() {
    const count = selectedActivities.length;
    $('#selected-count').text(count);
    $('#bulk-update-status-btn').prop('disabled', count === 0);
  }

  function clearSelectedActivities() {
    selectedActivities = [];
    $('.activity-checkbox').prop('checked', false);
    $('#select-all-activities').prop('checked', false);
    updateSelectedCount();
  }

  document.querySelectorAll('.sortable-header').forEach(header => {
    header.addEventListener('click', function() {
      const sortField = this.getAttribute('data-sort');
      const currentSortBy = document.getElementById('sort_by').value;
      const currentDirection = document.getElementById('sort_direction').value;
      const newDirection = sortField === currentSortBy ? (currentDirection === 'desc' ? 'asc' : 'desc') : 'desc';

      document.getElementById('sort_by').value = sortField;
      document.getElementById('sort_direction').value = newDirection;
      document.getElementById('filter-form').submit();
    });
  });

  $('.activity-checkbox').on('click', function() {
    const activityId = $(this).data('activity-id');

    if ($(this).is(':checked')) {
      if (!selectedActivities.includes(activityId)) {
        selectedActivities.push(activityId);
      }
    } else {
      const index = selectedActivities.indexOf(activityId);
      if (index > -1) {
        selectedActivities.splice(index, 1);
      }
      $('#select-all-activities').prop('checked', false);
    }

    updateSelectedCount();
  });

  $('#select-all-activities').on('click', function() {
    const isChecked = $(this).is(':checked');

    $('.activity-checkbox').prop('checked', isChecked);

    if (isChecked) {
      $('.activity-checkbox').each(function() {
        const activityId = $(this).data('activity-id');
        if (!selectedActivities.includes(activityId)) {
          selectedActivities.push(activityId);
        }
      });
    } else {
      $('.activity-checkbox').each(function() {
        const activityId = $(this).data('activity-id');
        const index = selectedActivities.indexOf(activityId);
        if (index > -1) {
          selectedActivities.splice(index, 1);
        }
      });
    }

    updateSelectedCount();
  });

  document.querySelectorAll('.edit-status-btn').forEach(button => {
    button.addEventListener('click', function() {
      const activityId = this.getAttribute('data-activity-id');
      const currentStatus = this.getAttribute('data-current-status');

      document.getElementById('edit-activity-id').value = activityId;

      const statusDropdown = document.getElementById('new-status');
      statusDropdown.innerHTML = '<option value="">-- Select Status --</option>';

      AVAILABLE_STATUSES.forEach(status => {
        if (status !== currentStatus) {
          const option = document.createElement('option');
          option.value = status;
          option.textContent = status;
          statusDropdown.appendChild(option);
        }
      });

      $('#editStatusModal').modal('show');
    });
  });

  document.getElementById('save-status-btn').addEventListener('click', function() {
    const activityId = document.getElementById('edit-activity-id').value;
    const newStatus = document.getElementById('new-status').value;

    if (!activityId || !newStatus) {
      alert('Please select a status');
      return;
    }

    fetch(URLS.updateActivityStatus, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ activity_ids: [activityId], new_status: newStatus })
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        $('#editStatusModal').modal('hide');
        alert('Status updated successfully!');
        location.reload();
      } else {
        alert('Error updating status: ' + (data.error || 'Unknown error'));
      }
    })
    .catch(error => {
      console.error('Error:', error);
      alert('An error occurred while updating the status.');
    });
  });

  document.querySelectorAll('.show-details-btn').forEach(button => {
    button.addEventListener('click', function() {
      document.getElementById('detail-activity-id').innerText = this.getAttribute('data-activity-id');
      document.getElementById('detail-email').innerText = this.getAttribute('data-email');
      document.getElementById('detail-workbench-id').innerText = this.getAttribute('data-workbench-id');
      document.getElementById('detail-build-type').innerText = this.getAttribute('data-build-type');
      document.getElementById('detail-workspace-id').innerText = this.getAttribute('data-workspace-id');
      document.getElementById('detail-error-info').innerText = this.getAttribute('data-error');

      $('#errorDetailsModal').modal('show');
    });
  });

  $('#bulk-update-status-btn').on('click', function() {
    if (selectedActivities.length === 0) {
      return;
    }

    $('#bulk-activity-count').text(selectedActivities.length);
    $('#bulk-new-status').val('');
    $('#bulkEditStatusModal').modal('show');
  });

  $('#bulk-save-status-btn').on('click', function() {
    const newStatus = $('#bulk-new-status').val();

    if (!newStatus) {
      alert('Please select a status');
      return;
    }

    if (selectedActivities.length === 0) {
      alert('No activities selected');
      return;
    }

    $(this).prop('disabled', true).html('<i class="fas fa-spinner fa-spin"></i> Updating...');

    fetch(URLS.updateActivityStatus, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        activity_ids: selectedActivities,
        new_status: newStatus
      })
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        $('#bulkEditStatusModal').modal('hide');
        alert('Activities updated successfully.');
        clearSelectedActivities();
        location.reload();
      } else {
        alert('Error updating statuses: ' + (data.error || 'Unknown error'));
        $('#bulk-save-status-btn').prop('disabled', false).html('Update All');
      }
    })
    .catch(error => {
      console.error('Error:', error);
      alert('An error occurred while updating the statuses.');
      $('#bulk-save-status-btn').prop('disabled', false).html('Update All');
    });
  });

  updateSelectedCount();
});
