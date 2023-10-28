frappe.provide("frappe.toolbar");
frappe.provide("tag_workflow");
frappe.flags.ats = [];
frappe.flags.ats_status = null;
$(document).bind("toolbar_setup", function () {
  $(".dropdown-help").empty();
  $(".navbar-home").html(
    `<img class="app-logo" src="/assets/tag_workflow/images/TAG-Logo.png">`
  );
  if (window.screen.width > 768) {
    $(".navbar-home").html(
      `<img class="app-logo" src="/assets/tag_workflow/images/TAG-Logo.png">`
    );
  } else {
    $(".navbar-home").html(
      `<img class="app-logo" src="/assets/tag_workflow/images/TAG-Logo-Emblem.png">`
    );
  }

  frappe.ui.toolbar.route_to_company = function () {
    location.href = "/app/company/" + frappe.boot.tag.tag_user_info.company;
  };
});

$(document).ready(function () {
  if (frappe.boot && frappe.boot.home_page !== "setup-wizard") {
    if (frappe.boot.tag.tag_user_info.company_type == "Staffing") {
      frappe.call({
        method: "tag_workflow.tag_data.get_ats_and_payroll_status",
        callback: (r) => {
          $(".main-section").append(
            frappe.render_template("tag", r.message[0])
          );
          frappe.flags.ats_status = r.message[0];
          if (r.message[0].ats == 0)
            frappe.flags.ats.push(
              "Employee Onboarding",
              "Employee Onboarding Template"
            );
          if (r.message[0].payroll == 0)
            frappe.flags.ats.push(
              "Salary Component",
              "Salary Structure",
              "Salary Structure Assignment",
              "Salary Slip",
              "Payroll Period",
              "Payroll Entry"
            );
        },
      });
      frappe.flags.ats.push("Hiring Company Review");
    } else {
      $(".main-section").append(
        frappe.render_template("tag", { ats: 1, payroll: 1 })
      );
    }
    list_for_hiring();
  }

  if (window.location.pathname == "/app/staff-home") {
    setTimeout(frappe.breadcrumbs.clear(), 5000);
  }
});

function list_for_hiring() {
  if (
    ["Hiring", "Exclusive Hiring"].includes(
      frappe.boot.tag.tag_user_info.company_type
    )
  ) {
    frappe.flags.ats.push("Company Review");
  }
}

