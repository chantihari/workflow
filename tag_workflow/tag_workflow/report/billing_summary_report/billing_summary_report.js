// Copyright (c) 2016, SourceFuse and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Billing Summary Report"] = {
  filters: [
    {
      fieldname: "start_date",
      label: "From Date",
      fieldtype: "Date",
      width: "100",
      reqd: 0,
      default: frappe.datetime.month_start(),
    },
    {
      fieldname: "end_date",
      label: "To Date",
      fieldtype: "Date",
      width: "100",
      reqd: 0,
      default: frappe.datetime.get_today(),
    },
    {
      fieldname: "companies",
      label: "Staffing Company Name",
      fieldtype: "Data",
      width: "100",
      reqd: 0,
    },
    {
      fieldname: "job_sites",
      label: "Job Site",
      fieldtype: "Link",
      options: "Job Site",
      width: "100",
      reqd: 0,
    },
  ],
  formatter: function (value, row, column, data, default_formatter) {
    value = default_formatter(value, row, column, data);
    if (value.includes("<br>") && row.length) {
      let row_no = row["meta"]["rowIndex"];
      let my_list = value.split("<br>");
      let tooltip_values = [];
      my_list.forEach((ele) => {
        tooltip_values.push("&#x2022 " + ele);
      });
      tooltip_values = tooltip_values.join("<br>");
      value =
        `<div data-toggle="popover" data-placement="right" id="report_${row_no}" onclick="showcasepopover('${row_no}', '${tooltip_values}')" onclick = "hideCasePopover('${row_no}')" style="cursor: pointer;"><u>Multiple Locations</u>` +
        ` (${my_list.length})` +
        `</div><br>` +
        my_list.join(" ");
    }
    return value;
  },
};

function showcasepopover(row_no, content) {
  $("#report_" + row_no)
    .popover({
      placement: "right",
      content: function () {
        return content;
      },
      html: true,
    })
    .popover("show");
}

function hideCasePopover(row_no) {
  $("#report_" + row_no).popover("hide");
}

function hide_tooltip() {
  $('[role = "tooltip"]').popover("dispose");
}

$(document).on("shown.bs.popover", '[data-toggle="popover"]', function () {
  let popoverElement = document.getElementsByClassName("popover");
  $(popoverElement).on("mouseover", function () {
    document.body.removeEventListener("scroll", hide_tooltip, true);
  });
  $(popoverElement).on("mouseout", function () {
    document.body.addEventListener("scroll", hide_tooltip, true);
  });
});

document.body.addEventListener("click", hide_tooltip, true);
document.body.addEventListener("input", hide_tooltip, true);

$("[data-route='query-report/Billing Summary Report'] .sub-heading").html(
  "A report showing the billing summary across all staffing companies and jobsites."
);
