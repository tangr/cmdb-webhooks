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
        $("#modal-execute-btn").off("click").on("click", function () {
          if (!confirm("Are you sure you want to execute this Jenkins job?")) return;
          $("#modal-execute-btn").addClass("loading disabled");
          var hiddenBtn = document.querySelector("#amis-form-container .amis-hidden-submit");
          if (hiddenBtn) hiddenBtn.click();
        });
      })
      .catch(function (error) {
        alert("Error loading job: " + error.message);
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

      // Build success message script
      // Amis puts response.data into event.data, so fields like execution_count, jenkins_response are directly accessible
      var successScript =
        '$("#modal-execute-btn").removeClass("loading disabled");' +
        'var d = event.data || {};' +
        'var msg = "Jenkins build triggered successfully!\\nExecution count: " + (d.execution_count || "");' +
        'var jr = d.jenkins_response || {};' +
        'if (jr._build_url) { msg += "\\n\\nBuild URL:\\n" + jr._build_url; }' +
        'else if (jr._queue_url) { msg += "\\n\\nQueue URL (build not yet started):\\n" + jr._queue_url; }' +
        'alert(msg);' +
        '$("#execute-modal").modal("hide");' +
        'if (window.__amisOnExecuteSuccess) { window.__amisOnExecuteSuccess(); }';

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
                script: '$("#modal-execute-btn").removeClass("loading disabled"); var d = event.data || {}; var msg = d.msg || d.detail || "Unknown error"; alert("Failed to execute: " + msg);'
              }]
            }
          },
          body: fieldSchema.concat([
            {
              type: "button",
              actionType: "submit",
              label: "",
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