frappe.provide("tag_workflow.workflow");
frappe.ui.form.States = Class.extend({
  init: function (opts) {
    $.extend(this, opts);
    this.state_fieldname = frappe.workflow.get_state_fieldname(
      this.frm.doctype
    );

    // no workflow?
    if (!this.state_fieldname) return;

    this.update_fields = frappe.workflow.get_update_fields(this.frm.doctype);

    let me = this;
    $(this.frm.wrapper).bind("render_complete", function () {
      me.refresh();
    });
  },

  setup_help: function () {
    let me = this;
    this.frm.page.add_action_item(
      __("Help"),
      function () {
        frappe.workflow.setup(me.frm.doctype);
        let state = me.get_state();
        let d = new frappe.ui.Dialog({
          title: "Workflow: " + frappe.workflow.workflows[me.frm.doctype].name,
        });
        let next_html =
          $.map(
            frappe.workflow.get_transitions(me.frm.doctype, state),
            function (r) {
              return r.action.bold() + __(" by Role ") + r.allowed;
            }
          ).join(", ") || __("None: End of Workflow").bold();

        $(d.body)
          .html(
            "<p>" +
              __("Current status") +
              ": " +
              state.bold() +
              "</p>" +
              "<p>" +
              __("Document is only editable by users of role") +
              ": " +
              frappe.workflow
                .get_document_state(me.frm.doctype, state)
                .allow_edit.bold() +
              "</p>" +
              "<p>" +
              __("Next actions") +
              ": " +
              next_html +
              "</p>" +
              (me.frm.doc.__islocal
                ? "<div class='alert alert-info'>" +
                  __("Workflow will start after saving.") +
                  "</div>"
                : "") +
              "<p class='help'>" +
              __("Note: Other permission rules may also apply") +
              "</p>"
          )
          .css({ padding: "15px" });
        d.show();
      },
      true
    );
  },

  refresh: function () {
    // hide if its not yet saved
    if (this.frm.doc.__islocal) {
      this.set_default_state();
      return;
    }
    // state text
    let state = this.get_state();

    if (state) {
      // show actions from that state
      this.show_actions(state);
    }
  },

  show_actions: function (state) {
    let added = false;
    let me = this;
    this.frm.page.clear_actions_menu();

    // if the loaded doc is dirty, don't show workflow buttons
    if (this.frm.doc.__unsaved === 1) {
      return;
    }

    frappe.workflow.get_transitions(this.frm.doc, state).then((transitions) => {
      $.each(transitions, function (_i, d) {
        if (frappe.user_roles.includes(d.allowed)) {
          added = true;
          me.frm.page.add_action_item(__(d.action), function () {
            let action = d.action;
            // capture current state
            if (action == "Reject") {
              me.frm.doc.__tran_state = d;
            } else {
              unreject(me, d);
            }
          });
        }
      });
    });

    if (added) {
      this.frm.page.btn_primary.addClass("hide");
      this.frm.toolbar.current_status = "";
      this.setup_help();
    }
  },

  set_default_state: function () {
    let default_state = frappe.workflow.get_default_state(
      this.frm.doctype,
      this.frm.doc.docstatus
    );
    if (default_state) {
      this.frm.set_value(this.state_fieldname, default_state);
    }
  },

  get_state: function () {
    if (!this.frm.doc[this.state_fieldname]) {
      this.set_default_state();
    }
    return this.frm.doc[this.state_fieldname];
  },

  bind_action: function () {
    let me = this;
    this.dropdown.on("click", "[data-action]", function () {
      me._bind = "0";
    });
  },
});

