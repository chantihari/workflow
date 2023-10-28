frappe.require("/assets/tag_workflow/js/twilio_utils.js");
frappe.ui.form.on("User", {
  refresh: function (frm) {
    $("#user-__details-tab").text("User Profile ");
    field_toggle();
    multiple_assign_properties(frm);
    $('[class="btn btn-primary btn-sm primary-action"]').show();
    $(".custom-actions.hidden-xs.hidden-md").show();

    cur_frm.clear_custom_buttons();
    set_options(frm);
    field_reqd();
    field_check();
    exclusive_fields(frm);
    if (frm.doc.__islocal == 1) {
      cancel_user(frm);
    }

    $('[data-fieldname = "mobile_no"]>div>div>div>input').attr(
      "placeholder",
      "Example: +XX XXX-XXX-XXXX"
    );
    $(document).on("keypress", function (event) {
      if (event.key === "Enter") {
        event.preventDefault();
      }
    });
    setting_user_field(frm);
  },
  form_render(frm, cdt, cdn) {
    if (frm.doc.__islocal != 1) {
      frm.fields_dict.assign_multiple_company.grid.wrapper
        .find(".grid-delete-row")
        .hide();
    }
  },

  setup: function (frm) {
    let roles = frappe.user_roles;
    if (frm.doc.__islocal == 1) {
      frm.set_df_property("assign_multiple_company", "hidden", 1);
      frm.set_value("company", "");
    }

    frm.set_query("organization_type", function () {
      if (roles.includes("Tag Admin")) {
        return {
          filters: [["Organization Type", "name", "!=", "Exclusive Hiring"]],
        };
      } else if (roles.includes("Staffing Admin")) {
        return {
          filters: [["Organization Type", "name", "not in", ["TAG", "Hiring"]]],
        };
      } else if (roles.includes("Hiring Admin")) {
        if (frappe.boot.tag.tag_user_info.company_type == "Hiring") {
          return {
            filters: [["Organization Type", "name", "=", "Hiring"]],
          };
        } else if (
          frappe.boot.tag.tag_user_info.company_type == "Exclusive Hiring"
        ) {
          return {
            filters: [["Organization Type", "name", "=", "Exclusive Hiring"]],
          };
        }
      }
    });
  },
  organization_type: function (frm) {
    set_options(frm);
    init_values(frm);
    if (!frm.doc.organization_type) {
      frm.set_query("company", function (doc) {
        return {
          query: "tag_workflow.tag_data.user_company",
          filters: {
            owner_company: doc.organization_type,
          },
        };
      });
    } else if (frappe.boot.tag.tag_user_info.company_type != "Exclusive Hiring") {
      let company = cur_frm.doc.organization_type;
      setup_company_value(company);
    } else {
      let company = "Exclusive Hiring";
      frm.set_value("company", frappe.boot.tag.tag_user_info.company);
      setup_company_value(company);
    }
    if (frm.doc.organization_type == "Hiring") {
      frm.set_value("tag_user_type", "Hiring Admin");
    } else if (frm.doc.organization_type == "Staffing") {
      frm.set_value("tag_user_type", "Staffing Admin");
    } else if (frm.doc.organization_type == "TAG") {
      frm.set_value("tag_user_type", "TAG Admin");
    }
    if (
      frappe.boot.tag.tag_user_info.company_type == "Hiring" ||
      (frm.doc.organization_type == "Staffing" &&
        frappe.boot.tag.tag_user_info.company_type == "Staffing")
    ) {
      org_info(frm);
    }
  },
  first_name: function () {
    if (cur_frm.doc.first_name) {
      let first_name = cur_frm.doc.first_name.trim();
      first_name = name_update(first_name);
      cur_frm.set_value("first_name", first_name);
    }
  },
  last_name: function () {
    if (cur_frm.doc.last_name) {
      let last_name = cur_frm.doc.last_name.trim();
      last_name = name_update(last_name);
      cur_frm.set_value("last_name", last_name);
    }
  },
  tag_user_type: function (frm) {
    setup_profile(frm);
  },

  before_save: function (frm) {
    setup_profile(frm);
    if (frm.doc.__islocal == 1) {
      let new_row = frm.add_child("assign_multiple_company");
      new_row.assign_multiple_company = frm.doc.company;
      frm.set_df_property("assign_multiple_company", "hidden", 0);
    }
    cur_frm.set_value("old_password", "");
  },
  after_save: function (frm) {
    update_employee(frm);
    multi_company_setup(frm);
    employee_status(frm);
  },
  birth_date: function (frm) {
    check_bd(frm);
  },
  enabled: function (frm) {
    field_toggle();
    terminated_option();
  },
  terminated: function () {
    if (cur_frm.doc.terminated == 1) {
      cur_frm.set_value("enabled", 0);
    }
  },
  onload: function (frm) {
    if (frappe.session.user != "Administrator") {
      $(".menu-btn-group").hide();
    }
  },
  validate: function (frm) {
    let phone = frm.doc.mobile_no;
    let old_password = frm.doc.old_password;
    let new_password = frm.doc.new_password;
    if (phone) {
      if (!validate_phone(phone)) {
        frappe.msgprint({
          message: __("Invalid Mobile Number!"),
          indicator: "red",
        });
        frappe.validated = false;
      } else {
        frm.set_value("mobile_no", validate_phone(phone));
      }
    }
    if (!cur_frm.get_field("old_password").df.hidden && new_password) {
      if (old_password) {
        check_old_password(frm, old_password, new_password);
      } else {
        frappe.throw("Pelase enter old password");
      }
    } else if (cur_frm.get_field("old_password").df.hidden) {
      //pass
    } else if (old_password) {
      frappe.throw("Pelase enter new password");
    }
    if (new_password){
      if(!validatePassword(new_password)){
        frappe.validated = false;
      }
    }
    validate_email(frm);
  },
  mobile_no: function (frm) {
    let phone = frm.doc.mobile_no;
    if (phone) {
      frm.set_value(
        "mobile_no",
        validate_phone(phone) ? validate_phone(phone) : phone
      );
    }
  },
});

