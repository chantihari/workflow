frappe.listview_settings["Sales Invoice"] = {
  onload: function (listview) {
    $('.primary-action').remove();
    [listview.columns[3],listview.columns[4],listview.columns[5],listview.columns[6]]=[listview.columns[4],listview.columns[5],listview.columns[6],listview.columns[3]]
    listview.columns[0].df.label = "Company";
    listview.columns[5].df.label = "Grand Total";
    listview.render_header(listview);
    document.getElementsByClassName(
       "list-row-col ellipsis"
    )[6].style.textAlign = "left";
    document.getElementsByClassName("list-row-col ellipsis")[5].classList.remove("text-right");
    document.getElementsByClassName("list-row-col ellipsis")[6].style.color = "#8d9cbc";
    document.getElementsByClassName("list-row-col ellipsis")[3].style.color = "#8d9cbc";
    listview.columns[3].df.label = "Job Order";
    listview.render_header(listview.columns[3]);
    listview.columns[6].df.label = "Paid";
    listview.render_header(listview.columns[6]);
    $('input[data-fieldname="name"]')[0].value = "";
    $('h3[title = "Invoice"]').html("Invoices");
    if (frappe.session.user != "Administrator") {
      $('[data-original-title="Refresh"]').hide();
      $(".menu-btn-group").hide();
    }
    $('[data-original-title="Job Order ID"]>div>div>input').attr(
      "placeholder",
      "Job Order"
    );
    $('[data-original-title="Customer"]>input').attr(
      "placeholder",
      "Company"
    );
    $('[data-original-title="Grand Total"]>input').val(null);
    if (frappe.boot.tag.tag_user_info.company_type == "TAG") {
      listview.page
        .add_button(__("Create monthly Invoice"), function () {
          create_monthly_invoice();
        })
        .addClass("btn-primary");
    }

    const filter = {
      condition: "=",
      default: null,
      fieldname: "docstatus",
      fieldtype: "Select",
      input_class: "input-xs",
      label: "Status",
      is_filter: 1,
      onchange: function () {
        listview.refresh();
      },
      options: [0, 1],
      placeholder: "Status",
    };
    let standard_filters_wrapper = listview.page.page_form.find(
      ".standard-filter-section"
    );
    listview.page.add_field(filter, standard_filters_wrapper);
    let doc_filter = document.querySelector(
      'select[data-fieldname = "docstatus"]'
    );
    doc_filter.options.add(new Option(), 0);
    doc_filter.options[1].innerHTML = "Draft";
    doc_filter.options[2].innerHTML = "Submitted";

    const filter_job_order = {
      condition: "like",
      default: null,
      fieldname: "job_order",
      fieldtype: "Data",
      input_class: "input-xs",
      label: "Job Order",
      is_filter: 1,
      onchange: function () {
        listview.refresh();
      },
      placeholder: "Job Order",
    };
    listview.page.add_field(filter_job_order, standard_filters_wrapper);

    const filter_date = {
      condition: "=",
      default: null,
      fieldname: "posting_date",
      fieldtype: "Date",
      input_class: "input-xs",
      label: "Date",
      is_filter: 1,
      onchange: function () {
        listview.refresh();
      },
      placeholder: "Date",
    };
    listview.page.add_field(filter_date, standard_filters_wrapper);
    $(
      '[data-original-title = "Date"][data-fieldname = "posting_date"]>input'
    ).hover(
      function () {
        /* this function is empty */
      },
      function () {
        listview.refresh();
      }
    );

    const filter_total = {
      condition: "=",
      default: null,
      fieldname: "total_billing_amount_premium",
      fieldtype: "Currency",
      input_class: "input-xs",
      label: "Grand Total",
      is_filter: 1,
      onchange: function () {
        listview.refresh();
      },
      placeholder: "Grand Total",
    };
    listview.page.add_field(filter_total, standard_filters_wrapper);

    const filters = {
      condition: "=",
      default: null,
      fieldname: "is_pos",
      fieldtype: "Select",
      input_class: "input-xs",
      label: "Paid Status",
      is_filter: 1,
      onchange: function () {
        listview.refresh();
      },
      options: [0, 1],
      placeholder: "Paid",
    };
    listview.page.add_field(filters, standard_filters_wrapper);
    let doc_filters = document.querySelector(
      'select[data-fieldname = "is_pos"]'
    );
    doc_filters.options.add(new Option(), "*");
    doc_filters.options[1].innerHTML = "Unpaid";
    doc_filters.options[2].innerHTML = "Paid";
  },
  formatters: {
    total_billing_amount_premium(val, _d, f) {
      let finalAmount = 0.0;
      if (typeof val == "number" && val > 0) {
        finalAmount = val.toFixed(2);
      } else {
        finalAmount = finalAmount.toFixed(2);
      }
      return `<div class="list-row-col ellipsis text-left "><span class="filterable ellipsis " title="" id="${val}-${f.name}" ><a class="filterable ellipsis" data-fieldname="${val}-${f.name}" >$ ${finalAmount}</a></span></div>`;
    },
    is_pos(val, d, f) {
      if (val == 1) {
        return `
				<div class="list-row-col ellipsis text-left" style="margin-right: 0px;">
				<span class="indicator-pill green ellipsis" title="" id="${val}-${f.name}">
						<a class=" green ellipsis" data-filter="${d.fieldname},=,${val}" data-fieldname="${val}-${f.name}" >Paid</a>
					</span>
					</div>`;
      }
      return `<span class=" ellipsis" title="" id="${val}-${f.name}" >
						<a data-filter="${d.fieldname},=,${val}" data-fieldname="${val}-${f.name}"> </a>
					</span>`;
    },
    job_order(val, _d, _f) {
      return `<span class="level-item  ellipsis" title="${val}">  <a href=${
        "/app/job-order/" + val
      } class="ellipsis"
				data-doctype= "Sales Invoice" data-name=${val} title="${val}" id="${val} data-jobname="name">
				${val}
				</a></span>`;
    },
    posting_date(val, _d, _f) {
      return `<span class="level-item  ellipsis" title="${val}">  <a class="ellipsis"
				data-doctype= "Sales Invoice" data-name=${val} title="${val}" id="${val} data-jobname="name">
				${val}
				</a></span>`;
    },
  },
  refresh: function () {
    $('[data-fieldname="name"]').hide();
    $("#navbar-breadcrumbs > li > a").html("Invoices");
    $('[class="btn btn-primary btn-sm primary-action"]').hide();
    $('[class="btn btn-default btn-sm ellipsis"]').hide();
    $("button.btn.btn-primary.btn-sm.btn-new-doc.hidden-xs").hide();
    let a = document.querySelector(
      '[data-original-title="Grand Total"]>input'
    ).value;
    if (a == 0.0) {
      $('[data-original-title="Grand Total"]>input').val("");
    }
    document.getElementsByClassName(
      "list-row-col ellipsis"
    )[6].style.textAlign = "left";
    document.getElementsByClassName("list-row-col ellipsis")[6].style.color =
      "#8d9cbc";
    document.getElementsByClassName("list-row-col ellipsis")[3].style.color =
      "#8d9cbc";
    document
      .getElementsByClassName("list-row-col ellipsis")[5]
      .classList.remove("text-right");
  },
  hide_name_column: true,
  // add_fields: ['type', 'reference_doctype', 'reference_name'],
  button: {
    show: function (doc) {
      return doc.name;
    },
    get_label: function () {
      return __("View Invoice");
    },
    get_description: function (doc) {
      return __("Open {0}", [`"Sales Invoice" ${doc.name}`]);
    },
    action: function (doc) {
      $(".custom-actions.hidden-xs.hidden-md").show();
      $('[class="btn btn-primary btn-sm primary-action"]').show();
      $('[class="btn btn-default btn-sm ellipsis"]').show();
      frappe.set_route("print-invoice", "Sales Invoice", doc.name);
    },
  },
};