/*------------------------------------------------*/
frappe.form.link_formatters["Employee"] = function (value, doc) {
  if (doc?.employee_name && doc.employee_name !== value) {
    return value ? doc.employee_name + ": " + value : doc.employee_name;
  } else {
    return value;
  }
};
function unreject(me, d) {
  let doc_before_action = copy_dict(me.frm.doc);
  // set new state
  let next_state = d.next_state;
  me.frm.doc[me.state_fieldname] = next_state;

  let new_state = frappe.workflow.get_document_state(
    me.frm.doctype,
    next_state
  );
  new_state.update_field = me.state_fieldname;
  let new_docstatus = cint(new_state.doc_status);

  if (new_state.update_field) {
    me.frm.set_value(new_state.update_field, "");
    me.frm.set_value(new_state.update_field, new_state.update_value);
    cur_frm.refresh_field(new_state.update_field);
  }

  // revert state on error
  let on_error = function () {
    // reset in locals
    frappe.model.add_to_locals(doc_before_action);
    me.frm.refresh();
  };

  // success - add a comment
  let success = function () {
    console.log("Success");
  };

  me.frm.doc.__tran_state = d;

  if (new_docstatus == 1 && me.frm.doc.docstatus == 0) {
    me.frm.savesubmit(null, success, on_error);
  } else if (new_docstatus == 0 && me.frm.doc.docstatus == 0) {
    me.frm.save("Save", success, null, on_error);
  } else if (new_docstatus == 1 && me.frm.doc.docstatus == 1) {
    me.frm.save("Update", success, null, on_error);
  } else if (new_docstatus == 2 && me.frm.doc.docstatus == 1) {
    me.frm.savecancel(null, success, on_error);
  } else {
    frappe.msgprint(
      __("Document Status transition from ") +
        me.frm.doc.docstatus +
        " " +
        __("to") +
        new_docstatus +
        " " +
        __("is not allowed.")
    );
    frappe.msgprint(
      __("Document Status transition from {0} to {1} is not allowed", [
        me.frm.doc.docstatus,
        new_docstatus,
      ])
    );
    return 0;
  }
}
/*----------fields-----------*/
tag_workflow.UpdateField = function update_field(frm, field) {
  if (field == "map") {
    frm.set_value("enter_manually", 0);
    frm.set_df_property("map", "hidden", 0);
  } else {
    frm.set_value("search_on_maps", 0);
    frm.set_df_property("map", "hidden", 1);
  }
};
frappe.search.AwesomeBar.prototype.setup = function (element) {
  let me = this;
  $(".search-bar").removeClass("hidden");
  let $input = $(element);
  let input = $input.get(0);
  this.options = [];
  this.global_results = [];

  let awesomplete = new Awesomplete(input, {
    minChars: 0,
    maxItems: 99,
    autoFirst: true,
    list: [],
    filter: function () {
      return true;
    },

    data: function (item) {
      return {
        label: item.index || "",
        value: item.value,
      };
    },

    item: function (item) {
      let d = this.get_item(item.value);
      let name = __(d.label || d.value);
      let html = "<span>" + name + "</span>";
      if (d.description && d.value !== d.description) {
        html +=
          '<br><span class="text-muted ellipsis">' +
          __(d.description) +
          "</span>";
      }

      return $("<li></li>")
        .data("item.autocomplete", d)
        .html(`<a style="font-weight:normal">${html}</a>`)
        .get(0);
    },

    sort: function (a, b) {
      return b.label - a.label;
    },
  });

  // Added to aid UI testing of global search
  input.awesomplete = awesomplete;
  this.awesomplete = awesomplete;

  $input.on(
    "input",
    frappe.utils.debounce(function (e) {
      let value = e.target.value;
      let txt = value.trim().replace(/\s\s+/g, " ");
      let last_space = txt.lastIndexOf(" ");
      me.global_results = [];
      me.options = [];

      if (txt && txt.length > 1) {
        if (last_space !== -1) {
          me.set_specifics(txt.slice(0, last_space), txt.slice(last_space + 1));
        }
        me.add_defaults(txt);
        me.options = me.options.concat(me.build_options(txt));
        me.options = me.options.concat(me.global_results);
      } else {
        me.options = me.options.concat(
          me.deduplicate(frappe.search.utils.get_recent_pages(txt || ""))
        );
        me.options = me.options.concat(
          frappe.search.utils.get_frequent_links()
        );
      }
      me.add_help();
      awesomplete.list = me.deduplicate(me.options);
    }, 100)
  );

  let open_recent = function () {
    if (!this.autocomplete_open) {
      $(this).trigger("input");
    }
  };

  $input.on("focus", open_recent);
  $input.on("awesomplete-open", function (e) {
    me.autocomplete_open = e.target;
  });

  $input.on("awesomplete-close", function () {
    me.autocomplete_open = false;
  });

  $input.on("awesomplete-select", function (e) {
    let o = e.originalEvent;
    let value = o.text.value;
    let item = awesomplete.get_item(value);

    setTimeout(function () {
      if (cur_frm || cur_page) {
        location.reload();
      }
    }, 500);

    if (item.route_options) {
      frappe.route_options = item.route_options;
    }

    if (item.onclick) {
      item.onclick(item.match);
    } else {
      frappe.set_route(item.route);
    }
    $input.val("");
  });

  $input.on("awesomplete-selectcomplete", function () {
    $input.val("");
  });

  $input.on("keydown", (e) => {
    if (e.key == "Escape") {
      $input.trigger("blur");
    }
  });
  frappe.search.utils.setup_recent();
  frappe.tags.utils.fetch_tags();
};
frappe.ui.form.ControlInput.prototype.set_label = function (label) {
  if (
    this.value &&
    !["Checkbox", "Password", "Attach Image", "Text Editor"].includes(
      this.df.fieldtype
    )
  ) {
    if (this.df.fieldtype == "Currency") {
      this.$wrapper.attr("title", "$" + Number(this.value).toFixed(2));
    } else if (this.df.fieldtype == "Date") {
      let date = this.value.split("-");
      let date_label = date[1] + "-" + date[2] + "-" + date[0];
      this.$wrapper.attr("title", __(date_label));
    } else if (this.df.fieldtype == "Time") {
      let time = this.value.split(":");
      let time_label = time[0] + ":" + time[1];
      this.$wrapper.attr("title", __(time_label));
    } else if (this.df.fieldtype == "Datetime") {
      let datetime = this.value.split(" ");
      let new_date = datetime[0].split("-");
      let new_time = datetime[1].split(":");
      let datetime_label =
        new_date[1] +
        "-" +
        new_date[2] +
        "-" +
        new_date[0] +
        " " +
        new_time[0] +
        ":" +
        new_time[1];
      this.$wrapper.attr("title", __(datetime_label));
    } else if (this.df.fieldtype == "Float") {
      this.$wrapper.attr("title", this.value.toFixed(2));
    } else if (this.df.fieldtype == "Attach") {
      let attach_label = this.value.split("/");
      this.$wrapper.attr("title", attach_label[attach_label.length - 1]);
    } else {
      this.$wrapper.attr("title", this.value);
    }
  }

  if (label) this.df.label = label;
  if (this.only_input || this.df.label == this._label) return;
  let icon = "";
  this.label_span.innerHTML =
    (icon ? '<i class="' + icon + '"></i> ' : "") + __(this.df.label) ||
    "&nbsp;";
  this._label = this.df.label;
};

