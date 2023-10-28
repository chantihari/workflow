// Copyright (c) 2021, SourceFuse and contributors
// For license information, please see license.txt
frappe.require("/assets/tag_workflow/js/twilio_utils.js");
window.multiple_comp = [];
let global_headcount_reduced_by_hiring = {}
let global_headcount_reduce_without_approved_by_hiring = {}
frappe.ui.form.on("Job Order", {
  assign_employees: function(frm) {
    if (frm.doc.to_date < frappe.datetime.now_datetime()) {
      frappe.msgprint({
        message: __("Date has been past to claim this order"),
        title: __("Job Order filled"),
        indicator: "blue",
      });
    } else if (
      frm.doc.__islocal != 1 &&
      frm.doc.owner != frappe.session.user &&
      frm.doc.total_workers_filled < frm.doc.total_no_of_workers
    ) {
      if (frm.is_dirty()) {
        frappe.msgprint({
          message: __("Please save the form before creating Quotation"),
          title: __("Save Job Order"),
          indicator: "red",
        });
      } else {
        assign_employe(frm);
      }
    } else if (frm.doc.total_workers_filled >= frm.doc.total_no_of_workers) {
      frappe.msgprint({
        message: __("No of workers already filled for this job order"),
        title: __("Worker Filled"),
        indicator: "red",
      });
    }
  },

  onload: function(frm) {
    frm.set_df_property("no_of_workers", "label", "No. of workers");
    localStorage.setItem("employee_removed_"+frm.doc.name,JSON.stringify([]))
    localStorage.setItem("test_employee_removed_"+frm.doc.name,JSON.stringify({}))

    if (
      frappe.boot.tag.tag_user_info.company_type == "Staffing" &&
      frm.doc.__islocal == 1
    ) {
      frm.set_value("e_signature_full_name", frappe.session.user_fullname);
      frm.set_df_property("e_signature_full_name", "read_only", 0);
    }

    make_invoice(frm);
    hide_employee_rating(frm);
    direct_order_staff_company(frm);

    if (frappe.session.user != "Administrator") {
      $(".menu-btn-group").hide();
    }

    if (frm.doc.__islocal != 1) {
      setTimeout(() => {
        $('*[data-fieldname="multiple_job_titles"]')
          .find(".grid-heading-row .col:last-child")
          .unbind("click");
      }, 500);

      if (frm.doc.__islocal != 1) {
        change_is_single_share(frm);
      }
    }

    if (frm.doc.__islocal == 1) {
      if (
        ["Hiring", "Exclusive Hiring"].includes(frappe.boot.tag.tag_user_info.company_type)
      ) {
        frm.set_value("company", frappe.boot.tag.tag_user_info.company);
      }
      frm.set_value("from_date", "");
      frm.set_df_property("time_remaining_for_make_edits", "options", " ");
    }
    if (frappe.boot.tag.tag_user_info.company_type != "Staffing") {
      fields_setup(frm);
    }
    set_multiple_title_filters(frm);
  },

  setup: function(frm) {
    if (frm.order_status != "Completed") {
      $(
        "div.row:nth-child(6) > div:nth-child(2) > div:nth-child(2) > form:nth-child(1) > div:nth-child(3) > div:nth-child(1) > div:nth-child(2) > div:nth-child(1)"
      ).attr("id", "div_rate");
      $(
        "div.row:nth-child(9) > div:nth-child(2) > div:nth-child(2) > form:nth-child(1) > div:nth-child(3) > div:nth-child(1) > div:nth-child(2) > div:nth-child(1)"
      ).attr("id", "div_extra");
    }

    frm.set_query("job_site", function(doc) {
      return {
        query: "tag_workflow.tag_data.get_org_site",
        filters: {
          job_order_company: doc.company,
        },
      };
    });

    frm.set_query("company", function() {
      return {
        filters: [
          [
            "Company",
            "organization_type",
            "in",
            ["Hiring", "Exclusive Hiring"],
          ],
          ["Company", "make_organization_inactive", "=", 0],
        ],
      };
    });

    frm.set_query("select_job", function(doc) {
      return {
        query:
          "tag_workflow.tag_workflow.doctype.job_order.job_order.get_jobtitle_list",
        filters: {
          job_order_company: doc.company,
          job_site: doc.job_site,
        },
      };
    });

    if (frm.doc.__islocal == 1) {
      fields_setup(frm);
    }

    frm.set_query("select_days", function() {
      return {
        query:
          "tag_workflow.tag_workflow.doctype.job_order.job_order.selected_days",
      };
    });
    set_multiple_title_filters(frm);
  },
  e_signature_full_name: function(frm) {
    if (frm.doc.e_signature_full_name) {
      let regex = /[^0-9A-Za-z ]/g;
      if (regex.test(frm.doc.e_signature_full_name) === true) {
        frappe.msgprint(
          __("E-Signature Full Name: Only alphabets and numbers are allowed.")
        );
        frm.set_value("e_signature_full_name", "");
        frappe.validated = false;
      }
    }
  },
  select_days: function(frm) {
    if (frm.doc.select_days) {
      $("span.btn-link-to-form").click(false);
      $("button.data-pill.btn.tb-selected-value").on("mouseover", function(e) {
        let file = e.target.innerText;
        $(this).attr("title", file);
      });
      $(".control-input.form-control.table-multiselect").on(
        "mouseover",
        function() {
          $(this).attr("title", "");
        }
      );
      set_custom_days(frm);
    }
  },
  refresh: function(frm) {
    date_pick(frm);
    setTimeout(() => add_id(frm), 500);
    if (frm.doctype === "Job Order") {
      update_order_status(frm);
    }
    availability_single_day(frm);
    $('[class="btn btn-primary btn-sm primary-action"]').show();
    $(".custom-actions.hidden-xs.hidden-md").css("display", "flex");
    staffing_company_remove(frm);
    staff_company_asterisks(frm);
    repeat_order(frm);
    set_multiple_title_filters(frm);
    order_buttons(frm);
    setTimeout(function() {
      view_button(frm);
      make_invoice(frm);
      cancel_or_delete_jo(frm);
    }, 10);

    if (
      frm.doc.__islocal != 1 &&
      frappe.boot.tag.tag_user_info.company_type == "Hiring" &&
      frm.doc.order_status == "Upcoming"
    ) {
      hide_unnecessary_data(frm);
    }
    update_section(frm);
    deny_job_order(frm);
    if(frm.doc.order_status=='Canceled'){
      frm.set_read_only(true);
      if(["Hiring", "Exclusive Hiring"].includes(frappe.boot.tag.tag_user_info.company_type)){
        frm.toggle_display("hiring_section_break", 1);
        frm.set_df_property(
          "hiring_html",
          "options",
          "<h3>Job Order Canceled.</h3>"
        );
      }
    }else{
      hiring_sections(frm);
    }

    $(document).on("click", '[data-fieldname="select_days"]', function() {
      advance_hide(3000);
    });
    $('[data-fieldname="select_days"]').mouseover(function() {
      advance_hide(500);
    });
    document.addEventListener("keydown", function() {
      advance_hide(500);
    });

    $('[data-fieldname="company"]').click(function() {
      return false;
    });
    $('[data-fieldname="company"]').click(function() {
      if (frm.doc.company && frm.doctype == "Job Order") {
        if (frm.doc.__islocal !== 1) {
          localStorage.setItem("company", frm.doc.company);
          window.location.href = "/app/dynamic_page";
        }
      }
    });

    if (frm.doc.__islocal != 1) {
      $('[data-fieldname="job_start_time"]').on("click", ()=>{
        $('.datepicker').hide();
      })
      localStorage.setItem("order", frm.doc.name);
      $('*[data-fieldname="multiple_job_titles"]')
        .find(".grid-buttons")
        .hide();

      frm.fields_dict["multiple_job_titles"].grid.wrapper
        .find(".btn-open-row")
        .click(function() {
          $(".row-actions").hide();
          $(".grid-footer-toolbar").hide();
        });

      $(".row-check").click(function() {
        $(".grid-footer-toolbar").hide();
      });
    } else {
      frm.set_df_property("time_remaining_for_make_edits", "hidden", 1);
      $('*[data-fieldname="multiple_job_titles"]')
        .find(".grid-buttons")
        .show();

      frm.fields_dict["multiple_job_titles"].grid.wrapper
        .find(".btn-open-row")
        .click(function() {
          $(".row-actions").show();
          $(".grid-footer-toolbar").show();
        });

      setTimeout(() => {
        $('*[data-fieldname="multiple_job_titles"]')
          .find(".grid-heading-row .col:last-child")
          .unbind("click");
      }, 500);
    }
    $('[data-fieldname = "phone_number"]>div>div>div>input').attr(
      "placeholder",
      "Example: +XX XXX-XXX-XXXX"
    );
    set_exc_industry_company(frm);
    order_claimed(frm);
    single_share_job(frm);
    $('.frappe-control[data-fieldname="html_3"]').attr(
      "id",
      "claim-order-submission"
    );
    $('.frappe-control[data-fieldname="resumes_required"]').attr(
      "id",
      "resume-required"
    );
    $("#awesomplete_list_4").attr("id", "jobsite-dropdown");
    prevent_click_event(frm);
    claim_job_order_staffing(frm);
  },

  select_job: function(frm) {
    if (frm.doc.select_job) {
      frappe.call({
        method:
          "tag_workflow.tag_workflow.doctype.job_order.job_order.update_joborder_rate_desc",
        args: {
          job_site: frm.doc.job_site,
          job_title: frm.doc.select_job,
        },
        callback: function(r) {
          if (r.message) {
            frm.set_df_property("category", "read_only", 1);
            frm.set_df_property("worker_comp_code", "read_only", 1);
            frm.set_value("rate", r.message[0].bill_rate);
            frm.set_value("category", r.message[0].industry_type);
            frm.set_value("worker_comp_code", r.message[0].comp_code);
            refresh_field("rate");
            refresh_field("category");
            refresh_field("worker_comp_code");
          }
        },
      });
    }
  },

  before_save: function(frm) {
    let total_workers = 0;
    let total_categories = [];
    let category_val_popup;
    ({ category_val_popup, total_workers } = category_values(
      total_workers,
      total_categories,
      frm
    ));
    console.log(total_workers);
    if (frm.doc.__islocal === 1) {
      no_of_worker_repeat(frm);
      if (frm.doc.availability == "Custom") {
        set_custom_days(frm);
      }
      set_custom_base_price(frm);
      rate_hour_contract_change(frm);
      if (frappe.validated) {
        frm.set_df_property("select_days", "reqd", 0);
        return new Promise(function(resolve, reject) {
          let profile_html;
          if (frm.doc.contact_number) {
            profile_html =
              "<span style='font-size: 14px;'>" +
              "<b>Industry: </b>" +
              category_val_popup +
              "<br><b>Start Date: </b>" +
              frm.doc.from_date +
              "<br><b>End Date: </b>" +
              frm.doc.to_date +
              "<br><b>Job Duration: </b>" +
              frm.doc.job_order_duration +
              "<br><b>Job Site: </b>" +
              frm.doc.job_site +
              "<br><b>Job Site Contact: </b>" +
              frm.doc.contact_name +
              "<br><b>Contact Phone Number: </b>" +
              frm.doc.contact_number +
              "<br><b>Total no. of Workers: </b>" +
              frm.doc.total_no_of_workers +
              "</span>";
          } else {
            profile_html =
              "<span style='font-size: 14px;'>" +
              "<b>Industry: </b>" +
              category_val_popup +
              "<br><b>Start Date: </b>" +
              frm.doc.from_date +
              "<br><b>End Date: </b>" +
              frm.doc.to_date +
              "<br><b>Job Duration: </b>" +
              frm.doc.job_order_duration +
              "<br><b>Job Site: </b>" +
              frm.doc.job_site +
              "<br><b>Job Site Contact: </b>" +
              frm.doc.contact_name +
              "<br><b>Total no. of Workers: </b>" +
              frm.doc.total_no_of_workers +
              "</span>";
          }
          let confirm_joborder = new frappe.ui.Dialog({
            title: __("Confirm Job Order Details"),
            fields: [
              {
                fieldname: "save_joborder",
                fieldtype: "HTML",
                options: profile_html,
              },
            ],
          });
          confirm_joborder.no_cancel();
          confirm_joborder.set_primary_action(__("Confirm"), function() {
            confirm_joborder.hide();
            frappe.call({
              method:
                "tag_workflow.tag_workflow.doctype.job_order.job_order.check_order_already_exist",
              args: {
                frm: frm.doc,
              },
              async: 1,
              callback: function(r) {
                check_exist_order(r, frm, resolve, reject);
              },
            });
          });
          confirm_joborder.set_secondary_action_label(__("Cancel"));
          confirm_joborder.set_secondary_action(() => {
            const cancelReason = "Cancelled by user";
            reject(cancelReason);
            confirm_joborder.hide();
          });
          confirm_joborder.show();
          confirm_joborder.$wrapper.find(".modal-dialog").css("width", "450px");
          confirm_joborder.standard_actions
            .find(".btn-modal-primary")
            .attr("id", "joborder-confirm-button");
          confirm_joborder.standard_actions
            .find(".btn-modal-secondary")
            .attr("id", "joborder-cancel-button");
          confirm_joborder.$wrapper.on("hidden.bs.modal", function() {
            $('[data-label="Save"]').removeAttr("disabled");
          });
        });
      }
    } else {
      if (frappe.validated) {
        frm.set_df_property("select_days", "reqd", 0);
      }
      check_increase_headcount(frm);
      setTimeout(function() {
        frappe.dom.unfreeze();
      }, 4000);
    }
    if (frm.doc.__islocal != 1) {
      change_is_single_share(frm);

      let message = "";
      let jobstarttime = {};
      message = start_time_duplicate_validation(jobstarttime, message);
      console.log(message);
      setTimeout(function() {
        frappe.dom.unfreeze();
      }, 4000); 
    }
  },

  after_save: function(frm) {
    if (frappe.boot.tag.tag_user_info.company_type == "Staffing") {
      localStorage.setItem("exclusive_case", 1);
      if (frm.doc.resumes_required == 0) {
        frappe.call({
          method: "tag_workflow.tag_data.claim_order_insert",
          freeze: true,
          freeze_message: "Please wait while order is claiming",
          args: {
            job_order: frm.doc,
          },
          callback: function(r) {
            if (r.message == 1) {
              frappe.msgprint("Job Order has been claimed");
              setTimeout(function() {
                location.reload();
              }, 5000);
            } else {
              frappe.msgprint("Automatic claim is not successful");
              setTimeout(function() {
                location.reload();
              }, 5000);
            }
          },
        });
      }
    }

    if (frm.doc.staff_org_claimed) {
      notification_joborder_change(frm);
    } else {
      frappe.call({
        method: "tag_workflow.tag_data.staff_email_notification",
        args: {
          hiring_org: frm.doc.company,
          job_order: frm.doc.name,
          job_order_title: frm.doc.select_job,
          staff_company: frm.doc.staff_company,
          multiple_comp: window.multiple_comp,
        },
        callback: function(r) {
          if (r.message == 1) {
            frappe.msgprint("Email Sent Successfully");
          }
        },
      });
    }
    no_of_workers_changed(frm);
    reomve_emploees_after_save_from_hiring(frm)
    modify_headcount_after_save_from_hiring(frm)
  },

  view_contract: function(frm) {
    let contracts =
      "<div class='contract_div'><h3>Staffing/Vendor Contract</h3>This Staffing/Vendor Contract (“Contract”) is entered into by and between Staffing Company and Hiring Company as further described and as set forth below. By agreeing to the Temporary Assistance Guru, Inc. (“TAG”) End-User License Agreement, and using the TAG application service and website (the “Service”) Staffing Company and Hiring Company agree that they have a contractual relationship with each other and that the following terms apply to such relationship: <br> <ol> <li> The billing rate Hiring Company shall pay Staffing Company to hire each temporary worker provided by Staffing Company (the “Worker”) is the rate set forth by the TAG Service for the location and position sought to be filled, and this rate includes all wages, worker’s compensation premiums, unemployment insurance, payroll taxes, and all other employer burdens recruiting, administration, payroll funding, and liability insurance.</li><li> Hiring Company agrees not to directly hire and employ the Worker until the Worker has completed at least 720 work hours. Hiring Company agrees to pay Staffing Company an administrative placement fee of $3,000.00 if Hiring Company directly employs the Worker prior to completion of 720 work hours.</li> <li> Hiring Company acknowledges that it has complete care, custody, and control of workplaces and job sites. Hiring Company agrees to comply with all applicable laws, regulations, and ordinances relating to health and safety, and agrees to provide any site/task specific training and/or safety devices and protective equipment necessary or required by law. Hiring Company will not, without prior written consent of Staffing Company, entrust Staffing Company employees with the handling of cash, checks, credit cards, jewelry, equipment, tools, or other valuables.</li> <li> Hiring Company agrees that it will maintain a written safety program, a hazard communication program, and an accident investigation program. Hiring Company agrees that it will make first aid kits available to Workers, that proper lifting techniques are to be used, that fall protection is to be used, and that Hiring Company completes regular inspections on electrical cords and equipment. Hiring Company represents, warrants, and covenants that it handles and stores hazardous materials properly and in compliance with all applicable laws. </li> <li> Hiring Company agrees to post Occupational Safety and Health Act (“OSHA”) of 1970 information and other safety information, as required by law. Hiring Company agrees to log all accidents in its OSHA 300 logs. Hiring Company agrees to indemnify and hold harmless Staffing Company for all claims, damages, or penalties arising out of violations of the OSHA or any state law with respect to workplaces or equipment owned, leased, or supervised by Hiring Company and to which employees are assigned. </li> <li>  Hiring Company will not, without prior written consent of Staffing Company, utilize Workers to operate machinery, equipment, or vehicles. Hiring Company agrees to indemnify and save Staffing Company and Workers harmless from any and all claims and expenses (including litigation) for bodily injury or property damage or other loss as asserted by Hiring Company, its employees, agents, the owner of any such vehicles and/or equipment or contents thereof, or by members of the general public, or any other third party, arising out of the operation or use of said vehicles and/or equipment by Workers. </li> <li> Commencement of work by dispatched Workers, or Hiring Company’s signature on work ticket serves as confirmation of Hiring Company’s agreement to conditions of service listed in or referred to by this Contract. </li> <li> Hiring Company agrees not to place Workers in a supervisory position except for a Worker designated as a “lead,” and, in that position, Hiring Company agrees to supervise all Workers at all times. </li> <li> Billable time begins at the time Workers report to the workplace as designated by the Hiring Company. </li> <li> Jobs must be canceled a minimum of 24 hours prior to start time to avoid a minimum of four hours billing per Worker. </li> <li> Staffing Company guarantees that its Workers will satisfy Hiring Company, or the first two hours are free of charge. If Hiring Company is not satisfied with the Workers, Hiring Company is to call the designated phone number for the Staffing Company within the first two hours, and Staffing Company will replace them free of charge.</li> <li> Staffing Company agrees that it will comply with Hiring Company’s safety program rules. </li> <li> Overtime will be billed at one and one-half times the regular billing rate for all time worked over forty hours in a pay period and/or eight hours in a day as provided by state law. </li> <li> Invoices are due 30 days from receipt, unless other arrangements have been made and agreed to by each of the parties. </li> <li> Interest Rate: Any outstanding balance due to Staffing Company is subject to an interest rate of two percent (2%) per month, commencing on the 90th day after the date the balance was due, until the balance is paid in full by Hiring Company. </li> <li> Severability. If any provision of this Contract is held to be invalid and unenforceable, then the remainder of this Contract shall nevertheless remain in full force and effect. </li> <li> Attorney’s Fees. Hiring Company agrees to pay reasonable attorney’s fees and/or collection fees for any unpaid account balances or in any action incurred to enforce this Contract. </li> <li> Governing Law. This Contract is governed by the laws of the state of Florida, regardless of its conflicts of laws rules. </li> <li>  If Hiring Company utilizes a Staffing Company employee to work on a prevailing wage job, Hiring Company agrees to notify Staffing Company with the correct prevailing wage rate and correct job classification for duties Staffing Company employees will be performing. Failure to provide this information or providing incorrect information may result in the improper reporting of wages, resulting in fines or penalties being imposed upon Staffing Company. The Hiring Company agrees to reimburse Staffing Company for any and all fines, penalties, wages, lost revenue, administrative and/or supplemental charges incurred by Staffing Company.</li> <li> WORKERS' COMPENSATION COSTS: Staffing Company represents and warrants that it has a strong safety program, and it is Staffing Company’s highest priority to bring its Workers home safely every day. AFFORDABLE CARE ACT (ACA): Staffing Company represents and warrants that it is in compliance with all aspects of the ACA. </li> <li> Representatives. The Hiring Company and the Staffing Company each certifies that its authorized representative has read all of the terms and conditions of this Contract and understands and agrees to the same. </li> ";

    if (frm.doc.contract_add_on) {
      frappe.db.get_value(
        "Company",
        { name: frm.doc.company },
        ["contract_addendums"],
        function() {
          let contract = new frappe.ui.Dialog({
            title: "Contract Details",
            fields: [
              {
                fieldname: "html_37",
                fieldtype: "HTML",
                options:
                  contracts +
                  "<li>" +
                  frm.doc.contract_add_on +
                  "</li>  </ol>  </div>",
              },
            ],
          });
          contract.show();
        }
      );
    } else {
      let contract = new frappe.ui.Dialog({
        title: "Contract Details",
        fields: [
          { fieldname: "html_37", fieldtype: "HTML", options: contracts },
        ],
      });
      contract.show();
    }
  },

  from_date: function(frm) {
    check_from_date(frm);
  },

  to_date(frm) {
    check_to_date(frm);
  },

  estimated_hours_per_day: function(frm) {
    let value = frm.doc.estimated_hours_per_day;
    if (value && (value < 0 || value > 24)) {
      frappe.msgprint({
        message: __(
          "<b>Estimated Hours Per Day</b> Cannot be Less Than Zero or Greater Than 24."
        ),
        title: __("Error"),
        indicator: "orange",
      });
      frm.set_value("estimated_hours_per_day", "");
    }
  },

  total_no_of_workers: function(frm) {
    let field = "Total No Of Workers";
    let name = "total_no_of_workers";
    let value = frm.doc.total_no_of_workers;
    check_value(frm, field, name, value);
  },

  rate: function(frm) {
    let field = "Rate";
    let name = "rate";
    let value = parseFloat(frm.doc.rate);
    check_value(frm, field, name, value);
    rate_calculation(frm);
  },

  extra_price_increase: function(frm) {
    let field = "Extra Price Increase";
    let name = "extra_price_increase";
    let value = frm.doc.extra_price_increase;
    check_value(frm, field, name, value);
    rate_calculation(frm);
  },

  per_hour: function(frm) {
    let field = "Per Hour";
    let name = "per_hour";
    let value = frm.doc.per_hour;
    check_value(frm, field, name, value);
  },

  flat_rate: function(frm) {
    let field = "Flat Rate";
    let name = "flat_rate";
    let value = frm.doc.flat_rate;
    check_value(frm, field, name, value);
  },

  availability: function(frm) {
    if (frm.doc.availability == "Custom") {
      frm.set_value("select_days", "");
      frm.set_value("selected_days", undefined);
      frm.set_df_property("select_days", "reqd", 1);
      frm.set_df_property("select_days", "read_only", 0);
    }
  },

  validate: function(frm) {
    frm.get_field("multiple_job_titles").grid.grid_rows.forEach((row) => {
      rate_calculation(locals, "Multiple Job Titles", row.doc.name);
      row.refresh_field("multiple_job_titles");
    });
    set_custom_base_price(frm);
    let l = {
      Company: frm.doc.company,
      "Job Order Start Date": frm.doc.from_date,
      "Job Site": frm.doc.job_site,
      "Job Order End Date": frm.doc.to_date,
      "Job Duration": frm.doc.job_order_duration,
      "E-Signature Full Name": frm.doc.e_signature_full_name,
      Availability: frm.doc.availability,
    };

    let message = "<b>Please Fill Mandatory Fields:</b>";
    for (let k in l) {
      if (l[k] === undefined || !l[k]) {
        message = message + "<br>" + k;
      }
    }
    if (frm.doc.agree_to_contract == 0) {
      message = message + "<br>Agree To Contract";
    }

    message = empty_title_details_validation(frm, message);


    let jobtitlecount = {};
    let jobstarttime = {};
    message = duplicate_validation_title(jobtitlecount, message);
    message = start_time_duplicate_validation(jobstarttime, message);
    if (frm.doc.availability == "Custom") {
      let selected_my_days = frm.doc.selected_days;
      if (frm.doc.selected_days === undefined || selected_my_days.length == 0) {
        message = message + "<br>Select Days";
        frm.set_df_property("select_days", "reqd", 1);
      }
    }

    if (message != "<b>Please Fill Mandatory Fields:</b>") {
      frappe.msgprint({
        message: __(message),
        title: __("Error"),
        indicator: "orange",
      });
      frappe.validated = false;
    }
    validate_email_number(frm);
  },

  drug_screen: (frm) => {
    if (frm.doc.drug_screen) rate_calculation(frm);
  },
  driving_record: (frm) => {
    if (frm.doc.driving_record) rate_calculation(frm);
  },
  shovel: (frm) => {
    if (frm.doc.shovel) rate_calculation(frm);
  },
  background_check: (frm) => {
    if (frm.doc.background_check) rate_calculation(frm);
  },

  company: function(frm) {
    if (
      (frm.doc.__islocal == 1 &&
        frm.doc.company &&
        frappe.boot.tag.tag_user_info.company_type == "Hiring") ||
      frappe.boot.tag.tag_user_info.company_type == "Exclusive Hiring"
    ) {
      check_company_detail(frm);
    }
    if (
      frappe.boot.tag.tag_user_info.company_type == "Staffing" &&
      frm.doc.company
    ) {
      fields_setup(frm);
      staffing_create_job_order(frm);
    }
    sessionStorage.setItem("joborder_company", frm.doc.company);
    sessionStorage.setItem("exc_joborder_company", frm.doc.company);
  },
  phone_number: function(frm) {
    let phone = frm.doc.phone_number;
    if (phone) {
      frm.set_value(
        "phone_number",
        validate_phone(phone) ? validate_phone(phone) : phone
      );
    }
  },
  job_site: function(frm) {
    frm.clear_table("multiple_job_titles");
    refresh_field("multiple_job_titles");
    frm.set_value("select_job", "");
  },
});

