frappe.require("/assets/tag_workflow/js/twilio_utils.js");
frappe.require("/assets/tag_workflow/js/emp_functions.js");
frappe.ui.form.off("Employee Onboarding", "refresh");
frappe.ui.form.on("Employee Onboarding", {
  setup: (frm) => {
    frm.set_query("staffing_company", function () {
      return {
        filters: [
          ["Company", "organization_type", "=", "Staffing"],
          ["Company", "make_organization_inactive", "=", 0],
          ["Company", "enable_ats", "=", 1],
        ],
      };
    });
    set_company(frm, "staffing_company");
    frm.set_query("employee_onboarding_template", function () {
      return {
        filters: [
          [
            "Employee Onboarding Template",
            "company",
            "=",
            frm.doc.staffing_company,
          ],
        ],
      };
    });
    get_user(frm, frm.doc.staffing_company);
  },
  onload: (frm) => {
    trigger_hide(frm);
    if (frm.is_new()) {
      frm.set_value("status", "Pending");
    }
    setTimeout(() => {
      $('[data-label = "View"]').hide();
      $('[data-label = "Cancel"]').hide();
    }, 250);
  },
  refresh: (frm) => {
    check_perm();
    core_functions(frm);
    $(".form-footer").hide();
    setTimeout(() => {
      $('[data-label = "Cancel"]').hide();
    }, 250);
    set_map(frm);
    show_addr(frm);
    hide_field(frm);
    $('[data-fieldname = "contact_number"]>div>div>div>input').attr(
      "placeholder",
      "Example: +XX XXX-XXX-XXXX"
    );
    password_fields(frm);
  },
  onload_post_render: (frm) => {
    if (frm.doc.search_on_maps) {
      setTimeout(() => {
        $('.frappe-control[data-fieldname="map"]').removeClass("hide-control");
      }, 1000);
    }
  },
  validate: (frm) => {
    let reqd_fields = {
      "First Name": frm.doc.first_name,
      "Last Name": frm.doc.last_name,
      Email: frm.doc.email,
      Company: frm.doc.staffing_company,
      "Template Name": frm.doc.template_name,
      Activities: frm.doc.activities,
    };
    mandatory_fields(reqd_fields);
    validate_phone_zip(frm);
    if (frm.doc.sssn && frm.doc.sssn.toString().length != 9) {
      frm.set_value("ssn", "");
      frm.set_value("sssn", "");
      frappe.msgprint(
        __("Minimum and Maximum Characters allowed for SSN are 9.")
      );
      frappe.validated = false;
    }
    frappe.validated = !check_ssn(frm) ? false : frappe.validated;

    let email = frm.doc.email;
    if (
      email &&
      email != undefined &&
      (email.length > 120 || !frappe.utils.validate_type(email, "email"))
    ) {
      frappe.msgprint({ message: __("Not A Valid Email"), indicator: "red" });
      frappe.validated = false;
    }

    if (frm.doc.first_name && frm.doc.last_name) {
      frm.set_value(
        "employee_name",
        frm.doc.first_name.trim() + " " + frm.doc.last_name.trim()
      );
    }

    if (frm.doc.__islocal == 1 && frappe.validated) {
      create_job_applicant_and_offer(frm);
    }
  },
  before_save: (frm) => {
    let today_date = frm.doc.date_of_joining
      ? frm.doc.date_of_joining
      : frappe.datetime.get_today();
    frm.set_value("date_of_joining", today_date);
    if (frm.doc.status) {
      frm.set_value("boarding_status", frm.doc.status);
    }
    remove_lat_lng(frm);
  },
  before_submit: (frm) => {
    let today_date = frm.doc.date_of_joining
      ? frm.doc.date_of_joining
      : frappe.datetime.get_today();
    frm.set_value("date_of_joining", today_date);
    frappe.call({
      method: "tag_workflow.tag_data.check_employee",
      args: {
        onb_email: frm.doc.email,
      },
      callback: (r) => {
        let msg = "";
        if (r.message) {
          if (!frm.doc.date_of_birth) {
            msg +=
              "Please fill Date of Birth before submitting the form.<hr>An Employee already exists with the same email. Please modify the email address.";
          } else {
            msg +=
              "An Employee already exists with the same email. Please modify the email address.";
          }
        } else if (!frm.doc.date_of_birth) {
          msg += "Please fill Date of Birth before submitting the form.";
        }
        if (msg != "") {
          frappe.msgprint({
            message: __(msg),
            title: __("Warning!"),
            indicator: "orange",
          });
          frappe.validated = false;
        }
      },
    });
  },
  first_name: (frm) => {
    if (frm.doc.first_name) {
      let first_name = frm.doc.first_name.trim();
      first_name = name_update(first_name);
      frm.set_value("first_name", first_name);
    }
  },
  last_name: (frm) => {
    if (frm.doc.last_name) {
      let last_name = frm.doc.last_name.trim();
      last_name = name_update(last_name);
      frm.set_value("last_name", last_name);
    }
  },
  staffing_company: (frm) => {
    get_user(frm);
    get_template_name(frm);
    get_holiday_list(frm);
  },
  status: (frm) => {
    frm.set_value("boarding_status", frm.doc.status);
  },
  contact_number: (frm) => {
    let contact = frm.doc.contact_number;
    if (contact) {
      frm.set_value(
        "contact_number",
        validate_phone(contact) ? validate_phone(contact) : contact
      );
    }
  },
  date_of_birth: (frm) => {
    let dob = frm.doc.date_of_birth || "";
    if (dob && dob >= frappe.datetime.year_start()) {
      frappe.msgprint({
        message: __("<b>Birth Year</b> must be earlier than this year."),
        title: __("Error"),
        indicator: "orange",
      });
      frm.set_value("date_of_birth", "");
    }
  },
  search_on_maps: (frm) => {
    if (frm.doc.search_on_maps == 1) {
      tag_workflow.UpdateField(frm, "map");
      hide_field(frm);
      show_addr(frm);
      update_complete_address(frm);
    } else if (frm.doc.search_on_maps == 0 && cur_frm.doc.enter_manually == 0) {
      frm.set_df_property("map", "hidden", 1);
      show_addr(frm);
    }
  },
  enter_manually: (frm) => {
    if (frm.doc.enter_manually == 1) {
      tag_workflow.UpdateField(frm, "manually");
      show_fields(frm);
      show_addr(frm);
    } else if (frm.doc.search_on_maps == 0 && frm.doc.enter_manually == 0) {
      frm.set_df_property("map", "hidden", 1);
      hide_field(frm);
      show_addr(frm);
    }
  },
  zip: (frm) => {
    let zip = frm.doc.zip;
    frm.set_value("zip", zip ? zip.toUpperCase() : zip);
  },
  on_submit: function (frm) {
    frappe.db.get_value(
      "Company",
      { name: frm.doc.staffing_company },
      ["workbright_subdomain", "workbright_api_key"],
      (r) => {
        if (r.workbright_subdomain && r.workbright_api_key) {
          let company_name = frm.doc.staffing_company;
          let first_name = frm.doc.first_name;
          let last_name = frm.doc.last_name;
          let job_applicant = frm.doc.job_applicant;
          let contact_number = frm.doc.contact_number;
          let complete_address = frm.doc.complete_address;
          let employee_gender = frm.doc.gender;
          let date_of_birth = frm.doc.date_of_birth;
          let ssn = frm.doc.sssn;
          frappe.call({
            method:
              "tag_workflow.utils.workbright_integration.workbright_create_employee",
            args: {
              frm: frm.doc.name,
              company_name: company_name,
              first_name: first_name,
              last_name: last_name,
              job_applicant: job_applicant,
              contact_number: contact_number,
              complete_address: complete_address,
              employee_gender: employee_gender,
              date_of_birth: date_of_birth,
              decrypted_ssn: ssn,
            },
            callback: function (reponse) {
              if (reponse["message"]["status"] == 200) {
                frappe.call({
                  method:
                    "tag_workflow.utils.workbright_integration.save_workbright_employee_id",
                  args: {
                    job_applicant: job_applicant,
                    workbright_emp_id: reponse["message"]["workbright_emp_id"],
                  },
                  callback: function (db_response) {
                    if (db_response) {
                      frappe.msgprint({
                        message: __(
                          "Employee successfully created in Workbright!"
                        ),
                      });
                    }
                  },
                });
              } else {
                frappe.msgprint({
                  message: __("Employee cannot be created in Workbright!"),
                });
              }
            },
          });
        }
      }
    );
  },
  template_name: (frm) => {
    if (frm.doc.template_name) {
      frappe.db.get_value(
        "Employee Onboarding Template",
        {
          company: frm.doc.staffing_company,
          template_name: frm.doc.template_name,
        },
        ["name"],
        (res) => {
          if (res?.name) {
            frm.set_value("employee_onboarding_template", res.name);
          }
        }
      );
    }
  },
});