/*----------------------------------------*/
function redirect_job(name, child_name) {
  window.location.href = "/app/assign-employee/" + name;
}

function remove_job(name, job, employee_id, removed, job_title, start_time) {
  $(".modal-content").hide();
  frappe.call({
    method: "tag_workflow.tag_data.remove_emp_from_order",
    args: {
      assign_emp: name,
      employee_name: employee_id,
      job_order: job,
      removed: removed,
      job_title: job_title,
      start_time: start_time,
      user: frappe.session.user
    },
    callback: function (r) {
      if (r.message) {
        if (r.message == "removed") {
          frappe.msgprint("Employee removed successfully");
        } else if (r.message == "unremoved") {
          frappe.msgprint("Employee unremoved successfully");
        } else if (r.message == "emp_not_required") {
          frappe.msgprint("No Employee is required for this job order");
        } else {
          frappe.msgprint("Something went wrong. Please try again");
        }
      }
      setTimeout(function () {
        window.location.reload();
      }, 4000);
    },
  });
}

function toogle_remove_button(name,job,employee_id,removed,job_title,start_time,row_name) {
  let dialog=$('.modal-dialog')
  let removed_emp_detail=JSON.parse(localStorage.getItem("employee_removed_"+job))
  let test_removed_emp_detail=JSON.parse(localStorage.getItem("test_employee_removed_"+job))

  if(dialog.find(`#remove-btn-${employee_id}-${job_title.replace(/[\s.]/g,'_')}-${start_time.replace(":","\\:")}`)[0].innerHTML=="Remove") {
    dialog.find(`#remove-btn-${employee_id}-${job_title.replace(/[\s.]/g,'_')}-${start_time.replace(":","\\:")}`).text("Restore").removeClass("btn-primary");
    if(!removed_emp_detail.includes(employee_id+"~"+job_title+"~"+start_time)) {
      removed_emp_detail.push(employee_id+"~"+job_title+"~"+start_time)
      localStorage.setItem("employee_removed_"+job,JSON.stringify(removed_emp_detail))
    }

    if(!test_removed_emp_detail[row_name].includes(employee_id+"~"+job_title+"~"+start_time)) {
      test_removed_emp_detail[row_name].push(employee_id+"~"+job_title+"~"+start_time)
      localStorage.setItem("test_employee_removed_"+job,JSON.stringify(test_removed_emp_detail))
    }
  }
  else {
    dialog.find(`#remove-btn-${employee_id}-${job_title.replace(/[\s.]/g,'_')}-${start_time.replace(":","\\:")}`).text("Remove").addClass("btn-primary");;
    let array_idx=removed_emp_detail.indexOf(employee_id+"~"+job_title+"~"+start_time);
    removed_emp_detail.splice(array_idx,1)
    localStorage.setItem("employee_removed_"+job,JSON.stringify(removed_emp_detail))

    let test_array_idx=test_removed_emp_detail[row_name].indexOf(employee_id+"~"+job_title+"~"+start_time);
    test_removed_emp_detail[row_name].splice(test_array_idx,1)
    localStorage.setItem("test_employee_removed_"+job,JSON.stringify(test_removed_emp_detail))
  }
}