frappe.ui.form.on("Multiple Job Titles", {
  select_job: function(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    if (row.select_job) {
      frappe.call({
        method:
          "tag_workflow.tag_workflow.doctype.job_order.job_order.update_joborder_rate_desc",
        args: {
          job_site: frm.doc.job_site,
          job_title: row.select_job,
        },
        callback: function(r) {
          if (r.message) {
            frappe.model.set_value(cdt, cdn, "rate", r.message[0].bill_rate);
            frappe.model.set_value(cdt, cdn, "category", r.message[0].industry_type);
            frappe.model.set_value(cdt, cdn, "worker_comp_code", r.message[0].comp_code);
            frm.refresh_field("multiple_job_titles");

          }
        },
      });
    }
    else{
      frappe.model.set_value(cdt,cdn,"category","");
      frappe.model.set_value(cdt,cdn,"description","");
      frappe.model.set_value(cdt,cdn,"rate","");
      frappe.model.set_value(cdt,cdn,"worker_comp_code","");
      frm.refresh_field("multiple_job_titles");
    }
  },

  rate: function(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    if (row.rate) {
      rate_calculation(locals, cdt, cdn);
    }
  },

  estimated_hours_per_day: function(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    let value = row.estimated_hours_per_day;
    if (value && (value < 0 || value > 24)) {
      frappe.msgprint({
        message: __(
          "<b>Estimated Hours Per Day</b> Cannot be Less Than Zero or Greater Than 24."
        ),
        title: __("Error"),
        indicator: "orange",
      });
      row.estimated_hours_per_day = "";
      refresh_field("multiple_job_titles");
    }
  },
  no_of_workers: function(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    let value = row.no_of_workers;
    if (value && value < 0) {
      frappe.msgprint({
        message: __("<b>No. of Workers</b> Cannot be Less Than Zero."),
        title: __("Error"),
        indicator: "orange",
      });
      row.no_of_workers = "";
      frappe.model.set_value(
        cdt,
        cdn,
        "no_of_workers",
        frm.doc.repeat_old_worker ? frm.doc.repeat_old_worker : 0
      );
      refresh_field("multiple_job_titles");
    }
      if(value>0 && frm.doc.__islocal!=1&&value<row.worker_filled&&row.worker_filled>0) {

        frappe.call({
          method: "tag_workflow.tag_data.check_can_reduce_count",
          args: {
            job_start_time: row.job_start_time,
            row_name: row.name,
            start_date: frm.doc.from_date
          },
          callback: function(r) {
            if(r.message[0]==0 && frm.doc.order_status != "Upcoming") {
              frappe.msgprint("Can't reduce the headcount or remove the employee once shift started.")
              frappe.model.set_value('Multiple Job Titles',row.name,"no_of_workers",r.message[1]);
              frm.refresh_fields('multiple_job_titles')
              frappe.validated = false
            }
            else if(frm.doc.resumes_required==0){
                reduce_headcount_remove_employee_without_resume_popup(frm,row.select_job,row.job_start_time.slice(0,-3),row.name)
              
            }
            else if(frm.doc.resumes_required==1){
              reduce_headcount_remove_employee_with_resume_popup(frm,row.select_job,row.job_start_time.slice(0,-3),row.name)
            }
          },
        });
      }
      else if(value>0 && frm.doc.__islocal!=1&&frm.doc.resumes_required==0&&row.worker_filled==0) {
        reduce_headcount_with_approved_claim_popup(frm,row)
      }
  },

  extra_price_increase: function(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    if (row.extra_price_increase) {
      rate_calculation(locals, cdt, cdn);
    }
  },

  drug_screen: function(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    if (row.drug_screen) {
      rate_calculation(locals, cdt, cdn);
    }
  },

  driving_record: function(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    if (row.driving_record) {
      rate_calculation(locals, cdt, cdn);
    }
  },

  shovel: function(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    if (row.shovel) {
      rate_calculation(locals, cdt, cdn);
    }
  },

  background_check: function(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    if (row.background_check) {
      rate_calculation(locals, cdt, cdn);
    }
  },
});

function multiple_title_workers_validation(message) {
  if (cur_frm.doc.multiple_job_titles) {
    for (let single_job_title of cur_frm.doc.multiple_job_titles) {
      if (single_job_title.no_of_workers) {
        if (single_job_title.no_of_workers < single_job_title.worker_filled) {
          message =
            single_job_title.worker_filled +
            " Employees are assigned to this order. Number of required workers must be greater than or equal to number of assigned employees. Please modify the number of workers required or work with the staffing companies to remove an assigned employee. ";
        }
      }
    }
  }
  return message;
}

function empty_title_details_validation(frm, message) {
  if (!frm.doc.multiple_job_titles || frm.doc.multiple_job_titles == 0) {
    message = message + "<br>" + "Job Titles";
  } else {
    const requiredFields = [
      "select_job",
      "category",
      "rate",
      "no_of_workers",
      "job_start_time",
      "estimated_hours_per_day",
    ];
    const notation = {
      select_job: "Job Title",
      category: "Industry",
      rate: "Rate",
      no_of_workers: "No. of Workers",
      job_start_time: "Start Time",
      estimated_hours_per_day: "Estimated Daily Hours",
    };

    for (let each_job_title of frm.doc.multiple_job_titles) {
      for (let field of requiredFields) {
        if (!each_job_title[field]) {
          message += "<br>Job Titles: " + notation[field] + " Required";
          break;
        }
      }
    }
  }
  return message;
}

function category_values(total_workers, total_categories, frm) {
  for (let jobTitle of cur_frm.doc.multiple_job_titles) {
    if (jobTitle.no_of_workers) {
      total_workers += jobTitle.no_of_workers;
      if (!total_categories.includes(jobTitle.category)) {
        total_categories.push(jobTitle.category);
      }
    }
  }
  let category_val_popup =
    total_categories[0] +
    (total_categories.length - 1
      ? " +" + parseInt(total_categories.length - 1)
      : "");
  frm.set_value("total_no_of_workers", total_workers);
  return { category_val_popup, total_workers };
}

function start_time_duplicate_validation(jobstarttime, message) {
  if (cur_frm.doc.multiple_job_titles) {
    for (let value of cur_frm.doc.multiple_job_titles) {
      let jobTitle = value;
      let selectjob = jobTitle.select_job;
      if (selectjob && jobTitle.job_start_time) {
        if (jobstarttime[selectjob]) {
          jobstarttime[selectjob].push(jobTitle.job_start_time);
        } else {
          jobstarttime[selectjob] = [];
          jobstarttime[selectjob].push(jobTitle.job_start_time);
        }
      }
    }
  }
  message = check_duplicate_time(jobstarttime, message);
  return message;
}

function check_duplicate_time(jobstarttime, message) {
  for (let each_job in jobstarttime) {
    let starttimeCount = jobstarttime[each_job].length;

    if (starttimeCount > 1) {
      let sortedstarttimes = jobstarttime[each_job].sort();
      let duplicatetime = false;

      for (let starttime of sortedstarttimes) {
        if (
          sortedstarttimes.indexOf(starttime) !==
          sortedstarttimes.lastIndexOf(starttime)
        ) {
          duplicatetime = true;
          break;
        }
      }
      if (duplicatetime) {
        message +=
          "<br>" +
          "Job title '" +
          each_job +
          "' has multiple rows with the same start time";
      }
    }
  }
  return message;
}

function duplicate_validation_title(jobtitlecount, message) {
  let unique_titles = [];
  if (cur_frm.doc.multiple_job_titles) {
    for (let every_single_job_title of cur_frm.doc.multiple_job_titles) {
      let each_jobTitle = every_single_job_title;
      let selectjob = each_jobTitle.select_job;
      if (selectjob && !unique_titles.includes(selectjob)) {
        unique_titles.push(selectjob);
      }
    }
    if (unique_titles.length > 20) {
      message += "<br>" + "Unique Job Titles cannot be more than 20";
    }
  }
  return message;
}

function set_multiple_title_filters(frm) {
  frm.set_query("select_job", "multiple_job_titles", function(doc, cdt, cdn) {
    return {
      query:
        "tag_workflow.tag_workflow.doctype.job_order.job_order.get_jobtitle_list",
      filters: {
        job_order_company: doc.company,
        job_site: doc.job_site,
      },
    };
  });
}

/*-------check company details---------*/
function check_company_detail(frm) {
  let roles = frappe.user_roles;
  if (
    roles.includes("Hiring User") ||
    (roles.includes("Hiring Admin") && frm.doc.company)
  ) {
    let company_name = frm.doc.company;
    frappe.call({
      method: "tag_workflow.tag_data.company_details",
      args: {
        company_name: company_name,
      },
      callback: function(r) {
        if (r.message != "success") {
          check_company_complete_details(r, frm);
        }
      },
    });
  }
}

/*----------------prepare quote--------------*/
function assign_employe(frm) {
  redirect_quotation(frm);
}

