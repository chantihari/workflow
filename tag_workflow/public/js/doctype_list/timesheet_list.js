frappe.require("/assets/tag_workflow/js/tag.js");
frappe.listview_settings["Timesheet"] = {
  hide_name_column: true,
  add_fields: [
    "status",
    "total_hours",
    "start_date",
    "end_date",
    "from_date",
    "to_date",
  ],
  right_column: "name",
  refresh: function() {
    $("#navbar-breadcrumbs > li > a").html("Timesheets");
    $(".custom-actions.hidden-xs.hidden-md").hide();
    $('[data-original-title="Menu"]').hide();
    $("button.btn.btn-primary.btn-sm.btn-new-doc.hidden-xs").hide();
    $(
      ".col.layout-main-section-wrapper, .col-md-12.layout-main-section-wrapper"
    ).css("max-width", "86.5%");
    $(
      ".editable-form .layout-main-section-wrapper .layout-main-section, .submitted-form .layout-main-section-wrapper .layout-main-section, #page-Company .layout-main-section-wrapper .layout-main-section, #page-Timesheet .layout-main-section-wrapper .layout-main-section, #page-Lead .layout-main-section-wrapper .layout-main-section"
    ).css("max-width", "none");
    if (cur_list.doctype == "Timesheet") {
      cur_list.page.btn_primary[0].style.display = "none";
    }
    $('[data-original-title="Name"]').hide();
  },

  formatters: {
    total_hours(val, d, f) {
      if (typeof val == "number") {
        val = val.toFixed(2);
      }

      if (val == "") {
        return `<span class="filterable ellipsis" title="" id="${val}-${f.name}" ><a class="filterable ellipsis" data-filter="${d.fieldname},=,${val}" data-fieldname="${val}-${f.name}" >0.00</a></span>`;
      } else {
        return `<span class="filterable ellipsis" title="" id="${val}-${f.name}" ><a class="filterable ellipsis" data-filter="${d.fieldname},=,${val}" data-fieldname="${val}-${f.name}" >${val}</a></span>`;
      }
    },
    ts_exported(val, d) {
      if (val == 0) {
        return `<span class="ellipsis" title="Exported: ">
          <a class="filterable ellipsis" data-filter="${d.fieldname},=,${val}">
            No
          </a>
        </span>`;
      } else {
        return `<span class="ellipsis" title="Exported: ">
          <a class="filterable ellipsis" data-filter="${d.fieldname},=,${val}">
            Yes
          </a>
        </span>`;
      }
    },
  },
  onload: function(listview) {
    $('[data-fieldname="name"]').hide();
    jQuery(document).on("click", ".apply-filters", function() {
      let jo = "";
      $(".link-field")
        .find("input:text")
        .each(function() {
          jo = $(this).val();
        });
      localStorage.setItem("job_order", jo);
    });

    [cur_list.columns[2], cur_list.columns[3]] = [
      cur_list.columns[3],
      cur_list.columns[2],
    ];
    [cur_list.columns[2], cur_list.columns[4]] = [
      cur_list.columns[4],
      cur_list.columns[2],
    ];
    [cur_list.columns[4], cur_list.columns[6]] = [
      cur_list.columns[6],
      cur_list.columns[4],
    ];
    [cur_list.columns[5], cur_list.columns[6]] = [
      cur_list.columns[6],
      cur_list.columns[5],
    ];

    cur_list.render_header(cur_list);

    $('h3[title = "Timesheet"]').html("Timesheets");
    if (cur_list.doctype == "Timesheet") {
      cur_list.page.btn_primary[0].style.display = "none";
    }

    if (frappe.session.user != "Administrator") {
      $(".custom-actions.hidden-xs.hidden-md").hide();
      $('[data-original-title="Refresh"]').hide();
      $(".menu-btn-group").hide();
    }

    if (
      (frappe.boot.tag.tag_user_info.company_type == "Hiring" &&
        frappe.boot.tag.tag_user_info.company) ||
      (frappe.boot.tag.tag_user_info.company_type == "Exclusive Hiring" &&
        frappe.boot.tag.tag_user_info.company)
    ) {
      listview.page
        .set_secondary_action(
          '<svg class="icon icon-xs" style=""><use class="" href="#icon-add"></use></svg>Add/Edit Timesheet',
          function() {
            update_job_order(listview);
          }
        )
        .addClass("btn-primary");
    }
    add_filters(listview);
    export_ts_button(listview);
    if (frappe.boot.tag.tag_user_info.export_ts == 0) {
      listview.columns.splice(-1);
      listview.render_header(listview.columns);
    }
  },
};