function download_resume_reduce_headcount(resume) {
  let file=resume;
  let link="";
  if(file.includes(".")) {
    if(file.length>1) {
      if(file.includes("/files/")) {
        link=window.location.origin+file;
      } else {
        link=window.location.origin+"/files/"+file;
      }
      let data=file.split("/");
      const anchor=document.createElement("a");
      anchor.href=link;
      anchor.download=data[data.length-1];
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
    }
  }
}


frappe.ui.form.Toolbar.prototype.set_page_actions = function (status) {
  let me = this;
  this.page.clear_actions();

  if (status !== "Edit") {
    let perm_to_check = this.frm.action_perm_type_map[status];
    if (!this.frm.perm[0][perm_to_check]) {
      return;
    }
  }

  if (status === "Edit") {
    this.page.set_primary_action(
      __("Edit"),
      function () {
        me.frm.page.set_view("main");
      },
      "edit"
    );
  } else if (status === "Cancel") {
    let add_cancel_button = () => {
      this.page.set_secondary_action(__(status), function () {
        me.frm.savecancel(this);
      });
    };
    if (this.has_workflow()) {
      frappe
        .xcall("frappe.model.workflow.can_cancel_document", {
          doctype: this.frm.doc.doctype,
        })
        .then((can_cancel) => {
          if (can_cancel) {
            add_cancel_button();
          }
        });
    } else {
      add_cancel_button();
    }
  } else {
    let click = {
      Save: function () {
        return me.frm.save("Save", null, this);
      },
      Submit: function () {
        return me.frm.savesubmit(this);
      },
      Update: async function () {
        check_update(me.frm);
      },
      Amend: function () {
        return me.frm.amend_doc();
      },
    }[status];

    let icon = {
      Update: "edit",
    }[status];

    this.page.set_primary_action(__(status), click, icon);
  }

  this.current_status = status;
};

function check_update(frm) {
  if (
    frm.doc.doctype == "Employee Onboarding" &&
    frm.doc.docstatus == 1 &&
    frm.doc.status == "Completed"
  ) {
    frappe.db
      .get_value("Employee Onboarding", { name: frm.doc.name }, ["status"])
      .then((res) => {
        if (res.message && res.message.status != "Completed") {
          update_emp_onb_status(frm);
        } else {
          return frm.save("Update", null, this);
        }
      });
  } else {
    return frm.save("Update", null, this);
  }
}