function redirect_quotation(frm) {
  let doc = frappe.model.get_new_doc("Assign Employee");
  let staff_company = staff_company_direct_or_general(frm);
  doc.transaction_date = frappe.datetime.now_date();
  doc.doctype = "Assign Employee";
  doc.company = staff_company[0];
  doc.job_order = frm.doc.name;
  doc.no_of_employee_required =  frm.doc.resumes_required == 1 ? frm.doc.total_no_of_workers - frm.doc.total_workers_filled : frm.doc.total_no_of_workers;

  if (frm.doc.staff_company) {
    doc.company = frm.doc.staff_company;
  }
  doc.hiring_organization = frm.doc.company;
  doc.job_category = frm.doc.select_job;
  doc.job_location = frm.doc.job_site;
  doc.job_order_email = frm.doc.owner;
  doc.resume_required = frm.doc.resumes_required;
  doc.is_single_share = frm.doc.is_single_share;
  doc.distance_radius = "5 miles";
  frappe.call({
    method:
      "tag_workflow.tag_workflow.doctype.assign_employee.assign_employee.multiple_job_title_details",
    args: {
      job_order: frm.doc.name,
      hiring_company: frm.doc.company,
      staffing_company: staff_company[0],
      job_site: frm.doc.job_site,
      resume_required: frm.doc.resumes_required,
    },
    callback: function(r) {
      if (r.message == "No Record") {
        frappe.msgprint("No Multiple Job Title Details");
      } else {
        r.message.forEach((row) => {
          let row_child = frappe.model.add_child(
            doc,
            "Multiple Job Title Details",
            "multiple_job_title_details"
          );
          row_child.select_job = row.select_job;
          row_child.category = row.category;
          row_child.no_of_workers = row.no_of_workers;
          row_child.worker_comp_code = row.worker_comp_code;
          row_child.rate = row.rate;
          row_child.employee_pay_rate = row.pay_rate;
          row_child.estimated_hours_per_day = row.estimated_hours_per_day;
          row_child.job_start_time = row.job_start_time;
          row_child.bill_rate = row.per_hour + row.flat_rate;
          if (frm.doc.resumes_required == 1) {
            row_child.no_of_workers = row.no_of_workers - row.worker_filled;
          } else {
            row_child.no_of_workers = row.no_of_workers
            row_child.approved_workers = row.approved_no_of_workers?row.approved_no_of_workers:0
          }
        });
      }
    },
  });
  staff_org_details(doc);
}

function staff_org_details(doc) {
  frappe.call({
    method: "tag_workflow.tag_data.staff_org_details",
    args: {
      company_details: frappe.boot.tag.tag_user_info.company,
    },
    callback: function(r) {
      if(r.message!="success") {
        staffing_company_details(r);
      } else {
        frappe.set_route("Form","Assign Employee",doc.name);
      }
    },
  });
}

function staff_company_direct_or_general(frm) {
  if (frm.doc.is_single_share) {
    return [frm.doc.staff_company];
  } else if (frappe.boot.tag.tag_user_info.company.length >=1 && Array.isArray(frappe.boot.tag.tag_user_info.company)){
      return frappe.boot.tag.tag_user_info.company}
  else if(frappe.boot.tag.tag_user_info.company.length >=1){
    return [frappe.boot.tag.tag_user_info.company]
  }
  else{
    return []
  }
}

function timer_value(frm) {
  if (frm.doc.bid > 0 || frm.doc.claim) {
    frm.toggle_display("section_break_8", 0);
  }
  if (frm.doc.order_status == "Completed") {
    frm.toggle_display("section_break_8", 0);
    frm.set_df_property("time_remaining_for_make_edits", "options", " ");
  } else if (
    ["Upcoming", "Ongoing"].includes(frm.doc.order_status)
  ) {
    time_value(frm);
    setTimeout(function() {
      time_value(frm);
      frm.refresh();
      view_button(frm);
    }, 60000);
  } else {
    frm.set_df_property("time_remaining_for_make_edits", "hidden", 1);
  }
}

function time_value(frm) {
  let jobstarttime = [];
  for (let jobtitles of frm.doc.multiple_job_titles) {
    let time = jobtitles.job_start_time;
    if (jobtitles.job_start_time.split(":")[0].length == 1) {
      time = "0" + jobtitles.job_start_time;
    }
    jobstarttime.push(time);
  }
  jobstarttime.sort((a, b) => a.localeCompare(b));
  let job_start_time = jobstarttime[0];
  let entry_datetime = frappe.datetime.now_datetime().split(" ")[1];
  let splitEntryDatetime = entry_datetime.split(":");
  let splitExitDatetime = job_start_time.split(":");
  let totalMinsOfEntry =
    splitEntryDatetime[0] * 60 +
    parseInt(splitEntryDatetime[1]) +
    splitEntryDatetime[0] / 60;
  let totalMinsOfExit =
    splitExitDatetime[0] * 60 +
    parseInt(splitExitDatetime[1]) +
    splitExitDatetime[0] / 60;
  let entry_date = new Date(frappe.datetime.now_datetime().split(" ")[0]);
  let exit_date = new Date(frm.doc.from_date.split(" ")[0]);
  let diffTime = Math.abs(exit_date - entry_date);
  if (exit_date - entry_date > 0 || exit_date - entry_date == 0) {
    let diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    let x = parseInt(diffDays * (24 * 60) + totalMinsOfExit - totalMinsOfEntry);
    if (x > 0) {
      let data1 =
        Math.floor(x / 24 / 60) +
        " Days:" +
        Math.floor((x / 60) % 24) +
        " Hours:" +
        (x % 60) +
        " Minutes";
      let data = `<p><b>Time Remaining for Job Order Start: </b> ${[
        data1,
      ]}</p>`;
      frm.set_df_property("time_remaining_for_make_edits", "options", data);
    } else {
      frm.set_df_property("time_remaining_for_make_edits", "hidden", 1);
    }
  } else {
    frm.set_df_property("time_remaining_for_make_edits", "hidden", 1);
  }
}

function notification_joborder_change(frm) {
  frappe.call({
    method:
      "tag_workflow.tag_workflow.doctype.job_order.job_order.joborder_notification",
    freeze: true,
    freeze_message: "<p><b>preparing notification for staffing orgs...</b></p>",
    args: {
      organizaton: frm.doc.staff_org_claimed,
      doc_name: frm.doc.name,
      company: frm.doc.company,
      job_title: frm.doc.select_job,
      job_site: frm.doc.job_site,
      posting_date: frm.doc.from_date,
    },
  });
}

function check_from_date(frm) {
  let from_date = frm.doc.from_date || "";
  let to_date = frm.doc.to_date || "";

  if (from_date && from_date < frappe.datetime.now_date()) {
    frappe.msgprint({
      message: __("<b>Start Date</b> Cannot be Past Date"),
      title: __("Error"),
      indicator: "orange",
    });
    frm.set_value("from_date", "");
  } else if (to_date && from_date && from_date > to_date) {
    frappe.msgprint({
      message: __("<b>End Date</b> Cannot be Less than Start Date"),
      title: __("Error"),
      indicator: "orange",
    });
    frm.set_value("from_date", "");
    frm.set_value("to_date", "");
  } else {
    job_order_duration(frm);
  }
}

function check_to_date(frm) {
  let from_date = frm.doc.from_date || "";
  let to_date = frm.doc.to_date || "";
  if (to_date && frappe.datetime.now_date() > to_date) {
    frappe.msgprint({
      message: __("<b>End Date</b> Cannot be Past Date"),
      title: __("Error"),
      indicator: "orange",
    });
    frm.set_value("to_date", "");
  } else if (to_date && from_date && from_date > to_date) {
    frappe.msgprint({
      message: __("<b>End Date</b> Cannot be Less than Start Date"),
      title: __("Error"),
      indicator: "orange",
    });
    frm.set_value("to_date", "");
  } else {
    job_order_duration(frm);
  }
}

function check_value(frm, field, name, value) {
  if (value && value < 0) {
    frappe.msgprint({
      message: __("<b>" + field + "</b> Cannot be Less Than Zero"),
      title: __("Error"),
      indicator: "orange",
    });
    frm.set_value(
      name,
      frm.doc.repeat_old_worker && name == "no_of_workers"
        ? frm.doc.repeat_old_worker
        : 0
    );
  }
}

function rate_hour_contract_change(frm) {
  if (frm.doc.total_no_of_workers < frm.doc.total_workers_filled) {
    frappe.msgprint({
      message: __("Workers Already Filled"),
      title: __("Error"),
      indicator: "orange",
    });
    frappe.validated = false;
  }

  if (frappe.validated) {
    frm.get_field("multiple_job_titles").grid.grid_rows.forEach((row) => {
      rate_calculation(locals, "Multiple Job Titles", row.doc.name);
      row.refresh_field("multiple_job_titles");
    });
  }
}

function rate_calculation(locals, cdt, cdn) {
  let row = locals[cdt][cdn];
  let extra_price_increase = row.extra_price_increase || 0;
  let total_per_hour = extra_price_increase + parseFloat(row.rate);
  let total_flat_rate = 0;
  const optional_field_data = [
    row.drug_screen,
    row.background_check,
    row.driving_record,
    row.shovel,
  ];
  const optional_fields = [
    "drug_screen",
    "background_check",
    "driving_record",
    "shovel",
  ];

  for (let i = 0; i < optional_fields.length; i++) {
    if (optional_field_data[i] && optional_field_data[i] != "None") {
      let y = optional_field_data[i];
      if (y.includes("Flat")) {
        y = y.split("$");
        total_flat_rate = total_flat_rate + parseFloat(y[1]);
      } else if (y.includes("Hour")) {
        y = y.split("$");
        total_per_hour = total_per_hour + parseFloat(y[1]);
      }
    } else {
      frappe.model.set_value(cdt, cdn, optional_fields[i], "None");
    }
  }
  frappe.model.set_value(cdt, cdn, "flat_rate", total_flat_rate);
  frappe.model.set_value(cdt, cdn, "per_hour", total_per_hour);
}

function hide_employee_rating(frm) {
  let table = frm.doc.employee_rating || [];
  if (table.length == 0) {
    frm.toggle_display("employee_rating", 0);
  }
}

/*----------make invoice---------*/
function make_invoice(frm) {
  let roles = frappe.user_roles;
  if (
    frm.doc.__islocal != 1 &&
    roles.includes("Staffing Admin", "Staffing User") &&
    frappe.boot.tag.tag_user_info.company
  ) {
    frappe.db.get_value(
      "Assign Employee",
      {
        company: frappe.boot.tag.tag_user_info.company,
        tag_status: "Approved",
        job_order: frm.doc.name,
      },
      "name",
      function(r) {
        if (r.name) {
          if (frm.doc.order_status != "Upcoming") {
            frm
              .add_custom_button(__("Create Invoice"), function() {
                frappe.model.open_mapped_doc({
                  method:
                    "tag_workflow.tag_workflow.doctype.job_order.job_order.make_invoice",
                  frm: frm,
                });
              })
              .addClass("btn-primary");
          }
        }
      }
    );
  }
}

function fields_setup(frm) {
  if (frm.doc.company) {
    frappe.db.get_value(
      "Company",
      { name: frm.doc.company },
      [
        "drug_screen_rate",
        "hour_per_person_drug",
        "background_check_rate",
        "background_check_flat_rate",
        "mvr_rate",
        "mvr_per",
        "shovel_rate",
        "shovel_per_person",
        "contract_addendums",
      ],
      function(r) {
        if (r.contract_addendums != "undefined" && frm.doc.__islocal == 1) {
          frm.set_value("contract_add_on", r.contract_addendums);
        }
        const org_optional_data = [
          r.drug_screen_rate,
          r.hour_per_person_drug,
          r.background_check_rate,
          r.background_check_flat_rate,
          r.mvr_rate,
          r.mvr_per,
          r.shovel_rate,
          r.shovel_per_person,
        ];

        const optional_field_data = [
          "drug_screen",
          "background_check",
          "driving_record",
          "shovel",
        ];
        let a = 0;
        for (let i = 0; i <= 3; i++) {
          frm.fields_dict["multiple_job_titles"].grid.update_docfield_property(
            optional_field_data[i],
            "options",
            "None\n" +
              "Flat Rate Person:$" +
              org_optional_data[a] +
              "\n" +
              "Hour Per Person:$" +
              org_optional_data[a + 1]
          );

          frm.set_df_property(
            optional_field_data[i],
            "options",
            "None\n" +
              "Flat Rate Person:$" +
              org_optional_data[a] +
              "\n" +
              "Hour Per Person:$" +
              org_optional_data[a + 1]
          );
          a = a + 2;
        }
      }
    );
  }
}

function job_order_duration(frm) {
  if (!frm.doc.from_date || !frm.doc.to_date) {
    frm.set_value("job_order_duration", "");
    frm.set_df_property("availability", "hidden", 0);
    frm.set_df_property("availability", "reqd", 1);
  } else {
    const to_date = frm.doc.to_date.split(" ")[0].split("-");
    const from_date = frm.doc.from_date.split(" ")[0].split("-");
    let to_date2 = new Date(to_date[1] + "/" + to_date[2] + "/" + to_date[0]);
    let from_date2 = new Date(
      from_date[1] + "/" + from_date[2] + "/" + from_date[0]
    );
    let diff = Math.abs(to_date2 - from_date2);
    let days = diff / (1000 * 3600 * 24) + 1;
    if (days == 1) {
      frm.set_value("job_order_duration", days + " Day");
      frm.set_df_property("availability", "hidden", 1);
      frm.set_df_property("availability", "reqd", 0);
      frm.set_df_property("select_days", "reqd", 0);
      frm.set_value("availability", "Everyday");
    } else {
      frm.set_value("job_order_duration", days + " Days");
      frm.set_df_property("availability", "hidden", 0);
      frm.set_df_property("availability", "read_only", 0);
      frm.set_df_property("availability", "reqd", 1);
    }
  }
}

function claim_job_order_staffing(frm) {
  if (
    frappe.boot.tag.tag_user_info.company_type == "Staffing" &&
    frm.doc.__islocal != 1 &&
    frm.doc.resumes_required == 0
  ) {
    frappe.call({
      method:
        "tag_workflow.tag_workflow.doctype.claim_order.claim_order.additional_claim",
      args: {
        job_order: frm.doc.name,
        staff_comp: frappe.boot.tag.tag_user_info.comps,
        no_of_workers: frm.doc.total_no_of_workers,
        order_status: frm.doc.order_status,
        direct_comp: frm.doc.staff_company2 ? frm.doc.staff_company2 : "normal",
      },
      callback: (res) => {
        if (res.message && res.message != "no_button") {
          frm.add_custom_button("Claim Order", () => {
            get_joborder_data(frm, res.message);
          }).addClass("btn-primary");
          frm.set_df_property("section_break_html1", "hidden", 1);
        }
      },
    });
  }
}

function get_joborder_data(frm, message) {
  frappe.call({
    method: "tag_workflow.tag_data.staff_org_details",
    args: {
      company_details: frappe.boot.tag.tag_user_info.company,
    },
    callback: function(r) {
      if (r.message != "success") {
        staffing_company_details(r);
      } else if (message == "new_claim") {
        new_claim_order(frm);
      } else {
        frappe.set_route("Form", "Claim Order", message);
      }
    }
  });
}

/**
 * The function creates a new claim order document and populates it with information from the form,
 * including multiple job titles and their respective details.
 * @param frm - The `frm` parameter is a reference to the current form object. It is used to access and
 * manipulate the data in the form.
 */
function new_claim_order(frm) {
  let doc = frappe.model.get_new_doc("Claim Order");
  if (frm.doc.is_single_share == 1) {
    doc.staffing_organization = frm.doc.staff_company;
    doc.single_share = 1;
  } else {
    doc.staffing_organization =
      frappe.boot.tag.tag_user_info.comps.length > 1
        ? ""
        : frappe.boot.tag.tag_user_info.comps[0];
  }
  doc.job_order = frm.doc.name;
  doc.hiring_organization = frm.doc.company;
  doc.contract_add_on = frm.doc.contract_add_on;
  frm.call({
    method: "submit_headcount",
    args: {
      job_order: frm.doc.name,
      job_titles: frm.doc.multiple_job_titles,
    },
    freeze: true,
    callback: function(s) {
      s.message.forEach((row) => {
        if (row.no_of_remaining_employee) {
          let row_child = frappe.model.add_child(
            doc,
            "Multiple Job Title Claim",
            "multiple_job_titles"
          );
          row_child.job_title = row.job_title;
          row_child.industry = row.industry;
          row_child.start_time = row.start_time;
          row_child.duration = row.duration;
          row_child.no_of_workers_joborder = row.no_of_workers_joborder;
          row_child.no_of_remaining_employee = row.no_of_remaining_employee;
          row_child.approved_no_of_workers = 0;
          row_child.bill_rate = row.bill_rate;
        }
      });
      frappe.set_route("Form", "Claim Order", doc.name);
    },
  });
}

function show_claim_bar(frm) {
  if (
    frm.doctype == "Job Order" &&
    frm.doc.staff_org_claimed &&
    frm.doc.staff_org_claimed.includes(frappe.boot.tag.tag_user_info.company)
  ) {
    frappe.call({
      method: "tag_workflow.tag_data.claim_order_company",
      args: {
        user_name: frappe.session.user,
        claimed: frm.doc.staff_org_claimed,
        job_order: frm.doc.name
      },
      callback: function(r) {
        if (r.message != "unsuccess") {
          claim_bar_data_hide(frm);
        }
      },
    });
  } else if (
    frm.doctype == "Job Order" &&
    frm.doc.claim &&
    frm.doc.claim.includes(frappe.boot.tag.tag_user_info.company) &&
    frm.doc.resumes_required == 0
  ) {
    frappe.call({
      method: "tag_workflow.tag_data.claim_order_company",
      args: {
        user_name: frappe.session.user,
        claimed: frm.doc.claim,
        job_order: frm.doc.name
      },
      callback: function(r) {
        if (r.message != "unsuccess") {
          frm.toggle_display("section_break_html2", 1);
          frm.set_df_property(
            "html_3",
            "options",
            "<h3>Your company has submitted a claim for this order.</h3>"
          );
        }
      },
    });
  } else if (
    frm.doctype == "Job Order" &&
    frm.doc.claim &&
    frm.doc.claim.includes(frappe.boot.tag.tag_user_info.company) &&
    frm.doc.resumes_required == 1
  ) {
    frappe.call({
      method: "tag_workflow.tag_data.claim_order_company",
      args: {
        user_name: frappe.session.user,
        claimed: frm.doc.claim,
        job_order: frm.doc.name
      },
      callback: function(r) {
        if (r.message != "unsuccess") {
          frm.remove_custom_button("Claim and Recommend");
          frm.toggle_display("section_break_html2", 1);
          frm.set_df_property(
            "html_3",
            "options",
            "<h3>Your company has submitted a claim for this order.</h3>"
          );
        }
      },
    });
  }
}

