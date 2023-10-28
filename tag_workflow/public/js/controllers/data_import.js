frappe.ui.form.off("Data Import", "show_import_warnings");
frappe.ui.form.off("Data Import", "import_file");
frappe.ui.form.off("Data Import", "start_import");
frappe.ui.form.on("Data Import", {
  before_save: function (frm) {
    if (frm.doc.__islocal == 1) {
      if (frappe.session.user != "Administrator") {
        cur_frm.set_value(
          "user_company",
          frappe.boot.tag.tag_user_info.company
        );
      } else {
        frappe.db.get_value(
          "User",
          { organization_type: "TAG" },
          ["company"],
          function (res) {
            frm.set_value("user_company", res["company"]);
          }
        );
      }
    }
  },
  refresh: function (frm) {
    $(".menu-btn-group").hide();
    $('[data-label="Save"]').hide();
    setTimeout(() => {
      $('[data-label="Start%20Import"]').show();
    }, 1500);

    let html_employee = `<span>Note: Bold Indicates required field</span><br><br><li> <strong>First Name</strong>: Max 140 characters, Alphanumeric</li>
        <li><strong>Last Name</strong>: Max 140 characters, Alphanumeric</li>
        
        <li><strong>Email</strong>: Max 140 characters, Alphanumeric &amp; formatted as <span style="color:#0052CC">abc@xyz.com</span></li>
        
        <li><strong>Company</strong>: The company as spelled within TAG and that the temp employee should be created. You can only add temp employees &nbsp;&nbsp;&nbsp;&nbsp; for companies you assigned.</li>
        
        <li><strong>Date of Birth</strong>: yyyy-MM-dd</li>
        
        <li><strong>Status</strong> : Active/Inactive/Suspended/Left</li>
        
        <li>Contact Number: Numbers only. 10 characters</li>
        
        <li>Gender: Female/Male/Decline to answer</li>
        
        <li>SSN: 9 numbers</li>
        
        <li>Military Veteran : 0 or blank for False; 1 for True</li>
        
        <li>Street Address: Max 255 characters, Alphanumeric</li>
        
        <li>Suite/Apartment Max 140 characters, Alphanumeric</li>
        
        <li>City : Max 255 characters, Alphanumeric</li>
        
        <li>State: Full spelling (ex: Florida)</li>
        <li>Zip : 5 characters, Numeric</li>`;

    let html_contact = `<span>Note: Bold Indicates required field</span><br><br>

        <li><strong>Company Name</strong>: Max 140 characters, Alphanumeric and special characters</li>
        
        <li><strong>Contact Name</strong>: Max 140 characters, Alphanumeric and special characters</li>
        
        <li><strong>Phone Number</strong>: Numbers only. 10 characters</li>
        
        <li><strong>Email Address</strong>: Max 140 characters, Alphanumeric and special characters</li>
        
        <li>Address: Max 140 characters, Alphanumeric and special characters</li>
        
        <li>City: Max 140 characters, Alphanumeric and special characters</li>
        
        <li>State: Full spelling (ex: Florida)</li>
        
        <li>Zip: 5 characters, Numeric</li>
        
        <li>Is Primary: 0 for False, 1 for True</li>`;

    if (frm.doc.reference_doctype && frm.doc.reference_doctype == "Contact") {
      frm.get_field("import_requirements").$wrapper.html(html_contact);
      frm.refresh_field("import_requirements");
    }

    if (frm.doc.reference_doctype && frm.doc.reference_doctype == "Employee") {
      frm.get_field("import_requirements").$wrapper.html(html_employee);
      frm.refresh_field("import_requirements");
    }
    frm.trigger("update_primary_action");
    uploaded_file_format(frm);
    data_import_values(frm);
  },
  setup: function (frm) {
    frm.set_query("reference_doctype", function () {
      return {
        query: "tag_workflow.utils.data_import.get_import_list",
        filters: {
          user_type: frappe.boot.tag.tag_user_info.company_type,
        },
      };
    });
  },
  reference_doctype: function (frm) {
    if (frm.doc.reference_doctype && frm.doc.reference_doctype == "Contact") {
      frm.set_value("import_type", "Insert New Records");
      frm.set_df_property("import_type", "read_only", 1);
    } else {
      frm.set_value("import_type", "");
      frm.set_df_property("import_type", "read_only", 0);
    }
  },
  import_type(frm) {
    if (frm.doc.reference_doctype && frm.doc.import_type) {
      frm.save();
    }
  },
  start_import(frm) {
    console.log(frm.doc.name);
    frappe
      .call({
        method: "tag_workflow.utils.data_import.form_start_import",
        args: { data_import: frm.doc.name },
        btn: frm.page.btn_primary,
      })
      .then((r) => {
        if (r.message === true) {
          frm.disable_save();
        }
      });
  },
  import_file(frm) {
    if (frm.doc.import_file) {
      frm.add_custom_button(__("Validate"), function () {
        $('[data-label="Save"]').hide();
        frm.toggle_display("section_import_preview", frm.has_import_file());
        frm.set_df_property("section_import_preview", "hidden", 0);
        if (!frm.has_import_file()) {
          frm.get_field("import_preview").$wrapper.empty();
          return;
        } else {
          frm.trigger("update_primary_action");
        }
        // load import preview
        frm.get_field("import_preview").$wrapper.empty();
        $('<span class="text-muted">')
          .html(__("Loading import file..."))
          .appendTo(frm.get_field("import_preview").$wrapper);
        frm
          .call({
            method: "get_preview_from_template",
            args: {
              data_import: frm.doc.name,
              import_file: frm.doc.import_file,
              google_sheets_url: frm.doc.google_sheets_url,
            },
            error_handlers: {
              TimestampMismatchError() {
                // ignore this error
              },
            },
          })
          .then((r) => {
            let preview_data = r.message;
            frm.events.show_import_preview(frm, preview_data);
          });
        frappe.call({
          method: "tag_workflow.utils.importer.read_file",
          args: {
            file: frm.doc.import_file,
            doctype: frm.doc.reference_doctype,
            comps: frappe.boot.tag.tag_user_info.comps,
            event:
              frm.doc.import_type == "Update Existing Records"
                ? "update"
                : "insert",
            user_type: frappe.boot.tag.tag_user_info.user_type,
          },
          callback: (res) => {
            validation_check(res, frm);
          },
        });
      });
    } else if (frm.doc.__islocal != 1) {
      let check = $('[data-label="Start%20Import"]');
      console.log(check.length);
      if (check.length > 0) {
        frm.set_df_property("section_import_preview", "hidden", 1);
        frm.set_df_property("validations_failed", "hidden", 1);
        frm.set_df_property("import_log_section", "hidden", 1);
        $('[data-label="Start%20Import"]').hide();
      }
    }
  },
});
function validation_check(res, frm) {
  console.log("res", res);
  if (res.message == "Wrong Columns") {
    let html = `<div><p><b>Column Should be in Original Formate</b></p>`;
    frm.set_df_property("validations_failed", "hidden", 0);
    frm.set_df_property("check_failed", "options", html);
  } else if (res.message && Object.keys(res.message).length > 0) {
    let hieght = 300;
    if (Object.keys(res.message).length < 5) {
      hieght = 200;
    }
    let html = `<div class="overflow-auto" id = "Error_list" style = "height: ${hieght}px;">`;
    for (let key in res.message) {
      let error = res.message[key].join(", ");
      let error_in_row = `<p><b>${key}</b>: ${error}</p>`;
      html += error_in_row;
    }
    html += "</div>";
    frm.set_df_property("validations_failed", "hidden", 0);
    frm.set_df_property("check_failed", "options", html);
  } else {
    let html = `<div><p><b>File is validated successfully</b></p>`;
    frm.set_df_property("validations_failed", "hidden", 0);
    frm.set_df_property("check_failed", "options", html);
    frm.save();
    frm.trigger("update_primary_action");
  }
}
function uploaded_file_format(frm) {
  frm.get_field("import_file").df.options = {
    restrictions: {
      allowed_file_types: [".csv", ".xlsx", ".xls"],
    },
  };
}
function data_import_values(frm) {
  if (
    frm.doc.__islocal == 1 &&
    frappe.route_history.length > 2 &&
    frappe.boot.tag.tag_user_info.company_type == "Staffing"
  ) {
    let histories = frappe.route_history.length;
    let get_old_reference = frappe.route_history[histories - 3][1];
    if (get_old_reference == "Contact") {
      frm.set_value("reference_doctype", "Contact");
      frm.set_value("import_type", "Insert New Records");
      frm.set_df_property("import_type", "read_only", 1);
      frm.set_df_property("reference_doctype", "read_only", 1);
    } else if (get_old_reference == "Employee") {
      frm.set_value("reference_doctype", "Employee");
      frm.set_df_property("reference_doctype", "read_only", 1);
    }
  }
}