frappe.ui.form.on("Companies Assigned", {
  form_render: function (frm, cdt, cdn) {},
  assign_multiple_company_add: function (frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    row.assign_multiple_company = undefined;
    cur_frm.refresh_field("assign_multiple_company");
  },
});

function multiple_assign_properties(frm) {
  if (frm.doc.__islocal != 1) {
    $('*[data-fieldname="assign_multiple_company"]')
      .find(".grid-remove-rows")
      .hide();
    $('*[data-fieldname="assign_multiple_company"]')
      .find(".grid-remove-all-rows")
      .hide();
    document
      .querySelectorAll(
        '[title="assign_multiple_company"] > .form-grid > .grid-body > .rows > .grid-row > .data-row > .row-index'
      )
      .forEach((el) => (el.style.pointerEvents = "none"));
    frm.fields_dict["assign_multiple_company"].grid.wrapper
      .find(".grid-delete-row")
      .hide();
    frm.fields_dict["assign_multiple_company"].grid.wrapper
      .find(".btn-open-row")
      .hide();
    frm.fields_dict["assign_multiple_company"].grid.grid_rows.forEach(
      function (element) {
        element.docfields[0].set_only_once = 1;
      }
    );
    frm.fields_dict["assign_multiple_company"].grid.refresh();
    let data = [];
    frm.doc.assign_multiple_company.forEach(function (element) {
      data.push(element.assign_multiple_company);
    });
    localStorage.setItem("already_assigned_company", JSON.stringify(data));
    frm.fields_dict["assign_multiple_company"].grid.get_field(
      "assign_multiple_company"
    ).get_query = function (doc) {
      return {
        filters: [
          ["Company", "name", "not in", cur_frm.doc.company],
          ["Company", "organization_type", "=", cur_frm.doc.organization_type],
          ["Company", "name", "not in", data],
        ],
      };
    };
  }
}