function assign_employees(frm) {
  if (frm.doc.to_date < frappe.datetime.nowdate()) {
    frappe.msgprint({
      message: __("Date has been past to claim this order"),
      title: __("Job Order filled"),
      indicator: "blue",
    });
  } else if (
    frm.doc.__islocal != 1 &&
    frm.doc.total_workers_filled < frm.doc.total_no_of_workers
  ) {
    if (frm.is_dirty()) {
      frappe.msgprint({
        message: __("Please save the form before creating Quotation"),
        title: __("Save Job Order"),
        indicator: "red",
      });
    } else {
      assign_employe(frm);
    }
  }
}

function view_button(frm) {
  if (
    frm.doctype == "Job Order" &&
    frappe.boot.tag.tag_user_info.company_type == "Staffing" &&
    frm.doc.__islocal != 1
  ) {
    if (frm.doc.claim) {
      frappe.call({
        method: "tag_workflow.tag_data.claim_order_company",
        args: {
          user_name: frappe.session.user,
          claimed: frm.doc.claim,
          job_order: frm.doc.name
        },
        callback: function(r) {
          if (r.message != "unsuccess") {
            view_buttons_staffing(frm);
          }
        },
      });
    }
  } else if (
    frappe.boot.tag.tag_user_info.company_type == "Hiring" ||
    (frappe.boot.tag.tag_user_info.company_type == "Exclusive Hiring" &&
      frm.doc.__islocal != 1)
  ) {
    view_buttons_hiring(frm);
  }
}

function view_buttons_hiring(frm) {
  hiring_buttons(frm);
  if (frm.doc.__islocal != 1) {
    let no_of_claims = 0;
    frappe.call({
      method:
        "tag_workflow.tag_workflow.doctype.job_order.job_order.no_of_claims",
      args: {
        job_order: frm.doc.name,
      },
      async: 0,
      callback: (r) => {
        no_of_claims += r.message;
      },
    });

    let datad1 = `<div class="my-2 p-3 border rounded cursor-pointer" id="data" style="display: flex;justify-content: space-between;"><p class="m-0 msg"> Claims  </p><label class="badge m-0 bg-danger rounded-circle font-weight-normal mr-4 text-white"> ${no_of_claims} </label></div>`;
    $("[data-fieldname = related_details]").click(function() {
      claim_orders(frm);
    });
    frm.set_df_property("related_details", "options", datad1);
    frm.toggle_display("related_actions_section", 1);
    if (frm.doc.claim) {
      let datad2 = `<div class="my-2 p-3 border rounded cursor-pointer" style="display: flex;justify-content: space-between;"><p class="m-0 msg">Messages </p></div>`;
      $("[data-fieldname = messages]").click(function() {
        messages();
      });

      frm.set_df_property("messages", "options", datad2);
      frm.toggle_display("related_actions_section", 1);
    }

    if (frm.doc.from_date <= frappe.datetime.nowdate()) {
      let datad3 = `<div class="my-2 p-3 border rounded cursor-pointer" style="display: flex;justify-content: space-between;"><p class="m-0 msg"> Timesheets  </p> </div>`;
      $("[data-fieldname = timesheets]").click(function() {
        timesheets_view(frm);
      });
      frm.set_df_property("timesheets", "options", datad3);
      frm.toggle_display("related_actions_section", 1);
      frm.add_custom_button(
        __("Timesheets"),
        function() {
          timesheets_view(frm);
        },
        __("View")
      );
    }

    if (
      frm.doc.order_status == "Completed" ||
      frm.doc.order_status == "Canceled" ||
      frm.doc.order_status == "Ongoing"
    ) {
      frappe.call({
        method: "tag_workflow.tag_data.timesheet_detail",
        args: {
          job_order: frm.doc.name,
          company_type: 'hiring'
        },
        callback: function(r) {
          if (r.message) {
            let datad4 = `<div class="my-2 p-3 border rounded cursor-pointer" style="display:flex;justify-content: space-between;"><p class="m-0 msg"> Invoices </p> </div>`;
            $("[data-fieldname = invoices]").click(function() {
              sales_invoice_data(frm);
            });
            frm.set_df_property("invoices", "options", datad4);
            frm.toggle_display("related_actions_section", 1);
            frm.add_custom_button(
              __("Invoices"),
              function() {
                sales_invoice_data(frm);
              },
              __("View")
            );
          }
        },
      });
    }
  }
}

function view_buttons_staffing(frm) {
  claim_assign_button(frm);
  if (frm.doc.claim.includes(frappe.boot.tag.tag_user_info.company)) {
    let data3 = `<div class="my-2 p-3 border rounded cursor-pointer" style="display:flex;justify-content: space-between;"><p class="m-0 msg">Messages </p></div>`;
    $("[data-fieldname = messages]").click(function() {
      messages();
    });

    frm.set_df_property("messages", "options", data3);
    frm.toggle_display("related_actions_section", 1);
    frm.add_custom_button(
      __("Messages"),
      function() {
        messages();
      },
      __("View")
    );
  }
  if (
    frm.doctype == "Job Order" &&
    frm.doc.staff_org_claimed &&
    (frm.doc.order_status != "Upcoming")
  ) {
    frappe.call({
      method: "tag_workflow.tag_data.claim_order_company",
      args: {
        user_name: frappe.session.user,
        claimed: frm.doc.staff_org_claimed,
        job_order: frm.doc.name
      },
      callback: function(r) {
        if (r.message != "unsuccess") {
          let data4 = `<div class=" p-3 border rounded cursor-pointer" style="display:flex;justify-content: space-between;"><p class="m-0 msg">Timesheets </p>  </div>`;
          $("[data-fieldname = timesheets]").click(function() {
            timesheets_view(frm);
          });
          frm.set_df_property("timesheets", "options", data4);
          frm.toggle_display("related_actions_section", 1);
          frm.add_custom_button(
            __("Timesheets"),
            function() {
              timesheets_view(frm);
            },
            __("View")
          );
        }
      },
    });
  }

  if (
    frm.doc.staff_org_claimed?.includes(
      frappe.boot.tag.tag_user_info.company
    ) &&
    (frm.doc.order_status == "Completed" || frm.doc.order_status == "Canceled" || frm.doc.order_status == "Ongoing")
  ) {
    frappe.call({
      method: "tag_workflow.tag_data.timesheet_detail",
      args: {
        job_order: frm.doc.name,
        company_type: 'staffing'
      },
      callback: function(r) {
        if (r.message == "success1") {
          let data5 = `<div class="my-2 p-3 border rounded" style="display:flex;justify-content: space-between;"> <p class="m-0 msg"> Invoices  </p> </div>`;
          $("[data-fieldname = invoices]").click(function() {
            sales_invoice_data(frm);
          });
          frm.set_df_property("invoices", "options", data5);
          frm.toggle_display("related_actions_section", 1);
          frm.add_custom_button(
            __("Invoices"),
            function() {
              sales_invoice_data(frm);
            },
            __("View")
          );
        } else if (r.message == "success") {
          let data6 = `<div class="my-2 p-3 border rounded" style="display:flex;justify-content: space-between;"><p class="m-0 msg">Invoices </p> </div>`;
          $("[data-fieldname = invoices]").click(function() {
            sales_invoice_data(frm);
          });
          frm.set_df_property("invoices", "options", data6);
          frm.toggle_display("related_actions_section", 1);
          frm.add_custom_button(
            __("Invoices"),
            function() {
              make_invoice(frm);
            },
            __("View")
          );
        }
      },
    });
  }
}

function hiring_buttons(frm) {
  if (frm.doc.__islocal != 1) {
    frm.add_custom_button(
      __("Claims"),
      function claim1() {
        claim_orders(frm);
      },
      __("View")
    );
    frappe.call({
      method: "tag_workflow.tag_data.assigned_employees",
      args: {
        job_order: frm.doc.name,
      },
      callback: function(r) {
        if (r.message == "success1") {
          frm.add_custom_button(
            __("Assigned Employees"),
            function() {
              approved_emp(frm);
            },
            __("View")
          );
          $("[data-fieldname = assigned_employees_hiring]").attr(
            "id",
            "approved_inactive"
          );
          let data = `<div class="my-2 p-3 border rounded cursor-pointer" style="display: flex;justify-content: space-between;"><p class="m-0 msg"> Assigned Employees  </p> </div>`;
          $("[data-fieldname = assigned_employees_hiring]")
            .off()
            .click(function() {
              if (
                $("[data-fieldname = assigned_employees_hiring]").attr("id") ==
                "approved_inactive"
              ) {
                approved_emp(frm);
              }
            });
          frm.set_df_property("assigned_employees_hiring", "options", data);
          frm.toggle_display("related_actions_section", 1);
        }
      },
    });
  }

  if (frm.doc.claim) {
    frm.add_custom_button(
      __("Messages"),
      function() {
        messages();
      },
      __("View")
    );
  }
}

function timesheets_view(frm) {
  if (
    frappe.user_roles.includes("Staffing Admin") ||
    frappe.user_roles.includes("Staffing User")
  ) {
    localStorage.setItem("order", frm.doc.name);
    window.location.href = "/app/timesheet-approval";
  } else {
    frappe.route_options = { job_order_detail: ["=", frm.doc.name] };
    frappe.set_route("List", "Timesheet");
  }
}

function claim_orders(frm) {
  if (frm.doc.order_status != "Completed" && frm.doc.resumes_required == 0) {
    if (frm.doc.staff_org_claimed) {
      frappe.route_options = {
        job_order: ["=", frm.doc.name],
        hiring_organization: ["=", frm.doc.company],
      };
      frappe.set_route("List", "Claim Order");
    } else {
      frappe.route_options = {
        job_order: ["=", frm.doc.name],
      };
      frappe.set_route("List", "Claim Order");
    }
  } else if (frm.doc.resumes_required == 0) {
    frappe.route_options = {
      job_order: ["=", frm.doc.name],
    };
    frappe.set_route("List", "Claim Order");
  }

  if (frm.doc.resumes_required == 1) {
    staff_assign_redirect(frm);
  }
}

function messages() {
  let x = document.getElementsByClassName(
    "li.nav-item.dropdown.dropdown-notifications.dropdown-mobile.chat-navbar-icon"
  );
  $(
    "li.nav-item.dropdown.dropdown-notifications.dropdown-mobile.chat-navbar-icon"
  ).click();
  if (frappe.route_history.length > 1) {
    $(x.css("display", "block"));
  }
}

function sales_invoice_data(frm) {
  frappe.route_options = {
    job_order: ["=", frm.doc.name],
  };
  frappe.set_route("List", "Sales Invoice");
}

function set_custom_base_price(frm) {
  frm.get_field("multiple_job_titles").grid.grid_rows.forEach((row) => {
    row.doc.base_price = row.doc.rate;
    row.doc.rate_increase = row.doc.per_hour - row.doc.rate;
    row.refresh_field("multiple_job_titles");
  });
  frm.refresh_field("multiple_job_titles");
  frm.set_value("base_price", frm.doc.rate);
  frm.set_value("rate_increase", frm.doc.per_hour - frm.doc.rate);
}

function check_increase_headcount(frm) {
  let headcounts = {};
  for (let every_single_job_title of cur_frm.doc.multiple_job_titles) {
    if (
      every_single_job_title.no_of_workers &&
      every_single_job_title.select_job
    ) {
      headcounts[every_single_job_title.select_job] =
        every_single_job_title.no_of_workers;
    }
  }

  frappe.call({
    method:
      "tag_workflow.tag_workflow.doctype.job_order.job_order.check_increase_headcounts",
    args: {
      no_of_workers_updated: headcounts,
      name: frm.doc.name,
      company: frm.doc.company,
    },
  });
}

function hide_unnecessary_data(frm) {
  let field_name = ["select_days", "total_workers_filled"];
  let arrayLength = field_name.length;
  for (let i = 0; i < arrayLength; i++) {
    frm.set_df_property(field_name[i], "hidden", 1);
  }

  let display_fields = ["base_price", "rate_increase"];
  let display_length = display_fields.length;
  for (let j = 0; j < display_length; j++) {
    frm.set_df_property(display_fields[j], "hidden", 0);
  }
}

function staff_assigned_emp(frm) {
  frappe.call({
    method: "tag_workflow.tag_data.staff_assigned_employees",
    args: {
      job_order: frm.doc.name,
      user_email: frappe.session.user_email,
      resume_required: frm.doc.resumes_required,
    },
    callback: function(r) {
      if (r.message) {
        if (frm.doc.resumes_required == 0) {
          staff_assign_button_claims(frm, r);
        } else {
          staff_assign_button_resume(frm, r);
        }
      }
    },
  });
}

function cancel_joborder(frm) {
  frm.add_custom_button(__("Cancel"), function() {
    frappe.set_route("Form", "Job Order");
  });
}

function claim_assign_button(frm) {
  if (frm.doc.resumes_required == 1) {
    assign_button(frm);
    staff_assigned_emp(frm);
  } else {
    staff_claim_button(frm);
  }
}

function assign_button(frm) {
  let data2 = `<div class="my-2 p-3 border rounded cursor-pointer" style="display:flex;justify-content: space-between;"><p class="m-0 msg">Claims </p></div>`;
  $("[data-fieldname = related_details]").click(function() {
    staff_assign_redirect(frm);
  });
  frm.set_df_property("related_details", "options", data2);
  frm.toggle_display("related_actions_section", 1);
}

function staff_assign_redirect(frm) {
  frappe.route_options = {
    job_order: ["=", frm.doc.name],
  };
  frappe.set_route("List", "Assign Employee");
}

function staff_claim_button(frm) {
  if (frm.doctype == "Job Order" && frm.doc.staff_org_claimed && !["Canceled", "Completed"].includes(frm.doc.order_status)) {
    frappe.call({
      method: "tag_workflow.tag_data.claim_order_company",
      args: {
        user_name: frappe.session.user,
        claimed: frm.doc.staff_org_claimed,
        job_order: frm.doc.name
      },
      callback: function(r) {
        if (r.message != "unsuccess") {
          frappe.db.get_value(
            "Assign Employee",
            {
              job_order: frm.doc.name,
              company: frappe.boot.tag.tag_user_info.company,
            },
            ["name"],
            function(rr) {
              if (rr.name === undefined) {
                let datadda1 = `<div class="my-2 p-3 border rounded cursor-pointer" style="display:flex;justify-content: space-between;"><p class="m-0 msg"> Assign Employees </p></div>`;
                $("[data-fieldname = assigned_employees]")
                  .off()
                  .click(function() {
                    assign_employe(frm);
                  });
                frm.set_df_property("assigned_employees", "options", datadda1);
                frm.toggle_display("related_actions_section", 1);

                frm.add_custom_button(
                  __("Assign Employees"),
                  function f1() {
                    assign_employe(frm);
                  },
                  __("View")
                );
              }
            }
          );
        }
      },
    });

    let data1 = `<div class="my-2 p-3 border rounded" style="display:flex;justify-content: space-between;"><p class="m-0 msg">Claims </p></div>`;
    $("[data-fieldname = related_details]").click(function() {
      claim_orders(frm);
    });
    frm.set_df_property("related_details", "options", data1);
    frm.toggle_display("related_actions_section", 1);
    staff_assigned_emp(frm);
  } else {
    let data2 = `<div class="my-2 p-3 border rounded" style="display:flex;justify-content: space-between;"><p class="m-0 msg">Claims </p></div>`;
    $("[data-fieldname = related_details]").click(function() {
      claim_orders(frm);
    });
    frm.set_df_property("related_details", "options", data2);
    frm.toggle_display("related_actions_section", 1);
    frm.add_custom_button(
      __("Claims"),
      function() {
        claim_orders(frm);
      },
      __("View")
    );
  }
}

function approved_emp(frm) {
  frappe.call({
    method: "tag_workflow.tag_data.assigned_employee_data",
    args: {
      job_order: frm.doc.name,
    },
    callback: function(rm) {
      let data = rm.message;
      let profile_html = `<table class="assign-emp-popup" style="width: 100%;"><th style="padding:0;width:20%">Job Title</th><th style="padding:0;width:20%">Employee Name</th><th style="padding:0;width:20%">Job Start Time</th><th style="padding:0;width:20%">Marked As</th><th style="padding:0;width:20%">Staffing Company</th>`;
      for (let p in data) {
        let marked_as = "";
        if (data[p].no_show) {
          marked_as += " " + data[p].no_show;
        }
        if (data[p].non_satisfactory) {
          marked_as += " " + data[p].non_satisfactory;
        }
        if (data[p].dnr) {
          marked_as += " " + data[p].dnr;
        }

        if (data[p].replaced) {
          marked_as += " Replaced";
        }
        profile_html += `<tr>
          <td style="padding:0;width:20%">${data[p].job_title}</td>
					<td style="padding:0;width:20%">${data[p].employee}</td>
          <td style="padding:0;width:20%">${data[p].job_start_time}</td>
					<td style="padding:0;width:20%">${marked_as}</td>
					<td style="padding:0;width:20%" >${data[p].staff_company}</td>
				</tr>`;
      }
      profile_html += `</table><style>th, td {padding-left: 50px;padding-right:50px;} input{width:100%;}</style>`;

      let dialog = new frappe.ui.Dialog({
        title: __("Assigned Employees"),
        fields: [
          {
            fieldname: "staff_companies",
            fieldtype: "HTML",
            options: profile_html,
          },
        ],
      });

      dialog.no_cancel();
      dialog.$wrapper.on("hidden.bs.modal", function() {
        $("[data-fieldname = assigned_employees_hiring]").attr(
          "id",
          "approved_inactive"
        );
      });
      dialog.set_primary_action(__("Close"), function() {
        dialog.hide();
        $("[data-fieldname = assigned_employees_hiring]").attr(
          "id",
          "approved_inactive"
        );
      });
      if (data.length) {
        dialog.add_custom_action(
          __(
            '<svg class="icon icon-sm"><use href="#icon-printer"></use></svg>'
          ),
          () => {
            let w = window.open(
              frappe.urllib.get_full_url(
                "/api/method/tag_workflow.tag_data.print_assigned_emp?company=hiring&job_order=" +
                  frm.doc.name
              )
            );
            if (!w) {
              frappe.msgprint(__("Please enable pop-ups"));
            }
          }
        );
      }
      if (
        $("[data-fieldname = assigned_employees_hiring]").attr("id") ==
        "approved_inactive"
      ) {
        dialog.show();
        dialog.$wrapper.find(".modal-dialog").css("max-width", "880px");
        dialog.$wrapper
          .find("textarea.input-with-feedback.form-control")
          .css("height", "108px");
        $("[data-fieldname = assigned_employees_hiring]").attr(
          "id",
          "approved_active"
        );
      }
    },
  });
}

