frappe.require("/assets/tag_workflow/js/staff_invoice_ratings.js");
frappe.ui.form.on("Sales Invoice", {
  onload: function (frm) {
    if (frappe.session.user != "Administrator") {
      $('[data-label="Get%20Items%20From"]').hide();
    }
    $('[data-fieldname="customer"]').click(function () {
      return false;
    });

    $("[data-fieldname=customer]").click(function () {
      let custt = frm.fields_dict.customer.value;
      localStorage.setItem("company", custt);
      window.location.href = "/app/dynamic_page";
    });
    setTimeout(function () {
      $('[data-label="Get%20Items%20From"]').hide();
      $('[data-label="View"]').hide();
      $('[data-label="Create"]').hide();
      $('[data-label="Fetch%20Timesheet"]').hide();
      $(".grid-footer")[0].style.display = "block";
    }, 550);
    if(frm.doc.month){
      frappe.meta.get_docfield(
        "Sales Invoice Item",
        "start_time",
        frm.doc.name
      ).hidden = 1;
      frappe.meta.get_docfield(
        "Sales Invoice Item",
        "start_time",
        frm.doc.name
      ).in_list_view = 0;
      frm.refresh_fields();
    }
  },
  refresh: function (frm) {
    $(".form-footer").hide();
    $('[data-original-title="Menu"]').hide();
    $('[class="btn btn-primary btn-sm primary-action"]').show();
    $(".custom-actions.hidden-xs.hidden-md").show();
    setTimeout(function () {
      $(".grid-footer")[0].style.display = "block";
    }, 550);
    frm.clear_custom_buttons();
    go_joborder_list(frm);
    if (frm.doc.__islocal == 1) {
      cancel_salesinvoice(frm);
    }
    $('[data-label="Save"]').show();
    check_staffing_reviews_invoice_page(frm);
    setTimeout(function () {
      $('[data-label="View"]').hide();
      $('[data-label="Get%20Items%20From"]').hide();
      $('[data-label="Create"]').hide();
      $('[data-label="Fetch%20Timesheet"]').hide();
    }, 250);

    $('[data-fieldname="company"]').click(function () {
      return false;
    });
    $('[data-fieldname="company"]').click(function () {
      if (frm.doc.company) {
        localStorage.setItem("company", frm.doc.company);
        window.location.href = "/app/dynamic_page";
      }
    });
    let child_table = [
      "item_code",
      "qty",
      "rate",
      "amount",
      "activity_type_time",
      "description",
      "from_time",
      "to_time",
      "billing_hours",
      "billing_amount",
      "sales_invoice_id",
      "job_order_id",
      "total_amount",
      "payment_term",
      "description",
      "due_date",
      "invoice_portion",
      "payment_amount",
    ];
    for (let i in child_table) {
      $("[data-fieldname=" + child_table[i] + "]").on(
        "mouseover",
        function (e) {
          let file = e.target.innerText;
          $(this).attr("title", file);
        }
      );
    }
    $('[data-label="Save"]').show();
    sync_with_quickbook(frm);
    $('[data-original-title="Printer"]').off("click");
    $('[data-original-title="Printer"]').on("click", () => {
      frappe.set_route("print-invoice", "Sales Invoice", frm.doc.name);
    });
  },
  on_submit: function (frm) {
    if (frm.doc.docstatus == 1) {
      frappe.call({
        method: "tag_workflow.tag_data.sales_invoice_notification",
        freeze: true,
        freeze_message:
          "<p><b>preparing notification for hiring orgs...</b></p>",
        args: {
          job_order: frm.doc.job_order,
          company: frm.doc.company,
          invoice_name: frm.doc.name,
          jo_company: frm.doc.customer
        },
      });

      let table = frm.doc.timesheets || [];

      if (table) {
        frappe.call({
          method:
            "tag_workflow.tag_data.update_timesheet_is_check_in_sales_invoice",
          args: {
            time_list: table,
            timesheet_used: frm.doc.timesheet_used,
          },
        });
      }
    }
  },
  before_save: function (frm) {
    let item = frm.doc.items || [];
    for (let i in item) {
      frappe.model.set_value(item[i].doctype, item[i].name, "item_code", "");
    }
    update_payment(frm);
    update_default_values(frm);
  },
  is_pos: function (frm) {
    if (frappe.user_roles.includes("System Manager")) {
      update_payment(frm);
    } else {
      check_timesheet(frm);
    }
  },

  posting_date: function (frm) {
    if (frm.doc.posting_date) {
      frm.clear_table("payment_schedule");
      frm.refresh_field("payment_schedule");
      let due_date = frappe.datetime.add_days(frm.doc.posting_date, 30);
      frm.set_value("due_date", due_date);
    }
  },
  due_date: function (frm) {
    frm.clear_table("payment_schedule");
    frm.refresh_field("payment_schedule");
  },
});

