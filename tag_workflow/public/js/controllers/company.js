localStorage.setItem("cert_list_exist", 0);
let cert_dict = {
  DBE: "DBE- Disadvantaged Business Enterprise",
  DVOSB: "DVOSB- Disabled Veteran Owned Small Business",
  MBE: "MBE- Minority Business Enterprise",
  SDVOSB: "SDVOSB- Service Disabled Veteran Owned Small Business",
  VOSB: "VOSB- Veteran Owned Small Business",
  WBE: "WBE- Women Business Enterprise",
  WOSB: "WOSB- Woman Owned Small Business",
};
frappe.require("/assets/tag_workflow/js/twilio_utils.js");
frappe.ui.form.on("Company", {
  client_id_data: function (frm) {
    update_auth_url(frm);
  },

  client_secret_data: function (frm) {
    update_auth_url(frm);
  },
  refresh: function (frm) {
    update_primary_language(frm);
    if ($(window).width() > 1200) {
      carousel_display(frm);
    }
    $(
      "#company-tab_break_63 > div.row.form-section.card-section.visible-section > div > div > form > div > div > div.form-grid-container > div > div.grid-heading-row > div:nth-child(2) > div"
    ).css("display", "none");
    $(
      "#company-tab_break_155 > div.row.form-section.card-section.visible-section > div > div > form > div > div > div.form-grid-container > div > div.grid-heading-row > div:nth-child(2) > div"
    ).css("display", "none");
    $('[data-fieldname="industry_type"]').on("click", () => {
      $('input[data-fieldname="industry_type"]').removeAttr("disabled");
    });
    update_company_fields(frm);
    init_values(frm);
    exclusive_staff_company_fields(frm);
    frm.set_value("search_on_maps", 1);
    hide_and_show_tables(frm);
    $('[class="btn btn-primary btn-sm primary-action"]').show();
    $(".custom-actions.hidden-xs.hidden-md").show();
    frm.clear_custom_buttons();
    removing_registration_verbiage(frm);
    frm.toggle_display("abbr", 0);
    frm.toggle_display("address_html", 0);
    update_lat_lng(frm);
    hide_tag_charges(frm);
    uploaded_file_format(frm);
    download_document(frm);
    bulk_upload_resume(frm);
    if (frappe.user.has_role("Tag Admin")) {
      frm.set_df_property("employees", "read_only", 1);
    }
    if (!frappe.user.has_role("Tag Admin")) {
      frm.set_df_property("make_organization_inactive", "hidden", 1);
      frm.set_df_property("make_organization_inactive", "read_only", 1);
    }
    if (frm.doc.__islocal == 1) {
      $('div[data-fieldname="average_rating"]').css("display", "none");
      cancel_company(frm);
    } else {
      set_up_cert_field(frm);
      make_button_disable(frm);
      if(frm.doc.organization_type=="Exclusive Hiring"){
        $('*[data-fieldname="invoice_premium_table"]').find(".grid-buttons").hide();
      }
      $("[data-fieldname='staffing_company'].grid-static-col").on("click", async function(){
        let title = $(this).find(".frappe-control").attr("title");
        let row_name = $(this).parent().parent().attr("data-name");
        await get_company_dropdown(frm, row_name, title);
      });
      $("[data-fieldname='invoice_premium'].grid-static-col").on("click", async function(){
        let title = $(this).siblings().find('[data-fieldname="staffing_company"]').attr("title");
        let row_name = $(this).parent().parent().attr("data-name");
        await get_company_dropdown(frm, row_name, title);
      });
    }

    if (frm.doc.organization_type == "Staffing") {
      $("#form-tabs1 .nav-item").css("padding", "0 8px");
      frm.set_df_property("job_title", "hidden", 1);
    } else {
      $("#form-tabs1 .nav-item").css("padding", "0 13px");
    }
    set_map(frm);
    hide_fields(frm);
    show_addr(frm);
    let child_table = [
      "industry_type",
      "job_titles",
      "wages",
      "industry_type",
      "job_titles",
      "job_site",
      "employee",
      "employee_name",
      "resume",
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
    $('[data-fieldname = "phone_no"]>div>div>div>input').attr(
      "placeholder",
      "Example: +XX XXX-XXX-XXXX"
    );
    $(
      '[data-fieldname = "accounts_payable_phone_number"]>div>div>div>input'
    ).attr("placeholder", "Example: +XX XXX-XXX-XXXX");
    $(
      '[data-fieldname = "accounts_receivable_phone_number"]>div>div>div>input'
    ).attr("placeholder", "Example: +XX XXX-XXX-XXXX");

    if (frm.doc.enable_jazz_hr) {
      let fields = { jazzhr_api_key: "jazzhr_api_key_html" };
      password_fields(frm, fields, false);
    }

    if (frm.doc.enable_quickbook) {
      let fields = {
        client_id: "client_id_html",
        client_secret: "client_secret_html",
      };
      password_fields(frm, fields, false);
    }

    if (frm.doc.enable_workbright) {
      let fields = {
        workbright_subdomain: "workbright_subdomain_html",
        workbright_api_key: "workbright_api_key_html",
      };
      password_fields(frm, fields, false);
    }

    redirect_job_site();
    public_profile_redirect(frm);
    add_lable(frm);
    window.onpageshow = function (event) {
      reload_company_setting_page(event);
    };
  },
  update_employee_records: function (frm) {
    if (frm.is_dirty()) {
      frappe.msgprint("Please save to proceed further");
    } else {
      update_existing_employees(frm);
    }
  },
  get_data_from_jazzhr: function (frm) {
    if (frm.is_dirty()) {
      frappe.msgprint("Please save to proceed further");
    } else {
      make_jazzhr_request(frm);
    }
  },

  setup: function (frm) {
    Array.from($('[data-fieldtype="Currency"]')).forEach((_field) => {
      if (
        _field.title !== "total_monthly_sales" &&
        frappe.boot.tag.tag_user_info.user_type != "Hiring User"
      ) {
        _field.id = "id_mvr_hour";
      }
    });

    $(
      "div.row:nth-child(16) > div:nth-child(2) > div:nth-child(2) > form:nth-child(1) > div:nth-child(8) > div:nth-child(1) > div:nth-child(2) > div:nth-child(1)"
    ).attr("id", "id_mvr_hour");
    init_values(frm);

    let ORG = "Organization Type";
    frm.set_query("organization_type", function () {
      if (frappe.session.user == "Administrator") {
        return {
          filters: [
            [
              ORG,
              "name",
              "in",
              ["TAG", "Hiring", "Staffing", "Exclusive Hiring"],
            ],
          ],
        };
      }
      if (frappe.user_roles.includes("Tag Admin")) {
        return {
          filters: [[ORG, "name", "!=", "TAG"]],
        };
      } else if (frappe.user_roles.includes("Staffing Admin")) {
        return {
          filters: [[ORG, "name", "=", "Exclusive Hiring"]],
        };
      } else if (frappe.user_roles.includes("Hiring Admin")) {
        return {
          filters: [[ORG, "name", "=", "Hiring"]],
        };
      }
    });
    frm.set_query("certificate_and_endorsements", function () {
      return {
        filters: [
          [
            "Certificate and Endorsement",
            "name",
            "not in",
            JSON.parse(localStorage.getItem("cert_list_exist")),
          ],
        ],
      };
    });
    $('[data-fieldname="parent_staffing"]').click(function () {
      return false;
    });
    $('[data-fieldname="parent_staffing"]').click(function () {
      if (frm.doc.__islocal !== 1) {
        let cust = $(this).text();
        let txt = cust.split(".")[1];
        let name1 = txt.replace(/%/g, " ");
        let name = name1.trim();
        localStorage.setItem("company", name);
        window.location.href = "/app/dynamic_page";
      }
    });
    frm.set_query("parent_staffing", function () {
      return {
        filters: [
          ["Company", "organization_type", "=", "Staffing"],
          ["Company", "make_organization_inactive", "=", 0],
        ],
      };
    });
    frm.fields_dict["employees"].grid.get_field("employee").get_query =
      function (doc) {
        let employees_data = frm.doc.employees,
          employees_list = [];
        for (let x in employees_data) {
          if (employees_data[x]["employee"]) {
            employees_list.push(employees_data[x]["employee"]);
          }
        }
        return {
          query: "tag_workflow.tag_data.filter_company_employee",
          filters: {
            company: doc.name,
            employees_list: employees_list,
          },
        };
      };

    frm.fields_dict["job_site"].grid.get_field("job_site").get_query =
      function (doc) {
        let li = [];
        let table_data = frm.doc.job_site;
        for (let i in table_data) {
          if (table_data[i]["job_site"]) {
            li.push(table_data[i]["job_site"]);
          }
        }
        return {
          query: "tag_workflow.tag_data.filter_jobsite",
          filters: {
            company: doc.name,
            site_list: li,
          },
        };
      };

    jazz_connect_button(frm);
    quick_connect_button(frm);
    work_connect_button(frm);
    staff_connect_button(frm);

    $('[data-fieldname="enable_jazz_hr"]').css({ visibility: "hidden" });
    $('[data-fieldname="enable_quickbook"]').css({ visibility: "hidden" });
    $('[data-fieldname="staff_complete_enable"]').css({ visibility: "hidden" });
    $('[data-fieldname="enable_workbright"]').css({ visibility: "hidden" });
  },
  organization_type: function (frm) {
    if (
      frm.doc.organization_type &&
      frm.doc.organization_type == "Exclusive Hiring"
    ) {
      org_info(frm);
    } else {
      frm.set_value("parent_staffing", "");
    }
  },

  set_primary_contact_as_account_receivable_contact: function (frm) {
    if (frm.doc.set_primary_contact_as_account_receivable_contact == 1) {
      if (
        frm.doc.contact_name &&
        frm.doc.phone_no &&
        frm.doc.email
      ) {
        frm.set_value("accounts_receivable_name", frm.doc.contact_name);
        frm.set_value("accounts_receivable_rep_email", frm.doc.email);
        frm.set_value(
          "accounts_receivable_phone_number",
          frm.doc.phone_no
        );
      } else {
        msgprint("You Can't set Primary Contact unless your value are filled");
        frm.set_value(
          "set_primary_contact_as_account_receivable_contact",
          0
        );
      }
    } else {
      frm.set_value("accounts_receivable_name", "");
      frm.set_value("accounts_receivable_rep_email", "");
      frm.set_value("accounts_receivable_phone_number", "");
    }
  },

  set_primary_contact_as_account_payable_contact: function (frm) {
    if (frm.doc.set_primary_contact_as_account_payable_contact == 1) {
      if (
        frm.doc.contact_name &&
        frm.doc.phone_no &&
        frm.doc.email
      ) {
        frm.set_value(
          "accounts_payable_contact_name",
          frm.doc.contact_name
        );
        frm.set_value("accounts_payable_email", frm.doc.email);
        frm.set_value(
          "accounts_payable_phone_number",
          frm.doc.phone_no
        );
      } else {
        msgprint("You Can't set Primary Contact unless your value are filled");
        frm.set_value("set_primary_contact_as_account_payable_contact", 0);
      }
    } else {
      frm.set_value("accounts_payable_contact_name", "");
      frm.set_value("accounts_payable_email", "");
      frm.set_value("accounts_payable_phone_number", "");
    }
  },
  after_save: async function (frm) {
    create_tag_job_title(frm);
    await frappe.call({
      method: "tag_workflow.tag_data.update_individual_company_lat_lng",
      args: { company: frm.doc.name },
    });
    await frappe.call({
      method:
        "tag_workflow.controllers.master_controller.make_update_comp_perm",
      args: { docname: frm.doc.name },
    });
    if (frm.doc.organization_type == "Staffing") {
      await frappe.call({
        method: "tag_workflow.utils.organization.initiate_background_job",
        args: {
          message: "Company",
          staffing_company: frm.doc.name,
        },
      });
    }
  },
  validate: function (frm) {
    mandatory_fields(frm);
    validate_phone_zip(frm);
    let account_phone_no = frm.doc.accounts_receivable_phone_number || "";
    let receive_email = frm.doc.accounts_receivable_rep_email;
    let pay_email = frm.doc.accounts_payable_email;
    let email = frm.doc.email;
    if (account_phone_no) {
      if (!validate_phone(account_phone_no)) {
        frappe.msgprint({
          message: __("Invalid Accounts Receivable Phone Number!"),
          indicator: "red",
        });
        frappe.validated = false;
      } else {
        set_field(frm, account_phone_no, "accounts_receivable_phone_number");
      }
    }
    if (
      receive_email &&
      (receive_email.length > 120 ||
        !frappe.utils.validate_type(receive_email, "email"))
    ) {
      frappe.msgprint({
        message: __("Not A Valid Accounts Receivable Email"),
        indicator: "red",
      });
      frappe.validated = false;
    }
    if (
      pay_email &&
      (pay_email.length > 120 ||
        !frappe.utils.validate_type(pay_email, "email"))
    ) {
      frappe.msgprint({
        message: __("Not A Valid Accounts Payable Email"),
        indicator: "red",
      });
      frappe.validated = false;
    }
    if (
      email &&
      (email.length > 120 || !frappe.utils.validate_type(email, "email"))
    ) {
      frappe.msgprint({ message: __("Invalid Email!"), indicator: "red" });
      frappe.validated = false;
    }
    if (frm.doc.__islocal != 1) {
      validate_cert_attachment(frm);
    }
    validate_office_code(frm);
  },
  make_organization_inactive(frm) {
    frappe.call({
      method: "tag_workflow.tag_data.disable_user",
      args: {
        company: frm.doc.company_name,
        check: frm.doc.make_organization_inactive,
      },
    });
  },
  click_here: function (frm) {
    if (frm.doc.organization_type != "TAG") {
      frappe.call({
        method:
          "tag_workflow.tag_workflow.doctype.company.company.check_ratings",
        args: {
          company_name: frm.doc.company_name,
          comp_type: frm.doc.organization_type,
        },
        callback: function (r) {
          console.log(r);
          if (r.message) {
            if (frm.doc.organization_type == "Staffing") {
              frappe.set_route("Form", "Company Review");
            } else {
              frappe.set_route("Form", "Hiring Company Review");
            }
          } else {
            frappe.msgprint("There are no reviews for this company yet");
          }
        },
      });
    } else {
      frappe.set_route("Form", "Company Review");
    }
  },
  onload: function (frm) {
    if (frappe.session.user != "Administrator") {
      $(".menu-btn-group").hide();
    }
    if (frappe.boot.tag.tag_user_info.user_type == "Staffing User") {
      frm.set_df_property("staff_complete_enable", "read_only", 1);
      frm.set_df_property("office_code", "read_only", 1);
    }
    filter_row(frm);
  },
  search_on_maps: function (frm) {
    if (frm.doc.search_on_maps == 1) {
      tag_workflow.UpdateField(frm, "map");
      hide_fields(frm);
      show_addr(frm);
      update_complete_address(frm);
    } else if (
      frm.doc.search_on_maps == 0 &&
      frm.doc.enter_manually == 0
    ) {
      frm.set_df_property("map", "hidden", 1);
      show_addr(frm);
    }
  },

  enter_manually: function (frm) {
    if (frm.doc.enter_manually == 1) {
      tag_workflow.UpdateField(frm, "manually");
      show_fields(frm);
      show_addr(frm);
    } else if (
      frm.doc.search_on_maps == 0 &&
      frm.doc.enter_manually == 0
    ) {
      hide_fields(frm);
      frm.set_df_property("map", "hidden", 1);
      show_addr(frm);
    }
  },
  before_save: async function (frm) {
    frm.doc.employees = [];
    frm.doc.enable_perpetual_inventory = 0;
    const u_type = frappe.boot.tag.tag_user_info.user_type
      ? frappe.boot.tag.tag_user_info.user_type.toLowerCase()
      : null;
    if (
      frappe.boot.tag.tag_user_info.company_type == "Hiring" ||
      frappe.boot.tag.tag_user_info.company_type == "Exclusive Hiring" ||
      (u_type == "tag admin" &&
        ["Hiring", "Exclusive Hiring"].includes(frm.doc.organization_type))
    ) {
      update_table(frm);
    }
    save_password_data(frm);
    update_invoice_view(frm);
    if (frm.doc.staff_complete_enable == 0) {
      frm.set_value("office_code", "");
    }

    frappe.dom.freeze();
    await check_enable_active(frm);
    await check_enable_active_staff(frm);
    await check_enable_active_quick(frm);
    await check_enable_active_work(frm);
    frappe.dom.unfreeze();
  },
  phone_no: function (frm) {
    set_field(frm, frm.doc.phone_no, "phone_no");
  },
  accounts_receivable_phone_number: function (frm) {
    set_field(
      frm,
      frm.doc.accounts_receivable_phone_number,
      "accounts_receivable_phone_number"
    );
  },
  accounts_payable_phone_number: function (frm) {
    set_field(
      frm,
      frm.doc.accounts_payable_phone_number,
      "accounts_payable_phone_number"
    );
  },
  zip: function (frm) {
    let zip = frm.doc.zip;
    frm.set_value("zip", zip ? zip.toUpperCase() : zip);
  },
  upload_company_logo: (frm) => {
    if (frm.doc.upload_company_logo) {
      frappe.db.get_value(
        "File",
        {
          file_url: frm.doc.upload_company_logo,
          attached_to_name: frm.doc.name,
          attached_to_field: "upload_company_logo",
        },
        ["file_size"],
        (r) => {
          if (r.file_size && r.file_size > 2097152) {
            frappe.msgprint({
              message: __(
                "File size exceeded the maximum allowed size of 2.0 MB"
              ),
              title: __("Message"),
              indicator: "red",
            });
            frm.set_value("upload_company_logo", "");
          }
        }
      );
    }
  },
  certificate_and_endorsements: (frm) => {
    let cert_list = ["DBE", "DVOSB", "MBE", "SDVOSB", "VOSB", "WBE", "WOSB"];
    let requested_cert = frm.doc.certificate_and_endorsements.split("-");
    if (frm.doc.certificate_and_endorsements) {
      if (localStorage.getItem("cert_list_exist") == 0) {
        localStorage.setItem(
          "cert_list_exist",
          JSON.stringify([frm.doc.certificate_and_endorsements])
        );
        console.log(JSON.parse(localStorage.getItem("cert_list_exist")));
      } else {
        let updated_list = JSON.parse(localStorage.getItem("cert_list_exist"));
        updated_list.push(frm.doc.certificate_and_endorsements);
        localStorage.setItem("cert_list_exist", JSON.stringify(updated_list));
        console.log(JSON.parse(localStorage.getItem("cert_list_exist")));
      }
    }
    if (frm.doc.certificate_and_endorsements) {
      frm.set_value("certificate_and_endorsements", "");
    }
    for (let cert of cert_list) {
      if (cert == requested_cert[0]) {
        let id_initiator = Number(localStorage.getItem("id_initiator")) + 1;
        localStorage.setItem("id_initiator", id_initiator);
        let updated_html = `
				<div class="row input_field_in_custom_div" id="eliminate_${id_initiator}">
					<div class="col-xl-3 pr-0">
						<div> <button type="button" id="cancel_${id_initiator}" class="px-2 btn btn-sm certificate-btn" onclick="eliminate_div(this.id)">
						<span id = "span_${id_initiator}"> ${cert} </span>
						<svg class="icon  icon-sm ml-1" style="">
							<use class="" href="#icon-delete"></use>
						</svg>
						</button> 
						</div>
					</div>
					<div class="col-xl-9 pl-lg-1 pl-3 mt-3 mt-lg-0 ">
						<div class="control-input-wrapper">						
						<div class="control-input">
							<div class="attached-file p-1 flex justify-between align-center" id ="after_attach_${id_initiator}"  style="display: none;">
								<div class="ellipsis">
									<i class="fa fa-paperclip"></i>
									<a class="attached-file-link" target="_blank" id="anchor_${id_initiator}" href="" value = "1"></a>
								</div>
								<div>
									<a class="btn btn-xs btn-default"  data-action="clear_attachment" id= "clear_${id_initiator}" onclick=clear_func(this.id)>Clear</a>
								</div>
							</div>
							<button class="btn btn-default btn-sm btn-attach" id="attach_${id_initiator}" data-fieldtype="Attach" data-fieldname="" onclick=attach_file(this.id) placeholder="" data-doctype="Company" style="display: inline-block;">Attach</button></div>					
							<div class="control-value like-disabled-input" style="display: none;"></div>							
						</div>
					</div>
				`;
        document.getElementById("custom_attach_div").innerHTML =
          document.getElementById("custom_attach_div").innerHTML + updated_html;
        break;
      }
    }
  },
  timeline_refresh: (frm) => {
    invoice_view(frm);
  },
});

function jazz_connect_button(frm) {
  let container = document.querySelector(
    `#company-integration_details > div:nth-child(3)`
  );
  let btn = document.createElement("button");
  btn.className = `btn btn-primary btn-xs primary-action add-btn-custom-location add-btn-jazz`;
  btn.id = `add-btn-jazz`;
  container.appendChild(btn);
  if (frm.doc.enable_jazz_hr === 1) {
    remove_btn_primary("jazz");
  } else {
    add_btn_primary("jazz");
  }
  btn.onclick = () => {
    if (btn.textContent === "Connect") {
      let enable_field_name = "enable_jazz_hr";
      let fields = { jazzhr_api_key: "jazzhr_api_key_html" };
      connect_integration(frm, enable_field_name, fields);
      if (frm.doc.enable_jazz_hr === 1) {
        remove_btn_primary("jazz");
      }
    } else {
      if (frm.doc.enable_jazz_hr === 0) {
        add_btn_primary("jazz");
      }
      let enable_field_name = ["enable_jazz_hr", "Jazz Hr"];
      let fields = { jazzhr_api_key: "jazzhr_api_key_html" };
      disconnect_integration(frm, enable_field_name, fields, "jazz");
    }
  };
}

function quick_connect_button(frm) {
  let container = document.querySelector(
    `#company-integration_details > div:nth-child(5)`
  );
  let btn = document.createElement("button");
  btn.className = `btn btn-primary btn-xs primary-action add-btn-custom-location add-btn-quick`;
  btn.id = `add-btn-quick`;
  container.appendChild(btn);
  if (frm.doc.enable_quickbook === 1) {
    remove_btn_primary("quick");
  } else {
    add_btn_primary("quick");
  }
  btn.onclick = () => {
    if (btn.textContent === "Connect") {
      let enable_field_name = "enable_quickbook";
      let fields = {
        client_id: "client_id_html",
        client_secret: "client_secret_html",
      };
      connect_integration(frm, enable_field_name, fields);
      if (frm.doc.enable_quickbook === 1) {
        remove_btn_primary("quick");
      }
    } else {
      if (frm.doc.enable_quickbook === 0) {
        add_btn_primary("quick");
      }
      let enable_field_name = ["enable_quickbook", "Quick Book"];
      let fields = {
        client_id: "client_id_html",
        client_secret: "client_secret_html",
      };
      disconnect_integration(frm, enable_field_name, fields, "quick");
    }
  };
}

function work_connect_button(frm) {
  let container = document.querySelector(
    `#company-integration_details > div:nth-child(9)`
  );
  let btn = document.createElement("button");
  btn.className = `btn btn-primary btn-xs primary-action add-btn-custom-location add-btn-work`;
  btn.id = `add-btn-work`;
  container.appendChild(btn);
  if (frm.doc.enable_workbright === 1) {
    remove_btn_primary("work");
  } else {
    add_btn_primary("work");
  }
  btn.onclick = () => {
    if (btn.textContent === "Connect") {
      let enable_field_name = "enable_workbright";
      let fields = {
        workbright_subdomain: "workbright_subdomain_html",
        workbright_api_key: "workbright_api_key_html",
      };
      connect_integration(frm, enable_field_name, fields);
      if (frm.doc.enable_workbright === 1) {
        remove_btn_primary("work");
      }
    } else {
      if (frm.doc.enable_workbright === 0) {
        add_btn_primary("work");
      }
      let enable_field_name = ["enable_workbright", "Workbright"];
      let fields = {
        workbright_subdomain: "workbright_subdomain_html",
        workbright_api_key: "workbright_api_key_html",
      };
      disconnect_integration(frm, enable_field_name, fields, "work");
    }
  };
}

function check_branch_connect_button(frm) {
  //For Branch Integration
  if (frappe.boot.tag.tag_user_info.user_type == "TAG Admin") {
    branch_connect_button(frm);
  }
}
function branch_connect_button(frm) {
  //For Branch Integration
  let container = document.querySelector(
    `#company-integration_details > div:nth-child(2)`
  );
  let btn = document.createElement("button");
  btn.className = `btn btn-primary btn-xs primary-action add-btn-custom-location add-btn-branch`;
  btn.id = `add-btn-branch`;
  container.appendChild(btn);
  if (frm.doc.branch_enabled === 1) {
    remove_btn_primary("branch");
  } else {
    add_btn_primary("branch");
  }
  btn.onclick = () => {
    if (btn.textContent === "Connect") {
      let enable_field_name = "branch_enabled";
      let fields = {
        branch_org_id: "branch_org_id_html",
        branch_api_key: "branch_api_key_html",
      };
      connect_integration(frm, enable_field_name, fields);
      if (frm.doc.branch_enabled === 1) {
        remove_btn_primary("branch");
      }
    } else {
      if (frm.doc.branch_enabled === 0) {
        add_btn_primary("branch");
      }
      let enable_field_name = ["branch_enabled", "Branch"];
      let fields = {
        branch_org_id: "branch_org_id_html",
        branch_api_key: "branch_api_key_html",
      };
      disconnect_integration(frm, enable_field_name, fields, "branch");
    }
  };
}

function staff_connect_button(frm) {
  let container = document.querySelector(
    `#company-integration_details > div:nth-child(8)`
  );
  let btn = document.createElement("button");
  btn.className = `btn btn-primary btn-xs primary-action add-btn-custom-location add-btn-staff`;
  btn.id = `add-btn-staff`;
  container.appendChild(btn);
  if (frm.doc.staff_complete_enable === 1) {
    remove_btn_primary("staff");
  } else {
    add_btn_primary("staff");
  }
  btn.onclick = () => {
    if (btn.textContent === "Connect") {
      let enable_field_name = "staff_complete_enable";
      frm.set_value(enable_field_name, 1);
      if (frm.doc.staff_complete_enable === 1) {
        remove_btn_primary("staff");
      }
    } else {
      if (frm.doc.staff_complete_enable === 0) {
        add_btn_primary("staff");
      }
      let enable_field_name = ["staff_complete_enable", "Staff Complete"];
      let fields = {};
      disconnect_integration(frm, enable_field_name, fields, "staff");
    }
  };
}

/*----------init values-----------*/
function init_values(frm) {
  if (frm.doc.__islocal == 1 && frm.doc.doctype == "Company") {
    $(".page-title .title-area .title-text").css("cursor", "auto");
    let company_data = {
      default_currency: "USD",
      country: "United States",
      create_chart_of_accounts_based_on: "Standard Template",
      chart_of_accounts: "Standard with Numbers",
      parent_staffing: "",
    };

    let keys = Object.keys(company_data);
    for (let val in keys) {
      frm.set_value(keys[val], company_data[keys[val]]);
      frm.toggle_enable(keys[val], 0);
    }
  } else {
    $(".page-title .title-area .title-text").css("cursor", "pointer");
  }
}

/*----update field properity-----*/
function update_company_fields(frm) {
  let roles = frappe.user_roles;
  let is_local = frm.doc.__islocal;
  let company_fields = [
    "organization_type",
    "country",
    "industry",
    "default_currency",
    "parent_staffing",
  ];

  if (
    roles.includes("System Manager") &&
    !is_local &&
    frm.doc.organization_type != "TAG"
  ) {
    for (let f in company_fields) {
      frm.toggle_enable(company_fields[f], 0);
    }
  }

  if (roles.includes("System Manager") || is_local == 1) {
    frm.toggle_display(company_fields[0], 1);
  } else {
    frm.toggle_enable(company_fields[0], 0);
  }

  if (
    frappe.boot.tag.tag_user_info.user_type == "Hiring User" ||
    frappe.boot.tag.tag_user_info.user_type == "Staffing User"
  ) {
    let company_field = [
      "organization_type",
      "country",
      "industry",
      "default_currency",
      "parent_staffing",
      "name",
      "jazzhr_api_key",
      "make_organization_inactive",
      "company_name",
      "fein",
      "title",
      "primary_language",
      "contact_name",
      "phone_no",
      "email",
      "set_primary_contact_as_account_payable_contact",
      "set_primary_contact_as_account_receivable_contact",
      "accounts_payable_contact_name",
      "accounts_payable_email",
      "accounts_payable_phone_number",
      "accounts_receivable_name",
      "accounts_receivable_rep_email",
      "accounts_receivable_phone_number",
      "cert_of_insurance",
      "w9",
      "safety_manual",
      "industry_type",
      "employees",
      "address",
      "city",
      "state",
      "zip",
      "drug_screen",
      "drug_screen_rate",
      "background_check",
      "background_check_rate",
      "upload_docs",
      "about_organization",
      "mvr",
      "mvr_rate",
      "shovel",
      "shovel_rate",
      "contract_addendums",
      "rating",
      "average_rating",
      "click_here",
      "hour_per_person_drug",
      "background_check_flat_rate",
      "mvr_per",
      "shovel_per_person",
      "workbright_subdomain",
      "workbright_api_key",
    ];
    for (let f in company_field) {
      frm.toggle_enable(company_field[f], 0);
    }
  }
}

/*--------phone and zip validation----------*/
function validate_phone_zip(frm) {
  let phone = frm.doc.phone_no || "";
  let zip = frm.doc.zip;
  let phone_no = frm.doc.accounts_payable_phone_number || "";
  let is_valid = 1;
  if (phone) {
    if (!validate_phone(phone)) {
      is_valid = 0;
      frappe.msgprint({
        message: __("Invalid Company Phone Number!"),
        indicator: "red",
      });
    } else {
      set_field(frm, phone, "phone_no");
    }
  }
  if (zip) {
    frm.set_value("zip", zip.toUpperCase());
    if (!validate_zip(zip)) {
      is_valid = 0;
      frappe.msgprint({ message: __("Invalid Zip!"), indicator: "red" });
    }
  }
  if (phone_no) {
    if (!validate_phone(phone_no)) {
      is_valid = 0;
      frappe.msgprint({
        message: __("Invalid Accounts Payable Phone Number!"),
        indicator: "red",
      });
    } else {
      set_field(frm, phone_no, "accounts_payable_phone_number");
    }
  }
  if (is_valid == 0) {
    frappe.validated = false;
  }
}

/*--------jazzhr------------*/
function make_jazzhr_request(frm) {
  if (frm.doc.jazzhr_api_key) {
    frappe.call({
      method: "tag_workflow.utils.jazz_integration.jazzhr_fetch_applicants",
      args: {
        api_key: frm.doc.jazzhr_api_key,
        company: frm.doc.name,
        action: 1,
      },
      freeze: true,
      freeze_message: "<p><b>Fetching records from JazzHR...</b></p>",
      callback: function () {
        frappe.msgprint(
          "Employees are being added in the background. You may continue using the application"
        );
        $('[data-fieldname="get_data_from_jazzhr"]')[1].disabled = 1;
        $('[data-fieldname="update_employee_records"]')[1].disabled = 1;
        add_terminate_button(frm);
      },
    });
  } else {
    frm.scroll_to_field("jazzhr_api_key");
    frappe.msgprint("<b>JazzHR API Key</b> is required");
  }
}

function hide_tag_charges(frm) {
  let roles = frappe.user_roles;
  if (!roles.includes("System Manager")) {
    frm.toggle_display("tag_charges", 0);
  }
}

function uploaded_file_format(frm) {
  frm.get_field("cert_of_insurance").df.options = {
    restrictions: {
      allowed_file_types: [".pdf", ".txt", ".docx"],
    },
  };

  frm.get_field("w9").df.options = {
    restrictions: {
      allowed_file_types: [".pdf", ".txt", ".docx"],
    },
  };

  frm.get_field("safety_manual").df.options = {
    restrictions: {
      allowed_file_types: [".pdf", ".txt", ".docx"],
    },
  };

  frm.get_field("upload_docs").df.options = {
    restrictions: {
      allowed_file_types: [".pdf", ".txt", ".docx"],
    },
  };
  frm.get_field("upload_company_logo").df.options = {
    restrictions: {
      allowed_file_types: [".jpg", ".jpeg", ".png", ".svg"],
    },
  };
}

function cancel_company(frm) {
  frm.add_custom_button(__("Cancel"), function () {
    frappe.set_route("Form", "Company");
  });
}

function org_info(frm) {
  frappe.call({
    method: "tag_workflow.tag_data.hiring_org_name",
    args: { current_user: frappe.session.user },
    callback: function (r) {
      if (r.message == "success") {
        frm.set_value("parent_staffing", frappe.boot.tag.tag_user_info.company);
      } else {
        frm.set_value("parent_staffing", "");
      }
    },
  });
}

function download_document(frm) {
  if (frm.doc.upload_docs && frm.doc.upload_docs.length > 1) {
    $('[data-fieldname="upload_docs"]').on("click", (e) => {
      doc_download(e);
    });
  }

  if (frm.doc.cert_of_insurance && frm.doc.cert_of_insurance.length > 1) {
    $('[data-fieldname="cert_of_insurance"]').on("click", (e) => {
      doc_download(e);
    });
  }

  if (frm.doc.w9 && frm.doc.w9.length > 1) {
    $('[data-fieldname="w9"]').on("click", (e) => {
      doc_download(e);
    });
  }

  if (frm.doc.safety_manual && frm.doc.safety_manual.length > 1) {
    $('[data-fieldname="safety_manual"]').on("click", (e) => {
      doc_download(e);
    });
  }

  $('[data-fieldname="resume"]').on("click", (e) => {
    doc_download(e);
  });
}

function doc_download(e) {
  let file = e.target.innerText;
  if (file.includes(".") && file.length > 1) {
    let link = "";
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

// for prevent Enter on company page
$(document).keypress(function (event) {
  if (event.which == "13") {
    event.preventDefault();
  }
});
function exclusive_staff_company_fields(frm) {
  if (
    frappe.boot.tag.tag_user_info.company_type == "Exclusive Hiring" &&
    frm.doc.__islocal != 1 &&
    frm.doc.organization_type == "Staffing"
  ) {
    let company_field = [
      "organization_type",
      "country",
      "industry",
      "default_currency",
      "parent_staffing",
      "name",
      "jazzhr_api_key",
      "make_organization_inactive",
      "company_name",
      "fein",
      "title",
      "primary_language",
      "contact_name",
      "phone_no",
      "email",
      "set_primary_contact_as_account_payable_contact",
      "set_primary_contact_as_account_receivable_contact",
      "accounts_payable_contact_name",
      "accounts_payable_email",
      "accounts_payable_phone_number",
      "accounts_receivable_name",
      "accounts_receivable_rep_email",
      "accounts_receivable_phone_number",
      "cert_of_insurance",
      "w9",
      "safety_manual",
      "industry_type",
      "employees",
      "address",
      "city",
      "state",
      "zip",
      "drug_screen",
      "drug_screen_rate",
      "background_check",
      "background_check_rate",
      "upload_docs",
      "about_organization",
      "mvr",
      "mvr_rate",
      "shovel",
      "shovel_rate",
      "contract_addendums",
      "rating",
      "average_rating",
      "click_here",
      "hour_per_person_drug",
      "background_check_flat_rate",
      "mvr_per",
      "shovel_per_person",
      "suite_or_apartment_no",
      "registration_details",
      "job_site",
    ];
    for (let f in company_field) {
      frm.toggle_enable(company_field[f], 0);
    }
    $('[data-label="Save"]').hide();
  } else if (
    frappe.boot.tag.tag_user_info.company_type == "Exclusive Hiring" &&
    frm.doc.__islocal != 1 &&
    frm.doc.organization_type == "Exclusive Hiring"
  ) {
    $('[data-label="Save"]').show();
  }
}

function removing_registration_verbiage(frm) {
  if (frm.doc.organization_type == "Staffing" && frm.doc.__islocal != 1) {
    frm.set_df_property("registration_details", "label", "");
    frm.set_df_property("registration_details", "description", "");
  }
}
function hide_fields(frm) {
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
function show_fields(frm) {
  frm.set_df_property("city", "hidden", 0);
  frm.set_df_property("state", "hidden", 0);
  frm.set_df_property("zip", "hidden", 0);
}

function update_existing_employees(frm) {
  if (frm.doc.jazzhr_api_key) {
    $('[data-fieldname="get_data_from_jazzhr"]')[1].disabled = 1;
    $('[data-fieldname="update_employee_records"]')[1].disabled = 1;
    frappe.msgprint(
      "Employees are being updated in the background. You may continue using the application"
    );

    frappe.call({
      method: "tag_workflow.utils.jazz_integration.jazzhr_update_applicants",
      args: { api_key: frm.doc.jazzhr_api_key, company: frm.doc.name },
    });
    add_terminate_button(frm);
  } else {
    frm.scroll_to_field("jazzhr_api_key");
    frappe.msgprint("<b>JazzHR API Key</b> is required");
  }
}

function show_addr(frm) {
  if (frm.doc.search_on_maps) {
    frm.get_docfield("address").label = "Complete Address";
  } else if (frm.doc.enter_manually) {
    frm.get_docfield("address").label = "Address";
  }
  frm.refresh_field("address");
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
const html_billing = `<!doctype html>
  <html>
    <head>
      <meta charset="utf-8">
    </head>
    <body>
      <input class="form-control" placeholder="Search a location" id="autocomplete-address-billing" style="height: 30px;margin-bottom: 15px;">
      <div class="tab-content" title="map_billing" style="text-align: center;padding: 4px;">
        <div id="map_billing" style="height:450px;border-radius: var(--border-radius-md);"></div>
      </div>
    </body>
  </html>
`;
function set_map(frm) {
  setTimeout(() => {
    $(frm.fields_dict.map.wrapper).html(html);
    initMap();
  }, 500);
  setTimeout(() => {
    $(frm.fields_dict.map_billing.wrapper).html(html_billing);
    initMapBilling();
  }, 500);
  if (frm.is_new()) {
    frm.set_df_property("map", "hidden", 1);
    $('.frappe-control[data-fieldname="html"]').html("");
    $('.frappe-control[data-fieldname="map"]').html("");
  } else if (
    (frm.doc.search_on_maps == 0 && frm.doc.enter_manually == 0) ||
    frm.doc.enter_manually == 1
  ) {
    frm.set_df_property("map", "hidden", 1);
  }
}

function set_field(frm, phone, fieldname) {
  if (phone) {
    frm.set_value(
      fieldname,
      validate_phone(phone) ? validate_phone(phone) : phone
    );
  }
}

/*-----------------------------------*/
function make_button_disable(frm) {
  frappe.call({
    method: "tag_workflow.utils.jazz_integration.button_disabled",
    args: { company: frm.doc.name },
    callback: function (r) {
      if (r.message) {
        $('[data-fieldname="get_data_from_jazzhr"]')[1].disabled = 1;
        $('[data-fieldname="update_employee_records"]')[1].disabled = 1;
        add_terminate_button(frm);
      }
    },
  });
}

function add_terminate_button(frm) {
  frm
    .add_custom_button(__("Stop JazzHR Job"), function () {
      frappe.call({
        method: "tag_workflow.utils.jazz_integration.terminate_job",
        args: { company: frm.doc.name },
        callback: function (r) {
          if (r.message) {
            frappe.msgprint(
              "The Background Job (JazzHR) for this company is stopped"
            );
            $('[data-fieldname="get_data_from_jazzhr"]')[1].disabled = 0;
            $('[data-fieldname="update_employee_records"]')[1].disabled = 0;
            frm.remove_custom_button("Stop JazzHR Job");
            make_button_disable(frm);
          }
        },
      });
    })
    .addClass("btn-primary");
}

function update_lat_lng(frm) {
  if (frappe.session.user == "Administrator") {
    frm
      .add_custom_button(__("Update lat lng"), function () {
        if (frm.doc.__islocal) {
          frappe.msgprint("Please save the form first.");
        } else {
          frappe.call({
            method: "tag_workflow.tag_data.update_lat_lng",
            args: { company: frm.doc.name },
            freeze: true,
            freeze_message: "<p><b>Fetching records from JazzHR...</b></p>",
            callback: function () {
              frappe.msgprint(
                "Employees are being updated in the background. You may continue using the application"
              );
            },
          });
        }
      })
      .addClass("btn-primary");
  }
}

/*-------------auth url------------*/
function update_auth_url(frm) {
  let domain = frappe.urllib.get_base_url();
  let redirect_url = `${domain}/api/method/tag_workflow.utils.quickbooks.callback`;
  if (frm.doc.redirect_url != redirect_url) {
    frm.set_value("redirect_url", redirect_url);
  }
}

/*------------------------------------*/
function bulk_upload_resume(frm) {
  if (
    frm.doc.__islocal != 1 &&
    frm.doc.bulk_resume &&
    frappe.boot.tag.tag_user_info.company_type != "Hiring"
  ) {
    frm
      .add_custom_button(__("Upload Resume"), function () {
        let attachments = frm.attachments.get_attachments();
        let attachment = [];
        for (let a in attachments) {
          if (frm.doc.bulk_resume == attachments[a].file_url) {
            attachment.push(attachments[a]);
          }
        }
        if (attachment) {
          frappe.call({
            method: "tag_workflow.utils.bulk_upload_resume.update_resume",
            args: {
              company: frm.doc.name,
              zip_file: frm.doc.bulk_resume,
              name: frm.doc.name,
              attachment_name: attachment[0].name,
              file_name: attachment[0].file_name,
              file_url: attachment[0].file_url,
            },
            freeze: 1,
            freeze_message:
              "<b>Please wait while we are working the file...</b>",
            callback: function () {
              frappe.msgprint(
                "Resume(s) are being updated in the background. You may continue using the application"
              );
            },
          });
        }
      })
      .addClass("btn-primary");
  }
}

/*--------------------Update Complete Address---------------------*/
function update_complete_address(frm) {
  if (frm.doc.zip && frm.doc.state && frm.doc.city) {
    let data = {
      street_number: "",
      route: frm.doc.suite_or_apartment_no ? frm.doc.suite_or_apartment_no : "",
      locality: frm.doc.city,
      administrative_area_level_1: frm.doc.state,
      postal_code: frm.doc.zip ? frm.doc.zip : 0,
    };
    update_comp_address(frm, data);
  } else {
    frm.set_value("complete_address", "");
  }
}

function update_comp_address(frm, data) {
  frappe.call({
    method: "tag_workflow.tag_data.update_complete_address",
    args: {
      data: data,
    },
    callback: function (r) {
      if (r.message != "No Data") {
        if (r.message != frm.doc.complete_address) {
          frm.set_value("complete_address", r.message);
          frm.set_value("address", r.message);
        }
      } else {
        frm.set_value("complete_address", "");
        frm.set_value("address", "");
      }
    },
  });
}

function mandatory_fields(frm) {
  let reqd_fields = {
    "Company Type": frm.doc.organization_type,
    "Company Name": frm.doc.company_name,
  };
  if (frm.doc.organization_type == "Exclusive Hiring") {
    reqd_fields["Parent Staffing"] = frm.doc.parent_staffing;
  }
  let message = "<b>Please Fill Mandatory Fields:</b>";
  for (let key in reqd_fields) {
    if (
      reqd_fields[key] === undefined ||
      !reqd_fields[key] ||
      (reqd_fields[key] && !reqd_fields[key].trim())
    ) {
      message = message + "<br>" + "<span>&bull;</span> " + key;
    }
  }
  if (message != "<b>Please Fill Mandatory Fields:</b>") {
    frappe.msgprint({
      message: __(message),
      title: __("Missing Fields"),
      indicator: "orange",
    });
    frappe.validated = false;
  }
}
const u_type = frappe.boot.tag.tag_user_info.user_type
  ? frappe.boot.tag.tag_user_info.user_type.toLowerCase()
  : null;
const u_roles = ["staffing admin", "tag admin"];
const comp = frappe.boot.tag.tag_user_info.company_type;

function hide_and_show_tables(frm) {
  if (
    comp == "Hiring" ||
    comp == "Exclusive Hiring" ||
    (u_type == "tag admin" &&
      !["Staffing", "TAG"].includes(frm.doc.organization_type)) ||
    (u_type == "staffing admin" &&
      frm.doc.organization_type == "Exclusive Hiring")
  ) {
    frm.set_df_property(
      "other_details",
      "options",
      update_inner_html("Job Titles")
    );
    frm.set_df_property("industry_type", "hidden", 1);
    frm.set_df_property("job_titles", "hidden", 0);
  } else if (u_type == "tag admin" && comp.toLowerCase == "tag") {
    frm.set_df_property(
      "other_details",
      "options",
      update_inner_html("Job Industry(ies)")
    );
    frm.set_df_property("industry_type", "hidden", 0);
    frm.set_df_property("job_titles", "hidden", 0);
  } else {
    frm.set_df_property(
      "other_details",
      "options",
      update_inner_html("Job Industry(ies)")
    );
    frm.set_df_property("industry_type", "hidden", 0);
    frm.set_df_property("job_titles", "hidden", 1);
  }
}
function update_inner_html(phrase) {
  const inner_html = `\n\t\t\t${phrase}\n\t\t\t<span class="ml-2 collapse-indicator mb-1 tip-top" style="display: inline;"><svg class="icon  icon-sm" style="">\n\t\t\t<use class="mb-1" id="up-down" href="#icon-down"></use>\n\t\t</svg></span>\n\t\t`;
  $(".frappe-control[data-fieldname='job_titles']")
    .parent()
    .parent()
    .parent(".section-body")
    .siblings(".section-head")
    .html(inner_html);
  return 1;
}

if (
  frappe.boot.tag.tag_user_info.company_type == "Hiring" ||
  frappe.boot.tag.tag_user_info.company_type == "Exclusive Hiring" ||
  u_roles.includes(u_type)
) {
  jQuery(document).on(
    "click",
    `.tip-top,.${$(".frappe-control[data-fieldname='job_titles']")
      .parent()
      .parent()
      .parent(".section-body")
      .siblings(".section-head")
      .attr("class")}`,
    function () {
      const cls = $(".frappe-control[data-fieldname='job_titles']")
        .parent()
        .parent()
        .parent(".section-body")
        .siblings(".section-head")
        .hasClass("collapsed");
      cls
        ? $("#up-down").attr("href", "#icon-down")
        : $("#up-down").attr("href", "#icon-up-line");
    }
  );
}

function filter_row(frm) {
  frm.fields_dict["job_titles"].grid.get_field("job_titles").get_query =
    function (doc, cdt, cdn) {
      const row = locals[cdt][cdn];
      let jobtitle = frm.doc.job_titles,
        title_list = [];
      for (let t in jobtitle) {
        if (jobtitle[t]["job_titles"]) {
          title_list.push(jobtitle[t]["job_titles"]);
        }
      }
      if (row.industry_type) {
        return {
          query: "tag_workflow.tag_data.get_jobtitle_based_on_industry",
          filters: {
            industry: row.industry_type,
            company: doc.name,
            title_list: title_list,
          },
        };
      } else {
        return {
          query: "tag_workflow.tag_data.get_jobtitle_based_on_company",
          filters: {
            company: doc.name,
            title_list: title_list,
          },
        };
      }
    };
}
function update_table(frm) {
  frappe.run_serially([
    () => frm.clear_table("industry_type"),
    () => {
      if (frm.doc.job_titles) {
        const industries = frm.doc.job_titles
          .map((title) => title.industry_type)
          .filter((value, index, self) => self.indexOf(value) === index);
        if (industries.length > 0) {
          industries.map((i) => {
            let row = frm.add_child("industry_type");
            row.industry_type = i;
          });
        }
      }
      frm.refresh_field("industry_type");
    },
  ]);
}

function get_date_time() {
  let today = new Date();
  let date_time = `${today.getFullYear()}-${
    today.getMonth() + 1
  }-${today.getDate()}  ${today.getHours()}:${today.getMinutes()}:${today.getSeconds()}`;
  return date_time.toString();
}

function password_fields(frm, fields, bool) {
  for (let field in fields) {
    let button_html = "";
    if (frappe.boot.tag.tag_user_info.user_type == "Staffing Admin") {
      button_html = staff_admin_edit_buttons(bool, button_html, field);
    } else if (frappe.boot.tag.tag_user_info.user_type == "Staffing User") {
      button_html = staffing_user_edit_buttons(field, button_html);
    } else {
      button_html += bool?
      `<button class="btn btn-default btn-more btn-sm" id="${field}-decrypt" onclick="show_decrypt(this.id, '${field}')" style="width: 60px;height: 25px;padding: 3px;display:none">Decrypt</button>`
      :`<button class="btn btn-default btn-more btn-sm" id="${field}-decrypt" onclick="show_decrypt(this.id, '${field}')" style="width: 60px;height: 25px;padding: 3px;">Decrypt</button>`;
      button_html += bool?
      `<button class="btn btn-default btn-more btn-sm" id="${field}-edit_off" onclick="edit_pass(this.id, '${field}')" style="width: 45px;height: 25px;padding: 3px;float: right;display:none">Edit</button>`
      :`<button class="btn btn-default btn-more btn-sm" id="${field}-edit_off" onclick="edit_pass(this.id, '${field}')" style="width: 45px;height: 25px;padding: 3px;float: right;">Edit</button>`;
    }
    $('[data-fieldname="' + field + '_data"]').attr("readonly", "readonly");
    $('[data-fieldname="' + field + '_data"]').attr("type", "password");
    $('[data-fieldname="' + field + '_data"]').attr("title", "");
    frm.set_df_property(fields[field], "options", button_html);
  }
}

window.edit_pass = (id, field) => {
  if (id.split("-")[1] == "edit_off") {
    $('[data-fieldname="' + field + '_data"]').removeAttr("readonly");
    $('[data-fieldname="' + field + '_data"]').attr("type", "text");
    $("#" + field + "-decrypt").hide();
    $("#" + field + "-encrypt").hide();
    $("#" + id).hide();
    $("#" + id).attr("id", field + "-edit_on");
    show_pass(field);
  }
};

window.show_decrypt = (id, field) => {
  if (id.split("-")[1] == "decrypt") {
    $('[data-fieldname="' + field + '_data"]').attr("type", "text");
    $("#" + field + "-decrypt").text("Encrypt");
    $("#" + field + "-decrypt").attr("id", field + "-encrypt");
    show_pass(field);
  } else {
    hide_pass(field);
    $('[data-fieldname="' + field + '_data"]').attr("type", "password");
    $("#" + field + "-encrypt").text("Decrypt");
    $("#" + field + "-encrypt").attr("id", field + "-decrypt");
  }
};

function staffing_user_edit_buttons(field, button_html) {
  if (["branch_org_id", "branch_api_key"].includes(field)) {
    button_html += `<button class="btn btn-default btn-more btn-sm" id="${field}-decrypt" onclick="show_decrypt(this.id, '${field}')" style="width: 60px;height: 25px;padding: 3px;">Decrypt</button>`;
  }
  return button_html;
}

function staff_admin_edit_buttons(bool, button_html, field) {
  if (bool) {
    button_html += `<button class="btn btn-default btn-more btn-sm" id="${field}-decrypt" onclick="show_decrypt(this.id, '${field}')" style="width: 60px;height: 25px;padding: 3px;display:none">Decrypt</button>`;
    if (!["branch_org_id", "branch_api_key"].includes(field)) {
      button_html += `<button class="btn btn-default btn-more btn-sm" id="${field}-edit_off" onclick="edit_pass(this.id, '${field}')" style="width: 45px;height: 25px;padding: 3px;float: right;display:none;">Edit</button>`;
    }
  } else {
    button_html += `<button class="btn btn-default btn-more btn-sm" id="${field}-decrypt" onclick="show_decrypt(this.id, '${field}')" style="width: 60px;height: 25px;padding: 3px;">Decrypt</button>`;
    if (!["branch_org_id", "branch_api_key"].includes(field)) {
      button_html += `<button class="btn btn-default btn-more btn-sm" id="${field}-edit_off" onclick="edit_pass(this.id, '${field}')" style="width: 45px;height: 25px;padding: 3px;float: right;">Edit</button>`;
    }
  }
  return button_html;
}

function show_pass(fieldname) {
  frappe.call({
    method: "tag_workflow.tag_data.get_password",
    args: {
      fieldname: fieldname,
      comp_name: cur_frm.doc.name,
    },
    callback: (res) => {
      if (res.message != "Not Found") {
        cur_frm.set_value(fieldname + "_data", res.message);
      } else if (cur_frm.doc[fieldname]) {
        cur_frm.set_value(
          fieldname + "_data",
          "•".repeat(cur_frm.doc[fieldname])
        );
      } else {
        cur_frm.set_value(fieldname + "_data", "");
      }
    },
  });
}

function hide_pass(fieldname) {
  if (cur_frm.doc[fieldname]) {
    cur_frm.set_value(fieldname, "•".repeat(cur_frm.doc[fieldname].length));
  }
}

function save_password_data(frm) {
  let fields = {
    jazzhr_api_key_data: "jazzhr_api_key",
    client_id_data: "client_id",
    client_secret_data: "client_secret",
    workbright_subdomain_data: "workbright_subdomain",
    workbright_api_key_data: "workbright_api_key"
  };
  for (let field in fields) {
    if (frm.doc[field]) {
      frm.set_value(fields[field], frm.doc[field]);
    } else {
      frm.set_value(fields[field], undefined);
    }
  }
}

function validate_cert_attachment(frm) {
  let check_for_update = 0;
  let cert_list_details = [];
  for (let i = 1; i <= Number(localStorage.getItem("id_initiator")); i++) {
    let cert_type = document.getElementById("span_" + i).innerHTML;
    cert_type = cert_type.trim();
    let link = document.getElementById("anchor_" + i).innerHTML;
    if (!link || link == "0") {
      check_for_update = 1;
      frappe.validated = false;
      frappe.msgprint({
        message: __("	Certificate and Endorsements: Please Attach Certificate"),
        title: __("Warning"),
        indicator: "red",
      });
      frm.refresh();
      break;
    }
    link = link.trim();
    let make_it_link = "/files/" + link;
    let record = {
      company: frm.doc.company_name,
      cert_type: cert_type,
      link: make_it_link,
      sequence: i,
    };
    cert_list_details.push(record);
  }
  if (!check_for_update) {
    frappe.call({
      method:
        "tag_workflow.tag_workflow.doctype.company.company.create_certificate_records",
      args: {
        company: frm.doc.company_name,
        cert_list: cert_list_details,
      },
    });
  }
}
function set_up_cert_field(frm) {
  if (
    frappe.boot.tag.tag_user_info.company_type == "Hiring" ||
    frappe.boot.tag.tag_user_info.company_type == "Exclusive Hiring" ||
    frm.doc.organization_type != "Staffing"
  ) {
    frm.set_df_property("accreditations", "hidden", 1);
    frm.set_df_property("certificate_and_endorsements", "hidden", 1);
  }
  localStorage.setItem("id_initiator", 0);
  let html = `
		<div id = "custom_attach_div"></div>
		<script>
			function clear_func(id){
				let clear = id.split("_")
				document.getElementById("after_attach_"+clear[1]).style.display = "none";
				document.getElementById("attach_"+clear[1]).style.display = "inline-block";
				document.getElementById("cancel_"+clear[1]).disabled = false
				document.getElementById("anchor_"+clear[1]).innerHTML = ""
				document.getElementById("cancel_"+clear[1]).style.pointerEvents = "auto";

			}
			function attach_file(id){
				let anchor_id = id.split("_")
				localStorage.setItem("file_name",0)
				localStorage.setItem("div_id","anchor_"+anchor_id[1])
				localStorage.setItem("check_flag_attach",1)
				let val =  new frappe.ui.FileUploader({"doctype":"Company","docname":cur_frm.doc.name,"custome_check_flag":"test","restrictions": {
					max_file_size:512000,
					allowed_file_types: ['.pdf', '.png', '.jpeg','.jpg']
				}});
				setTimeout(()=>{
					document.getElementsByClassName("btn-modal-primary")[0].onclick = function() {set_file(anchor_id[1])};
					console.log("working")
				},300)
			}
				
			function set_file(id){
				let file = localStorage.getItem("file_name")
				if(file!="0"){
				document.getElementById("after_attach_"+id).style.display = "flex";
				document.getElementById("attach_"+id).style.display = "none";	
				
				document.getElementById("anchor_"+id).innerHTML = file
				document.getElementById("anchor_"+id).href = "/private/files/"+file;
				localStorage.setItem("file_name",0)
				document.getElementById("cancel_"+id).disabled = true
				document.getElementById("cancel_"+id).style.pointerEvents = "none";
				}
			}
			function eliminate_div(id){
				let action_id = id.split("_")
				let id_starter = Number(action_id[1])
				let val = document.getElementById("span_"+action_id[1]).innerHTML
				val = val.trim()
				let cert_list_exist = JSON.parse(localStorage.getItem('cert_list_exist'))
				for(let i=0 ; i<cert_list_exist.length;i++){
					let check_val = cert_list_exist[i].split("-")
					if(val == check_val[0]){
						cert_list_exist.splice(i, 1);
					}
				}
				localStorage.setItem("cert_list_exist",JSON.stringify(cert_list_exist))
				let id_initiator = Number(localStorage.getItem("id_initiator"))
				let element = document.getElementById("eliminate_"+id_starter);
				element.parentNode.removeChild(element);
				for(let i = id_starter+1 ; i<=id_initiator;i++){
					let set_id = i-1
					document.getElementById("eliminate_"+i).id = "eliminate_"+set_id
					document.getElementById("cancel_"+i).id = "cancel_"+set_id
					document.getElementById("span_"+i).id = "span_"+set_id
					document.getElementById("after_attach_"+i).id = "after_attach_"+set_id
					document.getElementById("anchor_"+i).id = "anchor_"+set_id
					document.getElementById("clear_"+i).id = "clear_"+set_id
					document.getElementById("attach_"+i).id = "attach_"+set_id
				}
				localStorage.setItem("id_initiator",id_initiator-1)
				
			}
			</script>`;
  frm.set_df_property("input", "options", [html]);
  frappe.call({
    method:
      "tag_workflow.tag_workflow.doctype.company.company.get_previous_certificate",
    args: { company: frm.doc.company_name },
    callback: function (r) {
      for (let record of r.message) {
        if (localStorage.getItem("cert_list_exist") == 0) {
          localStorage.setItem(
            "cert_list_exist",
            JSON.stringify([cert_dict[record[1]]])
          );
        } else {
          let updated_list = JSON.parse(
            localStorage.getItem("cert_list_exist")
          );
          updated_list.push(cert_dict[record[1]]);
          localStorage.setItem("cert_list_exist", JSON.stringify(updated_list));
        }
        let id_initiator = Number(localStorage.getItem("id_initiator")) + 1;
        let file_name = record[2].split("/");
        localStorage.setItem("id_initiator", id_initiator);
        let updated_html = `
					<div class="row input_field_in_custom_div" id="eliminate_${id_initiator}">
						<div class="col-xl-3 pr-0">
							<div> 
								<button type="button" id="cancel_${id_initiator}" class="px-2 btn btn-sm certificate-btn" onclick="eliminate_div(this.id)">
									<span id = "span_${id_initiator}"> ${record[1]} </span>
									<svg class="icon  icon-sm ml-1" style="">
										<use class="" href="#icon-delete"></use>
									</svg>
								</button> 
							</div>
						</div>
						<div class="col-xl-9 pl-lg-1 pl-3 mt-3 mt-lg-0 ">
							<div class="control-input-wrapper">						
								<div class="control-input">
									<div class="attached-file p-1 flex justify-between align-center" id ="after_attach_${id_initiator}"  style="display: flex;">
										<div class="ellipsis">
											<i class="fa fa-paperclip"></i>
											<a class="attached-file-link" target="_blank" id="anchor_${id_initiator}" href="${record[2]}" value = "1">${file_name[2]}</a>
										</div>
										<div>
											<a class="btn btn-xs btn-default"  data-action="clear_attachment" id= "clear_${id_initiator}" onclick=clear_func(this.id)>Clear</a>
										</div>
									</div>
									<button class="btn btn-default btn-sm btn-attach" id="attach_${id_initiator}" data-fieldtype="Attach" data-fieldname="" onclick=attach_file(this.id) placeholder="" data-doctype="Company" style="display: none;">
										Attach
									</button>
									</div>					
									<div class="control-value like-disabled-input" style="display: none;"></div>							
							</div>
						</div>
					</div>
				`;

        document.getElementById("custom_attach_div").innerHTML =
          document.getElementById("custom_attach_div").innerHTML + updated_html;
        document.getElementById("cancel_" + id_initiator).disabled = true;
        document.getElementById("cancel_" + id_initiator).style.pointerEvents =
          "none";
      }
    },
  });
}

function invoice_view(frm) {
  let html = "";
  if (frm.doc.default_invoice_view == "Summary View") {
    html += `
		<div id="content">
			<div class="button-strip">
				<div class="strip-button active-strip-button" data-description="Summary View" onclick="myFunction(this.id)" id="summary_view"><span class="strip-button-text">Summary View</span></div>
				<div class="strip-button" data-description="Detailed View" onclick="myFunction(this.id)" id="detailed_view"><span class="strip-button-text">Detailed View</span></div>
			</div>
		</div>`;
  } else {
    html += `
		<div id="content">
			<div class="button-strip">
				<div class="strip-button" data-description="Summary View" onclick="myFunction(this.id)" id="summary_view"><span class="strip-button-text">Summary View</span></div>
				<div class="strip-button active-strip-button" data-description="Detailed View" onclick="myFunction(this.id)" id="detailed_view"><span class="strip-button-text">Detailed View</span></div>
			</div>
		</div>`;
  }
  html += `
	<style>
		.button-strip {
			width: 202px;
			height: 29px;
			border: 1px solid #21b9e4;
			border-radius: 3px;
			display: flex;
			box-shadow: var(--btn-shadow);
		}
		.strip-button {
			background-color: white;
			color: #21b9e4;
			width: 101px;
			height: 27px;
			text-align: center;
			vertical-align: middle;
			line-height: 26px;
			transition: background-color .4s linear, color .2s linear;
			cursor: pointer;
		}
		.strip-button span {
			color: inherit;
		}
		.strip-button-text {
			font-size: var(--text-md);
			color: #21b9e4;
			margin: 0px;
			padding: 0px;
		}
		.active-strip-button {
			background-color: #21b9e4;
			color: white;
		}
	</style>`;
  frm.set_df_property("invoice_view_html", "options", html);
}

window.myFunction = (id) => {
  let button = document.getElementById(id);
  let description = button.getAttribute("data-description");
  $("#summary_view").removeClass("active-strip-button");
  $("#detailed_view").removeClass("active-strip-button");
  $("#" + id).addClass("active-strip-button");
  cur_frm.set_value("default_invoice_view", description);
};
function redirect_job_site() {
  $('[data-fieldname="job_site"]').on("click", (e) => {
    let job_site_name = e.target.title ? e.target.title : e.target.innerText;
    if (job_site_name && job_site_name != "Job Site") {
      let data_link = $(`[data-name="${job_site_name.trim()}"]`).attr("href");
      window.location.href = data_link;
    }
  });
}

/*-------------------company profile button-----------------*/

function public_profile_redirect(frm) {
  if (frm.doc.__islocal != 1) {
    frm
      .add_custom_button(__("View Company Profile"), function () {
        localStorage.setItem("company", frm.doc.name);
        window.location = "/app/dynamic_page";
      })
      .addClass("btn-primary");
  }
}

function connect_integration(frm, enable_field_name, fields) {
  frm.set_value(enable_field_name, 1);
  password_fields(frm, fields, false);
}

function disconnect_integration(frm, enable_field_name, fields, type_name) {
  let profile_html = `<span style="font-size:14px">Do you really want to disconnect ${enable_field_name[1]} integration? It will remove all the data related to this integration.</span>`;
  let pop_up = new frappe.ui.Dialog({
    title: __("Disconnect"),
    fields: [
      { fieldname: "save_joborder", fieldtype: "HTML", options: profile_html },
    ],
  });
  pop_up.show();
  pop_up.$wrapper
    .find(".standard-actions>.btn-modal-primary")
    .css({ background: "#DC3545!important;" });
  pop_up.set_primary_action(__("Disconnect"), function () {
    pop_up.hide();
    frm.set_value(enable_field_name[0], 0);
    add_btn_primary(type_name);
    password_fields(frm, fields, true);
  });
  pop_up.set_secondary_action_label(__("Cancel"));
  pop_up.set_secondary_action(() => {
    pop_up.hide();
  });
}

/*------------------------------------*/

function update_invoice_view(frm) {
  let view = frappe.get_cookie("invoice_view").split("|");
  if (view.length == 1) {
    document.cookie =
      "invoice_view=" +
      frm.doc.name +
      "*" +
      frm.doc.default_invoice_view +
      ";path=/";
  } else if (view.length > 1) {
    let new_view = [];
    for (let i in view) {
      if (view[i].split("*")[0] == frm.doc.name) {
        new_view.push(frm.doc.name + "*" + frm.doc.default_invoice_view);
      } else {
        new_view.push(view[i]);
      }
    }
    document.cookie = "invoice_view =" + new_view.join("|") + ";path=/";
  }
}

function validate_office_code(frm) {
  let office_code = frm.doc.office_code;
  if (office_code) {
    if (office_code.length != 5) {
      frappe.msgprint(
        "Minimum and Maximum Characters allowed for Office Code are 5."
      );
      frappe.validated = false;
    }
    let regEx = /^[0-9a-zA-Z]+$/;
    if (!office_code.match(regEx)) {
      frappe.msgprint("Only alphabets and numbers are allowed in Office Code.");
      frappe.validated = false;
    }
  }
}
frappe.ui.form.on("Job Titles", {
  job_titles_add: () => {
    $('[data-fieldname="industry_type"]').on("click", () => {
      $('input[data-fieldname="industry_type"]').removeAttr("disabled");
    });
  },
});
let Company = "Company";
async function check_enable_active(frm) {
  if (frm.doc.enable_jazz_hr == 1 && frm.doc.jazzhr_api_key_data.length > 0) {
    frm.doc.active_jazz = 1;
  } else {
    frm.doc.active_jazz = 0;
  }
}

async function check_enable_active_quick(frm) {
  if (
    frm.doc.enable_quickbook == 1 &&
    ((frm.doc.enable && frm.doc.enable.length > 0) ||
      (frm.doc.client_id_data && frm.doc.client_id_data.length > 0) ||
      (frm.doc.client_secret_data && frm.doc.client_secret_data.length > 0) ||
      (frm.doc.quickbooks_company_id &&
        frm.doc.quickbooks_company_id.length > 0))
  ) {
    console.log("QUICK IF");
    frm.doc.active_quick_book = 1;
  } else {
    console.log("QUICK ELSE");
    frm.doc.active_quick_book = 0;
  }
}

async function check_enable_active_work(frm) {
  if (
    frm.doc.enable_workbright == 1 &&
    ((frm.doc.workbright_subdomain_data &&
      frm.doc.workbright_subdomain_data.length > 0) ||
      (frm.doc.workbright_api_key_data &&
        frm.doc.workbright_api_key_data.length > 0))
  ) {
    console.log("WORK IF");
    frm.doc.active_work_bright = 1;
  } else {
    console.log("WORK ELSE");
    frm.doc.active_work_bright = 0;
  }
}

async function check_enable_active_staff(frm) {
  if (
    frm.doc.staff_complete_enable == 1 &&
    frm.doc.office_code &&
    frm.doc.office_code.length > 0
  ) {
    console.log("STAFF IF");
    frm.doc.active_office_code = 1;
  } else {
    console.log("STAFF ELSE");
    frm.doc.active_office_code = 0;
  }
}

function check_enable_active_branch(frm) {
  //For Branch Integration
  if (
    frm.doc.branch_enabled == 1 &&
    ((frm.doc.branch_org_id_data && frm.doc.branch_org_id_data.length > 0) ||
      (frm.doc.branch_api_key_data && frm.doc.branch_api_key_data.length > 0))
  ) {
    console.log("BRANCH IF");
    frm.doc.active_branch = 1;
  } else {
    console.log("BRANCH ELSE");
    frm.doc.active_branch = 0;
  }
}

let parent = document.getElementById("company-integration_details").children;
let beforeend = "beforeend";
let active_pill_jazz = `<div class=active_pill_jazz><span class="indicator-pill whitespace-nowrap green"><span>Active</span></span></div>`;
let active_pill_quick = `<div class=active_pill_quick><span class="indicator-pill whitespace-nowrap green"><span>Active</span></span></div>`;
let active_pill_staff = `<div class=active_pill_staff><span class="indicator-pill whitespace-nowrap green"><span>Active</span></span></div>`;
let active_pill_work = `<div class=active_pill_work><span class="indicator-pill whitespace-nowrap green"><span>Active</span></span></div>`;
let enable_pill_jazz = `<div class=enable_pill_jazz><span class="indicator-pill whitespace-nowrap blue"><span>Enabled</span></span></div>`;
let enable_pill_quick = `<div class=enable_pill_quick><span class="indicator-pill whitespace-nowrap blue"><span>Enabled</span></span></div>`;
let enable_pill_staff = `<div class=enable_pill_staff><span class="indicator-pill whitespace-nowrap blue"><span>Enabled</span></span></div>`;
let enable_pill_work = `<div class=enable_pill_work><span class="indicator-pill whitespace-nowrap blue"><span>Enabled</span></span></div>`;
let blue = "blue";
let green = "green";
let activeText = "Active";
let enabledText = "Enabled";
let display_style = "flex";

function add_lable(frm) {
  jazz_pin_show(frm);
  quick_pin_show(frm);
  work_pin_show(frm);
  staff_pin_show(frm);
}

function branch_pin_show(frm) {
  //For Branch Integration
  let branchFirstChild = parent[1].children;
  branchFirstChild[0].style.display = display_style;
  let branchChildren = parent[1].children[0].children[1];

  if (
    frm.doc.branch_enabled == 1 &&
    ((frm.doc.branch_org_id_data && frm.doc.branch_org_id_data.length > 0) ||
      (frm.doc.branch_api_key_data && frm.doc.branch_api_key_data.length > 0))
  ) {
    branch_make_active(branchChildren, branchFirstChild);
  } else if (frm.doc.branch_enabled == 1 && frm.doc.active_branch == 0) {
    branch_make_enable(branchChildren, branchFirstChild);
  } else if (branchChildren) {
    branchChildren.remove();
  }
}

function branch_make_active(branchChildren, branchFirstChild) {
  if (branchChildren == undefined) {
    branchFirstChild[0].insertAdjacentHTML(beforeend, active_pill_branch);
  } else if (
    branchChildren.children[0].classList[2] &&
    [blue].includes(branchChildren.children[0].classList[2])
  ) {
    toogle_blue_to_green_pill(branchChildren);
  }
}

function branch_make_enable(branchChildren, branchFirstChild) {
  if (parent[1].children[0].children.length > 1) {
    branchChildren.remove();
  }

  if (branchChildren == undefined || branchChildren.children.length != 0) {
    branchFirstChild[0].insertAdjacentHTML(beforeend, enable_pill_branch);
  } else if (
    branchChildren.children[0].classList[2] &&
    [green].includes(branchChildren.children[0].classList[2])
  ) {
    toogle_green_to_blue_pill(branchChildren);
  }
}

function toogle_green_to_blue_pill(branchChildren) {
  let s = branchChildren.children[0];

  s.classList.remove(green);
  s.classList.add(blue);
  s.innerHTML = enabledText;
}

function staff_pin_show(frm) {
  let staffingFirstChild = parent[7].children;
  staffingFirstChild[0].style.display = display_style;
  let staffingChildren = parent[7].children[0].children[1];
  if (
    frm.doc.staff_complete_enable == 1 &&
    frm.doc.office_code &&
    frm.doc.office_code.length > 0
  ) {
    staff_make_active(staffingChildren, staffingFirstChild);
  } else if (
    frm.doc.staff_complete_enable == 1 &&
    frm.doc.active_office_code == 0
  ) {
    staff_make_enable(staffingChildren, staffingFirstChild);
  } else if (staffingChildren) {
    staffingChildren.remove();
  }
}

function staff_make_active(staffingChildren, staffingFirstChild) {
  if (staffingChildren == undefined) {
    staffingFirstChild[0].insertAdjacentHTML(beforeend, active_pill_staff);
  } else if (
    staffingChildren.children[0].classList[2] &&
    [blue].includes(staffingChildren.children[0].classList[2])
  ) {
    toogle_blue_to_green_pill(staffingChildren);
  }
}

function staff_make_enable(staffingChildren, staffingFirstChild) {
  if (parent[7].children[0].children.length > 1) {
    staffingChildren.remove();
  }

  if (staffingChildren == undefined || staffingChildren.children.length != 0) {
    staffingFirstChild[0].insertAdjacentHTML(beforeend, enable_pill_staff);
  } else if (
    staffingChildren.children[0].classList[2] &&
    [green].includes(staffingChildren.children[0].classList[2])
  ) {
    toogle_green_to_blue_pill(staffingChildren);
  }
}

function toogle_blue_to_green_pill(staffingChildren) {
  let p = staffingChildren.children[0];

  p.classList.remove(blue);
  p.classList.add(green);
  p.innerHTML = activeText;
}

function work_pin_show(frm) {
  let workbrightFirstChild = parent[8].children;
  workbrightFirstChild[0].style.display = display_style;
  let workbrightChildren = parent[8].children[0].children[1];
  if (
    frm.doc.enable_workbright == 1 &&
    ((frm.doc.workbright_subdomain_data &&
      frm.doc.workbright_subdomain_data.length > 0) ||
      (frm.doc.workbright_api_key_data &&
        frm.doc.workbright_api_key_data.length > 0))
  ) {
    work_make_active(workbrightChildren, workbrightFirstChild);
  } else if (
    frm.doc.enable_workbright == 1 &&
    frm.doc.active_work_bright == 0
  ) {
    work_make_enable(workbrightChildren, workbrightFirstChild);
  } else if (workbrightChildren) {
    workbrightChildren.remove();
  }
}

function work_make_enable(workbrightChildren, workbrightFirstChild) {
  if (parent[8].children[0].children.length > 1) {
    workbrightChildren.remove();
  }

  if (
    workbrightChildren == undefined ||
    workbrightChildren.children.length != 0
  ) {
    workbrightFirstChild[0].insertAdjacentHTML(beforeend, enable_pill_work);
  } else if (
    workbrightChildren.children[0].classList[2] &&
    [green].includes(workbrightChildren.children[0].classList[2])
  ) {
    toogle_green_to_blue_pill(workbrightChildren);
  }
}

function work_make_active(workbrightChildren, workbrightFirstChild) {
  if (workbrightChildren == undefined) {
    workbrightFirstChild[0].insertAdjacentHTML(beforeend, active_pill_work);
  } else if (
    workbrightChildren.children[0].classList[2] &&
    [blue].includes(workbrightChildren.children[0].classList[2])
  ) {
    toogle_blue_to_green_pill(workbrightChildren);
  }
}

function quick_pin_show(frm) {
  let quickBookFirstChild = parent[4].children;
  quickBookFirstChild[0].style.display = display_style;
  let quickBookChildren = parent[4].children[0].children[1];
  if (
    frm.doc.enable_quickbook == 1 &&
    ((frm.doc.enable && frm.doc.enable.length > 0) ||
      (frm.doc.client_id_data && frm.doc.client_id_data.length > 0) ||
      (frm.doc.client_secret_data && frm.doc.client_secret_data.length > 0) ||
      (frm.doc.quickbooks_company_id &&
        frm.doc.quickbooks_company_id.length > 0))
  ) {
    quick_make_active(quickBookChildren, quickBookFirstChild);
  } else if (frm.doc.enable_quickbook == 1 && frm.doc.active_quick_book == 0) {
    quick_make_enable(quickBookChildren, quickBookFirstChild);
  } else if (quickBookChildren) {
    quickBookChildren.remove();
  }
}

function quick_make_enable(quickBookChildren, quickBookFirstChild) {
  if (parent[4].children[0].children.length > 1) {
    quickBookChildren.remove();
  }

  if (
    quickBookChildren == undefined ||
    quickBookChildren.children.length != 0
  ) {
    quickBookFirstChild[0].insertAdjacentHTML(beforeend, enable_pill_quick);
  } else if (
    quickBookChildren.children[0].classList[2] &&
    [green].includes(quickBookChildren.children[0].classList[2])
  ) {
    toogle_green_to_blue_pill(quickBookChildren);
  }
}

function quick_make_active(quickBookChildren, quickBookFirstChild) {
  if (quickBookChildren == undefined) {
    quickBookFirstChild[0].insertAdjacentHTML(beforeend, active_pill_quick);
  } else if (
    quickBookChildren.children[0].classList[2] &&
    [blue].includes(quickBookChildren.children[0].classList[2])
  ) {
    toogle_blue_to_green_pill(quickBookChildren);
  }
}

function jazz_pin_show(frm) {
  let jazzFirstChild = parent[2].children;
  jazzFirstChild[0].style.display = display_style;
  let jazzChildren = parent[2].children[0].children[1];

  if (
    frm.doc.enable_jazz_hr == 1 &&
    frm.doc.jazzhr_api_key_data &&
    frm.doc.jazzhr_api_key_data.length > 0
  ) {
    jazz_make_active(jazzChildren, jazzFirstChild);
  } else if (frm.doc.enable_jazz_hr == 1 && frm.doc.active_jazz == 0) {
    jazz_make_enable(jazzChildren, jazzFirstChild);
  } else if (jazzChildren) {
    jazzChildren.remove();
  }
}

function jazz_make_enable(jazzChildren, jazzFirstChild) {
  if (parent[2].children[0].children.length > 1) {
    jazzChildren.remove();
  }

  if (jazzChildren == undefined || jazzChildren.children.length != 0) {
    jazzFirstChild[0].insertAdjacentHTML(beforeend, enable_pill_jazz);
  } else if (
    jazzChildren.children[0].classList[2] &&
    [green].includes(jazzChildren.children[0].classList[2])
  ) {
    toogle_green_to_blue_pill(jazzChildren);
  }
}

function jazz_make_active(jazzChildren, jazzFirstChild) {
  if (jazzChildren == undefined) {
    jazzFirstChild[0].insertAdjacentHTML(beforeend, active_pill_jazz);
  } else if (
    jazzChildren.children[0].classList[2] &&
    [blue].includes(jazzChildren.children[0].classList[2])
  ) {
    toogle_blue_to_green_pill(jazzChildren);
  }
}

function remove_btn_primary(type_name) {
  $(`#add-btn-${type_name}`).text("Disconnect");
  $(`#add-btn-${type_name}`).removeClass("btn-primary");
}

function add_btn_primary(type_name) {
  $(`#add-btn-${type_name}`).text("Connect");
  $(`#add-btn-${type_name}`).addClass("btn-primary");
}

function activate_tab() {
  let val = localStorage.getItem("slide_tab");
  if (val == "0") {
    $(".nav-link").removeClass("active");
    $("#company-display_settings-tab").click();
    localStorage.setItem("slide_tab", "1");
  } else {
    $(".nav-link").removeClass("active");
    $("#company-info-tab").click();
    localStorage.setItem("slide_tab", "0");
  }
}
function reload_company_setting_page(event) {
  if (event.persisted) {
    window.location.reload();
  }
}
function update_primary_language(frm) {
  if (frm.doc.__islocal) {
    frm.set_value("primary_language", "English");
  }
}
function carousel_display(frm) {
  if (frm.doc.__islocal == 1 || frm.doc.organization_type == "TAG") {
    $("#pre-slide").css("display", "none");
    $("#next-slide").css("display", "none");
    $("#form-tabs1").css("cssText", "justify-content: flex-start !important;");
  } else {
    $("#pre-slide").css("display", "block");
    $("#next-slide").css("display", "block");
    $(".carousel").carousel({
      interval: false,
    });
    document
      .getElementById("pre-slide")
      .addEventListener("click", activate_tab);
    document
      .getElementById("next-slide")
      .addEventListener("click", activate_tab);
  }
}

function create_tag_job_title(frm) {
  if (frm.doc.job_titles.length > 0) {
    frappe.call({
      method:
        "tag_workflow.tag_workflow.doctype.company.company.create_tag_job_title",
      args: {
        company: frm.doc.name,
      },
    });
  }
}

frappe.ui.form.on("Invoice Premium", {
  invoice_premium_table_add: (frm, cdt, cdn)=>{
    let row = locals[cdt][cdn];
    get_company_dropdown(frm, row.name, row.staffing_company);
  },
  before_invoice_premium_table_remove: (_frm,cdt,cdn)=>{
    let child=frappe.get_doc(cdt,cdn);
    if(child.staffing_company=="Default") {
      frappe.throw("You can't delete this row.");
    }
  },
  form_render: ()=>{
    $(".row-actions, .grid-footer-toolbar").hide();
  },
  staffing_company: (_frm, cdt, cdn)=>{
    let row = locals[cdt][cdn];
    if(row.idx==1){
      frappe.msgprint("You cannot change Default.");
      row.staffing_company = "Default";
    }
  }
});

async function get_company_dropdown(frm, row_name, title){
  let staff_comp = frm.doc.invoice_premium_table;
  let staff_comp_list = [];
  for (let x in staff_comp) {
    if (staff_comp[x]["staffing_company"]) {
      staff_comp_list.push(staff_comp[x]["staffing_company"]);
    }
  }
  staff_comp_list=staff_comp_list.filter(item => item !== title);
  frappe.call({
    "method": "tag_workflow.tag_workflow.doctype.company.company.staffing_comp_premium",
    "args": {
      staff_comp_list: staff_comp_list,
    },
    "async": 0,
    "callback": (res)=>{
      frappe.utils.filter_dict(frm.fields_dict.invoice_premium_table.grid.grid_rows_by_docname[row_name].docfields,{"fieldname": "staffing_company"})[0].options=res.message;
      frm.refresh_field("invoice_premium_table");
    }
  });
}