function assigned_emp(frm) {
  frappe.call({
    method: "tag_workflow.tag_data.staffing_assigned_employee",
    args: { job_order: frm.doc.name },
    callback: function(rm) {
      let data = rm.message || [];
      let profile_html_data = "";
      profile_html_data += job_profile_data(frm, data);
      let dialog1 = new frappe.ui.Dialog({
        title: __("Assigned Employees"),
        fields: [
          {
            fieldname: "staff_companies",
            fieldtype: "HTML",
            options: profile_html_data,
          },
          {
            fieldtype: "Button",
            label: __("Go to Assign Employee Form"),
            fieldname: "assign_new_emp",
          },
        ],
      });
      if (data.length) {
        dialog1.add_custom_action(
          __(
            '<svg class="icon icon-sm"><use href="#icon-printer"></use></svg>'
          ),
          () => {
            let w = window.open(
              frappe.urllib.get_full_url(
                "/api/method/tag_workflow.tag_data.print_assigned_emp?company=staffing&job_order=" +
                  frm.doc.name
              )
            );
            if (!w) {
              frappe.msgprint(__("Please enable pop-ups"));
            }
          }
        );
      }
      if (
        $("[data-fieldname = assigned_employees]").attr("id") ==
        "assigned_inactive"
      ) {
        dialog1.fields_dict.assign_new_emp.$input[0].className =
          "btn btn-xs btn-default d-flex m-auto assign_new_emp_btn";
        dialog1.fields_dict.assign_new_emp.input.onclick = function() {
          frappe.db.get_value(
            "Assign Employee",
            {
              job_order: frm.doc.name,
              company: frappe.boot.tag.tag_user_info.company,
            },
            ["name", "claims_approved"],
            function(rr) {
              redirect_job(rr.name, frm.doc.nam);
            }
          );
        };
      }
      dialog1.no_cancel();
      dialog1.$wrapper.on("hidden.bs.modal", function() {
        $("[data-fieldname = assigned_employees]").attr(
          "id",
          "assigned_inactive"
        );
      });

      dialog1.set_primary_action(__("Close"), function() {
        dialog1.hide();
        $("[data-fieldname = assigned_employees]").attr(
          "id",
          "assigned_inactive"
        );
      });
      if (
        $("[data-fieldname = assigned_employees]").attr("id") ==
        "assigned_inactive"
      ) {
        dialog1.show();
        dialog1.$wrapper.find(".modal-dialog").css("max-width", "880px");
        dialog1.$wrapper
          .find("textarea.input-with-feedback.form-control")
          .css("height", "108px");
        $("[data-fieldname = assigned_employees]").attr(
          "id",
          "assigned_active"
        );
      }
    },
  });
}


function cancel_job_order(frm) {
  return new Promise(function(resolve, reject) {
    const d = frappe.confirm(
      "<h4>Are you sure you want to discard this Job Order? </h4><h5>This Process is irreversible. Your whole data related to this order will be deleted.</h5>",
      function() {
        let resp = "frappe.validated = false";
        resolve(resp);
        deleting_data(frm);
      },
      function() {
        const rejectionReason = "Job Order cancellation was rejected.";
        reject(rejectionReason);
      }
    );
    d.standard_actions
      .find(".btn-modal-primary")
      .attr("id", "joborder-confirm-button");
    d.standard_actions
      .find(".btn-modal-secondary")
      .attr("is", "joborder-discard-button");
  });
}

function deleting_data(frm) {
  frappe.call({
    method:
      "tag_workflow.tag_workflow.doctype.job_order.job_order.data_deletion",
    args: { job_order: frm.doc.name },
    callback: function(r) {
      if (r.message == "success") {
        frappe.msgprint("Order Deleted Successfully");
        setTimeout(function() {
          window.location.href = "/app/job-order";
        }, 3000);
      }
    },
  });
}

function deny_job_order(frm) {
  if (
    !frm.doc.is_repeat &&
    frm.doc.is_single_share == 1 &&
    frappe.boot.tag.tag_user_info.company_type == "Staffing" &&
    frm.doc.order_status != "Completed" &&
    !frm.doc.claim
  ) {
    frm.add_custom_button(__("Deny Job Order"), function() {
      frappe.call({
        method:
          "tag_workflow.tag_workflow.doctype.job_order.job_order.after_denied_joborder",
        args: {
          staff_company: frm.doc.staff_company,
          joborder_name: frm.doc.name,
          job_title: frm.doc.select_job,
          hiring_name: frm.doc.company,
        },
        freeze: true,
        freeze_message:
          "<p><b>preparing notification for hiring orgs...</b></p>",
        callback: function() {
          frm.refresh();
          frm.reload_doc();
        },
      });
    });
  } else {
    frm.remove_custom_button("Deny Job Order");
  }
}

function cancel_job_order_deatils(frm) {
  if (frappe.boot.tag.tag_user_info.company_type == "Staffing") {
    show_claim_bar(frm);
  }

  if (frm.doc.__islocal == 1) {
    cancel_joborder(frm);
  } else {
    timer_value(frm);
    let roles = frappe.user_roles;
    if (roles.includes("Hiring User") || roles.includes("Hiring Admin")) {
      if (
        frappe.datetime.now_datetime() >= frm.doc.from_date &&
        frm.doc.to_date >= frappe.datetime.now_datetime()
      ) {
        frm.set_df_property("total_no_of_workers", "read_only", 0);
      }
    }
  }
}

function staffing_company_remove(frm) {
  if (
    frm.doc.__islocal == 1 &&
    frappe.boot.tag.tag_user_info.company_type == "Staffing" &&
    !frm.doc.repeat_from_company
  ) {
    frm.set_value("company", "");
  }
}

function claim_order_button(frm) {
  if (
    frm.doc.__islocal != 1 &&
    frm.doc.total_no_of_workers == frm.doc.total_workers_filled &&
    frm.doc.claim &&
    frm.doc.claim.includes(frappe.boot.tag.tag_user_info.company) &&
    frm.doc.staff_org_claimed &&
    !frm.doc.staff_org_claimed.includes(frappe.boot.tag.tag_user_info.company)
  ) {
    frm.set_df_property("section_break_html3", "hidden", 0);
  }
}

function direct_order_staff_company(frm) {
  if (frm.doc.staff_company) {
    frm.toggle_display("staff_company", 1);
    frm.set_df_property("staff_company", "read_only", 1);
  }
}

function advance_hide(time) {
  if ($('[data-fieldname="select_days"]')[1]) {
    setTimeout(() => {
      let txt = $('[data-fieldname="select_days"]')[1].getAttribute(
        "aria-owns"
      );
      let txt2 = 'ul[id="' + txt + '"]';
      let arry = document.querySelectorAll(txt2)[0].children;
      if (arry.length) {
        document.querySelectorAll(txt2)[0].children[
          arry.length - 1
        ].style.display = "none";
      }
    }, time);
  }
}

function change_is_single_share(frm) {
  frappe.call({
    method:
      "tag_workflow.tag_workflow.doctype.job_order.job_order.change_is_single_share",
    args: {
      bid: frm.doc.bid,
      name: frm.doc.name,
    },
    callback: function(resp) {
      frm.doc.is_single_share = resp.message;
    },
  });
}

function staff_company_asterisks(frm) {
  if (
    frm.doc.__islocal != 1 &&
    frappe.boot.tag.tag_user_info.company_type == "Staffing"
  ) {
    if (frm.doc.company_type == "Non Exclusive") {
      remove_asterisks(frm);
    } else {
      frappe.db.get_value(
        "User",
        { name: frm.doc.owner },
        ["organization_type"],
        function(r) {
          if (
            r.organization_type != "Staffing" ||
            r == null ||
            frm.doc.owner != frappe.session.user
          ) {
            remove_asterisks(frm);
          }
        }
      );
    }
  }
}

function remove_asterisks(frm) {
  let myStringArray = [
    "company",
    "category",
    "select_job",
    "from_date",
    "rate",
    "to_date",
    "job_start_time",
    "estimated_hours_per_day",
    "job_site",
    "total_no_of_workers",
    "e_signature_full_name",
    "agree_to_contract",
  ];
  let arrayLength = myStringArray.length;
  for (let i = 0; i < arrayLength; i++) {
    frm.set_df_property(myStringArray[i], "reqd", 0);
  }
  frm.set_df_property("agree_to_contract", "label", "Agree To Contract");
  frm.set_df_property(
    "agree_to_contract",
    "description",
    "Agree To Contract Is Required To Save The Order"
  );
}

function assign_emp_button(frm) {
  frappe.db.get_value(
    "Assign Employee",
    { job_order: frm.doc.name, company: frappe.boot.tag.tag_user_info.company },
    ["name"],
    function(rr) {
      if (rr.name === undefined) {
        frm.add_custom_button(__("Claim and Recommend"), function() {
          assign_employees(frm);
        }).addClass("btn-primary");
      }
    }
  );
}
function check_claim_company(frm) {
  if (frm.doc.claim?.includes(frappe.boot.tag.tag_user_info.company))
    return true;
}

function set_exc_industry_company(frm) {
  if (sessionStorage.exc_joborder_company && frm.doc.__islocal) {
    frm.set_value("company", sessionStorage.exc_joborder_company);
    if (frm.doc.category && frm.doc.company) {
      sessionStorage.setItem("exc_joborder_company", "");

      frappe.call({
        method: "tag_workflow.tag_data.job_industry_type_add",
        args: {
          company: frm.doc.company,
          user_industry: frm.doc.category,
        },
      });
    }
  }
}
function order_buttons(frm) {
  if (
    frm.doc.order_status != "Completed" &&
    frappe.boot.tag.tag_user_info.company_type == "Staffing"
  ) {
    if (frm.doc.resumes_required) {
      if (frm.doc.total_no_of_workers > frm.doc.total_workers_filled) {
        assign_emp_button(frm);
      } else if (
        (frm.doc.claim &&
          !frm.doc.claim.includes(frappe.boot.tag.tag_user_info.company)) ||
        (frm.doc.staff_org_claimed &&
          !frm.doc.staff_org_claimed.includes(
            frappe.boot.tag.tag_user_info.company
          ))
      ) {
        frm.set_df_property("section_break_html3", "hidden", 0);
      }
    } else {
      claim_order_button(frm);
    }
  }
}

/*---------------------------------------------*/
function repeat_order(frm) {
  let condition =
    frm.doc.__islocal != 1 &&
    frm.doc.order_status == "Completed" &&
    frappe.boot.tag.tag_user_info.company_type == "Hiring";
  if (condition) {
    frm.add_custom_button(__("Repeat Order"), function() {
      if (frm.doc.bid == 0) {
        let comp;
        trigger_new_order(frm, 0, 1, comp);
      } else {
        repeat_hiring_dia(frm);
      }
    });
  } else {
    repeat_order_remaining_orgs(frm);
  }
  if (frm.doc.is_repeat == 1 && frm.doc.is_direct == 1) {
    frm.fields_dict['multiple_job_titles'].grid.wrapper.find('.grid-remove-rows').hide();
    frm.fields_dict['multiple_job_titles'].grid.wrapper.find('.btn-open-row').click(function() {
      $(".grid-delete-row").hide();
    });
  }
}

/*--------------hiring dialog----------------------*/
function repeat_hiring_dia(frm) {
  let dialog = new frappe.ui.Dialog({
    title: __("Repeat Order"),
    fields: [
      {
        fieldname: "direct",
        fieldtype: "Check",
        label: "Direct Order",
        onchange: function() {
          let direct = cur_dialog.get_value("direct");
          if (direct === 1) {
            cur_dialog.set_value("normal", 0);
            cur_dialog.fields_dict.direct_2.df.hidden = 0;
            cur_dialog.fields_dict.company.df.hidden = 0;
            cur_dialog.fields_dict.company.df.reqd = 1;
          } else {
            cur_dialog.fields_dict.direct_2.df.hidden = 1;
            cur_dialog.fields_dict.company.df.hidden = 1;
            cur_dialog.fields_dict.company.df.reqd = 0;
            cur_dialog.set_value("selected_companies", "");
          }
          cur_dialog.fields_dict.company.refresh();
          cur_dialog.fields_dict.direct_2.refresh();
          window.multiple_comp = [];
        },
      },
      {
        fieldname: "selected_companies",
        fieldtype: "Select",
        label: "Select Company",
        hidden: 1,
        options: frappe.boot.tag.tag_user_info.comps.join("\n"),
        default: frm.doc.staff_company,
      },
      { fieldname: "direct_1", fieldtype: "Column Break" },
      {
        fieldname: "normal",
        fieldtype: "Check",
        label: "Open Order",
        onchange: function() {
          let normal = cur_dialog.get_value("normal");
          if (normal == 1) {
            cur_dialog.set_value("direct", 0);
            cur_dialog.set_value("company", "");
          }
        },
      },
      { fieldname: "direct_2", fieldtype: "Section Break", hidden: 1 },
      {
        fieldname: "company",
        fieldtype: "Select",
        label: "Select Company",
        options: get_company_list(frm),
        onchange: function() {
          cur_dialog.set_df_property("selected_companies", "hidden", 0);
          let direct = cur_dialog.get_value("company");
          let existed_company = cur_dialog.get_value("selected_companies");
          if (
            existed_company === undefined ||
            (existed_company.length == 1 && direct)
          ) {
            cur_dialog.set_value("selected_companies", direct);
            if (direct) {
              window.multiple_comp.push(direct);
            }
          } else if (!existed_company.includes(direct) && direct) {
            let new_value = existed_company + ", " + direct;
            cur_dialog.set_value("selected_companies", new_value);
            window.multiple_comp.push(direct);
          }
        },
      },
      {
        fieldname: "selected_companies",
        fieldtype: "Data",
        label: "Selected Companies",
        default: " ",
        read_only: 1,
        hidden: 1,
      },
    ],
  });

  dialog.set_primary_action(__("Proceed"), function() {
    let values = dialog.get_values();
    let dia_cond = values.direct || values.normal;
    if (dia_cond) {
      trigger_new_order(
        frm,
        values.direct,
        values.normal,
        values.selected_companies
      );
      dialog.hide();
    } else {
      frappe.msgprint({
        message: __("Please mark your selection"),
        title: __("Repeat Order"),
        indicator: "red",
      });
    }
  });
  dialog.set_secondary_action(function() {
    dialog.hide();
  });
  dialog.set_secondary_action_label("Cancel");
  dialog.show();
}

/*-------------------------------------------------------------*/
function repeat_order_remaining_orgs(frm) {
  if (
    frm.doc.__islocal != 1 &&
    frm.doc.order_status == "Completed" &&
    (frappe.boot.tag.tag_user_info.company_type == "Exclusive Hiring" ||
      (frappe.boot.tag.tag_user_info.company_type == "Staffing" &&
        frappe.boot.tag.tag_user_info.exces.includes(frm.doc.company)))
  ) {
    trigger_exc_stf_odr(frm);
  }
}

function trigger_exc_stf_odr(frm) {
  frm.add_custom_button(__("Repeat Order"), function() {
    frappe.confirm(
      "Are you sure you want to proceed?",
      () => {
        trigger_new_order(frm, 1, 0, "");
      },
      () => {
        // action to perform if No is selected
      }
    );
  });
}

function trigger_new_order(frm, direct, normal, company) {
  let doc = frm.doc;
  let no_copy_list = [
    "name",
    "amended_from",
    "amendment_date",
    "cancel_reason",
  ];
  let newdoc = frappe.model.get_new_doc(doc.doctype, doc, "");
  for (let key in doc) {
    // dont copy name and blank fields
    let df = frappe.meta.get_docfield(doc.doctype, key);
    let from_amend = 0;
    if (
      df &&
      !key.startsWith("__") &&
      !in_list(no_copy_list, key) &&
      !(df && !from_amend && cint(df.no_copy) == 1)
    ) {
      let value = doc[key] || [];
      if (frappe.model.table_fields.includes(df.fieldtype)) {
        for (let i = 0, j = value.length; i < j; i++) {
          let d = value[i];
          frappe.model.copy_doc(d, from_amend, newdoc, df.fieldname);
        }
      } else {
        newdoc[key] = doc[key];
      }
    }
  }

  newdoc.multiple_job_titles.forEach((row)=>{
    frappe.model.set_value(row.doctype, row.name, "worker_filled", 0);
  });

  let user = frappe.session.user;
  newdoc.__islocal = 1;
  newdoc.company = frm.doc.company;
  newdoc.is_direct = direct;
  newdoc.docstatus = 0;
  newdoc.owner = user;
  newdoc.creation = "";
  newdoc.modified_by = user;
  newdoc.modified = "";
  newdoc.is_repeat = 1;
  newdoc.repeat_from = frm.doc.name;
  newdoc.repeat_from_company = frm.doc.company;
  newdoc.repeat_staff_company =
    window.multiple_comp.join("~").length > 0
      ? window.multiple_comp.join("~")
      : company;
  newdoc.from_date = "";
  newdoc.to_date = "";
  newdoc.staff_org_claimed = "";
  newdoc.order_status = "Upcoming";
  newdoc.staff_company = company;
  newdoc.staff_company2 = newdoc.repeat_staff_company;
  newdoc.repeat_old_worker = frm.doc.total_no_of_workers;
  newdoc.total_no_of_workers = frm.doc.total_no_of_workers;
  newdoc.bid = 0;
  newdoc.claim = "";
  newdoc.total_workers_filled = 0;
  frappe.set_route("form", newdoc.doctype, newdoc.name);
}

function multiple_job_titles_repeat(frm, newdoc, normal){
  if(normal){
    newdoc.multiple_job_titles.forEach((row)=>{
      frappe.model.set_value(row.doctype, row.name, "worker_filled", 0);
    });
    newdoc.worker_filled = 0;
    newdoc.total_workers_filled = 0;
  }else{
    newdoc.worker_filled = frm.doc.total_workers_filled;
    newdoc.total_workers_filled = frm.doc.total_workers_filled;
  }
  return newdoc
}