function create_monthly_invoice() {
  let pop_up = new frappe.ui.Dialog({
    title: __("Monthly Staffing Sales Invoice"),
    fields: [
      {
        fieldname: "year",
        label: __("Start Year"),
        fieldtype: "Select",
        options: year_list(),
        reqd: 1,
        default: new Date().getUTCFullYear(),
        onchange: function () {
          month_list(cur_dialog);
        },
      },
      {
        fieldname: "month",
        label: "Month",
        fieldtype: "Select",
        options: current_month_year(),
        width: "80",
        default: "January",
        reqd: 1,
      },
      {
        fieldname: "company",
        fieldtype: "Select",
        options: get_staffing_company_list(),
        label: "staffing company",
        reqd: 1,
        onchange: function () {
          tag_staffing_charges(cur_dialog);
        },
      },
      {
        fieldname: "tag_charges",
        fieldtype: "Data",
        label: "Tag Charges",
        read_only: 1,
        depends_on: "eval: doc.company",
      },
    ],
    primary_action: function () {
      pop_up.hide();
      let staff_detail = pop_up.get_values();
      frappe.call({
        method: "tag_workflow.utils.invoice.make_month_invoice",
        freeze: true,
        freeze_message: "<p><b>Creating Monthly invoice ....</b></p>",
        args: {
          frm: staff_detail,
        },
        callback: function (rm) {
          if (rm.message) {
            frappe.show_alert(
              {
                message: __("Monthly Invoive created Succesfully"),
                indicator: "green",
              },
              5
            );
          }
        },
      });
    },
  });
  pop_up.show();
}

