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
  var _amisFormInstance = null;

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
          $("body").toast({ class: "success", message: "Status synced: " + escapeHtml(result.data.job_status), displayTime: 5000 });
          if (_onSuccess) _onSuccess();
        } else {
          $("body").toast({ class: "error", message: "Failed to sync: " + escapeHtml(result.msg), displayTime: 6000 });
        }
      })
      .catch(function (error) {
        $("body").toast({ class: "error", message: "Sync error: " + escapeHtml(error.message), displayTime: 6000 });
      });
  }

  function openExecuteModal(jobId) {
    fetch("/amis-jenkins/api/pending/" + jobId, { credentials: "include" })
      .then(function (response) { return response.json(); })
      .then(function (result) {
        if (result.status !== 0) {
          $("body").toast({ class: "error", message: "Failed to load job details: " + escapeHtml(result.msg), displayTime: 6000 });
          return;
        }
        _populateExecuteModal(jobId, result.data);
        $("#execute-modal").modal({
          closable: true,
          onHidden: function () {
            if (_amisFormInstance) {
              _amisFormInstance.unmount();
              _amisFormInstance = null;
            }
            $("#amis-form-container").html("");
            // Unbind execute button click
            $("#modal-execute-btn").off("click");
          }
        }).modal("show");
        // Bind execute button to trigger Amis form submit via hidden button
        // Amis confirmText on the hidden button handles the confirmation dialog
        $("#modal-execute-btn").off("click").on("click", function () {
          var hiddenBtn = document.querySelector("#amis-form-container .amis-hidden-submit");
          if (hiddenBtn) hiddenBtn.click();
        });
      })
      .catch(function (error) {
        $("body").toast({ class: "error", message: "Error loading job: " + escapeHtml(error.message), displayTime: 6000 });
      });
  }

  function _populateExecuteModal(jobId, job) {
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
    var modifiableFields = formSchemaConfig.fields || [];
    var requestParams = job.request_params || {};

    // Clean up previous Amis instance
    if (_amisFormInstance) {
      _amisFormInstance.unmount();
      _amisFormInstance = null;
    }

    if (fieldSchema.length > 0) {
      $("#amis-form-container").html("");

      // Build api.data mapping: only pick modifiable fields into modified_fields
      var modifiedFieldsMapping = {};
      modifiableFields.forEach(function (fieldName) {
        modifiedFieldsMapping[fieldName] = "${" + fieldName + "}";
      });

      var apiConfig = {
        method: "post",
        url: "/amis-jenkins/api/pending/" + jobId + "/execute",
        data: {
          modified_fields: modifiedFieldsMapping
        }
      };

      // Build success handler script
      // Amis submitSucc: response.data is in event.data.result or event.data
      var successScript =
        'var result = (event.data || {}).result || event.data || {};' +
        'var msg = "Execution count: " + (result.execution_count || "N/A");' +
        'var jr = result.jenkins_response || {};' +
        'if (jr._build_url) { msg += "<br><a href=\'" + jr._build_url + "\' target=\'_blank\'>Open Build Console</a>"; }' +
        'else if (jr._queue_url) { msg += "<br>Queued (build not yet started)"; }' +
        'doAction({actionType:"toast",args:{msgType:"success",msg:msg,position:"top-center",timeout:10000}});' +
        '$("#execute-modal").modal("hide");' +
        'if (window.__amisOnExecuteSuccess) { window.__amisOnExecuteSuccess(); }';

      // Build failure handler script
      var failScript =
        'var d = event.data || {};' +
        'var msg = d.msg || d.detail || "Unknown error";' +
        'doAction({actionType:"toast",args:{msgType:"error",msg:msg,position:"top-center",timeout:8000}});';

      var amisSchema = {
        type: "page",
        body: {
          type: "form",
          name: "executeForm",
          mode: "horizontal",
          wrapWithPanel: false,
          submitOnChange: false,
          api: apiConfig,
          actions: [],
          onEvent: {
            submitSucc: {
              actions: [{
                actionType: "custom",
                script: successScript
              }]
            },
            submitFail: {
              actions: [{
                actionType: "custom",
                script: failScript
              }]
            }
          },
          body: fieldSchema.concat([
            {
              type: "button",
              actionType: "submit",
              label: "",
              confirmText: "Are you sure you want to execute this Jenkins job?",
              className: "amis-hidden-submit",
              style: { position: "absolute", width: 0, height: 0, overflow: "hidden", opacity: 0 }
            }
          ])
        }
      };

      // Register success callback for modal close
      window.__amisOnExecuteSuccess = _onSuccess;

      var amis = amisRequire("amis/embed");
      _amisFormInstance = amis.embed(
        "#amis-form-container",
        amisSchema,
        {
          data: Object.assign({}, requestParams)
        },
        {
          theme: "cxd",
          locale: "zh-CN",
          getModalContainer: function () {
            return document.getElementById("amis-form-container");
          },
          fetcher: function (options) {
            var method = (options.method || "GET").toUpperCase();
            var headers = Object.assign({}, options.headers || {});
            var fetchOptions = {
              method: method,
              headers: headers,
              credentials: "include"
            };

            if (method !== "GET" && method !== "HEAD" && options.data) {
              if (typeof options.data === "object") {
                headers["Content-Type"] = "application/json";
                fetchOptions.body = JSON.stringify(options.data);
              } else {
                fetchOptions.body = options.data;
              }
              fetchOptions.headers = headers;
            }

            return fetch(options.url, fetchOptions)
              .then(function (response) {
                return response.json().then(function (data) {
                  return { status: response.status, data: data };
                });
              });
          },
          notify: function (type, msg) {
            if (type === "error") {
              console.error("[Amis Error]", msg);
            }
          }
        }
      );
    } else {
      $("#amis-form-container").html("<p>No parameters to display</p>");
    }
  }

  // ==================== Utility Functions ====================
  var _weekdays = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

  function formatTimestamp(ts) {
    if (!ts) return "N/A";
    var date = new Date(ts * 1000);
    var now = new Date();
    var diffMs = now - date;
    var diffSec = Math.floor(diffMs / 1000);
    var diffMin = Math.floor(diffSec / 60);
    var diffHour = Math.floor(diffMin / 60);
    var diffDay = Math.floor(diffHour / 24);

    var relative;
    if (diffSec < 60) {
      relative = "just now";
    } else if (diffMin < 60) {
      relative = diffMin + (diffMin === 1 ? " minute ago" : " minutes ago");
    } else if (diffHour < 24) {
      relative = diffHour + (diffHour === 1 ? " hour ago" : " hours ago");
    } else if (diffDay < 7) {
      relative = diffDay + (diffDay === 1 ? " day ago" : " days ago") + " (" + _weekdays[date.getDay()] + ")";
    } else {
      relative = _weekdays[date.getDay()] + " " + date.toLocaleString();
    }
    return relative;
  }

  function formatTimestampFull(ts) {
    if (!ts) return "N/A";
    var date = new Date(ts * 1000);
    return _weekdays[date.getDay()] + " " + date.toLocaleString();
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
    formatTimestampFull: formatTimestampFull,
    escapeHtml: escapeHtml
  };
})();