function get_company_list(frm) {
  let existed_comp;
  if (cur_dialog) {
    existed_comp = cur_dialog.get_value("selected_companies");
  }
  let company = "\n";
  frappe.call({
    method:
      "tag_workflow.tag_workflow.doctype.job_order.job_order.claim_data_list",
    args: { job_order_name: frm.doc.name, exist_comp: existed_comp },
    async: 0,
    callback: function(r) {
      company += r.message;
    },
  });
  return company;
}

function update_order_status(frm) {
  if (frm.doc.__islocal != 1) {
    frappe.call({
      method: "tag_workflow.tag_data.update_order_status",
      args: { job_order_name: frm.doc.name },
    });
  }
}

function set_custom_days(frm) {
  let selected = "";
  let data = frm.doc.select_days.length;
  for (let i = 0; i < data; i++) {
    if (frm.doc.select_days[i] != "None") {
      selected = selected + frm.doc.select_days[i].days + ", ";
    }
  }
  frm.set_value("selected_days", selected.slice(0, -2));
}

function validate_email_number(frm) {
  let email = frm.doc.email;
  if (
    email &&
    (email.length > 120 || !frappe.utils.validate_type(email, "email"))
  ) {
    frappe.msgprint({
      message: __("Not A Valid Email"),
      indicator: "red",
    });
    frappe.validated = false;
  }
  let phone = frm.doc.phone_number;
  if (phone) {
    if (!validate_phone(phone)) {
      frappe.msgprint({
        message: __("Invalid Phone Number!"),
        indicator: "red",
      });
      frappe.validated = false;
    } else {
      frm.set_value("phone_number", validate_phone(phone));
    }
  }
}

// updating job order status messages for staffing side.
function update_section(frm) {
  if (frm.doc.__islocal != 1) {
    frappe.call({
      method: "tag_workflow.tag_data.update_section_status",
      args: {
        company: frappe.boot.tag.tag_user_info.company,
        jo: frm.doc.name,
      },
      callback: function(r) {
        if (r.message) {
          if (r.message == "Canceled") {
            frm.set_df_property(
              "html_3",
              "options",
              "<h3>Job Order Canceled.</h3>"
            );
          }
          if (r.message == "Complete") {
            frm.set_df_property(
              "html_3",
              "options",
              "<h3>Job Order Closed.</h3>"
            );
          } else if (r.message == "Approved") {
            frm.set_df_property(
              "html_3",
              "options",
              "<h3>Please submit an invoice to complete the order.</h3>"
            );
          } else if (r.message == "Approval Request") {
            frm.set_df_property(
              "html_3",
              "options",
              "<h3>Timesheet available for approval.</h3>"
            );
          }
        }
      },
    });
  }
}

// updating job order status messages for hiring side.
function hiring_sections(frm) {
  if (
    frm.doc.__islocal != 1 &&
    ["Hiring", "Exclusive Hiring"].includes(frappe.boot.tag.tag_user_info.company_type)
  ) {
    frappe.call({
      method:
        "tag_workflow.tag_workflow.doctype.job_order.job_order.hiring_diff_status",
      args: {
        job_order_name: frm.doc.name,
      },
      callback: function(r) {
        if (r.message) {
          if (r.message == "Completed") {
            frm.toggle_display("hiring_section_break", 1);
            frm.set_df_property(
              "hiring_html",
              "options",
              "<h3>Job Order Closed</h3>"
            );
          } else if (r.message == "Invoice") {
            frm.toggle_display("hiring_section_break", 1);
            frm.set_df_property(
              "hiring_html",
              "options",
              "<h3>Please review invoice.</h3>"
            );
          } else if (r.message == "Timesheet") {
            frm.toggle_display("hiring_section_break", 1);
            frm.set_df_property(
              "hiring_html",
              "options",
              "<h3>Timesheets require review</h3>"
            );
          }
        } else {
          hiring_review_box(frm);
        }
      },
    });
  }
}
function hiring_review_box(frm) {
  if (frm.doc.staff_org_claimed) {
    frappe.db.get_value(
      "Assign Employee",
      { job_order: frm.doc.name },
      "name",
      function(r1) {
        if (r1.name) {
          frm.toggle_display("hiring_section_break", 1);
          frm.set_df_property(
            "hiring_html",
            "options",
            "<h3>Employees have been assigned. Please submit their timesheets.</h3>"
          );
        } else if (frm.doc.bid > 0) {
          frm.toggle_display("hiring_section_break", 1);
          frm.set_df_property(
            "hiring_html",
            "options",
            "<h3>Please review submitted claims.</h3>"
          );
        }
      }
    );
  } else if (frm.doc.bid > 0) {
    frm.toggle_display("hiring_section_break", 1);
    frm.set_df_property(
      "hiring_html",
      "options",
      "<h3>Please review submitted claims.</h3>"
    );
  }
}

function add_id(frm) {
  if (frm.doc.order_status == "Completed") {
    $('[data-fieldname="rate"]').attr("id", "_rate");
    non_claims(frm);
  }
  if (frm.doc.__islocal == 1) {
    $('[data-fieldname="rate"]').attr("id", "div_rate");
  }
}

function no_of_workers_changed(frm) {
  if (frm.doc.claim) {
    if (frm.doc.resumes_required == 0) {
      frappe.call({
        method:
          "tag_workflow.tag_workflow.doctype.job_order.job_order.no_of_workers_changed",
        args: {
          doc_name: frm.doc.name,
        },
      });
    } else {
      frappe.call({
        method:
          "tag_workflow.tag_workflow.doctype.job_order.job_order.change_assigned_emp",
        args: {
          doc_name: frm.doc.name,
        },
      });
    }
  }
}

function non_claims(frm) {
  let found = false;
  let claim_comps = frm.doc.claim;
  if (claim_comps?.includes("~")) {
    claim_comps = frm.doc.claim.split("~");
    for (let i in claim_comps) {
      if (
        frappe.boot.tag.tag_user_info.company_type == "Staffing" &&
        frappe.boot.tag.tag_user_info.comps.includes(claim_comps[i])
      ) {
        frm.toggle_display("section_break_html1", 0);
        found = true;
        break;
      }
    }
  } else if (
    frappe.boot.tag.tag_user_info.company_type == "Staffing" &&
    frappe.boot.tag.tag_user_info.comps.includes(claim_comps)
  ) {
    frm.toggle_display("section_break_html1", 0);
    found = true;
  }
  if (
    !found &&
    frappe.boot.tag.tag_user_info.company_type == "Staffing" &&
    frm.doc.order_status == "Completed"
  ) {
    frm.toggle_display("section_break_html1", 1);
    frm.set_df_property(
      "html_2",
      "options",
      "<h3>This Job Order is closed and unclaimed by your company.</h3>"
    );
  }
}

function order_claimed(frm) {
  if (
    frm.doc.resumes_required == 0 &&
    frappe.boot.tag.tag_user_info.company_type == "Staffing" &&
    frm.doc.claim &&
    !frm.doc.claim.includes(frappe.boot.tag.tag_user_info.company)
  ) {
    frappe.call({
      method:
        "tag_workflow.tag_workflow.doctype.job_order.job_order.claim_headcount",
      args: {
        job_order: frm.doc.name,
      },
      callback: function(r) {
        if (r.message) {
          order_claimed_contd(r.message, frm);
        }
      },
    });
  }
}

function order_claimed_contd(result, frm) {
  if (
    result == frm.doc.total_no_of_workers &&
    frm.doc.order_status != "Completed"
  ) {
    frm.set_df_property("section_break_html1", "hidden", 0);
    frm.set_df_property(
      "html_2",
      "options",
      "<h3>This Job Order has reached its desired head count.</h3>"
    );
  }
}

function check_exist_order(r, frm, resolve, reject) {
  if (r.message == 1) {
    frappe.validated = true;
    let resp = "frappe.validated = false";
    resolve(resp);
    check_company_detail(frm);
  } else {
    return new Promise(function() {
      let pop_up;
      if (r.message[0].length >= 2) {
        pop_up =
          "Warning:" + r.message[1] + " are scheduled for the same timeframe. ";
      } else {
        pop_up =
          "Warning:" + r.message[1] + " is scheduled for the same timeframe. ";
      }
      let confirm_joborder1 = new frappe.ui.Dialog({
        title: __("Warning"),
        fields: [
          { fieldname: "save_joborder", fieldtype: "HTML", options: pop_up },
        ],
      });
      confirm_joborder1.no_cancel();
      confirm_joborder1.set_primary_action(__("Confirm"), function() {
        let resp = "frappe.validated = false";
        resolve(resp);
        check_company_detail(frm);
        confirm_joborder1.hide();
      });
      confirm_joborder1.set_secondary_action_label(__("Cancel"));
      confirm_joborder1.set_secondary_action(() => {
        const cancelReason = "Cancelled by user";
        reject(cancelReason);
        confirm_joborder1.hide();
      });
      confirm_joborder1.show();
      confirm_joborder1.$wrapper.find(".modal-dialog").css("width", "450px");
    });
  }
}

function check_company_complete_details(r, frm) {
  let msg = "";
  msg =
    "<b>Your company profile is incomplete! Please define the the following fields on the My Company Profile page before creating a Job Order.</b><br>";
  for (let i of r.message) {
    msg += "- " + i + "<br>";
  }
  frappe.msgprint({
    message: __(msg),
    title: __("Error"),
    indicator: "orange",
  });
  frm.set_value("company", "");
  frappe.validated = false;
}
function staffing_company_details(r) {
  let staff_message =
    "<b>Your company profile is incomplete! Please define the following fields on the My Company Profile page before submitting a claim for this Job Order.</b><br>";
  for (let i of r.message) {
    staff_message += "- " + i + "<br>";
  }
  frappe.msgprint({
    message: __(staff_message),
    title: __("Error"),
    indicator: "orange",
  });
  frappe.validated = false;
}
function staffing_create_job_order(frm) {
  frappe.call({
    method: "tag_workflow.tag_data.company_details",
    args: {
      company_name: frm.doc.company,
    },
    callback: function(r_hiring) {
      frappe.call({
        method: "tag_workflow.tag_data.staff_org_details",
        args: {
          company_details: frappe.boot.tag.tag_user_info.company,
        },
        callback: function(r_staff) {
          if (frm.doc.company) {
            check_hiring_staffing_values(r_hiring, r_staff, frm);
          }
        },
      });
    },
  });
}
function check_hiring_staffing_values(r_hiring, r_staff, frm) {
  let msg = "";
  if (r_hiring.message != "success" && r_staff.message != "success") {
    msg =
      "<b>Your company & " +
      frm.doc.company +
      "'s company profile is incomplete! Please define the following fields on the My Company Profile page before creating a Job Order.</b><br>";
    msg += "<b>" + frm.doc.company + "</b><br>";
    for (let l of r_hiring.message) {
      msg += "- " + l + "<br>";
    }
    msg += "<b>" + frappe.boot.tag.tag_user_info.company + "</b><br>";
    for (let m of r_staff.message) {
      msg += "- " + m + "<br>";
    }
  } else if (r_hiring.message != "success") {
    msg =
      "<b>" +
      frm.doc.company +
      "'s company profile is incomplete! Please define the following fields on the My Company Profile page before creating a Job Order.</b><br>";
    for (let j of r_hiring.message) {
      msg += "- " + j + "<br>";
    }
  } else if (r_staff.message != "success") {
    msg =
      "<b>Your company profile is incomplete! Please define the the following fields on the My Company Profile page before creating a Job Order.</b><br>";
    for (let k of r_staff.message) {
      msg += "- " + k + "<br>";
    }
  }
  if (msg != "") {
    frappe.msgprint({
      message: __(msg),
      title: __("Error"),
      indicator: "orange",
    });
    frm.set_value("company", "");
    frappe.validated = false;
  }
}

function availability_single_day(frm) {
  if (frm.doc.__islocal != 1 && frm.doc.job_order_duration == "1 Day") {
    frm.set_df_property("availability", "hidden", 1);
  }
}

function date_pick(frm) {
  if (frm.doc.__islocal == 1) {
    frm.doc.from_date = frappe.datetime.now_date();
    frm.doc.to_date = frappe.datetime.now_date();
    refresh_field("from_date");
    refresh_field("to_date");
    cur_frm.doc.from_date = undefined;
    cur_frm.doc.to_date = undefined;
    refresh_field("from_date");
    refresh_field("to_date");
  }
}
function claim_bar_data_hide(frm) {
  frm.toggle_display("section_break_html2", 1);
  if (frm.doc.resumes_required == 1) {
    frm.remove_custom_button("Claim and Recommend");
  }
}
function staff_assign_button_claims(frm, r) {
  if (r.message[0] == "success1") {
    let claims_app = r.message[2];
    let assigned_empls = r.message[1].employee_details.length;
    assign_emp_hide_button(frm);
    if (
      frm.doc.total_no_of_workers - frm.doc.total_workers_filled != 0 &&
      r.message != "success2" &&
      claims_app > assigned_empls &&
      !["Completed", "Canceled"].includes(frm.doc.order_status)
    ) {
      frm.add_custom_button(__("Assign Employee"), function() {
        frappe.set_route("Form", "Assign Employee", r.message[1].name);
      });
    } else if (
      frm.doc.total_no_of_workers - frm.doc.total_workers_filled > 0 &&
      r.message != "success2" &&
      frm.doc.resumes_required == 0 &&
      claims_app > assigned_empls &&
      !["Completed", "Canceled"].includes(frm.doc.order_status)
    ) {
      frm.add_custom_button(__("Assign Employee"), function() {
        staff_assign_redirect(frm);
      });
    } else {
      frm.remove_custom_button("Assign Employee");
    }
  } else if (r.message == "success2") {
    assign_emp_hide_button(frm);
    frm.remove_custom_button("Assign Employee");
  }
}

function staff_assign_button_resume(frm, r) {
  if (r.message == "success1" || r.message == "success2") {
    assign_emp_hide_button(frm);
    if (
      frm.doc.total_no_of_workers - frm.doc.total_workers_filled != 0 &&
      r.message != "success2" &&
      !["Completed", "Canceled"].includes(frm.doc.order_status)
    ) {
      frm.add_custom_button(__("Claim and Recommend"), function() {
        assign_employees(frm);
      }).addClass("btn-primary");
    } else {
      frm.remove_custom_button("Claim and Recommend");
    }
  }
}

function assign_emp_hide_button(frm) {
  frm.add_custom_button(
    __("Assigned Employees"),
    function() {
      assigned_emp(frm);
    },
    __("View")
  );
  $("[data-fieldname = assigned_employees]").attr("id", "assigned_inactive");
  let data = `<div class="my-2 p-3 border rounded cursor-pointer" style="display: flex;justify-content: space-between;"><p class="m-0 msg"> Assigned Employees  </p> </div>`;
  $("[data-fieldname = assigned_employees]").click(function() {
    if (
      $("[data-fieldname = assigned_employees]").attr("id") ==
      "assigned_inactive"
    ) {
      assigned_emp(frm);
    }
  });
  frm.set_df_property("assigned_employees", "options", data);
  frm.toggle_display("related_actions_section", 1);
}