/*----------invoice table---------------*/
frappe.ui.form.on("Sales Invoice Item", {
  form_render: function (frm, cdt, cdn) {
    let child = frappe.get_doc(cdt, cdn);
    let table_fields = [
      "base_rate",
      "activity_type_time",
      "base_amount",
      "conversion_factor",
    ];
    for (let val in table_fields) {
      frm.fields_dict["items"].grid.grid_rows_by_docname[
        child.name
      ].toggle_display(table_fields[val], 0);
    }
    frm.refresh_fields()
  },
});

/*----------payments-----------*/
function check_timesheet(frm) {
  if (frm.doc.is_pos) {
    frappe.call({
      method: "tag_workflow.utils.whitelisted.check_timesheet",
      args: { job_order: frm.doc.job_order },
      callback: function (r) {
        let data = r.message;
        if (!data) {
          frm.set_value("is_pos", 0);
          frm.clear_table("payments");
          frm.refresh_field("payments");
        } else {
          update_payment(frm);
        }
      },
    });
  } else {
    frm.clear_table("payments");
    frm.refresh_field("payments");
  }
}

function update_payment(frm) {
  if (frm.doc.is_pos) {
    if (frm.doc.payments.length <= 0) {
      let child = frappe.model.get_new_doc(
        "Sales Invoice Payment",
        frm.doc,
        "payments"
      );
      $.extend(child, {
        mode_of_payment: "Cash",
        amount: frm.doc.grand_total,
      });
    } else {
      frm.doc.payments[0].amount = frm.doc.grand_total;
    }
  } else {
    frm.clear_table("payments");
    frm.refresh_field("payments");
  }
}

function update_default_values(frm) {
  frappe.db.get_value("Company", frm.doc.company, "abbr", (s) => {
    if (!frm.doc.debit_to) {
      frappe.db.get_value(
        "Company",
        frm.doc.company,
        "default_receivable_account",
        (d) => {
          if (!d.default_receivable_account) {
            let account = "1310 - Debtors - " + s.abbr;
            frappe.call({
              async: false,
              method: "frappe.client.set_value",
              args: {
                doctype: "Company",
                name: frm.doc.company,
                fieldname: "default_receivable_account",
                value: account,
              },
            });
            frm.set_value("debit_to", account);
          }
        }
      );
    }
    frm.doc.items.forEach(function (item) {
      if (!item.income_account) {
        frappe.db.get_value(
          "Company",
          frm.doc.company,
          "default_income_account",
          (d) => {
            if (!d.default_income_account) {
              let account2 = "4110 - Sales - " + s.abbr;
              frappe.call({
                async: false,
                method: "frappe.client.set_value",
                args: {
                  doctype: "Company",
                  name: frm.doc.company,
                  fieldname: "default_income_account",
                  value: account2,
                },
              });

              frm.set_value("income_account", account2);
            }
          }
        );
      }
    });
    frm.doc.items.forEach(function (item) {
      if (!item.cost_center) {
        frappe.db.get_value("Company", frm.doc.company, "cost_center", (d) => {
          cost_center_val_update(d, s, frm);
        });
      }
    });
  });
}