function month_list(dialog) {
  let year = parseInt(dialog.get_value("year"));
  let current_year = new Date().getUTCFullYear();

  if (year > current_year) {
    frappe.msgprint("future year is not accepted");
    cur_dialog.set_value("year", current_year);
    let op = current_month_year();
    dialog.set_df_property("month", "options", op);
  } else if (year < current_year) {
    let options1 =
      "January\nFebruary\nMarch\nApril\nMay\nJune\nJuly\nAugust\nSeptember\nOctober\nNovember\nDecember";
    dialog.set_df_property("month", "options", options1);
  } else {
    let month = current_month_year();
    dialog.set_df_property("month", "options", month);
  }
}

function tag_staffing_charges(dialog) {
  let company = dialog.get_value("company");
  if (company) {
    frappe.db.get_value(
      "Company",
      { name: company },
      ["tag_charges"],
      function (r) {
        if (r.tag_charges) {
          cur_dialog.set_value("tag_charges", r.tag_charges);
        }
      }
    );
  }
}

function current_month_year() {
  let months = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
  ];
  let options = "January";

  let cur_month = new Date().getMonth();

  for (let i = 1; i <= cur_month; i++) {
    options += "\n" + months[i];
  }
  return options;
}

function year_list() {
  let year_opt = "2021";
  let start_year = 2021;
  let current_year = new Date().getUTCFullYear();

  for (let i = start_year + 1; i <= current_year; i++) {
    year_opt += "\n" + i;
  }
  return year_opt;
}

function get_staffing_company_list() {
  let company = "";
  frappe.call({
    method: "tag_workflow.utils.whitelisted.get_staffing_company_list",
    args: { company_type: "Hiring" },
    async: 0,
    callback: function (r) {
      company += r.message;
    },
  });
  return company;
}

function get_staffing_company_invoices() {
  frappe.flags.company = null;
  frappe.call({
    method: "tag_workflow.utils.whitelisted.get_staffing_company_invoices",
    async: 0,
    callback: function (r) {
      frappe.flags.company = r.message;
    },
  });
  return frappe.flags.company;
}

frappe.views.ListView.prototype.get_column_html = function (col, doc) {
  if (col.type === "Status") {
    return `
<div class="list-row-col ellipsis">
${this.get_indicator_html(doc)}
</div>
`;
  }
  if (col.type === "Tag") {
    const tags_display_class = !this.tags_shown ? "hide" : "";
    let tags_html = doc._user_tags
      ? this.get_tags_html(doc._user_tags, 2)
      : '<div class="tags-empty">-</div>';
    return `
<div class="list-row-col tag-col ${tags_display_class} hidden-xs ellipsis">
${tags_html}
</div>
`;
  }
  return this.render_html(col, doc);
};

frappe.views.ListView.prototype.get_meta_html = function (doc) {
  let html = "";

  let settings_button = null;
  if (this.settings.button?.show(doc)) {
    settings_button = `
<span class="list-actions">
<button class="btn btn-action btn-primary btn-xs"
data-name="${doc.name}" data-idx="${doc._idx}"
title="${this.settings.button.get_description(doc)}">
${this.settings.button.get_label(doc)}
</button>
</span>
`;
  }

  const modified = comment_when(doc.modified, true);

  let assigned_to = `<div class="list-assignments">
<span class="avatar avatar-small">
<span class="avatar-empty"></span>
</div>`;

  let assigned_users = JSON.parse(doc._assign || "[]");
  if (assigned_users.length) {
    assigned_to = `<div class="list-assignments">
${frappe.avatar_group(assigned_users, 3, { filterable: true })[0].outerHTML}
</div>`;
  }

  const comment_count = `<span class="${
    !doc._comment_count ? "text-extra-muted" : ""
  } comment-count">
${frappe.utils.icon("small-message")}
${doc._comment_count > 99 ? "99+" : doc._comment_count}
</span>`;

  html += `
<div class="level-item list-row-activity ">
<div class="">
${settings_button || assigned_to}
</div>
${modified}
${comment_count}
</div>
<div class="level-item visible-xs text-right">
${this.get_indicator_dot(doc)}
</div>
`;

  return html;
};

