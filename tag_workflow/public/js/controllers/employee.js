frappe.require("/assets/tag_workflow/js/twilio_utils.js");
frappe.require("/assets/tag_workflow/js/emp_functions.js");
frappe.ui.form.on("Employee", {
  refresh: function (frm) {
    $("#employee-basic_details_tab > div:nth-child(5)").hide();
    $('[class="btn btn-primary btn-sm primary-action"]').show();
    $(".custom-actions.hidden-xs.hidden-md").show();
    update_employees_data(frm);
    $("button.ellipsis:nth-child(1)").hide();
    hide_sync_btn(frm);
    trigger_hide();
    required_field();
    employee_work_history(frm);
    employee_timesheets(frm);
    download_document(frm);
    uploaded_file_format(frm);
    if (frm.doc.__islocal == 1) {
      cancel_employee(frm);
      tag_company(frm);
    }
    employee_delete_button(frm);
    set_map(frm);
    hide_field(frm);
    show_addr(frm);
    $('*[data-fieldname="block_from"]')
      .find(".grid-add-row")[0]
      .addEventListener("click", function () {
        const li = [];
        frm.doc.block_from.forEach((element) => {
          li.push(element.blocked_from);
        });
        frappe.call({
          method: "tag_workflow.utils.whitelisted.get_orgs",
          args: {
            company: frappe.boot.tag.tag_user_info.company,
            employee_lis: li,
          },
          callback: function (r) {
            if (r) {
              frm.fields_dict.block_from.grid.update_docfield_property(
                "blocked_from",
                "options",
                [""].concat(r.message)
              );
            }
          },
        });
      });

    window.onclick = function () {
      attachrefresh();
    };

    $('*[data-fieldname="miscellaneous"]')
      .find(".grid-add-row")[0]
      .addEventListener("click", function () {
        attachrefresh();
      });

    $("[data-fieldname=miscellaneous]").mouseover(function () {
      attachrefresh();
    });

    $('*[data-fieldname="background_check_or_drug_screen"]')
      .find(".grid-add-row")[0]
      .addEventListener("click", function () {
        attachrefresh();
      });

    $("[data-fieldname=background_check_or_drug_screen]").mouseover(
      function () {
        attachrefresh();
      }
    );

    $('*[data-fieldname="id_requirements"]')
      .find(".grid-add-row")[0]
      .addEventListener("click", function () {
        attachrefresh();
      });

    $("[data-fieldname=id_requirements]").mouseover(function () {
      attachrefresh();
    });

    $('*[data-fieldname="direct_deposit_letter"]')
      .find(".grid-add-row")[0]
      .addEventListener("click", function () {
        attachrefresh();
      });

    $("[data-fieldname=direct_deposit_letter]").mouseover(function () {
      attachrefresh();
    });

    attachrefresh();

    $(document).on("click", '[data-fieldname="company"]', function () {
      setTimeout(() => {
        $('[data-fieldname="company"]').find(".link-btn").addClass("hide");
      }, 300);
    });

    $('[data-fieldname="company"]').mouseover(function () {
      setTimeout(() => {
        $('[data-fieldname="company"]').find(".link-btn").addClass("hide");
      }, 500);
    });

    document.addEventListener("keydown", function () {
      setTimeout(() => {
        $('[data-fieldname="company"]').find(".link-btn").addClass("hide");
      }, 400);
    });

    $('[data-fieldname="company"]').click(function () {
      if (cur_frm.doc.__islocal !== 1) {
        setTimeout(() => {
          let cust = cur_frm.fields_dict.company.value;
          localStorage.setItem("company", cust);
          window.location.href = "/app/dynamic_page";
        }, 600);
      }
    });

    $(document).on("click", '[data-fieldtype="Attach"]', function () {
      setTimeout(() => {
        document.getElementsByClassName("modal-title")[0].innerHTML =
          "Upload <h6>(Accepted File Type : pdf, txt or docx ,png ,jpg only, file size 10mb) </h6>";
      }, 300);
    });

    $(document).on("click", '[data-fieldname="resume"]', function () {
      filerestriction();
    });

    $(document).on("click", '[data-fieldname="w4"]', function () {
      filerestriction();
    });

    $(document).on("click", '[data-fieldname="miscellaneous"]', function () {
      filerestriction();
    });

    let child_table = [
      "job_category",
      "blocked_from",
      "no_show_company",
      "job_order",
      "date",
      "unsatisfied_organization_name",
      "dnr",
      "id_requirements",
      "direct_deposit_letter",
      "drug_screen",
      "attachments",
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
    $('[data-fieldname= "ssn"]').attr("title", "");
    $('[data-fieldname = "contact_number"]>div>div>div>input').attr(
      "placeholder",
      "Example: +XX XXX-XXX-XXXX"
    );
    password_fields(frm);
  },

  resume: function (frm) {
    if (
      frm.doc.resume &&
      !hasExtensions(frm.doc.resume, [".pdf", ".txt", ".docx", ".png", "jpg"])
    ) {
      let array = frm.doc.resume.split("/");
      let file_name = array[array.length - 1];
      frappe.call({
        method: "tag_workflow.tag_data.delete_file_data",
        args: { file_name: file_name },
      });

      frm.set_value("resume", "");
      refresh_field("resume");
      frappe.msgprint("Upload Wrong File type in Resume");
    }
  },

  validate: function (frm) {
    let reqd_fields = {
      "First Name": frm.doc.first_name,
      "Last Name": frm.doc.last_name,
      Company: frm.doc.company,
      "Date of Birth": cur_frm.doc.date_of_birth,
      Email: cur_frm.doc.email,
      Status: frm.doc.status,
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

    if (
      frm.doc.employee_job_category &&
      frm.doc.employee_job_category.length > 0
    ) {
      frm.set_value(
        "job_category",
        frm.doc.employee_job_category[0]["job_category"]
      );
    } else {
      frm.set_value("job_category", null);
    }
    append_job_category(frm);
  },

  before_save: function (frm) {
    remove_lat_lng(frm);
    job_title_filter(frm);
    frm.doc.date_of_joining = frappe.datetime.get_today();
  },
  setup: function (frm) {
    frm.set_query("company", function () {
      return {
        filters: [
          ["Company", "organization_type", "in", ["Staffing"]],
          ["Company", "make_organization_inactive", "=", 0],
        ],
      };
    });
  },
  after_save: function (frm) {
    update_lat_lng(frm);
  },

  search_on_maps: function (frm) {
    if (cur_frm.doc.search_on_maps == 1) {
      tag_workflow.UpdateField(frm, "map");
      hide_field(frm);
      show_addr(frm);
      update_complete_address(frm);
    } else if (
      cur_frm.doc.search_on_maps == 0 &&
      cur_frm.doc.enter_manually == 0
    ) {
      cur_frm.set_df_property("map", "hidden", 1);
      show_addr(frm);
    }
  },

  enter_manually: function (frm) {
    if (cur_frm.doc.enter_manually == 1) {
      tag_workflow.UpdateField(frm, "manually");
      show_fields(frm);
      show_addr(frm);
    } else if (
      cur_frm.doc.search_on_maps == 0 &&
      cur_frm.doc.enter_manually == 0
    ) {
      cur_frm.set_df_property("map", "hidden", 1);
      hide_field(frm);
      show_addr(frm);
    }
  },
  onload_post_render: function (frm) {
    if (frm.doc.search_on_maps) {
      setTimeout(() => {
        $('.frappe-control[data-fieldname="map"]').removeClass("hide-control");
      }, 1000);
    }
  },
  contact_number: function (frm) {
    let contact = frm.doc.contact_number;
    if (contact) {
      frm.set_value(
        "contact_number",
        validate_phone(contact) ? validate_phone(contact) : contact
      );
    }
  },
  zip: function (frm) {
    let zip = frm.doc.zip;
    frm.set_value("zip", zip ? zip.toUpperCase() : zip);
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
  }
});

function get_args(frm) {
  let args = {};
  if (frm.doc.__islocal == 1) {
    if (frm.doc.sssn && !frm.doc.ssn) {
      args["ssn"] = frm.doc.sssn;
    }
    if (frm.doc.date_of_birth) {
      args["dob"] = frm.doc.date_of_birth;
    }
  } else {
    args["emp_id"] = frm.doc.name;
    args["doctype"] = "Employee";
  }
  return args;
}

function warning_message(frm, message, message2) {
  //For Branch Integration
  if (message != "<b>Please fill the below fields to Opt In for Branch:</b>") {
    if (message2) {
      message += "<hr>" + message2;
    }
    frappe.msgprint({
      message: __(message),
      title: __("Missing Fields"),
      indicator: "orange",
    });
    frappe.validated = false;
    frm.set_value("opt_in", "");
  } else if (message2) {
    frappe.msgprint({
      message: __(message2),
      title: __("Warning"),
      indicator: "orange",
    });
    frappe.validated = false;
    frm.set_value("opt_in", "");
  }
}

frappe.ui.form.on("Job Category", {
  job_category(frm) {
    append_job_category(frm);
  },
  employee_job_category_remove(frm) {
    append_job_category(frm);
  },
});

function hasExtensions(filename, exts) {
  return new RegExp("(" + exts.join("|").replace(/\./g, "\\.") + ")$").test(
    filename
  );
}
function hide_sync_btn(frm) {
  frappe.db.get_value(
    "Company",
    frm.doc.company,
    "jazzhr_api_key",
    function (r) {
      let check = 0;
      frappe.db.get_value(
        "Company",
        frm.doc.company,
        "enable_jazz_hr",
        function (r) {
          if (r.enable_jazz_hr) {
            check = 1;
          }
        }
      );
      setTimeout(() => {
        if (r.jazzhr_api_key && check == 1) {
          $("button.ellipsis:nth-child(1)").show();
        }
      }, 300);
    }
  );
}
/*----------hide field----------*/
function trigger_hide() {
  let hide_fields = [
    "date_of_joining",
    "gender",
    "emergency_contact_details",
    "salutation",
    "erpnext_user",
    "joining_details",
    "job-profile",
    "approvers_section",
    "attendance_and_leave_details",
    "salary_information",
    "health_insurance_section",
    "contact_details",
    "sb53",
    "personal_details",
    "educational_qualification",
    "previous_work_experience",
    "history_in_company",
    "exit",
    "naming_series",
    "middle_name",
    "employment_details",
    "job_profile",
  ];
  for (let val in hide_fields) {
    cur_frm.toggle_display(hide_fields[val], 0);
  }
}

/*------required---------*/
function required_field() {
  let reqd_fields = ["email", "last_name"];
  for (let fld in reqd_fields) {
    cur_frm.toggle_reqd(reqd_fields[fld], 1);
  }
}

function uploaded_file_format(frm) {
  frm.get_field("resume").df.options = {
    restrictions: {
      allowed_file_types: [".pdf", ".txt", ".docx"],
    },
  };

  frm.get_field("w4").df.options = {
    restrictions: {
      allowed_file_types: [".pdf", ".txt", ".docx"],
    },
  };

  frm.get_field("e_verify").df.options = {
    restrictions: {
      allowed_file_types: [".pdf", ".txt", ".docx", ".jpg", ".png"],
    },
  };

  frm.get_field("i_9").df.options = {
    restrictions: {
      allowed_file_types: [".pdf", ".txt", ".docx", ".jpg", ".png"],
    },
  };

  frm.get_field("hire_paperwork").df.options = {
    restrictions: {
      allowed_file_types: [".pdf", ".txt", ".docx", ".jpg", ".png"],
    },
  };

  frappe.meta.get_docfield(
    "Employee ID requirements",
    "id_requirements",
    cur_frm.doc.name
  ).options = {
    restrictions: {
      allowed_file_types: [".pdf", ".txt", ".docx", ".jpg", ".png"],
    },
  };

  frappe.meta.get_docfield(
    "Employee Direct Deposit letter",
    "direct_deposit_letter",
    cur_frm.doc.name
  ).options = {
    restrictions: {
      allowed_file_types: [".pdf", ".txt", ".docx", ".jpg", ".png"],
    },
  };

  frappe.meta.get_docfield(
    "Employee Drug Screen",
    "drug_screen",
    cur_frm.doc.name
  ).options = {
    restrictions: {
      allowed_file_types: [".pdf", ".txt", ".docx", ".jpg", ".png"],
    },
  };
}

function cancel_employee(frm) {
  frm.add_custom_button(__("Cancel"), function () {
    frappe.set_route("Form", "Employee");
  });
}

function tag_company(frm) {
  if (frappe.boot.tag.tag_user_info.company_type == "TAG") {
    frm.set_value("company", "");
  }
}

function download_document(frm) {
  if (frm.doc.resume && frm.doc.resume.length > 1) {
    $(".attached-file-link").on("click", function () {
      download_emp_resume(this.innerHTML);
      return false;
    });
  }

  if (frm.doc.w4 && frm.doc.w4.length > 1) {
    $('[data-fieldname="w4"]').on("click", (e) => {
      doc_download(e);
    });
  }

  $('[data-fieldname="attachments"]').on("click", (e) => {
    e.preventDefault();
    if (e.target.target === "_blank") {
      download_emp_resume(e.target.innerHTML);
    }
  });
}

function doc_download(e) {
  let file = e.target.innerText;
  let link = "";
  if (file.includes(".") && file.length > 1) {
    if (file.includes("/files/")) {
      link = window.location.origin + file;
    } else {
      link = window.location.origin + "/files/" + file;
    }

    let data = file.split("/");
    const anchor = document.createElement("a");
    anchor.href = link;
    anchor.download = data[data.length - 1];
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
  }
}

function attachrefresh() {
  setTimeout(() => {
    document
      .querySelectorAll('div[data-fieldname="attachments"]')
      .forEach(function (oInput) {
        oInput.children[1].innerText = oInput.children[1].innerText
          .split("/")
          .slice(-1);
      });

    document
      .querySelectorAll('div[data-fieldname="id_requirements"]')
      .forEach(function (oInput) {
        oInput.children[1].innerText = oInput.children[1].innerText
          .split("/")
          .slice(-1);
      });

    document
      .querySelectorAll('div[data-fieldname="direct_deposit_letter"]')
      .forEach(function (oInput) {
        oInput.children[1].innerText = oInput.children[1].innerText
          .split("/")
          .slice(-1);
      });

    document
      .querySelectorAll('div[data-fieldname="drug_screen"]')
      .forEach(function (oInput) {
        oInput.children[1].innerText = oInput.children[1].innerText
          .split("/")
          .slice(-1);
      });
  }, 200);
}

function employee_delete_button(frm) {
  if (
    frm.doc.__islocal != 1 &&
    (frappe.user_roles.includes("Staffing Admin") ||
      frappe.user_roles.includes("Staffing User") ||
      frappe.user_roles.includes("Tag Admin"))
  ) {
    frm.add_custom_button(__("Delete"), function () {
      delete_employee(frm);
    });
  }
}

function delete_employee(frm) {
  return new Promise(function (resolve, reject) {
    frappe.confirm(
      "All the data linked to this employee will be deleted?",
      function () {
        let resp = "frappe.validated = false";
        resolve(resp);
        deleting_data(frm);
      },
      function () {
        const cancelReason = "Cancelled by user";
        reject(cancelReason);
      }
    );
  });
}

function deleting_data(frm) {
  frappe.call({
    method: "tag_workflow.utils.employee.delete_data",
    args: { emp: frm.doc.name },
    callback: function (r) {
      if (r.message == "Done") {
        frappe.msgprint("Employee Deleted Successfully");
        setTimeout(function () {
          window.location.href = "/app/employee";
        }, 2000);
      }
    },
  });
}

function filerestriction() {
  setTimeout(() => {
    document.getElementsByClassName("modal-title")[0].innerHTML =
      "Upload <h6>(Accepted File Type : pdf, txt or docx  file size 10mb) </h6>";
  }, 300);
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

function update_employees_data(frm) {
  let roles = frappe.user_roles;
  if (
    roles.includes("Staffing Admin") ||
    (roles.includes("Staffing User") && frm.doc.employee_number)
  ) {
    frm
      .add_custom_button("Sync with JAZZHR", function () {
        cur_frm.is_dirty() == 1
          ? frappe.msgprint("Please save the form first")
          : update_existing_employees(frm);
      })
      .addClass("btn-primary");
  }
}

function update_existing_employees(frm) {
  if (frm.doc.employee_number) {
    frappe.call({
      method: "tag_workflow.utils.jazz_integration.update_single_employee",
      args: {
        employee_number: frm.doc.employee_number,
        company: frm.doc.company,
      },
      freeze: true,
      freeze_message: "<p><b>Updating Employees Record</b></p>",
      callback: function (r) {
        if (r) {
          frappe.msgprint(
            "Employees Updation are done in the background . You can continue using the application"
          );
        }
      },
    });
  } else {
    cur_frm.scroll_to_field("jazzhr_api_key");
    frappe.msgprint("<b>JazzHR API Key</b> is required");
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

function employee_work_history(frm) {
  if (
    frm.doc.__islocal != 1 &&
    (frappe.boot.tag.tag_user_info.company_type == "Staffing" ||
      frappe.boot.tag.tag_user_info.company_type == "TAG")
  ) {
    employee_history(frm);
  }
}
function employee_history(frm) {
  frappe.call({
    method: "tag_workflow.tag_data.employee_work_history",
    args: {
      employee_no: frm.doc.name,
    },
    callback: function (r) {
      let profile_html = ``;
      if (r.message == "No Record") {
        profile_html += `<span>No Employment History<span>`;
      } else {
        let data = r.message;
        profile_html = `<table class="col-md-12 basic-table table-headers table table-hover"><th>Job Order</th><th>Start Date</th><th>Job Title</th><th>Hiring Company</th><th>Total Hours</th>`;
        for (let p in data) {
          profile_html += `<tr>
					<td style="margin-right:20px;" ><a href="${
            window.location.origin
          }/app/job-order/${data[p].job_order_detail}">${
            data[p].job_order_detail
          }</a></td>
					<td>${data[p].from_date}</td>
					<td>${data[p].job_name}</td>
					<td>${data[p].company}</td>
					<td>${data[p].total_hours.toFixed(2)} ${
            data[p].workflow_state == "Approval Request" ? "*" : ""
          } </td>
					</tr>`;
        }
        profile_html += `</table>`;
      }
      frm.set_df_property("employee_job_history", "options", profile_html);
    },
  });
}

function append_job_category(frm) {
  if (frm.doc.employee_job_category) {
    let emp_category = frm.doc.employee_job_category;
    let length = emp_category.length;
    let title = "";
    for (let i in emp_category) {
      if (!emp_category[i].job_category) {
        length -= 1;
      } else if (title == "") {
        title = emp_category[i].job_category;
      }
    }

    let job_categories = length > 1 ? title + " + " + (length - 1) : title;
    frm.set_value("job_categories", job_categories);
    refresh_field("job_categories");
  } else {
    frm.set_value("job_categories", null);
    refresh_field("job_categories");
  }
}

/*--------------------download---------------------*/
function download_emp_resume(file) {
  if (file) {
    frappe.call({
      method: "tag_workflow.utils.bulk_upload_resume.download_resume",
      args: { resume: file },
      freeze: true,
      freeze_message: "<b>working...</b>",
      callback: function (r) {
        let msg = r.message;
        console.log(msg);
        file = file.split("/");
        let filename =
          frappe.urllib.get_base_url() + "/files/" + file[file.length - 1];
        window.open(filename);
      },
    });
  }
}

function job_title_filter(frm) {
  let job_categories = [];
  if (frm.doc.employee_job_category) {
    frm.doc.employee_job_category.forEach(function (row) {
      job_categories.push(row.job_category);
    });
    frm.set_value("job_title_filter", job_categories.join(","));
    refresh_field("job_title_filter");
  }
}

function branch_card(frm) {
  //For Branch Integration
  if (frm.doc.company) {
    frappe.db.get_value(
      "Company",
      { name: frm.doc.company },
      ["branch_enabled"],
      (res) => {
        if (res.branch_enabled == 1) {
          frm.set_df_property("branch_integration", "hidden", 0);
          if (frm.doc.opt_in == 1) {
            fetch_branch_data();
          }
        } else {
          frm.set_df_property("branch_integration", "hidden", 1);
        }
      }
    );
  } else {
    frm.set_df_property("branch_integration", "hidden", 1);
  }
}

function fetch_branch_data() {
  //For Branch Integration
  frappe.call({
    method: "tag_workflow.utils.branch_integration.get_wallet_data",
    args: {
      emp_id: cur_frm.doc.name,
    },
    async: 0,
    freeze: true,
    callback: (res) => {
      if (typeof res.message == "string") {
        if (res.message.includes("Error")) {
          frm.set_df_property("branch_details", "options", res.message);
        } else {
          branch_details(cur_frm, "No Data");
        }
      } else {
        branch_details(cur_frm, res.message);
      }
    },
  });
}

function branch_details(frm, data) {
  //For Branch Integration
  if (frm.doc.opt_in == 1) {
    let profile_html = `
		<label class="control-label">Account Status</label>
		<p class="text-muted small grid-description" style="display: none"></p>
		<div class="grid-custom-buttons grid-field"></div>
		<div class="form-grid">
			<div class="grid-heading-row">
				<div class="grid-row">
					<div class="data-row row">
						<div class="col grid-static-col col-xs-2" data-fieldname="account_number" data-fieldtype="Password" title="Account Number">
							<div class="field-area" style="display: none"></div>
							<div class="static-area ellipsis">Account Number</div>
						</div>
						<div class="col grid-static-col col-xs-2" data-fieldname="account_status" data-fieldtype="Data" title="Account Status">
							<div class="field-area" style="display: none"></div>
							<div class="static-area ellipsis">Account Status</div>
						</div>
						<div class="col grid-static-col col-xs-2" data-fieldname="card_status" data-fieldtype="Data" title="Card Status">
							<div class="field-area" style="display: none"></div>
							<div class="static-area ellipsis">Card Status</div>
						</div>
						<div class="col grid-static-col col-xs-2" data-fieldname="reason_code" data-fieldtype="Data" title="Reason Code">
							<div class="field-area" style="display: none"></div>
							<div class="static-area ellipsis">Reason Code</div>
						</div>
						<div class="col grid-static-col col-xs-2" data-fieldname="reason" data-fieldtype="Data" title="Reason">
							<div class="field-area" style="display: none"></div>
							<div class="static-area ellipsis">Reason</div>
						</div>
						<div class="col grid-static-col col-xs-2" data-fieldname="time_created" data-fieldtype="Datetime" title="Time Created">
							<div class="field-area" style="display: none"></div>
							<div class="static-area ellipsis">Time Created</div>
						</div>
					</div>
				</div>
			</div>`;

    if (data == "No Data") {
      profile_html += `<div class="grid-body">
				<div class="grid-empty text-center">
					<img src="/assets/frappe/images/ui-states/grid-empty-state.svg" alt="Grid Empty State" class="grid-empty-illustration"/>
					No Data
				</div>
			</div>`;
    } else {
      let account_no = "•".repeat(cur_frm.doc.account_number.length);
      profile_html += `
			<div class="grid-body">
				<div class="rows">
					<div class="grid-row">
						<div class="data-row row" style="display: flex;">
								<div class="col grid-static-col col-xs-2" id="account_no" data-fieldtype="Password" title="Account Number"><div class="static-area ellipsis" >${account_no}</div></div>
								<div class="col grid-static-col col-xs-2 " id="account_status" title = '${
                  data.acc_status_label || ""
                }'><div class="static-area ellipsis"><span id="acc_status_color">${
        data.acc_status || ""
      }</span></div></div>
								<div class="col grid-static-col col-xs-2 " id="card_status"><div class="static-area ellipsis"><span id="card_status_color">${
                  data.card_status || ""
                }</span></div></div>
								<div class="col grid-static-col col-xs-2 " id="reason_code" title = '${
                  data.reason_code_label || ""
                }'><div class="static-area ellipsis"><span id="reason_code">${
        data.reason_code || ""
      }</span></div></div>
								<div class="col grid-static-col col-xs-2 " id="reason"><div class="static-area ellipsis"></div>${
                  data.reason || ""
                }</div>
								<div class="col grid-static-col col-xs-2 " id="time_created"><div class="static-area ellipsis">${
                  data.time_created
                }</div></div>
							</div>
						</div>
					</div>
				</div>
			</div>`;
    }
    profile_html += `</div>
		<div class="small form-clickable-section grid-footer">
			<div class="flex justify-between">
				<div class="grid-buttons">
					<button class="btn btn-xs btn-secondary" onclick="fetch_data()">Refresh Status</button>
					<button class="btn btn-xs btn-secondary" id='decrypt_acc' onclick="show_acc(this.id, '${data.acc_no}')">Decrypt Account Number</button>
				</div>
				<div class="grid-pagination"></div>
			</div>
		</div>
		`;
    frm.set_df_property("branch_details", "options", profile_html);
    card_status_color(data.card_status);
    account_status_color(data.acc_status);
    reason_code_color(data.reason_code);
  }
}

window.fetch_data = () => {
  //For Branch Integration
  fetch_branch_data();
};

window.show_acc = (id, acc_no) => {
  if (id == "decrypt_acc") {
    $("#account_no").text(acc_no);
    $("#decrypt_acc").html("Encrypt Account Number");
    $("#decrypt_acc").attr("id", "encrypt_acc");
  } else {
    $("#account_no").text("•".repeat(acc_no.length));
    $("#encrypt_acc").html("Decrypt Account Number");
    $("#encrypt_acc").attr("id", "decrypt_acc");
  }
};

function card_status_color(card_status) {
  //For Branch Integration
  if (card_status == "False") {
    $("#card_status_color").addClass("indicator-pill red");
  } else {
    $("#card_status_color").addClass("indicator-pill green");
  }
}

function account_status_color(acc_status) {
  //For Branch Integration
  if (acc_status) {
    if (["NOT CREATED", "FAILED", "CLOSED"].includes(acc_status)) {
      $("#acc_status_color").addClass("indicator-pill red");
    } else if (
      ["PENDING", "REVIEW", "CREATED", "UNCLAIMED"].includes(acc_status)
    ) {
      $("#acc_status_color").addClass("indicator-pill yellow");
    } else {
      $("#acc_status_color").addClass("indicator-pill green");
    }
  }
}

function reason_code_color(reason_code) {
  //For Branch Integration
  if (reason_code) {
    if (
      [
        "CONFIRMED FRAUD",
        "DENIED",
        "KYC SSN INVALID",
        "KYC PII SSN MISMATCH",
        "KYC DECEASED",
        "KYC ERROR",
        "EMPLOYEE NOT FOUND",
        "ERROR",
      ].includes(reason_code)
    ) {
      $("#acc_status_color").addClass("indicator-pill red");
    } else {
      $("#acc_status_color").addClass("indicator-pill yellow");
    }
  }
}

function password_fields(frm) {
  if (frm.doc.__islocal != 1) {
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

function employee_timesheets(frm) {
  frappe.call({
    method: "tag_workflow.tag_data.employee_timesheets",
    args: {
      employee_no: frm.doc.name,
    },
    callback: function (r) {
      let profile_html = ``;
      if (r.message == "No Record") {
        profile_html += `<span>No Timesheets Found<span>`;
      } else {
        let data = r.message;
        profile_html = `<table class="col-md-12 basic-table table-headers table table-hover"><th>Date of Timesheet</th><th>Status</th><th>Job Title</th><th>Job Order</th><th>Total Hours</th><th>Status of Work Order</th>`;
        for (let p in data) {
          profile_html += `<tr>
					<td style="margin-right:20px;" ><a href="${
            window.location.origin
          }/app/timesheet/${data[p].name}">${data[p].date_of_timesheet}</a></td>
					<td>${data[p].workflow_state}</td>
					<td>${data[p].job_title}</td>
					<td>${data[p].job_order_detail}</td>
					<td>${data[p].total_hours.toFixed(2)}</td>
					<td>${data[p].status_of_work_order}</td>
					</tr>`;
        }
        profile_html += `</table>`;
      }
      frm.set_df_property("timesheet_empty", "options", profile_html);
    },
  });
}