function single_share_job(frm) {
  if (frm.doc.__islocal != 1 && frm.doc.is_single_share == 0) {
    frm.set_df_property("staff_company", "hidden", 1);
  }
  if (
    frm.doc.__islocal != 1 &&
    frappe.boot.tag.tag_user_info.company_type == "Staffing"
  ) {
    if (
      frm.doc.staff_company &&
      !frm.doc.staff_company.includes(frappe.boot.tag.tag_user_info.company)
    ) {
      frm.set_df_property("staff_company", "hidden", 1);
    }
  }
}
function job_profile_data(frm, data) {
  let profile_html = `<div class="table-responsive pb-2 pb-sm-0"><table class="assign-emp-popup assigne-employee-popup" ><th style="padding:0;width:16%">Job Title</th><th style="padding:0;width:16%">Employee Name</th><th style="padding:0;width:16%">Job Start Time</th><th style="padding:0;width:16%">Marked As</th><th style="padding:0;width:16%">Actions</th>`;
  for (let p in data) {
    let marked_as = "";
    if (data[p].no_show) {
      marked_as += " " + data[p].no_show;
    }
    if (data[p].non_satisfactory) {
      marked_as += " " + data[p].non_satisfactory;
    }
    if (data[p].dnr) {
      marked_as += " " + data[p].dnr;
    }

    if (data[p].replaced) {
      marked_as += " Replaced";
    }

    if (data[p].removed) {
      marked_as += " Removed";
    }

    profile_html += `<tr><td style="padding:0;width:16%">${data[p].job_title}</td><td style="padding:0;width:16%">${data[p].employee}</td><td style="padding:0;width:16%">${data[p].job_start_time}</td><td style="padding:0;width:16%">${marked_as}</td>`;

    if (marked_as != " Replaced" && !["Completed", "Canceled"].includes(frm.doc.order_status)) {
      profile_html += `
				<td class="replace" data-fieldname="replace" style="padding:0;width:16%">
					<button class="btn btn-primary btn-xs mt-2" onclick=redirect_job('${
            data[p].assign_name
          }','${data[p].child_name}')>Replace</button>
				</td>`;
    }
    profile_html += `</tr>`;
  }

  profile_html += `</div></table><style>th, td {padding-left: 50px;padding-right:50px;} input{width:100%;}</style>`;
  return profile_html;
}
function decreasing_employee(frm) {
  if (frm.doc.resumes_required == 1) {
    if (frm.doc.total_workers_filled > frm.doc.total_no_of_workers) {
      frappe.msgprint(
        frm.doc.total_workers_filled +
          " Employees are assigned to this order. Number of required workers must be greater than or equal to number of assigned employees. Please modify the number of workers required or work with the staffing companies to remove an assigned employee. "
      );
      frappe.validated = false;
      frm.set_value("total_no_of_workers", "");
    }
  } else {
    check_emp_claims(frm);
  }
}
function check_emp_claims(frm) {
  frappe.call({
    method:
      "tag_workflow.tag_workflow.doctype.job_order.job_order.claim_headcount",
    args: {
      job_order: frm.doc.name,
    },
    callback: function(r) {
      if (r.message.length > 0) {
        if (
          frm.doc.total_workers_filled == r.message &&
          frm.doc.total_no_of_workers < r.message
        ) {
          frappe.msgprint(
            frm.doc.total_workers_filled +
              " Employees are assigned to this order. Number of required workers must be greater than or equal to number of assigned employees. Please modify the number of workers required or work with the staffing companies to remove an assigned employee. "
          );
          frappe.validated = false;
          frm.set_value("total_no_of_workers", "");
        } else if (
          frm.doc.total_workers_filled != r.message &&
          frm.doc.total_no_of_workers < r.message
        ) {
          workers_claimed_change(frm);
        }
      }
    },
  });
}
function workers_claimed_change(frm) {
  let new_no = frm.doc.total_no_of_workers;
  frm.set_value("total_no_of_workers", "");
  frappe.call({
    method:
      "tag_workflow.tag_workflow.doctype.job_order.job_order.workers_required_order_update",
    args: {
      doc_name: frm.doc.name,
    },
    callback: function(rm) {
      frappe.db.get_value(
        "Job Order",
        { name: frm.doc.name },
        [
          "company",
          "select_job",
          "from_date",
          "to_date",
          "total_no_of_workers",
          "per_hour",
          "total_workers_filled",
        ],
        function(r) {
          let job_data = rm.message;
          let profile_html = `<table class="table-responsive"><th>Claim No.</th><th>Staffing Company</th><th>Claims</th><th>Claims Approved</th><th>Modifiy Claims Approved</th>`;
          for (let p in job_data) {
            profile_html += `<tr>
				<td>${job_data[p].name}</td>
				<td style="margin-right:20px;" id="${job_data[p].claims}">${job_data[p].staffing_organization}</td>
				<td>${job_data[p].staff_claims_no}</td>
				<td>${job_data[p].approved_no_of_workers}</td>
				<td><input type="number" id="${job_data[p].name}" min="0" max=${job_data[p].staff_claims_no}></td>
				</tr>`;
          }
          profile_html += `</table><style>th, td {
					padding: 10px;
					} input{width:100%;}
				</style>`;

          let modified_pop_up = new frappe.ui.Dialog({
            title: "Update Wokers",
            fields: [
              {
                fieldname: "html_workers1",
                fieldtype: "HTML",
                options:
                  "<label>No. Of Workers Required:</label>" +
                  frm.doc.total_no_of_workers,
              },
              { fieldname: "inputdata2", fieldtype: "Section Break" },
              {
                fieldname: "staff_companies1",
                fieldtype: "HTML",
                options: profile_html,
              },
            ],
            primary_action: function() {
              modified_pop_up.hide();
              let data_len = job_data.length;
              let l = 0;
              let dict = {};

              dict = update_claims(data_len, l, dict, job_data, r, new_no);
              if (Object.keys(dict.dict).length > 0 && dict.valid1 != "False") {
                frappe.call({
                  method:
                    "tag_workflow.tag_workflow.doctype.job_order.job_order.update_new_claims",
                  args: {
                    my_data: dict.dict,
                    doc_name: frm.doc.name,
                  },
                  callback: function(r2) {
                    if (r2.message == 1) {
                      frm.set_value("total_no_of_workers", new_no);
                      frm.save();
                      setTimeout(function() {
                        window.location.href =
                          "/app/job-order/" + listview.data[0].job_order;
                      }, 10000);
                    } else if (r2.message == 0) {
                      setTimeout(function() {
                        window.location.href = "/app/job-order/" + frm.doc.name;
                      }, 1000);
                    }
                  },
                });
              }
            },
          });
          modified_pop_up.show();
        }
      );
    },
  });
}

function update_claims(data_len, l, dict, job_data, r, new_no) {
  let valid1 = "";
  let total_count = 0;
  for (let i = 0; i < data_len; i++) {
    let y = document.getElementById(job_data[i].name).value;
    if (y.length == 0) {
      total_count += job_data[i].approved_no_of_workers;
      continue;
    }
    y = parseInt(y);
    l = parseInt(l) + parseInt(y);
    if (y == job_data[i].approved_no_of_workers) {
      frappe.msgprint({
        message: __(
          "No Of Workers Are Same that previously assigned For:" +
            job_data[i].name
        ),
        title: __("Error"),
        indicator: "red",
      });
      valid1 = "False";

      setTimeout(function() {
        location.reload();
      }, 5000);
    } else if (y < 0) {
      frappe.msgprint({
        message: __(
          "No Of Workers Can't Be less than 0 for:" +
            job_data[i].staffing_organization
        ),
        title: __("Error"),
        indicator: "red",
      });
      valid1 = "False";

      setTimeout(function() {
        location.reload();
      }, 5000);
    } else if (y > job_data[i].name) {
      frappe.msgprint({
        message: __("No Of Workers Exceed For:" + job_data[i].name),
        title: __("Error"),
        indicator: "red",
      });
      valid1 = "False";

      setTimeout(function() {
        location.reload();
      }, 5000);
    } else if (l > new_no) {
      frappe.msgprint({
        message: __("No Of Workers Exceed For Than required "),
        title: __("Error"),
        indicator: "red",
      });
      valid1 = "False";

      setTimeout(function() {
        location.reload();
      }, 5000);
    } else {
      total_count += y;
      y = { approve_count: y };
      dict[job_data[i].name] = y;
    }
  }
  if (total_count > r["total_no_of_workers"]) {
    frappe.msgprint({
      message: __(
        "No Of Workers Exceed For Than required",
        total_count,
        r["total_no_of_workers"],
        r["total_workers_filled"],
        r["total_no_of_workers"] - r["total_workers_filled"]
      ),
      title: __("Error"),
      indicator: "red",
    });
    valid1 = "False";

    setTimeout(function() {
      location.reload();
    }, 5000);
  }
  return { dict, valid1 };
}

frappe.get_modal = function(title, content) {
  return $(`<div class="modal fade" style="overflow: auto;" tabindex="-1">
		<div class="modal-dialog">
			<div class="modal-content">
				<div class="modal-header">
					<div class="fill-width flex title-section">
						<span class="indicator hidden"></span>
						<h4 class="modal-title">${title}</h4>
					</div>
					<div class="modal-actions">
						<button class="btn btn-modal-minimize btn-link hide">
							${frappe.utils.icon("collapse")}
						</button>
						<button class="btn btn-modal-close btn-link" data-dismiss="modal" id="joborder-close-dialog">
							${frappe.utils.icon("close-alt", "sm", "close-alt")}
						</button>
					</div>
				</div>
				<div class="modal-body ui-front" id="joborder-confirm-popup">${content}</div>
				<div class="modal-footer hide">
					<div class="custom-actions"></div>
					<div class="standard-actions">
						<button type="button" class="btn btn-secondary btn-sm hide btn-modal-secondary">
						</button>
						<button type="button" class="btn btn-primary btn-sm hide btn-modal-primary">
							${__("Confirm")}
						</button>
					</div>
				</div>
			</div>
		</div>
	</div>`);
};
function prevent_click_event(frm) {
  if (
    frm.doc.__islocal != 1 &&
    frappe.boot.tag.tag_user_info.company_type == "Staffing"
  ) {
    $('[data-doctype="Item"]').on("click", function(e) {
      remove_href("Item", e);
    });
    $('[data-doctype="Industry Type"]').on("click", function(e) {
      remove_href("Industry Type", e);
    });
    $('[data-doctype="Job Site"]').on("click", function(e) {
      remove_href("Job Site", e);
    });
  }
}
function remove_href(doc_name, e) {
  e.preventDefault();
  Array.from($('[data-doctype="' + doc_name + '"]')).forEach((_field) => {
    _field.href = "#";
  });
}

function no_of_worker_repeat(frm) {
  if (
    frm.doc.__islocal == 1 &&
    frm.doc.resumes_required == 0 &&
    frm.doc.is_repeat &&
    frm.doc.total_no_of_workers &&
    frm.doc.is_direct
  ) {
    frm.call({
      method: "repeat_no_of_workers",
      args: {
        job_order: frm.doc.repeat_from,
        staff_comp: frm.doc.staff_company2,
        no_of_worker: frm.doc.total_no_of_workers,
      },
      async: 0,
      callback: (res) => {
        if (res.message == "failed") {
          frappe.msgprint(
            "Number of workers cannot be less than number of approved workers."
          );
          frappe.validated = false;
        }
      },
    });
  }
}

function cancel_or_delete_jo(frm) {
  if (frappe.boot.tag.tag_user_info.company_type == "Staffing") {
    if(frm.doc.order_status=='Canceled'){
      frm.toggle_display("section_break_html2", 1);
      frm.set_df_property(
        "html_3",
        "options",
        "<h3>Job Order Canceled</h3>"
      );
    }else{
      show_claim_bar(frm);
    }
  }
  if (frm.doc.__islocal == 1) {
    cancel_joborder(frm);
  } else {
    job_order_button(frm)
    timer_value(frm);
  }
}

function job_order_button(frm) {
  frappe.db.get_value(
    "User",
    { name: frm.doc.owner },
    ["organization_type"],
    function(r) {
      if (
        ['Hiring', 'Exclusive Hiring', 'TAG'].includes(frappe.boot.tag.tag_user_info.company_type) ||
        (frappe.boot.tag.tag_user_info.company_type == "Staffing" && frm.doc.company_type == "Exclusive" && r.organization_type == "Staffing")
      ) {
        if(frm.doc.claim){
          job_order_cancel_button(frm);
        }else{
          frm.add_custom_button(__("Delete"), function() {
            cancel_job_order(frm);
          });
        }
        if (frm.doc.order_status != "Completed") {
          $('[data-fieldname="rate"]').attr("id", "div_rate");
        }
      }
    }
  );
}

function job_order_cancel_button(frm){
  if(!["Completed", "Canceled"].includes(frm.doc.order_status)){
    frm.add_custom_button(__("Cancel"), function() {
      return new Promise(function(resolve, reject) {
        const d = frappe.confirm(
          "Are you sure you want to cancel this Job Order?",
          function() {
            let resp = "frappe.validated = false";
            resolve(resp);
            cancelling_jo(frm);
          },
          function() {
            const rejectionReason = "Job Order cancellation was rejected.";
            reject(rejectionReason);
          }
        );
        d.standard_actions
          .find(".btn-modal-primary")
          .attr("id", "cancel-confirm-button");
        d.standard_actions
          .find(".btn-modal-secondary")
          .attr("id", "cancel-discard-button");
      });
    });
  }
}

function cancelling_jo(frm){
  frm.call({
    'method': 'cancel_job_order',
    'args': {
      'job_order': frm.doc.name,
      'user': frappe.session.user,
      'approved_claims': frm.doc.staff_org_claimed?frm.doc.staff_org_claimed:''
    },
    'callback': ()=>{
      frappe.msgprint('Job Order Canceled Successfully');
      setTimeout(()=>{
        window.location.reload();
      }, 3000);
    }
  });
}

function reduce_headcount_remove_employee_without_resume_popup(frm,job_category,job_start_time,row_name) {
  frappe.call({
    method: "tag_workflow.tag_data.assigned_employee_data_title_wise",
    args: {
      job_order: frm.doc.name,
      job_category: job_category,
      job_start_time: job_start_time,
      row_name: row_name
    },
    callback: function(rm) {
      let data=rm.message[0];
      let actual_headcounts=rm.message[1][0]
      let actual_approved=rm.message[1][1]
      let current_stored_remove_employees=JSON.parse(localStorage.getItem("test_employee_removed_"+frm.doc.name))
      let profile_html=`<h5>You are attempting to reduce the number of workers below the number required. Please select which workers to remove in order to reduce the headcount:</h5><br><table class="assign-emp-popup" style="width: 100%;"><th style="padding:0;width:20%">Job Title</th><th style="padding:0;width:20%">Employee Name</th><th style="padding:0;width:20%">Job Start Time</th><th style="padding:0;width:20%">Est. Daily Hours</th><th style="padding:0;width:20%">Staffing Company</th>`;
      current_stored_remove_employees[row_name]=[]
      localStorage.setItem("test_employee_removed_"+frm.doc.name,JSON.stringify(current_stored_remove_employees))

      for(let p in data) {
        profile_html+=`<tr>
          <td style="padding:0;width:20%">${data[p].job_title}</td>
					<td style="padding:0;width:20%">${data[p].employee}</td>
          <td style="padding:0;width:20%">${data[p].job_start_time}</td>
          <td style="padding:0;width:20%">${data[p].estimated_hours_per_day}</td>
					<td style="padding:0;width:20%" >${data[p].staff_company}</td>
          <td class="remove_employee" data-fieldname="remove_employee" style="padding:2px;width:14%">
					<button id=remove-btn-${data[p].employee_id}-${data[p].job_title.replace(/[\s.]/g,'_')}-${data[p].job_start_time} class="btn btn-primary btn-xs mt-2" onclick="toogle_remove_button('${data[p].assign_name
          }','${frm.doc.name}','${data[p].employee_id}','${data[p].removed}','${data[p].job_title
          }','${data[p].job_start_time}','${row_name}')">${data[p].removed=="0"? "Remove":"Unremove"
          }</button>
				</td>
				</tr>`;
      }
      profile_html+=`</table><style>th, td {padding-left: 50px;padding-right:50px;} input{width:100%;}</style>`;

      let dialog=new frappe.ui.Dialog({
        title: __(`<span class="indicator orange"></span>Error`),
        fields: [
          {
            fieldname: "staff_companies",
            fieldtype: "HTML",
            options: profile_html,
          },
        ],
      });

      dialog.no_cancel();
      dialog.$wrapper.on("hidden.bs.modal",function() {
        $("[data-fieldname = assigned_employees_hiring]").attr(
          "id",
          "approved_inactive"
        );
      });
      dialog.set_primary_action(__("Save"),function() {
        dialog.hide();
        dialog_closed_unexpect=false
        frappe.validated = true
        current_stored_remove_employees=JSON.parse(localStorage.getItem("test_employee_removed_"+frm.doc.name))

        if(actual_approved-current_stored_remove_employees[row_name].length<=0) {
          frappe.msgprint(__("Cannot remove all employees. Need to keep at least one employee"));
          current_stored_remove_employees=JSON.parse(localStorage.getItem("test_employee_removed_"+frm.doc.name))
          current_stored_remove_employees[row_name]=[]
          localStorage.setItem("test_employee_removed_"+frm.doc.name,JSON.stringify(current_stored_remove_employees))
          localStorage.setItem("employee_removed_"+frm.doc.name,JSON.stringify([]))
          frappe.model.set_value('Multiple Job Titles',row_name,"no_of_workers",actual_headcounts);
        }
        else {
          frappe.model.set_value('Multiple Job Titles',row_name,"no_of_workers",actual_approved-current_stored_remove_employees[row_name].length);
          frappe.model.set_value('Multiple Job Titles',row_name,"worker_filled",actual_approved-current_stored_remove_employees[row_name].length);
        }
        frm.refresh_fields('multiple_job_titles')
      });
      dialog.set_secondary_action_label(__("Cancel"));
      dialog.set_secondary_action(() => {
        dialog.hide();
        dialog_closed_unexpect=false
        current_stored_remove_employees=JSON.parse(localStorage.getItem("test_employee_removed_"+frm.doc.name))
        current_stored_remove_employees[row_name]=[]
        localStorage.setItem("test_employee_removed_"+frm.doc.name,JSON.stringify(current_stored_remove_employees))
        localStorage.setItem("employee_removed_"+frm.doc.name,JSON.stringify([]))
        frappe.model.set_value('Multiple Job Titles',row_name,"no_of_workers",actual_headcounts);
        frm.refresh_fields('multiple_job_titles')
      });
      let dialog_closed_unexpect=true
      dialog.$wrapper.on('hidden.bs.modal',() => {
        if(dialog_closed_unexpect) {
          frappe.model.set_value('Multiple Job Titles',row_name,"no_of_workers",actual_headcounts);
          frm.refresh_fields('multiple_job_titles')
        }
      });
      if(data.length) {
        dialog.add_custom_action(
          __(
            '<svg class="icon icon-sm"><use href="#icon-printer"></use></svg>'
          ),
          () => {
            let w=window.open(
              frappe.urllib.get_full_url(
                "/api/method/tag_workflow.tag_data.print_assigned_emp?company=hiring&job_order="+
                frm.doc.name
              )
            );
            if(!w) {
              frappe.msgprint(__("Please enable pop-ups"));
            }
          }
        );
      }
      if(
        $("[data-fieldname = assigned_employees_hiring]").attr("id")==
        "approved_inactive"
      ) {
        dialog.show();
        frappe.validated = false
        dialog.$wrapper.find(".modal-dialog").css("max-width","880px");
        dialog.$wrapper
          .find("textarea.input-with-feedback.form-control")
          .css("height","108px");
        $("[data-fieldname = assigned_employees_hiring]").attr(
          "id",
          "approved_active"
        );
      }
    },
  });
}

function reomve_emploees_after_save_from_hiring(frm) {
  let all_removed_emp_from_hiring=JSON.parse(localStorage.getItem("test_employee_removed_"+frm.doc.name))
  let test_remove_unremove_job_data_hiring=[].concat(...Object.values(all_removed_emp_from_hiring));
  let remove_unremove_job_data_hiring=[]
  for(let i in test_remove_unremove_job_data_hiring) {
    let data=test_remove_unremove_job_data_hiring[i].split("~")
    remove_unremove_job_data_hiring.push([data[0],frm.doc.name,1,data[1],data[2]])
  }
  if(remove_unremove_job_data_hiring.length) {
    frappe.call({
      method: "tag_workflow.tag_data.remove_emp_from_order_hiring",
      freeze: true,
      freeze_message: "<p><b>please wait while updating data...</b></p>",
      args: {
        list_array_removed_emps: remove_unremove_job_data_hiring,
      },
      callback: function(rm) {
        if(rm.message=="removed")
          localStorage.setItem("employee_removed_"+frm.doc.name,JSON.stringify([]))
        localStorage.setItem("test_employee_removed_"+frm.doc.name,JSON.stringify({}))
        let total_approved=get_total_approved_counts();

        if(frm.doc.resumes_required==1) {
          update_assign_employee_with_resume_required(remove_unremove_job_data_hiring,frm,total_approved);
        }
        else{
          update_claims_employee_assigned(remove_unremove_job_data_hiring,frm);
        }
      }
    });
  }

  function get_total_approved_counts() {
    let total_approved=0;
    for(let each in frm.doc.multiple_job_titles) {
      total_approved+=frm.doc.multiple_job_titles[each].worker_filled;
    }
    frappe.db.set_value('Job Order',frm.doc.name,'total_workers_filled',total_approved);
    frm.refresh_fields("total_workers_filled");
    return total_approved;
  }
}