function trigger_hide(frm) {
  $(".form-footer").hide();
  let fields = [
    "job_applicant",
    "job_offer",
    "employee_name",
    "company",
    "project",
    "department",
    "designation",
    "employee_grade",
  ];
  for (let i in fields) {
    frm.set_df_property(fields[i], "hidden", 1);
  }
}

const html = `<!doctype html>
	<html>
		<head>
			<meta charset="utf-8">
		</head>
		<body>
			<input class="form-control" placeholder="Search a location" id="autocomplete-address" style="height: 30px;margin-bottom: 15px;">
			<div class="tab-content" title="map" style="text-align: center;padding: 4px;">
				<div id="map" style="height:450px;border-radius: var(--border-radius-md);"></div>
			</div>
		</body>
	</html>
`;

function set_map(frm) {
  setTimeout(() => {
    $(frm.fields_dict.map.wrapper).html(html);
    initMap();
  }, 500);
}

function hide_field(frm) {
  frm.set_df_property(
    "city",
    "hidden",
    frm.doc.city && frm.doc.enter_manually == 1 ? 0 : 1
  );
  frm.set_df_property(
    "state",
    "hidden",
    frm.doc.state && frm.doc.enter_manually == 1 ? 0 : 1
  );
  frm.set_df_property(
    "zip",
    "hidden",
    frm.doc.zip && frm.doc.enter_manually == 1 ? 0 : 1
  );
}