function update_emp_onb_status(frm) {
  let tasks_list = [];
  frm.doc.activities.forEach((element) => {
    tasks_list.push(element.task);
  });
  frappe.db
    .get_list("Task", {
      filters: {
        project: frm.doc.project,
        status: ["!=", "Completed"],
        name: ["in", tasks_list],
      },
      fields: ["name", "subject"],
    })
    .then((res) => {
      if (res && res.length > 0) {
        let message =
          "The following Onboard Employee Tasks are not set to 'Completed'. Do you wish to create the employee record?";
        let incomplete_tasks = [];
        for (let i in res) {
          message +=
            "<br>" + "<span>&bull;</span> " + res[i].subject.split(":")[0];
          incomplete_tasks.push(res[i].name);
        }
        frappe.confirm(message, async () => {
          await frm.save("Update", null, this);
          frappe.call({
            method: "tag_workflow.tag_data.set_status_complete",
            args: {
              docname: frm.doc.name,
              tasks_list: incomplete_tasks,
            },
          });
          window.location.reload();
        });
      } else {
        return frm.save("Update", null, this);
      }
    });
}

frappe.search.utils.get_doctypes = function (keywords) {
  let me = this;
  let out = [];
  let level, target, label;
  tag_workflow.option = function (type, route, order) {
    // check to skip extra list in the text
    // eg. Price List List should be only Price List
    let skip_list = type === "List" && target.endsWith("List");
    let label_without_type = me.bolden_match_part(__(target), keywords);
    if (skip_list) {
      label = label_without_type;
    } else {
      label = __(`{0} ${skip_list ? "" : type}`, [label_without_type]);
    }
    if (
      frappe.session.user == "Administrator" ||
      frappe.boot.tag.tag_user_info.company_type == "TAG"
    ) {
      label = check_error_label(target, type, label);
    }

    return {
      type: type,
      label: label,
      value: __(`{0} ${type}`, [target]),
      index: level + order,
      match: target,
      route: route,
    };
  };
  frappe.boot.user.can_read.forEach(function (item) {
    level = me.fuzzy_search(keywords, item);
    if (level) {
      target = item;
      if (in_list(frappe.boot.single_types, item)) {
        out.push(tag_workflow.option("", ["Form", item, item], 0.05));
      } else if (frappe.boot.user.can_search.includes(item)) {
        check_list(me, item, level, keywords, out);
      }
    }
  });
  return out;
};
function check_error_label(target, type, label) {
  if (target == "Company Review") {
    if (type == "Report") {
      return "Staffing Ratings & Reviews Report";
    } else if (type == "List") {
      return "Staffing Ratings & Reviews List";
    } else {
      return "Staffing Ratings & Reviews";
    }
  } else if (target == "Hiring Company Review") {
    if (type == "Report") {
      return "Hiring Ratings & Reviews Report";
    } else if (type == "List") {
      return "Hiring Ratings & Reviews List";
    } else if (type == "") {
      return "Hiring Ratings & Reviews";
    }
  }
  return label;
}

function check_list(me, item, level, keywords, out) {
  let check = 0;
  if (
    frappe.session.user == "Administrator" ||
    (frappe.boot.tag.tag_user_info.company_type == "TAG" &&
      (item == "Company Review" || item == "Hiring Company Review"))
  ) {
    check = 1;
  }
  // include 'making new' option
  if (in_list(frappe.boot.user.can_create, item)) {
    let match = item;
    if (!frappe.flags.ats.includes(item) && !check) {
      out.push({
        type: "New",
        label: __("New {0}", [me.bolden_match_part(__(item), keywords)]),
        value: __("New {0}", [__(item)]),
        index: level + 0.015,
        match: item,
        onclick: function () {
          frappe.new_doc(match, true);
        },
      });
    }
  }
  if (in_list(frappe.boot.treeviews, item)) {
    out.push(tag_workflow.option("Tree", ["Tree", item], 0.05));
  } else if (!frappe.flags.ats.includes(item)) {
      out.push(tag_workflow.option("List", ["List", item], 0.05));
      if (frappe.model.can_get_report(item)) {
        out.push(tag_workflow.option("Report", ["List", item, "Report"], 0.04));
      }
    }
}