function update_assign_employee_with_resume_required(remove_unremove_job_data_hiring,frm,total_approved) {
  frappe.call({
    method: "tag_workflow.tag_data.update_assign_emps_total_workers_reduced_head_count",
    freeze: true,
    freeze_message: "<p><b>please wait while updating data...</b></p>",
    args: {
      list_array_removed_emps: remove_unremove_job_data_hiring,
      job_order: frm.doc.name,
      total_no_of_workers: frm.doc.total_no_of_workers,
      total_workers_filled: total_approved
    },
    callback: function(rm1) {
      if(rm1.message=="removed")
        localStorage.setItem("employee_removed_"+frm.doc.name,JSON.stringify([]));
      localStorage.setItem("test_employee_removed_"+frm.doc.name,JSON.stringify({}));
    }
  });
}

function update_claims_employee_assigned(remove_unremove_job_data_hiring,frm) {
  frappe.call({
    method: "tag_workflow.tag_workflow.doctype.claim_order.claim_order.save_modified_claims_hiring_with_emp_assigned",
    freeze: true,
    freeze_message: "<p><b>please wait while updating data...</b></p>",
    args: {
      list_array_removed_emps: remove_unremove_job_data_hiring,
      job_order: frm.doc.name
    },
  });
  frappe.call({
    method: "tag_workflow.tag_data.update_assign_emps_total_workers_reduced_head_count_non_resume",
    freeze: true,
    freeze_message: "<p><b>please wait while updating data...</b></p>",
    args: {
      list_array_removed_emps: remove_unremove_job_data_hiring,
      job_order: frm.doc.name,
      total_no_of_workers: frm.doc.total_no_of_workers
    },
    callback: function(rm2) {
      if(rm2.message=="removed")
        localStorage.setItem("employee_removed_"+frm.doc.name,JSON.stringify([]));
      localStorage.setItem("test_employee_removed_"+frm.doc.name,JSON.stringify({}));
    }
  });
}

function reduce_headcount_remove_employee_with_resume_popup(frm,job_category,job_start_time,row_name) {
  frappe.call({
    method: "tag_workflow.tag_data.assigned_employee_data_title_wise",
    args: {
      job_order: frm.doc.name,
      job_category: job_category,
      job_start_time: job_start_time,
      row_name: row_name
    },
    callback: function(rm) {
      let data=rm.message[0];
      let actual_headcounts=rm.message[1][0]
      let actual_approved=rm.message[1][1]
      let current_stored_remove_employees=JSON.parse(localStorage.getItem("test_employee_removed_"+frm.doc.name))
      let profile_html=`<h5>You are attempting to reduce the number of workers below the number required. Please select which workers to remove in order to reduce the headcount:</h5><br><table class="assign-emp-popup" style="width: 100%;"><th style="padding:0;width:20%">Job Title</th><th style="padding:0;width:20%">Employee Name</th><th style="padding:0;width:20%">Job Start Time</th><th style="padding:0;width:20%">Est. Daily Hours</th><th style="padding:0;width:20%">Staffing Company</th><th>Resume</th>`;
      current_stored_remove_employees[row_name]=[]
      localStorage.setItem("test_employee_removed_"+frm.doc.name,JSON.stringify(current_stored_remove_employees))
      for(let p in data) {
        profile_html+=`<tr>
          <td style="padding:0;width:20%">${data[p].job_title}</td>
					<td style="padding:0;width:20%">${data[p].employee}</td>
          <td style="padding:0;width:20%">${data[p].job_start_time}</td>
          <td style="padding:0;width:20%">${data[p].estimated_hours_per_day}</td>
					<td style="padding:0;width:20%" >${data[p].staff_company}</td>
          <td class="download_employee_resume" data-fieldname="remove_employee_download" style="width:20%;text-align:center;">
            <button id=resume-download-btn-${data[p].employee_id}-${data[p].job_title.replace(/[\s.]/g,'_')}-${data[p].job_start_time} class="btn btn-xs mt-2" onclick="download_resume_reduce_headcount('${data[p].resume
          }')">Download</button>
				  </td>
          <td class="remove_employee" data-fieldname="remove_employee" style="padding:2px;width:14%">
					<button id=remove-btn-${data[p].employee_id}-${data[p].job_title.replace(/[\s.]/g,'_')}-${data[p].job_start_time} class="btn btn-primary btn-xs mt-2" onclick="toogle_remove_button('${data[p].assign_name
          }','${frm.doc.name}','${data[p].employee_id}','${data[p].removed}','${data[p].job_title
          }','${data[p].job_start_time}','${row_name}')">${data[p].removed=="0"? "Remove":"Unremove"
          }</button>
				</td>
				</tr>`;
      }
      profile_html+=`</table><style>th, td {padding-left: 50px;padding-right:50px;} input{width:100%;}</style>`;

      let dialog=new frappe.ui.Dialog({
        title: __(`<span class="indicator orange"></span>Error`),
        fields: [
          {
            fieldname: "staff_companies",
            fieldtype: "HTML",
            options: profile_html,
          },
        ],
      });

      dialog.no_cancel();
      dialog.$wrapper.on("hidden.bs.modal",function() {
        $("[data-fieldname = assigned_employees_hiring]").attr(
          "id",
          "approved_inactive"
        );
      });
      dialog.set_primary_action(__("Save"),function() {
        dialog.hide();
        dialog_closed_unexpect=false
        frappe.validated = true
        current_stored_remove_employees=JSON.parse(localStorage.getItem("test_employee_removed_"+frm.doc.name))
        if(actual_approved-current_stored_remove_employees[row_name].length<=0) {
          frappe.msgprint(__("Cannot remove all employees. Need to keep at least one employee"));
          current_stored_remove_employees=JSON.parse(localStorage.getItem("test_employee_removed_"+frm.doc.name))
          current_stored_remove_employees[row_name]=[]
          localStorage.setItem("test_employee_removed_"+frm.doc.name,JSON.stringify(current_stored_remove_employees))
          localStorage.setItem("employee_removed_"+frm.doc.name,JSON.stringify([]))
          frappe.model.set_value('Multiple Job Titles',row_name,"no_of_workers",actual_headcounts);
        }
        else {
          frappe.model.set_value('Multiple Job Titles',row_name,"no_of_workers",actual_approved-current_stored_remove_employees[row_name].length);
          frappe.model.set_value('Multiple Job Titles',row_name,"worker_filled",actual_approved-current_stored_remove_employees[row_name].length);
        }
        frm.refresh_fields('multiple_job_titles')
      });
      dialog.set_secondary_action_label(__("Cancel"));
      dialog.set_secondary_action(() => {
        dialog.hide();
        dialog_closed_unexpect=false
        current_stored_remove_employees=JSON.parse(localStorage.getItem("test_employee_removed_"+frm.doc.name))
        current_stored_remove_employees[row_name]=[]
        localStorage.setItem("test_employee_removed_"+frm.doc.name,JSON.stringify(current_stored_remove_employees))
        localStorage.setItem("employee_removed_"+frm.doc.name,JSON.stringify([]))
        frappe.model.set_value('Multiple Job Titles',row_name,"no_of_workers",actual_headcounts);
        frm.refresh_fields('multiple_job_titles')
      });
      if(data.length) {
        dialog.add_custom_action(
          __(
            '<svg class="icon icon-sm"><use href="#icon-printer"></use></svg>'
          ),
          () => {
            let w=window.open(
              frappe.urllib.get_full_url(
                "/api/method/tag_workflow.tag_data.print_assigned_emp?company=hiring&job_order="+
                frm.doc.name
              )
            );
            if(!w) {
              frappe.msgprint(__("Please enable pop-ups"));
            }
          }
        );
      }
      let dialog_closed_unexpect=true
      dialog.$wrapper.on('hidden.bs.modal',() => {
        if(dialog_closed_unexpect) {
          frappe.model.set_value('Multiple Job Titles',row_name,"no_of_workers",actual_headcounts);
          frm.refresh_fields('multiple_job_titles')
        }
      });
      if(
        $("[data-fieldname = assigned_employees_hiring]").attr("id")==
        "approved_inactive"
      ) {
        dialog.show();
        frappe.validated = false
        dialog.$wrapper.find(".modal-dialog").css("max-width","880px");
        dialog.$wrapper
          .find("textarea.input-with-feedback.form-control")
          .css("height","108px");
        $("[data-fieldname = assigned_employees_hiring]").attr(
          "id",
          "approved_active"
        );
      }
    },
  });
}

function reduce_headcount_with_approved_claim_popup(frm,row) {
  frappe.call({
    method:
      "tag_workflow.tag_workflow.doctype.claim_order.claim_order.get_total_approved_headcounts",
    args: {
      job_order: frm.doc.name,
      industry: row.category,
      start_time: row.job_start_time,
      select_job: row.select_job
    },
    callback: function(rm) {
      if(rm.message>row.no_of_workers) {
        frappe.call({
          method: "tag_workflow.tag_data.check_can_reduce_count",
          args: {
            job_start_time: row.job_start_time,
            row_name: row.name,
            start_date: frm.doc.from_date
          },
          callback: function(r) {
            if(r.message[0]==0 && frm.doc.order_status != "Upcoming") {
              frappe.msgprint("Can't reduce the headcount or remove the employee once shift started.")
              frappe.model.set_value('Multiple Job Titles',row.name,"no_of_workers",r.message[1]);
              frm.refresh_fields('multiple_job_titles')
              frappe.validated = false
            }
            else {
              frappe.call({
                method:
                  "tag_workflow.tag_workflow.doctype.claim_order.claim_order.modify_heads_reduce_headcount_hiring",
                args: {
                  doc_name: frm.doc.name,
                  job_title: row.select_job,
                  industry: row.category,
                  start_time: row.job_start_time
                },
                freeze: true,
                callback: function(rm) {
                  let profile_html=`<h5>You are attempting to reduce the number of workers below the number required. Please select which workers to remove in order to reduce the headcount:</h5><br><table id = "modify_headcount${row.name}" class="table-responsive"><tr id="header"><th>Claim No.</th><th>Staffing Company</th><th>Job Title</th><th>Start Time</th><th>Available Claims</th><th>Requested Claims</th><th>Claims Approved</th><th>Modify Claims Approved</th></tr>`;
                  profile_html=html_data_modify_claims(rm.message,profile_html);
                  profile_html+=`</table><style>th, td {padding: 10px;} input{width:100%;}</style>`;
                  let modified_pop_up=new frappe.ui.Dialog({
                    title: `<span class="indicator orange"></span>Error`,
                    id: "modify_headcount",
                    fields: [
                      {
                        fieldname: "staff_companies1",
                        fieldtype: "HTML",
                        options: profile_html,
                      },
                    ],
                  });

                  modified_pop_up.no_cancel()
                  modified_pop_up.set_primary_action(__("Save"),function() {
                    let headcount_table=document.getElementById(`modify_headcount${row.name}`);
                    modified_pop_up.hide();
                    frappe.validated = true
                    modified_pop_up_closed_unexpect=false
                    let updated_data=modified_headcount_warnings(headcount_table,row.no_of_workers,row.name,r.message[1]);
                    // let row_wise_data=[]
                    global_headcount_reduced_by_hiring[row.name]=updated_data
                  });

                  modified_pop_up.set_secondary_action_label(__("Cancel"));
                  modified_pop_up.set_secondary_action(() => {
                    modified_pop_up.hide();
                    modified_pop_up_closed_unexpect=true
                    global_headcount_reduced_by_hiring[row.name]={}
                  });
                  modified_pop_up.$wrapper.find(".modal-dialog").css("max-width","880px");
                  modified_pop_up.show();
                  frappe.validated = false
                  let modified_pop_up_closed_unexpect=true
                  modified_pop_up.$wrapper.on('hidden.bs.modal',() => {
                    $(`#modify_headcount${row.name}`).remove();
                    if(modified_pop_up_closed_unexpect) {
                      frappe.model.set_value('Multiple Job Titles',row.name,"no_of_workers",r.message[1]);
                      frm.refresh_fields('multiple_job_titles')
                    }
                  });
                },
              });
            }
          },
        });
      }
      else{
        let key = `${row.select_job}~${row.job_start_time}`
        global_headcount_reduce_without_approved_by_hiring[key] = row.no_of_workers
      }
    }
  })
}

function html_data_modify_claims(job_data,profile_html) {
  for(let p in job_data) {
    let time=job_data[p].start_time.split(":");

    profile_html+=`<tr>
      <td>${job_data[p].name}</td>
      <td style="margin-right:20px;">${job_data[p].staffing_organization}</td>
      <td>${job_data[p].job_title}</td>
      <td>${time[0].padStart(2,'0')+":"+time[1]}</td>
      <td style="text-align: center;">${job_data[p].no_of_workers_joborder}</td>
      <td style="text-align: center;">${job_data[p].staff_claims_no}</td>
      <td style="text-align: center;">${job_data[p].approved_no_of_workers}</td>
      <td><input type="number" min="0" max=${job_data[p].staff_claims_no}></td>
    </tr>`;
  }
  return profile_html;
}

function modified_headcount_warnings(headcount_table,no_of_workers,row_name,actual_headcounts) {
  let updated_data={};
  let total_approved=0;
  let valid=true;
  for(let row=1;row<headcount_table.rows.length;row++) {
    let data=headcount_table.rows[row];
    if(data?.id=="header") {continue;}
    let claim_name="~"+data.cells[0].innerText;
    let staffing_comp=data.cells[1].innerText;
    let job_title=data.cells[2].innerText;
    let start_time=data.cells[3].innerText;
    let staff_claims_no=parseInt(data.cells[5].innerText);
    let hiring_approved_no=parseInt(data.cells[6].innerText);
    let hiring_updated_no=data.cells[7].lastChild.value;

    hiring_updated_no=hiring_updated_no.length? parseInt(hiring_updated_no):hiring_approved_no;
    total_approved+=hiring_updated_no;

    if(hiring_updated_no>staff_claims_no) {
      valid=false;
      frappe.msgprint({
        message: __("<b>Row "+row+": <b>Claims approved cannot be greater than the no. of workers claimed by Staffing Company for: "+staffing_comp),
        title: __("Error"),
        indicator: "red",
      });
      frappe.model.set_value('Multiple Job Titles',row_name,"no_of_workers",actual_headcounts);
      frm.refresh_fields('multiple_job_titles')
    }
    else if(hiring_updated_no<0) {
      frappe.msgprint({
        message: __("Claim should be more than Zero."),
        title: __("Error"),
        indicator: "red",
      });
      frappe.model.set_value('Multiple Job Titles',row_name,"no_of_workers",actual_headcounts);
      frm.refresh_fields('multiple_job_titles')
    }
    else {
      let my_data={
        "job_title": job_title,
        "industry": data.cells[1].innerText,
        "start_time": start_time,
        "updated_approved_no": hiring_updated_no,
        "new_headcount": no_of_workers
      };
      updated_data=update_dict(updated_data,staffing_comp,my_data,claim_name)
    }
  }
  if(total_approved==0) {
    frappe.msgprint({
      message: __("Claim at least one employee."),
      title: __("Error"),
      indicator: "red",
    });
    frappe.model.set_value('Multiple Job Titles',row_name,"no_of_workers",actual_headcounts);
    frm.refresh_fields('multiple_job_titles')
    return [{},false]
  } else if((total_approved!=no_of_workers)) {
    frappe.msgprint({
      message: __("Total approved claim must be equal to "+no_of_workers),
      title: __("Error"),
      indicator: "red",
    });
    frappe.model.set_value('Multiple Job Titles',row_name,"no_of_workers",actual_headcounts);
    frm.refresh_fields('multiple_job_titles')
    return [{},false]
  }
  return [updated_data,valid]
}

function update_dict(dict,staffing_comp,my_data,claim_name="") {
  if(staffing_comp+claim_name in dict) {
    dict[staffing_comp+claim_name].push(my_data);
  } else {
    dict[staffing_comp+claim_name]=[]
    dict[staffing_comp+claim_name].push(my_data);
  }
  return dict;
}

function update_db_modified(updated_data,job_order) {
  if(updated_data[1]) {
    if(Object.keys(updated_data[0]).length>0) {
      frappe.call({
        method:
          "tag_workflow.tag_workflow.doctype.claim_order.claim_order.save_modified_claims_hiring",
        args: {
          "doc_name": job_order,
          "updated_data": updated_data[0],
        },
        async: 0,
        callback: function(r2) {
        },
      });
    }
  }
}


function update_db_modified_claims_without_approved(key,updated_data,job_order) {
  frappe.call({
    method:
      "tag_workflow.tag_workflow.doctype.claim_order.claim_order.save_modified_claims_hiring_without_approved",
    args: {
      "job_order": job_order,
      "no_of_workers_updated": updated_data,
      "key":key
    },
    async: 0,
    callback: function(r2) {
    },
  });
}


function modify_headcount_after_save_from_hiring(frm) {
  for(let each in global_headcount_reduce_without_approved_by_hiring) {
    if(global_headcount_reduce_without_approved_by_hiring[each]) {
      update_db_modified_claims_without_approved(each,global_headcount_reduce_without_approved_by_hiring[each],frm.doc.name);
      delete global_headcount_reduce_without_approved_by_hiring[each]
    }
  }
  for(let each in global_headcount_reduced_by_hiring) {
    if(global_headcount_reduced_by_hiring[each].length) {
      update_db_modified(global_headcount_reduced_by_hiring[each],frm.doc.name);
      delete global_headcount_reduced_by_hiring[each]
    }
  }
}