function cost_center_val_update(d, s, frm) {
  if (!d.cost_center) {
    let accountc = "Main - " + s.abbr;
    frappe.call({
      async: false,
      method: "frappe.client.set_value",
      args: {
        doctype: "Company",
        name: frm.doc.company,
        fieldname: "cost_center",
        value: accountc,
      },
    });
    frm.set_value("cost_center", accountc);
  }
}

function go_joborder_list(frm) {
  frm
    .add_custom_button(__("Go To Job Order List"), function () {
      frappe.set_route("List", "Job Order");
    })
    .addClass("btn-primary");
}

function cancel_salesinvoice(frm) {
  frm.add_custom_button(__("Cancel"), function () {
    frappe.set_route("Form", "Sales Invoice");
  });
}

/*--------------------QuickBooks Export------------------*/
function sync_with_quickbook(frm) {
  let roles = frappe.user_roles || [];
  if (
    !frm.doc.quickbook_invoice_id &&
    frm.doc.docstatus == 1 &&
    (roles.includes("Staffing Admin") ||
      roles.includes("Staffing User") ||
      roles.includes("Tag User") ||
      roles.includes("Tag Admin"))
  ) {
    frappe.db.get_value(
      "Company",
      { name: frm.doc.company },
      ["client_id", "client_secret", "quickbooks_company_id"],
      function (r) {
        if (r.client_id && r.client_secret && r.quickbooks_company_id) {
          frm
            .add_custom_button(__("Export to QuickBooks"), function () {
              insert_update_quickbook_invoice(frm);
            })
            .addClass("btn-primary");
        }
      }
    );
  } else if (frm.doc.quickbook_invoice_id) {
    frm.dashboard.set_headline(
      __(
        `<div style="display: flex;flex-direction: inherit;"><p>This Invoice was successfully exported to QuickBooks with quickbooks id: <b>${frm.doc.quickbook_invoice_id}</b></p></div>`
      )
    );
  }
}

function insert_update_quickbook_invoice(frm) {
  frappe.call({
    method: "tag_workflow.utils.quickbooks.auth_quickbook_and_sync",
    args: { company: frm.doc.company, invoice: frm.doc.name },
    freeze: true,
    freeze_message: "<p><b>Exporting to QuickBooks...</b></p>",
    callback: function (r) {
      let data = r.message;
      if (data.authorization_url) {
        frappe.msgprint(
          "Please Authenticate yourself before Migrating Data to Quickbook. We are now redirecting you to the Authentication page"
        );
        sleep(1500).then(() => {
          window.open(data.authorization_url);
        });
      } else if (data.invoice_id && !frm.doc.quickbook_invoice_id) {
        frappe.msgprint(
          "Invoice <b>" +
            frm.doc.name +
            "</b> successfully exported to QuickBooks."
        );
        frm.reload_doc();
      } else if (data.invoice_id && frm.doc.quickbook_invoice_id) {
        frappe.msgprint(
          "Invoice <b>" +
            frm.doc.name +
            "</b> successfully updated in QuickBooks."
        );
      } else if (data.error && !frm.doc.quickbook_invoice_id) {
        frappe.msgprint(
          "Invoice <b>" +
            frm.doc.name +
            "</b> failed to export with the following error: " +
            data.error +
            "."
        );
      } else if (data.error && frm.doc.quickbook_invoice_id) {
        frappe.msgprint(
          "Invoice <b>" +
            frm.doc.name +
            "</b> failed to update with the following error: " +
            data.error +
            "."
        );
      }
    },
  });
}

// sleep time expects milliseconds
function sleep(time) {
  return new Promise((resolve) => setTimeout(resolve, time));
}