/*-------------------------------*/
function update_job_order(listview) {
  if (cur_list.$checks.length == 0) {
    let flt = listview.filters || [];
    for (let f in flt) {
      if (flt[f][1] == "job_order_detail") {
        frappe.route_options = { job_order_detail: flt[f][3] };
      }
      if (flt[f][1] == "job_order") {
        frappe.route_options = { job_order_detail: flt[f][3] };
      }
    }
    frappe.set_route("form", "add-timesheet");
  } else {
    checking_selected_values(listview);
  }
}

function add_filters(listview) {
  const df1 = {
    condition: "like",
    default: null,
    fieldname: "employee_name",
    fieldtype: "Data",
    input_class: "input-xs",
    label: "Employee Name",
    is_filter: 1,
    onchange: function() {
      listview.refresh();
    },
    placeholder: "Employee Name",
  };
  const df2 = {
    condition: "=",
    default: null,
    fieldname: "employee_company",
    fieldtype: "Autocomplete",
    input_class: "input-xs",
    label: "Staffing Company",
    is_filter: 1,
    onchange: function() {
      listview.refresh();
    },
    options: get_company(),
    placeholder: "Staffing Company",
  };
  const df3 = {
    condition: "=",
    default: null,
    fieldname: "workflow_state",
    fieldtype: "Select",
    input_class: "input-xs",
    label: "Status",
    is_filter: 1,
    onchange: function() {
      listview.refresh();
    },
    options: ["Open", "Approval Request", "Approved", "Denied"],
    placeholder: "Status",
  };
  let standard_filters_wrapper = listview.page.page_form.find(
    ".standard-filter-section"
  );
  if (frappe.boot.tag.tag_user_info.company_type != "Staffing") {
    listview.page.add_field(df2, standard_filters_wrapper);
  } else {
    listview.columns.splice(6, 1);
    listview.render_header(listview.columns[6]);
    listview.refresh();
    $(".frappe-card").attr("id", "staffing_timesheet");
  }
  listview.page.add_field(df1, standard_filters_wrapper);
  listview.page.add_field(df3, standard_filters_wrapper);
  let doc_filter = document.querySelector(
    'select[data-fieldname = "workflow_state"]'
  );
  doc_filter.options.add(new Option(), 0);
}

function get_company() {
  let text = "";
  frappe.call({
    method: "tag_workflow.tag_data.timesheet_company",
    args: {
      hiring_company: frappe.boot.tag.tag_user_info.company,
    },
    async: 0,
    callback: function(r) {
      if (r.message) {
        text += r.message;
      }
    },
  });
  return text;
}

function checking_selected_values(listview) {
  let selected_values = [];
  for (const element of cur_list.$checks) {
    selected_values.push(element.dataset.name);
  }
  frappe.call({
    method: "tag_workflow.utils.timesheet.checking_same_values_timesheet",
    args: { user_selected_timesheet: selected_values },
    callback: function(r) {
      if (r.message == "Different Status") {
        frappe.msgprint("Only Timesheets in an open state can be edited.");
      } else if (
        r.message == "Different Job Order" ||
        r.message == "Different Job Order Dates"
      ) {
        frappe.msgprint(
          "Dates and Job Order ID are not consistent with all selected values. Please update your selection and try again."
        );
      } else {
        localStorage.setItem("job_order", r.message[1]);
        localStorage.setItem("date", r.message[2]);
        localStorage.setItem("timesheet_to_update", r.message[0]);
        frappe.set_route("form", "add-timesheet");
      }
    },
  });
}

$(document).on(
  "change",
  '[title="Select All"], .list-row-checkbox',
  function() {
    if (cur_list.$checks.length == 0) {
      $("#main_export_ts").hide();
    } else {
      $("#main_export_ts").show();
    }
  }
);

function export_ts_button(listview) {
  if (frappe.boot.tag.tag_user_info.export_ts == 1) {
    listview.page
      .set_secondary_action("Export Timesheets", () => {
        let selected_rows = cur_list.$checks;
        let ts_name = [];
        for (let i in selected_rows) {
          if (!isNaN(parseInt(i))) ts_name.push(selected_rows[i].dataset.name);
        }
        if (ts_name.length > 0) {
          export_csv(ts_name);
        }
      })
      .addClass("btn-primary")
      .attr("id", "main_export_ts");
    $("#main_export_ts").hide();
  }
}