function create_job_applicant_and_offer(frm) {
  let args = {
    applicant_name: frm.doc.employee_name,
    email: frm.doc.email,
    company: frm.doc.staffing_company,
  };
  if (frm.doc.contact_number) {
    args.contact_number = frm.doc.contact_number;
  }
  frappe.call({
    method: "tag_workflow.tag_data.create_job_applicant_and_offer",
    args: args,
    callback: (r) => {
      if (r.message) {
        frm.set_value("job_applicant", r.message[0]);
        frm.set_value("job_offer", r.message[1]);
      } else {
        frappe.validated = false;
      }
    },
  });
}

frappe.ui.form.on("Employee Boarding Activity", {
  form_render: (frm, cdt, cdn) => {
    check_count(frm, cdt, cdn);
  },
  document_required: (frm, cdt, cdn) => {
    document_required(frm, cdt, cdn);
  },
  document: (frm, cdt, cdn) => {
    document_field(frm, cdt, cdn);
  },
});

function core_functions(frm) {
  if (!frm.doc.employee && frm.doc.docstatus === 1) {
    frm.add_custom_button(
      __("Employee"),
      function () {
        validate_employee(frm);
      },
      __("Create")
    );
    frm.page.set_inner_btn_group_as_primary(__("Create"));
  }
}

function validate_employee(frm) {
  let activities = frm.doc.activities;
  if (frm.doc.docstatus != 1) {
    frappe.msgprint(__("Submit this to create the Employee record."));
  } else if (activities) {
    frappe.call({
      method: "tag_workflow.tag_data.validate_employee_creation",
      args: {
        emp_onb_name: frm.doc.name,
      },
      callback: (r) => {
        if (!r.message) {
          confirmation(frm);
        } else if (Array.isArray(r.message)) {
          confirmation(frm, r.message[0], r.message[1]);
        } else {
          frappe.model.open_mapped_doc({
            method: "tag_workflow.tag_data.make_employee",
            frm: frm,
          });
        }
      },
    });
  } else {
    frappe.model.open_mapped_doc({
      method: "tag_workflow.tag_data.make_employee",
      frm: frm,
    });
  }
}

function confirmation(frm, incomplete_tasks = [], task_ids = []) {
  return new Promise(function (resolve) {
    let message =
      "Onboard Employee Status not set to 'Completed'. Do you wish to create the employee record?";
    let args = { docname: frm.doc.name };
    if (incomplete_tasks.length > 0) {
      message =
        "The following Onboard Employee Tasks are not set to 'Completed'. Do you wish to create the employee record?";
      for (let i in incomplete_tasks) {
        message += "<br>" + "<span>&bull;</span> " + incomplete_tasks[i];
      }
      args["tasks_list"] = task_ids;
    }
    frappe.confirm(message, () => {
      frappe.call({
        method: "tag_workflow.tag_data.set_status_complete",
        args: args,
      });
      frappe.model.open_mapped_doc({
        method: "tag_workflow.tag_data.make_employee",
        frm: frm,
      });
      resolve();
    });
  });
}