function export_csv(ts_list) {
  frappe.call({
    method: "tag_workflow.utils.timesheet.csv_data",
    args: {
      ts_list: ts_list,
    },
    callback: (r) => {
      if (r.message[0] == "Success") {
        let export_ts_headers =
          "Customer Code, Personnel Code, Hour Type, Work Date, Position Code, Pay Hours, Bill Hours, Office Code, Date Time IN, Date Time OUT, Pay Rate, Bill Rate, PO Number, Approver Name, Approval Date Time, Source, Assignment Number, Project Code";
        r.message[1].forEach(function (row) {
          export_ts_headers += "\n" + row.join(",");
        });
        //merge the data with CSV
        let exporttimesheetElement = document.createElement("a");
        exporttimesheetElement.href =
          "data:text/csv;charset=utf-8," + encodeURI(export_ts_headers);
        exporttimesheetElement.target = "_blank";

        //provide the name for the CSV file to be downloaded
        let datetimestamp = frappe.datetime.now_datetime().split(" ");
        datetimestamp[0] = frappe.format(datetimestamp[0], {
          fieldtype: "Date",
        });
        datetimestamp[1] = datetimestamp[1].split(":").join("_");
        exporttimesheetElement.download =
          "TimeClockImport_" + datetimestamp.join(" ") + ".csv";

        exporttimesheetElement.click();
      } else {
        let message = "";
        if (r.message[1].includes(" and "))
          message =
            "These companies do not have office codes: " +
            r.message[1] +
            ". Please fill the details or unselect them to continue.";
        else
          message =
            r.message[1] +
            " does not have office code. Please fill the details to export the timesheet(s).";
        frappe.msgprint(message);
      }
    },
  });
}

function change_view() {
  let ch = document.querySelector(".toggle_icon").id;
  if (ch == "toggle_display_1") {
    document.querySelector(".toggle_icon").id = "toggle_display_0";
    $(
      ".col.layout-main-section-wrapper, .col-md-12.layout-main-section-wrapper"
    ).css({ left: "11rem", "max-width": "86.5%", width: "100%" });
  } else {
    document.querySelector(".toggle_icon").id = "toggle_display_1";
    $(
      ".col.layout-main-section-wrapper, .col-md-12.layout-main-section-wrapper"
    ).css({ left: "0rem", "max-width": "none!important", width: "100%" });
  }
}

// Disables "Updated To A New Version" pop-up
frappe.Application.prototype.show_change_log = function () {};

// Disables "New Updates are available" pop-up
frappe.Application.prototype.show_update_available = function () {};

$(document).on("click", () => {
  $(".dropdown-list").hide();
});

frappe.show_message_page = (opts) => {
  // opts can include `page_name`, `message`, `icon` or `img`
  if (!opts.page_name) {
    opts.page_name = frappe.get_route_str();
  }

  if (opts.icon) {
    opts.img = repl('<span class="%(icon)s message-page-icon"></span> ', opts);
  } else if (opts.img) {
    opts.img = repl('<img src="%(img)s" class="message-page-image">', opts);
  }

  let page =
    frappe.pages[opts.page_name] || frappe.container.add_page(opts.page_name);

  $(page).html(
    repl(
      `<div class="page message-page">\
			<div class="text-center message-page-content">\
				%(img)s\
				<p class="lead">%(message)s</p>\
				<a class="btn btn-default btn-sm btn-home">%(home)s</a>\
			</div>\
		</div>`,
      {
        img: opts.img || "",
        message: opts.message || "",
        home: __("Home"),
      }
    )
  );
  $(".btn-home").on("click", () => {
    if (
      ["Hiring", "Exclusive Hiring"].includes(
        frappe.boot.tag.tag_user_info.company_type
      )
    ) {
      window.location.href = "/app/hiring-home";
    } else if (frappe.boot.tag.tag_user_info.company_type == "Staffing") {
      window.location.href = "/app/staff-home";
    } else if (frappe.boot.tag.tag_user_info.company_type == "TAG") {
      window.location.href = "/app/tagadmin-page";
    } else {
      window.location.href = "/app/home";
    }
  });
  frappe.container.change_to(opts.page_name);
};