/*-------first_and_last_name--------------*/
function name_update(string) {
  return string.charAt(0).toUpperCase() + string.slice(1);
}

function field_reqd() {
  let data = ["company", "date_of_joining"];
  for (let value in data) {
    cur_frm.toggle_reqd(data[value], 1);
  }
}

function field_check() {
  let values = ["email", "company", "organization_type"];
  let pass = "new_password";
  if (!cur_frm.doc.__islocal) {
    $(".page-title .title-area .title-text").css("cursor", "pointer");
    for (let vals in values) {
      cur_frm.toggle_enable(values[vals], 0);
    }
  } else {
    cur_frm.set_value(pass, "Entry@123");
    $(".page-title .title-area .title-text").css("cursor", "auto");
  }

  cur_frm.doc.__islocal === undefined &&
  !frappe.user_roles.includes("System Manager")
    ? cur_frm.toggle_enable("tag_user_type", 0)
    : console.log("TAG");
  frappe.session.user === cur_frm.doc.name
    ? cur_frm.toggle_enable("enabled", 0)
    : console.log("TAG");
}

function init_values(frm) {
  if (frm.doc.__islocal == 1) {
    let clear_values = [
      "username",
      "email",
      "first_name",
      "last_name",
      "company",
      "gender",
      "birth_date",
      "tag_user_type",
      "location",
      "mobile_no",
    ];
    for (let val in clear_values) {
      frm.set_value(clear_values[val], "");
    }
  }
}

/*--------setup option-------------*/
function set_options(frm) {
  let options = "";
  let organization_type = frm.doc.organization_type;

  if (organization_type == "TAG") {
    options = "\nTAG Admin";
  } else if (
    organization_type == "Hiring" ||
    organization_type == "Exclusive Hiring"
  ) {
    options = "\nHiring Admin\nHiring User";
  } else if (organization_type == "Staffing") {
    options = "\nStaffing Admin\nStaffing User";
  }
  cur_frm.set_df_property("tag_user_type", "options", options);
}

/*--------setup profile------------*/
function setup_profile(frm) {
  let role_profile = "role_profile_name";
  let module_profile = "module_profile";
  let type = frm.doc.tag_user_type;
  if (type == "Hiring Admin") {
    frm.set_value(role_profile, "Hiring Admin");
    frm.set_value(module_profile, "Hiring");
  } else if (type == "Hiring User") {
    frm.set_value(role_profile, "Hiring User");
    frm.set_value(module_profile, "Hiring");
  } else if (type == "Staffing Admin") {
    frm.set_value(role_profile, "Staffing Admin");
    frm.set_value(module_profile, "Staffing");
  } else if (type == "Staffing User") {
    frm.set_value(role_profile, "Staffing User");
    frm.set_value(module_profile, "Staffing");
  } else if (type == "TAG Admin") {
    frm.set_value(role_profile, "Tag Admin");
    frm.set_value(module_profile, "Tag Admin");
  } else if (type == "TAG User") {
    frm.set_value(role_profile, "Tag User");
    frm.set_value(module_profile, "Tag Admin");
  }
}

/*------------update employee--------------*/
function update_employee(frm) {
  if (frm.doc.enabled == 1) {
    if (cur_frm.doc.organization_type == "Exclusive Hiring") {
      frappe.call({
        method: "tag_workflow.tag_data.update_exclusive_org",
        args: {
          exclusive_email: cur_frm.doc.email,
          staffing_email: cur_frm.doc.owner,
          staffing_comapny: frappe.defaults.get_user_defaults("Company")[0],
          exclusive_company: frm.doc.company,
        },
      });
    }
  }
}

function setup_company_value(company) {
  cur_frm.fields_dict["company"].get_query = function () {
    return {
      filters: {
        organization_type: company,
      },
    };
  };
}