frappe.views.ListView.prototype.get_header_html = function () {
  if (!this.columns) {
    return;
  }

  const subject_field = this.columns[0].df;
  let subject_html = `
<input class="level-item list-check-all" type="checkbox"
title="${__("Select All")}">
<span class="level-item list-liked-by-me hidden-xs">
<span title="${__("Likes")}">${frappe.utils.icon(
    "heart",
    "sm",
    "like-icon"
  )}</span>
</span>
<span class="level-item">${__(subject_field.label)}</span>
`;
  const $columns = this.columns
    .map((col) => {
      let classes = [
        "list-row-col ellipsis",
        col.type == "Subject" ? "list-subject level" : "",
        col.type == "Tag" ? "tag-col hide" : "",
        frappe.model.is_numeric_field(col.df) ? "text-right" : "",
      ].join(" ");

      return `
<div class="${classes}">
${
  col.type === "Subject"
    ? subject_html
    : `
<span>${__((col.df?.label) || col.type)}</span>`
}
</div>
`;
    })
    .join("");

  return this.get_header_html_skeleton(
    $columns,
    '<span class="list-count"></span>'
  );
};
frappe.views.ListView.prototype.render_html = function (col, doc) {
  const df = col.df || {};
  const label = df.label;
  const fieldname = df.fieldname;
  const value = doc[fieldname] || "";
  const format = () => {
    if (df.fieldtype === "Code") {
      return value;
    } else if (df.fieldtype === "Percent") {
      return `<div class="progress" style="margin: 0px;">
<div class="progress-bar progress-bar-success" role="progressbar"
aria-valuenow="${value}"
aria-valuemin="0" aria-valuemax="100" style="width: ${Math.round(value)}%;">
</div>
</div>`;
    } else {
      return frappe.format(value, df, null, doc);
    }
  };

  const field_html = () => {
    let html;
    let _value;
    let strip_html_required =
      df.fieldtype == "Text Editor" ||
      (df.fetch_from && ["Text", "Small Text"].includes(df.fieldtype));

    if (strip_html_required) {
      _value = strip_html(value);
    } else {
      _value =
        typeof value === "string" ? frappe.utils.escape_html(value) : value;
    }

    if (df.fieldtype === "Image") {
      html = df.options
        ? `<img src="${doc[df.options]}"
style="max-height: 30px; max-width: 100%;">`
        : `<div class="missing-image small">
${frappe.utils.icon("restriction")}
</div>`;
    } else if (df.fieldtype === "Select") {
      html = `<span class="filterable indicator-pill ${frappe.utils.guess_colour(
        _value
      )} ellipsis"
data-filter="${fieldname},=,${value}">
<span class="ellipsis"> ${__(_value)} </span>
</span>`;
    } else if (df.fieldtype === "Link") {
      html = `<a class="filterable ellipsis"
data-filter="${fieldname},=,${value}">
${_value}
</a>`;
    } else if (
      [
        "Text Editor",
        "Text",
        "Small Text",
        "HTML Editor",
        "Markdown Editor",
      ].includes(df.fieldtype)
    ) {
      html = `<span class="ellipsis">
${_value}
</span>`;
    } else {
      html = `<a class="filterable ellipsis"
data-filter="${fieldname},=,${frappe.utils.escape_html(value)}">
${format()}
</a>`;
    }

    return `<span class="ellipsis"
title="${__(label)}: ${frappe.utils.escape_html(_value)}">
${html}
</span>`;
  };

  const class_map = {
    Subject: "list-subject level",
    Field: " ",
  };
  const css_class = [
    "list-row-col ellipsis",
    class_map[col.type],
    frappe.model.is_numeric_field(df) ? "text-right" : "",
  ].join(" ");

  const html_map = {
    Subject: this.get_subject_html(doc),
    Field: field_html(),
  };
  let column_html = html_map[col.type];

  // listview_setting formatter
  if (this.settings.formatters?.[fieldname]) {
    column_html = this.settings.formatters[fieldname](value, df, doc);
  }
  return `
<div class="${css_class}">
${column_html}
</div>
`;
};