function password_fields(frm) {
  if (frm.doc.__islocal != 1 && frm.doc.docstatus == 0) {
    get_template_name(frm, "Template Defined");
    $('[data-fieldname="sssn"]').attr("readonly", "readonly");
    $('[data-fieldname="sssn"]').attr("type", "password");
    $('[data-fieldname="sssn"]').attr("title", "");
    let button_html = `<button class="btn btn-default btn-more btn-sm" id="decrypt" onclick="show_decrypt(this.id)" style="width: 60px;height: 25px;padding: 3px;">Decrypt</button>
		<button class="btn btn-default btn-more btn-sm" id="edit_off" onclick="edit_pass(this.id)" style="width: 45px;height: 25px;padding: 3px;float: right;">Edit</button>`;
    frm.set_df_property("ssn_html", "options", button_html);
  }
}

window.edit_pass = (id) => {
  if (id == "edit_off") {
    $('[data-fieldname="sssn"]').removeAttr("readonly");
    $('[data-fieldname="sssn"]').attr("type", "text");
    $("#decrypt").hide();
    $("#encrypt").hide();
    $("#edit_off").hide();
    $("#edit_off").attr("id", "edit_on");
    show_pass();
  }
};

window.show_decrypt = (id) => {
  if (id == "decrypt") {
    $('[data-fieldname="sssn"]').attr("type", "text");
    $("#decrypt").text("Encrypt");
    $("#decrypt").attr("id", "encrypt");
    show_pass();
  } else {
    hide_pass();
    $('[data-fieldname="sssn"]').attr("type", "password");
    $("#encrypt").text("Decrypt");
    $("#encrypt").attr("id", "decrypt");
  }
};

function show_pass() {
  frappe.call({
    method: "tag_workflow.tag_data.api_sec",
    args: {
      doctype: cur_frm.doc.doctype,
      frm: cur_frm.doc.name,
    },
    callback: (res) => {
      if (res.message != "Not Found") {
        cur_frm.set_value("sssn", res.message);
      } else if (cur_frm.doc.sssn) {
        cur_frm.set_value("sssn", "•".repeat(cur_frm.doc.sssn.length));
      } else {
        cur_frm.set_value("sssn", "");
      }
    },
  });
}

function hide_pass() {
  if (cur_frm.doc.sssn) {
    cur_frm.set_value("sssn", "•".repeat(cur_frm.doc.sssn.length));
  }
}

frappe.ui.form.on("Employee Boarding Activity", {
  status: (frm, cdt, cdn) => {
    const row = locals[cdt][cdn];
    if (row.status && row.status == "Completed") {
      console.log(frappe.meta.get_docfield);
      frm.fields_dict["activities"].grid.grid_rows_by_docname[
        row.name
      ].toggle_editable("completed_on", 1);
      frm.fields_dict["activities"].grid.grid_rows_by_docname[
        row.name
      ].toggle_reqd("completed_on", 1);
      frappe.model.set_value(
        cdt,
        cdn,
        "completed_on",
        frappe.datetime.now_date()
      );
      frm.fields_dict["activities"].grid.grid_rows_by_docname[
        row.name
      ].refresh_field("completed_on");
    } else if (row.status && row.status != "Completed") {
      frm.fields_dict["activities"].grid.grid_rows_by_docname[
        row.name
      ].toggle_editable("completed_on", 0);
      frappe.model.set_value(cdt, cdn, "completed_on", undefined);
      frm.fields_dict["activities"].grid.grid_rows_by_docname[
        row.name
      ].toggle_reqd("completed_on", 0);
      frm.fields_dict["activities"].grid.grid_rows_by_docname[
        row.name
      ].refresh_field("completed_on");
    }
  },
});

function get_template_name(frm, message = "") {
  if (frm.doc.staffing_company) {
    frappe.call({
      method: "tag_workflow.tag_data.get_template_name",
      args: {
        company: frm.doc.staffing_company,
      },
      callback: (res) => {
        if (res.message[0]) {
          frm.set_df_property("template_name", "options", res.message[0]);
        } else {
          frm.set_df_property("template_name", "options", "");
        }

        if (res.message[1] && !message) {
          frm.set_value("template_name", res.message[1]);
        }
      },
    });
  }
}

function get_holiday_list(frm) {
  frappe.db.get_value(
    "Company",
    { name: frm.doc.staffing_company },
    ["enable_ats", "default_holiday_list"],
    (res) => {
      if (res.enable_ats == 1 && res.default_holiday_list) {
        frm.set_value("holiday_list", res.default_holiday_list);
      }
    }
  );
}
