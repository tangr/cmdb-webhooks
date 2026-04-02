/**
 * Shared functions for Amis Jenkins pages (form.html & pending.html).
 *
 * Requires: jQuery, Amis SDK (amisRequire), Semantic UI modal.
 *
 * Usage:
 *   1. Include this script after amis sdk.js
 *   2. Call AmisJenkins.init(onSuccessCallback) on page ready
 *   3. Use AmisJenkins.syncJobStatus / AmisJenkins.openExecuteModal in UI
 */
var AmisJenkins = (function () {
  var _onSuccess = null;
  var _currentModalJobId = null;
  var _currentModalJobData = null;
  var _amisFormInstance = null;
  var _amisFormData = {};

  function init(onSuccessCallback) {
    _onSuccess = onSuccessCallback;
  }

  function syncJobStatus(jobId) {
    fetch("/amis-jenkins/api/pending/" + jobId + "/sync", {
      method: "POST",
      credentials: "include"
    })
      .then(function (response) { return response.json(); })
      .then(function (result) {
        if (result.status === 0) {
          alert("Status synced: " + result.data.job_status);
          if (_onSuccess) _onSuccess();
        } else {
          alert("Failed to sync: " + result.msg);
        }
      })
      .catch(function (error) {
        alert("Error: " + error.message);
      });
  }

  function openExecuteModal(jobId) {
    fetch("/amis-jenkins/api/pending/" + jobId, { credentials: "include" })
      .then(function (response) { return response.json(); })
      .then(function (result) {
        if (result.status !== 0) {
          alert("Failed to load job details: " + result.msg);
          return;
        }
        _currentModalJobId = jobId;
        _currentModalJobData = result.data;
        _populateExecuteModal(result.data);
        $("#execute-modal").modal({
          closable: true,
          onApprove: function () {
            _executeJobFromModal();
            return false;
          },
          onHidden: function () {
            if (_amisFormInstance) {
              _amisFormInstance.unmount();
              _amisFormInstance = null;
            }
            $("#amis-form-container").html("");
            window.__amisExecuteFormData = null;
          }
        }).modal("show");
      })
      .catch(function (error) {
        alert("Error loading job: " + error.message);
      });
  }

  function _populateExecuteModal(job) {
    // Job info header
    var infoHtml = '<div class="ui list">';
    infoHtml += '<div class="item"><strong>Form:</strong> ' + escapeHtml(job.form_title) + '</div>';
    infoHtml += '<div class="item"><strong>Jenkins Job:</strong> ' + escapeHtml(job.jenkins_job) + '</div>';
    infoHtml += '<div class="item"><strong>Submitted by:</strong> ' + escapeHtml(job.username) + '</div>';
    if (job.execution_count > 0) {
      infoHtml += '<div class="item"><strong>Executed:</strong> ' + job.execution_count + ' time(s)</div>';
    }
    if (job.max_executions > 0) {
      infoHtml += '<div class="item"><strong>Max executions:</strong> ' + job.max_executions + '</div>';
    }
    if (job.expire_at > 0) {
      infoHtml += '<div class="item"><strong>Expires:</strong> ' + formatTimestamp(job.expire_at) + '</div>';
    }
    infoHtml += '</div>';
    $("#modal-job-info").html(infoHtml);

    // Get field schema (includes all fields, non-modifiable marked as static)
    var formSchemaConfig = job.execution_form_schema || {};
    var fieldSchema = formSchemaConfig.schema || [];
    var requestParams = job.request_params || {};

    // Clean up previous Amis instance
    if (_amisFormInstance) {
      _amisFormInstance.unmount();
      _amisFormInstance = null;
    }

    if (fieldSchema.length > 0) {
      $("#amis-form-container").html("");

      var amisSchema = {
        type: "page",
        body: {
          type: "form",
          name: "executeForm",
          mode: "horizontal",
          wrapWithPanel: false,
          submitOnChange: false,
          actions: [],
          onEvent: {
            change: {
              actions: [{
                actionType: "custom",
                script: "window.__amisExecuteFormData = Object.assign(window.__amisExecuteFormData || {}, event.data);"
              }]
            }
          },
          body: fieldSchema
        }
      };

      _amisFormData = Object.assign({}, requestParams);
      window.__amisExecuteFormData = Object.assign({}, requestParams);

      var amis = amisRequire("amis/embed");
      _amisFormInstance = amis.embed(
        "#amis-form-container",
        amisSchema,
        {
          data: _amisFormData
        },
        {
          theme: "cxd",
          locale: "zh-CN",
          getModalContainer: function () {
            return document.getElementById("amis-form-container");
          }
        }
      );
    } else {
      $("#amis-form-container").html("<p>No parameters to display</p>");
    }
  }

  function _executeJobFromModal() {
    if (!_currentModalJobId) {
      alert("No job selected");
      return;
    }

    var modifiedFields = {};
    var formSchemaConfig = _currentModalJobData.execution_form_schema || {};
    var modifiableFields = formSchemaConfig.fields || [];

    if (modifiableFields.length > 0) {
      // Read current form values tracked by onEvent.change
      var currentValues = window.__amisExecuteFormData || _amisFormData;

      modifiableFields.forEach(function (fieldName) {
        if (currentValues.hasOwnProperty(fieldName)) {
          modifiedFields[fieldName] = currentValues[fieldName];
        }
      });
    }

    $("#modal-execute-btn").addClass("loading disabled");

    var requestBody = {};
    if (Object.keys(modifiedFields).length > 0) {
      requestBody.modified_fields = modifiedFields;
    }

    fetch("/amis-jenkins/api/pending/" + _currentModalJobId + "/execute", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(requestBody)
    })
      .then(function (response) { return response.json(); })
      .then(function (result) {
        $("#modal-execute-btn").removeClass("loading disabled");
        if (result.status === 0) {
          $("#execute-modal").modal("hide");
          var msg = "Jenkins build triggered successfully!\nExecution count: " + result.data.execution_count;
          var jr = result.data.jenkins_response || {};
          if (jr._build_url) {
            msg += "\n\nBuild URL:\n" + jr._build_url;
          } else if (jr._queue_url) {
            msg += "\n\nQueue URL (build not yet started):\n" + jr._queue_url;
          }
          alert(msg);
          if (_onSuccess) _onSuccess();
        } else {
          alert("Failed to execute: " + result.msg);
        }
      })
      .catch(function (error) {
        $("#modal-execute-btn").removeClass("loading disabled");
        alert("Error: " + error.message);
      });
  }

  // ==================== Utility Functions ====================
  function formatTimestamp(ts) {
    if (!ts) return "N/A";
    var date = new Date(ts * 1000);
    return date.toLocaleString();
  }

  function escapeHtml(text) {
    if (text === null || text === undefined) return "";
    var div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  // Public API
  return {
    init: init,
    syncJobStatus: syncJobStatus,
    openExecuteModal: openExecuteModal,
    formatTimestamp: formatTimestamp,
    escapeHtml: escapeHtml
  };
})();