/*-------multi company--------*/
function multi_company_setup(frm) {
  if (cur_frm.doc.__islocal != 1) {
    make_multicompany(frm);
  }
}

function make_multicompany(frm) {
  let data = frm.doc.assign_multiple_company || [];
  let company = [];
  for (let d in data) {
    data[d].assign_multiple_company
      ? company.push(data[d].assign_multiple_company)
      : console.log(".");
  }
  let already_assigned_company_array = JSON.parse(
    localStorage.getItem("already_assigned_company")
  );
  if (
    company.length > 1 &&
    already_assigned_company_array.length < company.length
  ) {
    localStorage.removeItem("already_assigned_company");
    company.shift();
    frappe.call({
      method: "tag_workflow.controllers.master_controller.multi_company_setup",
      args: { user: frm.doc.name, company: company.join(",") },
      freeze: true,
      freeze_message: "<p><b>Assigning user to multiple companies...</b></p>",
      callback: function () {
        frappe.msgprint(
          "<b>" +
            frm.doc.name +
            "</b> has been assigned as <b>" +
            frm.doc.tag_user_type +
            "</b> to <b>" +
            company.join(",") +
            "</b>"
        );
        cur_frm.reload_doc();
      },
    });
  }
}

/*------birth date-------*/
function check_bd(frm) {
  let date = frm.doc.birth_date || "";
  if (date && date >= frappe.datetime.now_date()) {
    frappe.msgprint({
      message: __("<b>Birth Date</b> Cannot be Today`s date or Future date"),
      title: __("Error"),
      indicator: "orange",
    });
    cur_frm.set_value("birth_date", "");
  }
}
function org_info(frm) {
  frappe.call({
    method: "tag_workflow.tag_data.hiring_org_name",
    args: { current_user: frappe.session.user },
    callback: function (r) {
      if (r.message == "success") {
        frm.set_value("company", frappe.boot.tag.tag_user_info.company);
      } else {
        frm.set_value("company", "");
      }
    },
  });
}

function cancel_user(frm) {
  frm.add_custom_button(__("Cancel"), function () {
    frappe.set_route("Form", "User");
  });
}

function add_old_joborder(frm) {
  if (frm.doc.organization_type == "Staffing") {
    frappe.call({
      method: "tag_workflow.controllers.master_controller.addjob_order",
      args: { current_user: frm.doc.name, company: frm.doc.company },
    });
  }
}
function exclusive_fields(frm) {
  if (
    frm.doc.__islocal != 1 &&
    frappe.boot.tag.tag_user_info.company_type == "Staffing" &&
    frm.doc.organization_type == "Exclusive Hiring"
  ) {
    frappe.db.get_value(
      "User",
      { name: frm.doc.owner },
      ["organization_type"],
      function (r) {
        if (r.organization_type != "Staffing" || r == null) {
          $('[data-label="Save"]').hide();
          $('[data-label="Assign%20Multi%20Company"]').hide();

          let myStringArray = [
            "first_name",
            "last_name",
            "enabled",
            "terminated",
            "gender",
            "birth_date",
            "location",
            "mobile_no",
            "new_password",
            "old_password",
            "logout_all_sessions",
          ];
          let arrayLength = myStringArray.length;
          for (let i = 0; i < arrayLength; i++) {
            frm.set_df_property(myStringArray[i], "read_only", 1);
          }
          frm.set_df_property("change_password", "hidden", 1);
        }
      }
    );
  } else if (
    frm.doc.__islocal != 1 &&
    frappe.boot.tag.tag_user_info.company_type == "Staffing"
  ) {
    $('[data-label="Save"]').show();
  }
}

/*--------perpare field display-----------*/
function field_toggle() {
  let perm_dis_fields = ["sb1", "sb3"];
  for (let field in perm_dis_fields) {
    cur_frm.toggle_display(perm_dis_fields[field], 0);
  }
}

function terminated_option() {
  if (cur_frm.doc.enabled == 1) {
    cur_frm.set_value("terminated", 0);
  }
}
function setting_user_field(frm) {
  if (
    frappe.boot.tag.tag_user_info.user_type == "Staffing User" ||
    frappe.boot.tag.tag_user_info.user_type == "Hiring User"
  ) {
    $('[id="user-add-new"]').show();
    if (frappe.session.user == cur_frm.doc.email) {
      frm.set_df_property("enabled", "read_only", 1);
      frm.set_df_property("terminated", "read_only", 1);
    } else {
      $('[id="user-add-new"]').hide();
      let l = [
        "first_name",
        "last_name",
        "enabled",
        "terminated",
        "location",
        "mobile_no",
        "change_password",
        "new_password",
        "logout_all_sessions",
      ];
      for (let vals in l) {
        cur_frm.toggle_enable(l[vals], 0);
      }
      frm.set_df_property("change_password", "hidden", 1);
    }
  }
  if (frappe.session.user != cur_frm.doc.email) {
    frm.set_df_property("old_password", "hidden", 1);
  }
}

function check_old_password(frm, old_password, new_password) {
  if (old_password && new_password) {
    if (old_password == new_password) {
      frappe.validated = false;
      frappe.throw("Old and new password can not be same");
    } else {
      let old_pwd = cur_frm.doc.old_password
      let pkey = "-----BEGIN PUBLIC KEY-----" +
      "MIIBojANBgkqhkiG9w0BAQEFAAOCAY8AMIIBigKCAYEAspmf3aOPSF1irR8azmVe" +
      "yAc9/961iyIL2QPyZBjgp6IJqHMxv285nJV/w3eXJO4mhFydRgn1xeHn7eDahbit" +
      "D1CY5lJVcSlTh4cuxo7ftxBFd1L//D4MEGIpbqlzeZZHsqiXwblM74mlK7G+x+Cc" +
      "70ZZFXvNXhBLhSgORGRsTj9mbgHQmSpNxWRTR8xduwrmjcb1T5dGkRy5SVZbt7vd" +
      "I2wS1zESDVj8GokXw9R02ro4P0FApAr585f30fb+VeBeXp9dgffDtl8iMikbIL85" +
      "aUlNNCdXY+sbjbAloL27t7ROPC+Dw+M4fRCaIi9gecjGQzONBSM2nHfuz+37kVPa" +
      "pUP+VEfLXIwOviZ9t3A1NAP/R02rtJ+KjRVjUjfF3qTAB7pGs2nUmdxfZ+Xr8tV0" +
      "pZ5rrOV2KXOooqHW6mx+/lfIZdsW2bN/Q4Dbuh+irkceJR/u6sN7GWxiFG+Na3ID" +
      "KOVT50/2+BYLrkXB6theS6JloK1Kx3Ci4DyjDQ2iPYwnAgMBAAE=" +
      "-----END PUBLIC KEY-----";
		let publicKey = forge.pki.publicKeyFromPem(pkey);

		let encrypted = publicKey.encrypt(old_pwd, "RSA-OAEP", {
					md: forge.md.sha256.create(),
					mgf1: forge.mgf1.create()
				});
		let base64 = forge.util.encode64(encrypted);
  		old_pwd = base64;
      frappe.call({
        method: "tag_workflow.tag_data.check_old_password",
        args: {
          current_user: cur_frm.doc.email,
          old_password: old_pwd,
        },
        callback: function (r) {
          if (!r.message) {
            frappe.validated = false;
            frappe.throw("Old password is incorrect");
          }
        },
      });
    }
  } else {
    frappe.throw("Pelase enter new password");
  }
}

function employee_status(frm) {
  frappe.call({
    method: "tag_workflow.tag_data.employee_status_change",
    args: {
      user: frm.doc.name,
    },
  });
}

function validate_email(frm){
  if(frm.doc.email && !frappe.utils.validate_type(frm.doc.email, "email")){
    frappe.validated=false;
    frappe.msgprint("Invalid email.");
  }
}