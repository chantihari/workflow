// // Copyright (c) 2021, SourceFuse and contributors
// // For license information, please see license.txt
let condition=localStorage.getItem("exclusive_case");
window.conf=0;
window.job_order=null;
let note="";
let company_branch=0;
let each_title_times={}
let employees_to_be_removed_row_no = []
let employees_to_be_removed_row_dict = {}
let redirected_company;
frappe.ui.form.on("Assign Employee",{
  refresh: function(frm,cdt,cdn) {
    $('[data-original-title="Menu"]').hide();
    frm.refresh_fields("employee_details")
    frappe.call({
      method: "frappe.client.get",
      args: {
        doctype: "Job Order",
        name: frm.doc.job_order,
      },
      async: 0,
      callback: function(response) {
        window.job_order=response.message;
      },
    });

    setTimeout(() => add_dynamic(frm),500);
    hide_class_code_rate(frm);
    select_employees(frm);
    setTimeout(function() {
      staffing_company(frm);
    },1000);
    $('[class="btn btn-primary btn-sm primary-action"]').show();
    $(".custom-actions.hidden-xs.hidden-md").show();
    window.onclick=function() {
      attachrefresh();
    };
    $(".form-footer").hide();
    if(frm.doc.__islocal==1) {
      $(".grid-add-row").attr("class","btn btn-xs btn-secondary grid1-row");
      if(!frm.doc.hiring_organization) {
        frappe.msgprint(
          __("Your Can't Assign Employee without job order detail")
        );
        frappe.validated=false;
        setTimeout(() => {
          frappe.set_route("List","Job Order");
        },5000);
      }
      $('[data-label="Save"]').show();
    } else {
      assigned_direct(frm);
    }
    staff_comp(frm);
    update_claim_approve(frm);
    render_table(frm);
    approved_employee(frm);
    back_job_order_form(frm);
    $('[data-fieldname="company"]').css("display","block");
    child_table_label();
    render_tab(frm);
    set_payrate_field(frm);
    window.conf=0;
    add_notes_button(frm);
    add_notes(frm);
    set_multiple_title_filters(frm)
    frm.fields_dict.multiple_job_title_details.grid.grid_buttons.addClass('hidden');
    create_global_time_object(frm);
    setTimeout(function() {
      create_global_time_object(frm);
    },3000);
    multiple_job_title_details_update_data(frm)
    if(frm.doc.__islocal!=1) {
      for(let each_data of frm.doc.employee_details) {
        set_multiple_time_filters(frm,cdt,cdn,each_data);
      }
    }
    frm.fields_dict["multiple_job_title_details"].grid.cannot_add_rows=true;
    frm.fields_dict["multiple_job_title_details"].refresh();
    frm.fields_dict["multiple_job_title_details"].grid.wrapper
      .find(".btn-open-row")
      .click(function() {
        $(".row-actions").hide();
        $(".grid-footer-toolbar").hide();
      });

    if (
      ["Hiring", "Exclusive Hiring"].includes(
        frappe.boot.tag.tag_user_info.company_type
      )
    ) {
      $("body").addClass("hiring-section");
    }
    if(["Completed", "Canceled"].includes(frm.doc.job_order_status)){
      frm.set_read_only(true)
      frm.set_df_property("employee_details","read_only",1);
      frm.set_df_property("distance_radius","read_only",1);
      frm.set_df_property("show_all_employees","read_only",1);
      resume_download();
    }else if (["Hiring", "Exclusive Hiring"].includes(frappe.boot.tag.tag_user_info.company_type)){
      resume_download();
    }
  },
  e_signature_full_name: function(frm) {
    if(frm.doc.e_signature_full_name) {
      let regex=/[^0-9A-Za-z ]/g;
      if(regex.test(frm.doc.e_signature_full_name)===true) {
        frappe.msgprint(
          __("E-Signature Full Name: Only alphabets and numbers are allowed.")
        );
        frm.set_value("e_signature_full_name","");
        frappe.validated=false;
      }
    }
  },

  onload_post_render: function(frm) {
    if(frm.doc.resume_required==1) {
      add_employee_button(frm);
    } else if(frm.doc.employee_details){
      add_employee_row(frm);
    }
    old_unknown_function(frm);
    render_tab(frm);
    remove_cache_data();
  },

  onload: function(frm) {
    redirected_company = frm.doc.company
    hide_resume(frm);
    frappe.call({
      method: "frappe.client.get",
      args: {
        doctype: "Job Order",
        name: frm.doc.job_order,
      },
      async: 0,
      callback: function(response) {
        window.job_order=response.message;
      },
    });
    frm.refresh_field("employee_details");
    frm.fields_dict["employee_details"].grid.get_field(
      "employee"
    ).get_query=function(doc,cdt,cdn) {
      let row=locals[cdt][cdn];
      let emp_list=[];
      return {
        query:
          "tag_workflow.tag_workflow.doctype.assign_employee.assign_employee.get_employee",
        filters: {
          company: frm.doc.hiring_organization,
          emp_company: frm.doc.company,
          all_employees: row.show_all_employees,
          job_category: row.job_category,
          distance_radius: row.distance_radius.includes('miles')?row.distance_radius:undefined,
          job_location: frm.doc.job_location,
          employee_lis: emp_list,
          job_order: frm.doc.job_order,
          resume_required: frm.doc.resume_required
        },
      };
    };
  },

  before_save: function(frm) {
    check_employee_data(frm);
    frm.set_value("previous_worker",parseInt(frm.doc.employee_details.length));
  },
  company: function(frm) {
    if((!redirected_company)||(redirected_company && redirected_company !=frm.doc.company)){
    frm.clear_table("employee_details");
    frm.refresh_fields();
    }
    if(frm.doc.company&&frm.doc.__islocal==1) {
      set_pay_rate_class_code(frm);
    }
  },

  after_save: function(frm) {
    localStorage.clear();
    frappe.call({
      method:
        "tag_workflow.tag_workflow.doctype.assign_employee.assign_employee.payrate_change",
      freeze: true,
      freeze_message:"<p><b>please wait while updating data...</b></p>",
      args: {
        docname: frm.doc.name,
      },
      callback: function(r) {
        if(r.message=="success") {
          if(frm.doc.tag_status=="Open"&&frm.doc.resume_required==1) {
            make_hiring_notification(frm);
          } else {
            worker_notification(frm);
            make_notification_approved(frm);
          }
        }
      },
    });
    check_job_title(frm);

    frappe.call({
      method:
        "tag_workflow.tag_workflow.doctype.assign_employee.assign_employee.create_after_save_code_rate_title",
      freeze: true,
      freeze_message:"<p><b>please wait while updating data...</b></p>",
      args: {
        this_doc: frm.doc,
      },
    });
    update_workers_filled(frm);
    remove_emp_from_staffing(frm);
  },

  validate: async function(frm) {
    let staff_class_code;
    let message="<b>Please Fill Mandatory Fields:</b>";
    let final_message="";
    for(let each_job_title of frm.doc.multiple_job_title_details) {
      staff_class_code=each_job_title.staff_class_code;
      if(staff_class_code&&staff_class_code.length>10) {
        final_message=
          final_message+
          "<br>Maximum Characters allowed for Class Code are 10.";
        frm.set_value("staff_class_code","");
      }
    }
    final_message=check_duplicate_employee(frm,final_message);

    message=field_validation(frm,message);
    let is_negative=negative_pay_rate(frm);
    if(message!="<b>Please Fill Mandatory Fields:</b>") {
      final_message+=is_negative
        ? message+"<hr>Negative Pay Rate not accepted."
        :message;
    } else if(is_negative) {
      final_message+="Negative Pay Rate not accepted.";
    }

    if(final_message!="") {
      frappe.msgprint({
        message: __(final_message),
        title: __("Error"),
        indicator: "orange",
      });
      frappe.validated=false;
      return;
    }

    await handleEmployeeRemoval(frm);

    if(frm.doc.resume_required==0) {
      await new Promise((resolve) => {
        check_approved_no_of_workers(frm,resolve);
      })
    }
    
    if(window.conf==0&&frappe.validated && frappe.boot.tag.tag_user_info.company_type=="Staffing") {
        await new Promise((resolve,reject) => {
          frappe.validated=false;
          confirm_message(frm,resolve);
        })
    }
  },

  setup: function(frm) {
    frm.set_query("company",function() {
      return {
        filters: [["Company","organization_type","=","Staffing"]],
      };
    });
    staffing_company(frm);
  },
  view_contract: function() {
    let contracts=
      "<div class='contract_div'><h3>Staffing/Vendor Contract</h3>This Staffing/Vendor Contract (“Contract”) is entered into by and between Staffing Company and Hiring Company as further described and as set forth below. By agreeing to the Temporary Assistance Guru, Inc. (“TAG”) End-User License Agreement, and using the TAG application service and website (the “Service”) Staffing Company and Hiring Company agree that they have a contractual relationship with each other and that the following terms apply to such relationship: <br> <ol> <li> The billing rate Hiring Company shall pay Staffing Company to hire each temporary worker provided by Staffing Company (the “Worker”) is the rate set forth by the TAG Service for the location and position sought to be filled, and this rate includes all wages, worker’s compensation premiums, unemployment insurance, payroll taxes, and all other employer burdens recruiting, administration, payroll funding, and liability insurance.</li><li> Hiring Company agrees not to directly hire and employ the Worker until the Worker has completed at least 720 work hours. Hiring Company agrees to pay Staffing Company an administrative placement fee of $3,000.00 if Hiring Company directly employs the Worker prior to completion of 720 work hours.</li> <li> Hiring Company acknowledges that it has complete care, custody, and control of workplaces and job sites. Hiring Company agrees to comply with all applicable laws, regulations, and ordinances relating to health and safety, and agrees to provide any site/task specific training and/or safety devices and protective equipment necessary or required by law. Hiring Company will not, without prior written consent of Staffing Company, entrust Staffing Company employees with the handling of cash, checks, credit cards, jewelry, equipment, tools, or other valuables.</li> <li> Hiring Company agrees that it will maintain a written safety program, a hazard communication program, and an accident investigation program. Hiring Company agrees that it will make first aid kits available to Workers, that proper lifting techniques are to be used, that fall protection is to be used, and that Hiring Company completes regular inspections on electrical cords and equipment. Hiring Company represents, warrants, and covenants that it handles and stores hazardous materials properly and in compliance with all applicable laws. </li> <li> Hiring Company agrees to post Occupational Safety and Health Act (“OSHA”) of 1970 information and other safety information, as required by law. Hiring Company agrees to log all accidents in its OSHA 300 logs. Hiring Company agrees to indemnify and hold harmless Staffing Company for all claims, damages, or penalties arising out of violations of the OSHA or any state law with respect to workplaces or equipment owned, leased, or supervised by Hiring Company and to which employees are assigned. </li> <li>  Hiring Company will not, without prior written consent of Staffing Company, utilize Workers to operate machinery, equipment, or vehicles. Hiring Company agrees to indemnify and save Staffing Company and Workers harmless from any and all claims and expenses (including litigation) for bodily injury or property damage or other loss as asserted by Hiring Company, its employees, agents, the owner of any such vehicles and/or equipment or contents thereof, or by members of the general public, or any other third party, arising out of the operation or use of said vehicles and/or equipment by Workers. </li> <li> Commencement of work by dispatched Workers, or Hiring Company’s signature on work ticket serves as confirmation of Hiring Company’s agreement to conditions of service listed in or referred to by this Contract. </li> <li> Hiring Company agrees not to place Workers in a supervisory position except for a Worker designated as a “lead,” and, in that position, Hiring Company agrees to supervise all Workers at all times. </li> <li> Billable time begins at the time Workers report to the workplace as designated by the Hiring Company. </li> <li> Jobs must be canceled a minimum of 24 hours prior to start time to avoid a minimum of four hours billing per Worker. </li> <li> Staffing Company guarantees that its Workers will satisfy Hiring Company, or the first two hours are free of charge. If Hiring Company is not satisfied with the Workers, Hiring Company is to call the designated phone number for the Staffing Company within the first two hours, and Staffing Company will replace them free of charge.</li> <li> Staffing Company agrees that it will comply with Hiring Company’s safety program rules. </li> <li> Overtime will be billed at one and one-half times the regular billing rate for all time worked over forty hours in a pay period and/or eight hours in a day as provided by state law. </li> <li> Invoices are due 30 days from receipt, unless other arrangements have been made and agreed to by each of the parties. </li> <li> Interest Rate: Any outstanding balance due to Staffing Company is subject to an interest rate of two percent (2%) per month, commencing on the 90th day after the date the balance was due, until the balance is paid in full by Hiring Company. </li> <li> Severability. If any provision of this Contract is held to be invalid and unenforceable, then the remainder of this Contract shall nevertheless remain in full force and effect. </li> <li> Attorney’s Fees. Hiring Company agrees to pay reasonable attorney’s fees and/or collection fees for any unpaid account balances or in any action incurred to enforce this Contract. </li> <li> Governing Law. This Contract is governed by the laws of the state of Florida, regardless of its conflicts of laws rules. </li> <li>  If Hiring Company utilizes a Staffing Company employee to work on a prevailing wage job, Hiring Company agrees to notify Staffing Company with the correct prevailing wage rate and correct job classification for duties Staffing Company employees will be performing. Failure to provide this information or providing incorrect information may result in the improper reporting of wages, resulting in fines or penalties being imposed upon Staffing Company. The Hiring Company agrees to reimburse Staffing Company for any and all fines, penalties, wages, lost revenue, administrative and/or supplemental charges incurred by Staffing Company.</li> <li> WORKERS' COMPENSATION COSTS: Staffing Company represents and warrants that it has a strong safety program, and it is Staffing Company’s highest priority to bring its Workers home safely every day. AFFORDABLE CARE ACT (ACA): Staffing Company represents and warrants that it is in compliance with all aspects of the ACA. </li> <li> Representatives. The Hiring Company and the Staffing Company each certifies that its authorized representative has read all of the terms and conditions of this Contract and understands and agrees to the same. </li> ";

    let contract=new frappe.ui.Dialog({
      title: "Contract Details",
      fields: [{fieldname: "html_37",fieldtype: "HTML",options: contracts}],
    });
    contract.show();
  },
  employee_pay_rate: function(frm) {
    let emp_details=frm.doc.employee_details;
    $.each(emp_details||[],function(_i,v) {
      frappe.model.set_value(
        v.doctype,
        v.name,
        "pay_rate",
        frm.doc.employee_pay_rate
      );
    });
    frm.refresh_field("employee_details");
  },
  staff_class_code: function(frm) {
    if(frm.doc.staff_class_code&&frm.doc.staff_class_code.length>10) {
      frappe.msgprint({
        message: __("Maximum Characters allowed for Class Code are 10."),
        title: __("Error"),
        indicator: "orange",
      });
      frm.set_value("staff_class_code","");
      frappe.validated=false;
    }
  },
});

async function handleEmployeeRemoval(frm) {
    let any_emps_removed = [];
    for(let each in employees_to_be_removed_row_dict){
      if(employees_to_be_removed_row_dict[each]==1){
        any_emps_removed.push(each)
      }
    }
    if(any_emps_removed?.length) {
      try {
        await new Promise((resolve,reject) => {
          confirm_remove_employee_popup(resolve,reject);
        });
      } catch(error) {
        return;
      }
    }
    await new Promise((resolve) => {
      if(Object.keys(employees_to_be_removed_row_dict).length-any_emps_removed.length > 0 && Object.keys(employees_to_be_removed_row_dict).length-any_emps_removed.length != any_emps_removed.length){
        frappe.db.get_value(
          "Job Order",
          {name: frm.doc.job_order},
          ["total_no_of_workers"],
          function(req) {
            frappe.db.get_value(
              "Job Order",
              {name: frm.doc.job_order},
              ["total_workers_filled"],
              function(filled) {
                if(req.total_no_of_workers < parseInt(filled.total_workers_filled) + Object.keys(employees_to_be_removed_row_dict).length-any_emps_removed.length){
                frappe.msgprint("Can not unremove employees as headcount limit already reached")
                frappe.validated = false
                }
                resolve()
              })
          })
      }
      else{
        resolve()
      }
    });
}

function confirm_remove_employee_popup(resolve,reject) {
  let options_html=`Are You sure to remove below employees ? <br><br>`;
  for(let key in employees_to_be_removed_row_dict) {
    if(employees_to_be_removed_row_dict[key]==1){
      let keys=key.split("~");
      options_html+=`<li style="margin-left:2%"><b>${keys[0]}</b> from <b>${keys[1]}</b> at <b>${keys[2]}</b></li>`;
    }
    
  }
  let confirm_remove=new frappe.ui.Dialog({
    title: __(`<span class="indicator orange"></span> Warning`),
    fields: [
      {
        fieldname: "save_joborder",
        fieldtype: "HTML",
        options: options_html,
      },
    ],
  });
  confirm_remove.no_cancel();
  confirm_remove.set_primary_action(__("Confirm"),function() {
    confirm_remove.hide();
    frappe.validated=true;
    resolve();
  });

  confirm_remove.set_secondary_action_label(__("Cancel"));
  confirm_remove.set_secondary_action(() => {
    confirm_remove.hide();
    frappe.validated=false;
    reject(new Error("User canceled"));
  });
  confirm_remove.show();
  confirm_remove.$wrapper.find(".modal-dialog").css("width","450px");
}

function remove_emp_from_staffing(frm) {
  let remove_unremove_job_data=[];
  let employees=frm.doc.employee_details;
  for(let each in employees) {
    let key = employees[each].employee+"~"+employees[each].job_category+"~"+employees[each].job_start_time
    if (key in employees_to_be_removed_row_dict){
      let each_data=[frm.doc.name,employees[each].employee,frm.doc.job_order,employees[each].remove_employee,employees[each].job_category,employees[each].job_start_time];
      remove_unremove_job_data.push(each_data);
    }
    
  }
  let total_removed_emps = []
  for(let key in employees_to_be_removed_row_dict) {
    if(employees_to_be_removed_row_dict[key]==1){
      total_removed_emps.push(key)
    }
    
  }
  if(remove_unremove_job_data) {
    frappe.call({
      method: "tag_workflow.tag_data.remove_emp_from_order_staffing",
      freeze: true,
      freeze_message: "<p><b>please wait while updating data...</b></p>",
      args: {
        list_array_removed_emps: remove_unremove_job_data,
        notification_flag: !!total_removed_emps.length
      },
      callback: function(r) {
        if(frm.doc.resume_required==1) {
          add_employee_button(frm);
        } else if(frm.doc.employee_details){
          add_employee_row(frm);
        }
        frm.refresh_fields('employee_details')
      frm.reload_doc();
    }
    });
  }
  employees_to_be_removed_row_no=[]
  employees_to_be_removed_row_dict = {}
}

function update_non_resume_miles_default_field(frm) {
  if(frm.doc.resume_required==0) {
    frm.fields_dict["employee_details"].grid.update_docfield_property(
      "distance_radius",
      "options",
      "5 miles\n10 miles\n20 miles\n50 miles"
    );
    frm.refresh_fields('employee_details');
  }
}

function create_global_time_object(frm) {
  for(let each of frm.doc.multiple_job_title_details) {
    if((frm.doc.resume_required==1&&each.no_of_workers>=1)||(frm.doc.resume_required==0&&each.approved_workers>0)) {
      let time=each.job_start_time;
      time=time.split(":");
      time.pop();
      time=time.join(":");
      if(each.select_job in each_title_times) {
        if(!each_title_times[each.select_job].includes(time)){each_title_times[each.select_job].push(time)};
      }
      else {
        each_title_times[each.select_job]=[];
        each_title_times[each.select_job].push(time);
      }
    }
  }
}

function set_multiple_time_filters(frm,cdt,cdn,each_data) {
  if(each_data.job_category) {
    let time_val=each_title_times[each_data.job_category];
    if(time_val&&time_val.length==1) {
      each_data.job_start_time = time_val[0]      
      frm.refresh_field("employee_details");
    }
    frappe.utils.filter_dict(frm.fields_dict.employee_details.grid.grid_rows_by_docname[each_data.name].docfields,{"fieldname": "job_start_time"})[0].options=time_val;
    if(frm.doc.resume_required==0){
      frappe.utils.filter_dict(frm.fields_dict.employee_details.grid.grid_rows_by_docname[each_data.name].docfields,{"fieldname": "job_start_time"})[0].read_only=1;
      frappe.utils.filter_dict(frm.fields_dict.employee_details.grid.grid_rows_by_docname[each_data.name].docfields,{"fieldname": "job_category"})[0].read_only=1;
    }
    if(frm.doc.__islocal==1 || (each_data.approved==0 && frm.doc.resume_required==1)){
      frappe.utils.filter_dict(frm.fields_dict.employee_details.grid.grid_rows_by_docname[each_data.name].docfields,{"fieldname": "remove_employee"})[0].read_only=1;
    }
    frm.fields_dict['employee_details'].grid.get_grid_row(each_data.name).refresh();
  }
}

function check_approved_no_of_workers(frm,resolve) {
  frappe.call({
    method:
      "tag_workflow.tag_workflow.doctype.assign_employee.assign_employee.validate_approved_workers",
    args: {
      job_order: frm.doc.job_order,
      staff_company: frm.doc.company,
    },
    callback: function(r) {
      let all_assigned_emps_count={};
      let own_msg=[];
      for(let each_emp in frm.doc.employee_details) {
        if(frm.doc.employee_details[each_emp].employee&&r.message && frm.doc.employee_details[each_emp].remove_employee==0) {
          let key=
            frm.doc.employee_details[each_emp]["job_category"]+
            "~"+
            frm.doc.employee_details[each_emp]["job_start_time"];
          get_assigned_employee_counts(key,all_assigned_emps_count);
          if(
            !r.message[key]||
            all_assigned_emps_count[key]>(r.message[key]||0)
          ) {
            let single_ms=
              "Employee Details(<b>"+
              all_assigned_emps_count[key]+
              "</b>) value is more than No. Of Employees Approved(<b>"+
              (r.message[key]||0)+
              "</b>) for the Job Title(<b>"+
              key.split("~")[0]+
              "</b>) for Start Time (<b>"+
              key.split("~")[1]+
              "</b>)";
            if(!own_msg.includes(single_ms)) {
              own_msg.push(single_ms);
            }
          }
        }
      }
      if(own_msg.length) {
        frappe.validated=false;
        frappe.msgprint({
          message: own_msg.join("<br>"),
          title: __("Error"),
          indicator: "red",
        });
      }
      resolve()     
    },
  });
}

function get_assigned_employee_counts(key,all_assigned_emps_count) {
  if(key in all_assigned_emps_count) {
    all_assigned_emps_count[key]+=1;
  } else {
    all_assigned_emps_count[key]=1;
  }
}

function check_duplicate_employee(frm,final_message) {
  let duplicate_employee_data={};
  let duplicate_msg={};
  for(let each_emp of frm.doc.employee_details) {
    if(each_emp.employee) {
      let key=
        each_emp.job_category+
        "~"+
        each_emp.job_start_time+
        "~"+
        each_emp.employee;
      if(key in duplicate_employee_data) {
        duplicate_employee_data[key].push(each_emp.idx);
      } else {
        duplicate_employee_data[key] = [each_emp.idx];
      }
    }
  }
  for (let key in duplicate_employee_data) {
    let employee_id = key.split("~")[2];
    if (duplicate_employee_data[key].length > 1) {
      let rows = duplicate_employee_data[key].map((idx) => "<b>Row: " + idx + "</b>");
      let new_msg =
        "<br>Employee <b>" +
        employee_id +
        "</b> assigned multiple times for <b>" +
        key.split("~")[0] +
        "</b> at <b>" +
        key.split("~")[1] +
        "</b> in " +
        rows.join(", ") +
        "<br>";

      if (duplicate_msg[new_msg] === undefined) {
        final_message += new_msg;
        duplicate_msg[new_msg] = 1;
      }
    }
  }
  return final_message;
}

/*-----------hiring notification--------------*/
function make_hiring_notification(frm) {
  frappe.db.get_value(
    "Job Order",
    {name: frm.doc.job_order},
    ["owner"],
    function(r_own) {
      frappe.db.get_value(
        "User",
        {name: r_own.owner},
        ["organization_type"],
        function(r) {
          if(r.organization_type!="Staffing"||r==null) {
            frappe.call({
              method: "tag_workflow.tag_data.receive_hiring_notification",
              freeze: true,
              freeze_message:
                "<p><b>preparing notification for Hiring orgs...</b></p>",
              args: {
                user: frappe.session.user,
                company_type: frappe.boot.tag.tag_user_info.company_type,
                hiring_org: frm.doc.hiring_organization,
                job_order: frm.doc.job_order,
                staffing_org: frm.doc.company,
                emp_detail: frm.doc.employee_details,
                doc_name: frm.doc.name,
                employee_filled: frm.doc.employee_details.length,
                no_of_worker_req: frm.doc.no_of_employee_required,
                is_single_share: frm.doc.is_single_share,
                job_title: frm.doc.job_category,
                notification_check: frm.doc.notification_check,
              },
              callback: function(r1) {
                pop_up_message(r1,frm);
              },
            });
          } else {
            let count_len=frm.doc.employee_details.length;
            if(frm.doc.previous_worker) {
              count_len=
                frm.doc.employee_details.length-frm.doc.previous_worker;
            }

            frappe.call({
              method: "tag_workflow.tag_data.staff_own_job_order",
              freeze: true,
              freeze_message: "<p><b>preparing notification</b></p>",
              args: {
                job_order: frm.doc.job_order,
                staffing_org: frm.doc.company,
                emp_detail: count_len,
                doc_name: frm.doc.name,
              },
              callback: function() {
                setTimeout(function() {
                  window.location.href="/app/job-order/"+frm.doc.job_order;
                },2000);
              },
            });
          }
        }
      );
    }
  );
}

function check_job_title(frm) {
  frappe.call({
    method:
      "tag_workflow.tag_workflow.doctype.assign_employee.assign_employee.add_job_title",
    freeze: true,
    freeze_message:"<p><b>please wait while updating data...</b></p>",
    args: {
      job_order: frm.doc.job_order,
      assign_emp_detail: frm.doc.employee_details
    },
  });
}

/*---------employee data--------------*/
function check_employee_data(frm) {
  let msg=[];
  let table=frm.doc.employee_details||[];
  let assigned=0;

  if(frm.doc.resume_required==1) {
    resume_data(msg,table);
  }
  if(frm.doc.resume_required!=1||condition==1) {
    table_emp(frm,table,msg);
  }
  company_check(frm,table,msg);

  for(let e in table) {
    assigned+=table[e].approved==1? 1:0;
  }
  if(
    assigned==0&&
    frm.doc.__islocal!=1&&
    !["Staffing","TAG"].includes(frappe.boot.tag.tag_user_info.company_type)
  ) {
    msg.push("Please select an employee to assign.");
  }
  if(msg.length) {
    frappe.msgprint({
      message: msg.join("<br>"),
      title: __("Warning"),
      indicator: "red",
    });
    frappe.validated=false;
  }
}

function duplicate_employee(frm) {
  let employee=frm.doc.employee_details.length;
  let employee_count={};
  let msg="";
  for(let emp in frm.doc.employee_details) {
    let emp_id=frm.doc.employee_details[emp].employee;
    let row=parseInt(emp)+1
    if(employee_count[emp_id]) {
      employee_count[emp_id][0]++;
      employee_count[emp_id][1].push("Row: "+row)
    } else {
      employee_count[emp_id]=[1,["Row: "+row],[frm.doc.employee_details[emp].job_start_time]];
    }
  }
  if(employee>1) {
    for(let k in employee_count) {
      if(employee_count[k][0]>1) {
        msg+=
        "Employee <b>"+
        k+
        " </b>has assigned multiple times on <b>"+employee_count[k][1].join(" </b>, <b> ")+
        "</b><br>";
      }
    }
  }

  return msg;
}

/*--------------child table------------------*/
function render_table(frm) {
  if(frm.doc.tag_status=="Approved") {
    frappe.call({
      method: "tag_workflow.utils.timesheet.check_employee_editable",
      args: {
        job_order: frm.doc.job_order,
        name: frm.doc.name,
        creation: frm.doc.creation,
      },
      callback: function(r) {
        if(r&&r.message==0) {
          frm.fields_dict["employee_details"].refresh();
        } else {
          frm.fields_dict["employee_details"].grid.cannot_add_rows=false;
          frm.fields_dict["employee_details"].refresh();
          frm.toggle_display("replaced_employees",1);
        }
      },
    });
  }
}

function render_tab(frm) {
  let items=frm.doc.employee_details||[];
  let emps=0;
  let is_open=0;
  for(let i in items) {
    if(frm.doc.resume_required==1&&items[i].approved) {
      emps+=1;
    }
  }

  if(
    (frm.doc.resume_required==1&&frm.doc.tag_status!="Approved")||
    (frm.doc.resume_required==0&&items.length<frm.doc.claims_approved)
  ) {
    is_open=1;
  }

  if(is_open==1) {
    frm.set_df_property("employee_details","read_only",0);
    frm.fields_dict["employee_details"].grid.cannot_add_rows=false;
    frm.fields_dict["employee_details"].refresh();
    frm.refresh_field("employee_details");
  }
}

/*-------------------------------*/

frappe.ui.form.on("Multiple Job Title Details",{
  employee_pay_rate: function(frm,cdt,cdn) {
    let child=locals[cdt][cdn];
    if(child.employee_pay_rate && frm.doc.employee_details) {
      for(let each_emp of frm.doc.employee_details) {
        let each_time=child.job_start_time.split(":");
        each_time.pop();
        each_time=each_time.join(":");
        if(
          each_emp.job_category==child.select_job&&
          child.employee_pay_rate
        ) {
          frappe.model.set_value(
            "Assign Employee Details",
            each_emp.name,
            "pay_rate",
            child.employee_pay_rate
          );
          frm.refresh_field("employee_details");
        }
      }
    }
    let sel_job=child.select_job;
    let emp_pay_rate=child.employee_pay_rate;

    for(let all_emp of frm.doc.multiple_job_title_details) {
      if(all_emp.select_job===sel_job) {
        frm.doc.multiple_job_title_details.forEach((emp) => {
          if(emp.select_job===sel_job) {
            emp.employee_pay_rate=emp_pay_rate;
          }
        });
      }
    }
    frm.refresh_field("multiple_job_title_details");
  },
  staff_class_code: function(frm,cdt,cdn) {
    let child=locals[cdt][cdn];
    if(child.staff_class_code&&child.staff_class_code.length>10) {
      frappe.msgprint({
        message: __("Maximum Characters allowed for Class Code are 10.<br>"),
        title: __("Error"),
        indicator: "orange",
      });
      frappe.model.set_value(cdt,cdn,"staff_class_code","");
      frm.refresh_field('multiple_job_title_details');
    }
  },
});

/*-------------------------------*/

frappe.ui.form.on("Assign Employee Details",{
  before_employee_details_remove: function(frm,cdt,cdn) {
    let child=frappe.get_doc(cdt,cdn);
    if(frm.doc.tag_status=="Approved"&&child.__islocal!=1) {
      frappe.throw("You can't delete employee details once it's Approved.");
    }
  },
  employee: function(frm,cdt,cdn) {
    let child=locals[cdt][cdn];

    if(child.employee) {
      check_mandatory_field(child.employee,child.employee_name);
      frappe.call({
        method: "tag_workflow.tag_data.joborder_resume",
        args: {name: child.employee},
        callback: function(r) {
          if(r.message[0]["resume"]) {
            frappe.model.set_value(cdt,cdn,"resume",r.message[0]["resume"]);
          } else {
            frappe.model.set_value(cdt,cdn,"resume","");
          }
          frm.refresh_field("employee_details");
        },
      });

      if(frm.doc.show_all_employees==0) {
        frappe.db.get_value(
          "Employee",
          {name: child.employee},
          ["job_category"],
          function(r) {
            if(r.job_category&&r.job_category!="null") {
              frappe.model.set_value(
                cdt,
                cdn,
                "job_category",
                child.job_category
              );
            }
          }
        );
      }

      if(child.__islocal!=1) {
        check_old_value(frm,child);
      }
      frappe.model.set_value(cdt,cdn,"remove_employee",0);
      frm.refresh_field("employee_details");
    }
  },
  job_start_time: function(frm,cdt,cdn) {
    let child=locals[cdt][cdn];

    if(child.job_start_time) {
      if(child.job_category) {
        let valid_time=false;
        for(let each_title of frm.doc.multiple_job_title_details) {
          let each_tile_time=each_title.job_start_time.split(":");
          each_tile_time.pop();
          each_tile_time=each_tile_time.join(":");
          if(
            each_tile_time==child.job_start_time&&
            each_title.select_job==child.job_category
          ) {
            valid_time=true;
            frappe.model.set_value(
              cdt,
              cdn,
              "estimated_hours_per_day",
              each_title.estimated_hours_per_day
            );
            frappe.model.set_value(
              cdt,
              cdn,
              "pay_rate",
              each_title.employee_pay_rate
            );
            frm.refresh_field("employee_details");
          }
        }
        if(!valid_time) {
          frappe.model.set_value(cdt,cdn,"job_start_time","");
          frappe.msgprint(
            "Select Valid Start Time according to selected Job Title"
          );
          frm.refresh_field("employee_details");
        }
      } else {
        frappe.msgprint("Select Job Title first to select Start Time.");
        frappe.model.set_value(cdt,cdn,"job_start_time","");
        frm.refresh_field("employee_details");
      }
    }
  },
  job_category: function(frm,cdt,cdn) {
    let child=locals[cdt][cdn];
    if(child.job_category) {
      let time_val=each_title_times[child.job_category];
      if(time_val&&time_val.length==1) {
        frappe.model.set_value(cdt,cdn,"job_start_time",time_val[0]);
        frm.refresh_field("employee_details");
      }
      frappe.utils.filter_dict(
        frm.fields_dict.employee_details.grid.grid_rows_by_docname[child.name]
          .docfields,
        {fieldname: "job_start_time"}
      )[0].options=time_val;
      frm.fields_dict["employee_details"].grid
        .get_grid_row(child.name)
        .refresh();
    }
    else{
      frappe.model.set_value(cdt,cdn,"job_start_time","");
    }
    if(frm.doc.resume_required==1){
      frappe.model.set_value(cdt,cdn,"employee","");
      frappe.model.set_value(cdt,cdn,"employee_name","");
      frappe.model.set_value(cdt,cdn,"resume","");
      frm.refresh_field("employee_details");
    }
  },
  distance_radius: function(frm,cdt,cdn){
    if(frm.doc.resume_required==1){
      frappe.model.set_value(cdt,cdn,"employee","");
      frappe.model.set_value(cdt,cdn,"employee_name","");
      frappe.model.set_value(cdt,cdn,"resume","");
      frm.refresh_field("employee_details");
    }
  },
  remove_employee: async function(frm,cdt,cdn) {
    let child=locals[cdt][cdn];
    let employees_to_be_removed_row_no_key=child.employee+"~"+child.job_category+"~"+child.job_start_time

    if(child.remove_employee==0&&child.removed_by_hiring==1) {
      frappe.msgprint(
        "Employee already removed by hiring to reduce headcounts."
      );
      frappe.model.set_value(cdt,cdn,"remove_employee",1);
      frm.refresh_field("employee_details");
    }
    if(child.removed_by_hiring==0) {
      if(child.remove_employee==1&&!employees_to_be_removed_row_no.includes(employees_to_be_removed_row_no_key)) {
        employees_to_be_removed_row_no.push(employees_to_be_removed_row_no_key)
      }
      else if(employees_to_be_removed_row_no.includes(employees_to_be_removed_row_no_key)) { 
          let array_idx=employees_to_be_removed_row_no.indexOf(employees_to_be_removed_row_no_key);
          employees_to_be_removed_row_no.splice(array_idx,1)
      }
      if(employees_to_be_removed_row_no_key in employees_to_be_removed_row_dict){
        delete employees_to_be_removed_row_dict[employees_to_be_removed_row_no_key]
      }
      else{
        employees_to_be_removed_row_dict[employees_to_be_removed_row_no_key] = child.remove_employee
      }
    }
  },
  form_render: ()=>{
    let resume_element = $('[data-fieldtype="Attach"].frappe-control.input-max-width>div>div>div');
    if(resume_element.length && window.getComputedStyle(resume_element[0]).display=="none"){
      $('[data-fieldtype="Attach"].frappe-control.input-max-width').on("click", (e) => {
        e.stopPropagation();
        document_download(e);
      });
    }
  },
  show_all_employees: (frm, cdt, cdn)=>{
    let child=locals[cdt][cdn];
    if(child.show_all_employees==0){
      frappe.msgprint("The employees will be filtered according to the Job Titles linked.");
    }
  }
});

function approved_employee(frm) {
  if(
    frm.doc.tag_status=="Approved"&&
    (frappe.boot.tag.tag_user_info.company_type=="Hiring"||
      frappe.boot.tag.tag_user_info.company_type=="Exclusive Hiring")&&
    frm.doc.resume_required==1&&
    frm.doc.approve_employee_notification===1
  ) {
    let current_date=new Date(frappe.datetime.now_datetime());
    let approved_date=new Date(frm.doc.modified);
    let diff=current_date.getTime()-approved_date.getTime();
    let emp_selected=0;
    for(let i in frm.doc.employee_details) {
      emp_selected+=frm.doc.employee_details[i]["approved"];
    }
    diff=parseInt(diff/1000);
    if(diff<60) {
      frappe.call({
        method: "tag_workflow.tag_data.update_job_order",
        freeze: true,
        freeze_message:
          "<p><b>preparing notification for Staffing orgs...</b></p>",
        args: {
          user: frappe.session.user,
          company_type: frappe.boot.tag.tag_user_info.company_type,
          sid: frappe.boot.tag.tag_user_info.sid,
          job_name: frm.doc.job_order,
          employee_filled: emp_selected,
          staffing_org: frm.doc.company,
          hiringorg: frm.doc.hiring_organization,
          name: frm.doc.name,
        },
        callback: function(r) {
          pop_up_message(r,frm);
        },
      });
    }

    // cur_frm.set_value('approve_employee_notification',0)
    frm.refresh_field("approve_employee_notification");
  }
}

function hide_resume(frm) {
  let refresh=0;
  if(frm.doc.__islocal==1){
    let remove_employee_field=frappe.meta.get_docfield(
      "Assign Employee Details",
      "remove_employee",
      frm.doc.name
    );
    remove_employee_field.read_only=1;
    refresh=1;
  }
  if(
    frm.doc.resume_required&&
    frappe.boot.tag.tag_user_info.company_type=="Staffing"&&
    frm.doc.tag_status!="Approved"
  ) {
    let table=frappe.meta.get_docfield(
      "Assign Employee Details",
      "approved",
      frm.doc.name
    );
    table.hidden=1;
    refresh=1;
  }
  if(frappe.boot.tag.tag_user_info.company_type!="Staffing") {
    let staff_class_code_rate_field=frappe.meta.get_docfield(
      "Multiple Job Title Details",
      "staff_class_code_rate",
      frm.doc.name
    );
    staff_class_code_rate_field.hidden=1;

    let staff_class_code_field=frappe.meta.get_docfield(
      "Multiple Job Title Details",
      "staff_class_code",
      frm.doc.name
    );
    staff_class_code_field.hidden=1;

    let employee_pay_rate_field=frappe.meta.get_docfield(
      "Multiple Job Title Details",
      "employee_pay_rate",
      frm.doc.name
    );
    employee_pay_rate_field.hidden=1;

    let distance_radius_field=frappe.meta.get_docfield(
      "Assign Employee Details",
      "distance_radius",
      frm.doc.name
    );
    distance_radius_field.hidden=1;
    refresh=1;
    console.log(refresh);
  }
  if(frm.doc.resume_required && frm.doc.tag_status=="Approved"){
    let start_time=frappe.meta.get_docfield(
      "Assign Employee Details",
      "job_start_time",
      frm.doc.name
    );
    start_time.read_only=1;
    let job_title=frappe.meta.get_docfield(
      "Assign Employee Details",
      "job_category",
      frm.doc.name
    );
    job_title.read_only=1;
    refresh=1;
    console.log(refresh);
  }
  if(!frm.doc.resume_required) {
    let resume=frappe.meta.get_docfield(
      "Assign Employee Details",
      "resume",
      frm.doc.name
    );
    resume.hidden=1;
    let approved=frappe.meta.get_docfield(
      "Assign Employee Details",
      "approved",
      frm.doc.name
    );
    approved.hidden=1;
    refresh=1;
    if(["Completed", "Canceled"].includes(frm.doc.job_order_status)){
      frm.set_df_property("employee_details","read_only",1);
      frm.set_df_property("distance_radius","read_only",1);
      frm.set_df_property("show_all_employees","read_only",1);
    }
  } else {
    let approved_worker_filled=frappe.meta.get_docfield(
      "Multiple Job Title Details",
      "approved_workers",
      frm.doc.name
    );
    approved_worker_filled.hidden=1;
  }
  if(
    ["Hiring","Exclusive Hiring"].includes(
      frappe.boot.tag.tag_user_info.company_type
    )
  ) {
    let rate_field=frappe.meta.get_docfield(
      "Assign Employee Details",
      "pay_rate",
      frm.doc.name
    );
    rate_field.hidden=1;
  }
  if(refresh==1) {
    frm.refresh_fields();
  }
}

function back_job_order_form(frm) {
  frm.add_custom_button(
    __("Job Order"),
    function() {
      frappe.set_route("Form","Job Order",frm.doc.job_order);
    },
    __("View")
  );
}

function staff_comp(frm) {
  if(frm.doc.__islocal==1&&frm.doc.is_single_share==1) {
    frm.set_df_property("company","read_only",1);
  }
}

function worker_notification(frm) {
  setTimeout(function() {
    if(
      frm.doc.tag_status=="Open"&&
      frappe.boot.tag.tag_user_info.company_type=="Staffing"&&
      frm.doc.__islocal!=1
    ) {
      frappe.call({
        method:
          "tag_workflow.tag_workflow.doctype.assign_employee.assign_employee.worker_data",
        freeze: true,
        freeze_message:"<p><b>please wait while updating data...</b></p>",
        args: {
          job_order: frm.doc.job_order,
        },
        callback: function(r) {
          let worker_required=
            r.message[0].total_no_of_workers-
            r.message[0].total_workers_filled;
          if(
            worker_required<frm.doc.employee_details.length&&
            (frm.doc.resume_required!=1||
              condition==1||
              frappe.boot.tag.tag_user_info.company_type=="Hiring")
          ) {
            frappe.msgprint(
              "No Of Workers required for "+
              frm.doc.job_order+
              " is "+
              worker_required
            );
            frm.fields_dict["employee_details"].grid.cannot_add_rows=false;
            frm.set_df_property("employee_details","read_only",0);
            frm.fields_dict["employee_details"].refresh();
          }
        },
      });
    }
  },2000);
}

function table_emp(frm,table,msg) {
  let count = 0
    for(let each in frm.doc.employee_details){
      if(frm.doc.employee_details[each].remove_employee==0){
        count = count + 1
      }
    }
  if(frm.doc.tag_status=="Approved"&&frm.doc.resume_required==0) {
    count>Number(frm.doc.claims_approved)
      ? msg.push(
        "Employee Details(<b>"+
        count+
        "</b>) value is more than No. Of Employees Approved(<b>"+
        frm.doc.claims_approved+
        "</b>) for the Job Order(<b>"+
        frm.doc.job_order+
        "</b>)"
      )
      :console.log("TAG");
  } else if(frm.doc.resume_required==0) {
    count>Number(frm.doc.claims_approved)
      ? msg.push("Please Assign "+frm.doc.claims_approved+" Employee(s)")
      :console.log("TAG");
  } else {
    count>Number(frm.doc.no_of_employee_required)
      ? msg.push(
        "Employee Details(<b>"+
        table.length+
        "</b>) value is more than total No. Of Employees Required(<b>"+
        frm.doc.no_of_employee_required+
        "</b>) for the Job Order(<b>"+
        frm.doc.job_order+
        "</b>)"
      )
      :console.log("TAG");
  }
}

function make_notification_approved(frm) {
  let count=frm.doc.employee_details.length;
  if(frm.doc.previous_worker) {
    count=frm.doc.employee_details.length-frm.doc.previous_worker;
  }

  frappe.call({
    method: "tag_workflow.tag_data.receive_hire_notification",
    freeze: true,
    freeze_message: "<p><b>preparing notification for Hiring orgs...</b></p>",
    args: {
      user: frappe.session.user,
      company_type: frappe.boot.tag.tag_user_info.company_type,
      hiring_org: frm.doc.hiring_organization,
      job_order: frm.doc.job_order,
      staffing_org: frm.doc.company,
      emp_detail: frm.doc.employee_details,
      doc_name: frm.doc.name,
      no_of_worker_req: frm.doc.no_of_employee_required,
      is_single_share: frm.doc.is_single_share,
      job_title: frm.doc.job_category,
      worker_fill: count,
    },
    callback: function(r) {
      pop_up_message(r,frm);
    },
  });
}

function resume_data(msg,table) {
  for(let r in table) {
    if(
      table[r].resume===null||
      table[r].resume==undefined||
      table[r].resume==""
    ) {
      let message="Attach the Resume to Assign the Employee.";
      if(!msg.includes(message)) {
        msg.push(message);
      }
      frappe.validated=false;
    }
  }
}


function document_download(e) {
  let file=e.target.innerText;
  let link="";
  if(file.includes(".")) {
    if(file.length>1) {
      if(file.includes("/files/")) {
        link=window.location.origin+file;
      } else {
        link=window.location.origin+"/files/"+file;
      }
      let data=file.split("/");
      const anchor=document.createElement("a");
      anchor.href=link;
      anchor.download=data[data.length-1];
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
    }
  }
}


function attachrefresh() {
  setTimeout(() => {
    document
      .querySelectorAll('div[data-fieldname="resume"]')
      .forEach(function(oInput) {
        try {
          if(oInput.children.length>=2) {
            oInput.children[1].innerText=oInput.children[1].innerText
              .split("/")
              .slice(-1)[0];
          }
        } catch(error) {
          console.log(error);
        }
      });
  },200);
}

function company_check(frm,table,msg) {
  for(let d in table) {
    if(
      table[d].company!=null&&
      table[d].company!=frm.doc.company&&
      table[d].company
    ) {
      msg.push(
        "Employee <b>"+
        table[d].employee+
        " </b>does not belong to "+
        frm.doc.company
      );
    }
  }
}

function child_table_label() {
  let child_table=[
    "employee",
    "employee_name",
    "resume",
    "employee_status",
    "employee_replaced_by",
  ];
  for(let i in child_table) {
    $("[data-fieldname="+child_table[i]+"]").on("mouseover",function(e) {
      let file=e.target.innerText;
      $(this).attr("title",file);
    });
  }
}

function add_employee_row(frm) {
  let count = 0
    for(let each in frm.doc.employee_details){
      if(frm.doc.employee_details[each].remove_employee==0){
        count = count + 1
      }
    }
  if(frm.doc.claims_approved) {
    if(frm.doc.claims_approved>count) {
      frm.fields_dict["employee_details"].grid.cannot_add_rows=false;
      frm.fields_dict["employee_details"].refresh();
    } else {
      frm.fields_dict["employee_details"].grid.cannot_add_rows=true;
      frm.fields_dict["employee_details"].refresh();
    }
  } else if(frm.doc.claims_approved>count) {
      console.log(
        frm.doc.no_of_employee_required>=count
      );
      frm.fields_dict["employee_details"].grid.cannot_add_rows=false;
      frm.fields_dict["employee_details"].refresh();
    } else {
      frm.fields_dict["employee_details"].grid.cannot_add_rows=true;
      frm.fields_dict["employee_details"].refresh();
    }
}

function staffing_company(frm) {
  if(
    frm.doc.__islocal==1&&
    frappe.boot.tag.tag_user_info.company_type=="Staffing"&&
    frappe.boot.tag.tag_user_info.comps.length==1 &&
    frappe.boot.tag.tag_user_info.company != frm.doc.company
  ) {
    frm.set_value("company",frappe.boot.tag.tag_user_info.company);
    redirected_company = undefined
  }
}

/*-------------------------------------*/
function check_old_value(frm,child) {
  if(child.employee) {
    frappe.call({
      method:
        "tag_workflow.tag_workflow.doctype.assign_employee.assign_employee.check_old_value",
      args: {name: child.name},
      callback: function(r) {
        let emp=r.message;
        if(emp[0]!=child.employee) {
          update_replaced_emp(frm,emp);
        }
      },
    });
  }
}

function update_replaced_emp(frm,emp) {
  let items=frm.doc.items||[];
  let is_emp=1;
  for(let i in items) {
    if(items[i].employee==emp[0]) {
      is_emp=0;
    }
  }

  if(is_emp) {
    let child=frappe.model.get_new_doc("Replaced Employee",frm.doc,"items");
    $.extend(child,{
      employee: emp[0],
      pay_rate: emp[1],
      job_start_time: emp[2],
      job_category: emp[3],
    });
    frm.refresh_field("items");
  }
}

function old_unknown_function(frm) {
  if(frm.doc.employee_details) {
    $('*[data-fieldname="employee_details"]')
      .find(".grid-add-row")[0]
      .addEventListener("click",function() {
        attachrefresh();
      });

    $("[data-fieldname=employee_details]").mouseover(function() {
      attachrefresh();
    });

    attachrefresh();
    employee_resume_fun(frm);
  }
}

function employee_resume_fun(frm) {
  $(document).on("click",'[data-fieldname="employee"]',function() {
    if(
      $('[data-fieldname="employee"]')
        .last()
        .val()!=""
    ) {
      frappe.call({
        method: "tag_workflow.tag_data.joborder_resume",
        args: {
          name: $('[data-fieldname="employee"]')
            .last()
            .val(),
        },
        callback: function(r) {
          if(
            $('[data-fieldname="resume"]')
              .last()
              .text()=="Attach"
          ) {
            frm.doc.employee_details.forEach((element) => {
              if(
                element.employee===
                $('[data-fieldname="employee"]')
                  .last()
                  .val()
              ) {
                element.resume=r.message[0]["resume"];
              }
            });
            frm.refresh_field("employee_details");
          }
        },
      });
    }
  });
}

function add_dynamic(frm) {
  if(frm.doc.company&&frm.doc.__islocal!=1) {
    Array.from($('[data-doctype="Company"]')).forEach((_field) => {
      localStorage.setItem("company",frm.doc.company);
      _field.href="/app/dynamic_page";
    });
  }
}

function select_employees(frm) {
  if(
    (frappe.boot.tag.tag_user_info.company_type=="Hiring"||
      frappe.boot.tag.tag_user_info.company_type=="Exclusive Hiring")&&
    frm.doc.tag_status=="Open"
  ) {
    frm.add_custom_button(__("Select Employees"),function() {
      pop_up(frm);
    });
  }
}

function pop_up(frm) {
  note="";
  let head=`<div class="table-responsive employee_popup"><table class="col-md-12 my-2 basic-table table-headers table table-hover"><thead><tr><th><input type="checkbox" class="grid-row-check pull-left" onclick="select_all1()" id="all"></th><th>Employee ID</th><th>Job Title</th><th>Start Time</th><th>Employee Name</th><th>Resume</th><th></th></tr></thead><tbody>`;
  let html=``;

  for(let d in frm.doc.employee_details) {
    let resume=frm.doc.employee_details[d].resume.split("/");
    let resume1=resume[resume.length-1];
    html+=`<tr>
    <td><input type="checkbox" id="${frm.doc.employee_details[d].employee}---${((frm.doc.employee_details[d].job_category).replaceAll(" ","_")).replace(/[`~!@#$%^&*()_|+=?;:'",.<>{}[\]\\/]/gi,'-')}---${(frm.doc.employee_details[d].job_start_time).replace(":","_")}" </td>
		<td>${frm.doc.employee_details[d].employee}</td>
    <td>${frm.doc.employee_details[d].job_category}</td>
    <td>${frm.doc.employee_details[d].job_start_time}</td>
		<td>${frm.doc.employee_details[d].employee_name}</td>
    <td>${resume1}</td>
		</tr>`;
  }
  let body;
  if(html) {
    body=head+html+"</tbody></table>";
  } else {
    body=
      head+
      `<tr><td></td><td></td><td>No Data Found</td><td></td><td></td><td></td></tbody></table> </div>`;
  }
  let assign_emp_id=frm.doc.name;

  let notes_field=`<div class="px-3"><p class="mb-1"><label for="w3review">Invoice Notes:</label></p><textarea class="w-100" rows="3" label="Notes" id="_${assign_emp_id}_notes" class="head_count_tittle" maxlength="160" ></textarea><small>Character limit: 160</small> </div>`;
  body=body+notes_field;
  let fields=[
    {fieldname: "custom_notes",fieldtype: "HTML",options: body},
  ];
  let dialog=new frappe.ui.Dialog({
    title: "Select Employees",
    fields: fields,
  });
  dialog.show();
  dialog.$wrapper.find(".modal-dialog").css("max-width","750px");
  populate_notes(frm,dialog,"custom_notes");
  dialog.set_primary_action(__("Submit"),function() {
    update_table(frm,dialog);
  });
}

window.select_all1=function() {
  let all_len=$('[id="all"]').length;
  let all=$('[id="all"]')[all_len-1].checked;
  for(let d in cur_frm.doc.employee_details) {
    let employee=cur_frm.doc.employee_details[d].employee;
    let jobCategory=(cur_frm.doc.employee_details[d].job_category.replaceAll(" ","_")).replace(/[`~!@#$%^&*()_|+=?;:'",.<>{}[\]\\/]/gi,'-')
    let jobStartTime=cur_frm.doc.employee_details[d].job_start_time.replace(":","_")
    let id1=employee+"---"+jobCategory+"---"+jobStartTime;
    let l=$("[id="+id1+"]").length;
    if(all) {
      $("[id="+id1+"]")[l-1].checked=true;
    } else {
      $("[id="+id1+"]")[l-1].checked=false;
    }
  }
};

function update_table(frm,dialog) {
  let data=[];
  let requird_workers_count={}
  let approved_count={}
  let approved_condition=1
  let excess_employees_title=[]
  for(let title in frm.doc.multiple_job_title_details) {
    let time=frm.doc.multiple_job_title_details[title].job_start_time.split(":")
    time.pop()
    time=time.join(":")
    let key=frm.doc.multiple_job_title_details[title].select_job+"~"+time
    requird_workers_count[key]=frm.doc.multiple_job_title_details[title].no_of_workers
  }
  for(let d in frm.doc.employee_details) {
    let employee=cur_frm.doc.employee_details[d].employee;
    let jobCategory=(cur_frm.doc.employee_details[d].job_category.replaceAll(" ","_")).replace(/[`~!@#$%^&*()_|+=?;:'",.<>{}[\]\\/]/gi,'-')
    let jobStartTime=cur_frm.doc.employee_details[d].job_start_time.replace(":","_")
    let id1=employee+"---"+jobCategory+"---"+jobStartTime;
    let l=$("[id="+id1+"]").length;
    if($("[id="+id1+"]")[l-1].checked) {
      data.push([employee,cur_frm.doc.employee_details[d].job_category,cur_frm.doc.employee_details[d].job_start_time]);
      let key=frm.doc.employee_details[d].job_category+"~"+frm.doc.employee_details[d].job_start_time
      if(key in approved_count) {
        approved_count[key]+=1
      }
      else {
        approved_count[key]=1
      }
      if(approved_count[key]>requird_workers_count[key]) {
        approved_condition=0
        !excess_employees_title.includes(key.replace("~","-"))? excess_employees_title.push(key.replace("~","-")):console.log("TAG")
      }
    }
  }
  approved_employee_validation(
    approved_condition,
    data,
    frm,
    dialog,
    excess_employees_title
  );
  dialog.hide();
}

function approved_employee_validation(
  approved_condition,
  data,
  frm,
  dialog,
  excess_employees_title
) {
  if(approved_condition) {
    frappe.call({
      method: "tag_workflow.tag_data.approved_employee",
      args: {
        id: data,
        name: frm.doc.name,
        job_order: frm.doc.job_order,
        assign_note: dialog.fields_dict["custom_notes"].disp_area.querySelector(
          "textarea"
        ).value,
        company: frm.doc.company,
      },
      callback: function(r) {
        if(r.message=="error") {
          frappe.msgprint(
            "No. of selected employees is greater than no. of employees required"
          );
          setTimeout(frm.reload_doc(),2000);
        }
        frm.refresh_field("employee_details");
        frm.reload_doc();
        frm.reload_doc();
      },
    });
  } else {
    frappe.msgprint(
      "No. of selected employees is greater than no. of employees required for job title(s) <br><li><b>"+
      excess_employees_title.join("</li><li>")+
      "</b></li>"
    );
    frm.refresh_field("employee_details");
    frm.reload_doc();
    frm.reload_doc();
  }
}

function pop_up_message(r,frm) {
  if(r.message==1) {
    frappe.msgprint("Email Sent Successfully");
    setTimeout(function() {
      window.location.href="/app/job-order/"+frm.doc.job_order;
    },3000);
  }
}
async function confirm_message(frm,resolve) {
  frappe.call({
    method:
      "tag_workflow.tag_workflow.doctype.assign_employee.assign_employee.check_emp_available",
    args: {
      frm: frm.doc,
    },
    async: 1,
    callback: async function(r) {
      if(r.message[0].length==0||r.message[0]==1) {
        await check_pay_rate(frm,r.message[1]);
        resolve()
      } else {
        const data=await new Promise(function(resolve,reject) {
          let pop_up1;
          let msgSet=new Set();
          for(let i=0;i<=r.message[0].length-1;i++) {
            if(r.message[0][i]["job_order"]!=1) {
              let new_msg=
                "Warning: "+
                r.message[0][i]["employee"]+
                " is scheduled for "+
                r.message[0][i]["job_order"]+
                " within this Job Order’s timeframe.";
              msgSet.add(new_msg);
            }
          }
          let msg1=Array.from(msgSet).join("<br>");
          let pay_msg=pay_rate_message(frm,r.message[1]);
          let pop_up2=duplicate_employee(frm);
          return set_popup(msg1,pop_up1,pay_msg,pop_up2,frm,resolve,reject);
        });
        if(data) {
          resolve()
          return data
        }
        resolve()
        return data
      }
    },
  });
}
function set_popup(msg1,pop_up1,pay_msg,pop_up2,frm,resolve,reject) {
  if(msg1) {
    let dialog_closed_unexpect=true
    pop_up1=pay_msg==""? msg1:msg1+"<hr>"+pay_msg;
    pop_up1=pop_up2==""? pop_up1:pop_up1+"<hr>"+pop_up2;
    let confirm_assign=new frappe.ui.Dialog({
      title: __("Warning"),
      fields: [
        {
          fieldname: "save_joborder",
          fieldtype: "HTML",
          options: pop_up1,
        },
      ],
    });
    confirm_assign.no_cancel();
    confirm_assign.set_primary_action(__("Confirm"),function() {
      window.conf=1;
      confirm_assign.hide();
      dialog_closed_unexpect=false
      frappe.validated=true
      resolve("True");
    });
    confirm_assign.set_secondary_action_label(__("Cancel"));
    confirm_assign.set_secondary_action(() => {
      confirm_assign.hide();
      dialog_closed_unexpect=false
      frappe.validated=false
      resolve("True");
    });
    confirm_assign.show();
    confirm_assign.$wrapper.find(".modal-dialog").css("width","450px");
    confirm_assign.$wrapper.on('hidden.bs.modal',() => {
      if(dialog_closed_unexpect) {
        frappe.validated=false
        resolve("True")
      }
    })
  } else {
    window.conf=1;
    frappe.validated=true
    resolve("True");
  }
}
function add_employee_button(frm) {
  if(frm.doc.tag_status=="Open") {
    frm.fields_dict["employee_details"].grid.cannot_add_rows=false;
    frm.fields_dict["employee_details"].refresh();
  } else {
    frm.fields_dict["employee_details"].grid.cannot_add_rows=true;
    frm.fields_dict["employee_details"].refresh();
  }
}

function assigned_direct(frm) {
  if(
    frm.doc.claims_approved&&
    frm.doc.claims_approved>frm.doc.employee_details.length
  ) {
    frm.set_df_property("employee_details","read_only",0);
  } else {
    frappe.db.get_value(
      "Job Order",
      {name: frm.doc.job_order},
      ["order_status"],
      (r) => {
        if(
          r.order_status!="Completed"&&
          ["Staffing Admin","TAG Admin","Administrator"].includes(
            frappe.boot.tag.tag_user_info.user_type
          )
        ) {
          let table_fields=["employee_name","company","approved"];
          for(let i in table_fields) {
            frm.fields_dict.employee_details.grid.update_docfield_property(
              table_fields[i],
              "read_only",
              1
            );
            frm.refresh_fields();
          }
        } else {
          frm.set_df_property("employee_details","read_only",1);
        }
      }
    );
  }
}

function set_payrate_field(frm) {
  frm.set_df_property(
    "employee_pay_rate",
    "label",
    'Employee Pay Rate <span style="color: red;">&#42;</span>'
  );
  frappe.db.get_value(
    "Job Order",
    {name: frm.doc.job_order},
    ["order_status"],
    (r) => {
      if(r.order_status=="Completed") {
        frm.set_df_property("employee_pay_rate","read_only",1);
        frm.set_df_property("staff_class_code","read_only",1);
        frm.set_df_property("staff_class_code_rate","read_only",1);
      } else {
        $('[data-fieldname = "employee_pay_rate"]').attr("id","emp_pay_rate");
      }
    }
  );
}

function set_pay_rate(frm) {
  frappe.call({
    method:
      "tag_workflow.tag_workflow.doctype.claim_order.claim_order.set_pay_rate",
    args: {
      hiring_company: frm.doc.hiring_organization,
      job_title: frm.doc.job_category,
      job_site: frm.doc.job_location,
      staffing_company: frm.doc.company,
    },
    callback: function(res) {
      let rate=res?.message? res.message.toFixed(2):undefined;
      frm.set_value("employee_pay_rate",rate);
    },
  });
}

function set_pay_rate_class_code(frm) {
  if(frm.doc.__islocal==1) {
    frappe.call({
      method:
        "tag_workflow.tag_workflow.doctype.claim_order.claim_order.get_pay_rate_class_code",
      args: {
        job_order: window.job_order,
        staffing_company: frm.doc.company,
      },
      callback: (res) => {
        frm.doc.multiple_job_title_details.forEach((val) => {
          if(res.message&&val["select_job"] in res.message) {
            frappe.model.set_value(
              val["doctype"],
              val["name"],
              "staff_class_code",
              res.message[val["select_job"]]["comp_code"]
            );
            frappe.model.set_value(
              val["doctype"],
              val["name"],
              "staff_class_code_rate",
              res.message[val["select_job"]]["rate"]
            );
            frappe.model.set_value(
              val["doctype"],
              val["name"],
              "employee_pay_rate",
              res.message[val["select_job"]]["emp_pay_rate"]
            );
          }
        });
        frm.refresh_fields();
      },
    });
  }
}

async function check_pay_rate(frm,pay_rate_details) {
  let msg=pay_rate_message(frm,pay_rate_details);
  let duplicate_emps_msg=duplicate_employee(frm);
  if(msg!=""&&duplicate_emps_msg!="") {
    msg=msg+"<hr>"+duplicate_emps_msg;
  }
  else if(duplicate_emps_msg!="") {
    msg+=duplicate_emps_msg
  }
  const popup_data=await new Promise(function(resolve) {
    if(msg!="") {
      frappe.validated=false;
      let dialog=new frappe.ui.Dialog({
        title: __("Warning!"),
        fields: [
          {fieldname: "check_pay_rate",fieldtype: "HTML",options: msg},
        ],
      });
      dialog.no_cancel();
      dialog.set_primary_action(__("Yes"),function() {
        window.conf=1;
        frappe.validated=true
        dialog.hide();
        resolve("True");
      });
      dialog.set_secondary_action_label(__("No"));
      dialog.set_secondary_action(function() {
        dialog.hide();
        frappe.validated=false
        resolve("True");
      });
      dialog.show();
    }
    else {
      window.conf=1;
      frappe.validated=true;
      resolve("True");
    }
  });
  return !!popup_data;
}

function create_pay_rate(frm) {
  frappe.call({
    method:
      "tag_workflow.tag_workflow.doctype.claim_order.claim_order.create_pay_rate",
    args: {
      hiring_company: frm.doc.hiring_organization,
      job_order: frm.doc.job_order,
      employee_pay_rate: frm.doc.employee_pay_rate,
      staffing_company: frm.doc.company,
    },
  });
}

function field_validation(frm,message) {
  let emp_pay_rate;
  let approved_workers;
  let asigned_titles=[]
  let time;
  for(let each_job_title of frm.doc.employee_details) {
    asigned_titles.push(each_job_title.job_category+"~"+each_job_title.job_start_time)
  }
  for(let each_job_title of frm.doc.multiple_job_title_details) {
    emp_pay_rate=each_job_title.employee_pay_rate;
    approved_workers=each_job_title.approved_workers;
    time=each_job_title.job_start_time;
    time=time.split(":")
    time.pop()
    time=time.join(":")
    if(((frm.doc.resume_required==0&&approved_workers>0)||(frm.doc.resume_required==1&&asigned_titles.includes(each_job_title.select_job+"~"+time)))&&(emp_pay_rate===undefined||!emp_pay_rate||emp_pay_rate==0)) {
      message=message+"<br>Employee Pay Rate";
    }
  }

  let emp_tab=frm.doc.employee_details;
  if(emp_tab===undefined||emp_tab.length==0) {
    message=message+"<br>Employee Details";
  } else {
    for(let i in emp_tab) {
      message=individual_empty_validations(emp_tab,i,message);
    }
  }

  return message+field_validation_contd(frm);
}

function individual_empty_validations(emp_tab,i,message) {
  if(
    !emp_tab[i].job_category||
    (emp_tab[i].job_category==0&&!message.includes("<br>Job Title"))
  ) {
    message=message+"<br>Job Title";
  }
  if(
    !emp_tab[i].job_start_time||
    (emp_tab[i].job_start_time==0&&!message.includes("<br>Start Time"))
  ) {
    message=message+"<br>Start Time";
  }
  if(
    !emp_tab[i].employee||
    (emp_tab[i].employee==0&&!message.includes("<br>Employee"))
  ) {
    message=message+"<br>Employee";
  }
  if(
    !emp_tab[i].pay_rate||
    (emp_tab[i].pay_rate==0&&!message.includes("<br>Pay Rate"))
  ) {
    message=message+"<br>Pay Rate";
  }
  return message;
}

function field_validation_contd(frm) {
  let message="";
  let sign=frm.doc.e_signature_full_name;
  if(frm.doc.resume_required==1) {
    if(sign===undefined||!sign) {
      message=message+"<br>E Signature Full Name";
    }
    if(frm.doc.agree_contract==0||frm.doc.agree_contract===undefined) {
      message=message+"<br>Agree To Contract";
    }
  }
  return message;
}

function negative_pay_rate(frm) {
  let emp_tab=frm.doc.employee_details;
  let mul_titles = frm.doc.multiple_job_title_details
  let is_negative=false;
  for(let i in emp_tab) {
    if(emp_tab[i].pay_rate<0) {
      is_negative=true;
    }
  }

  for(let i in mul_titles) {
    if(mul_titles[i].employee_pay_rate<0) {
      is_negative=true;
    }
  }
  return is_negative
}

function pay_rate_message(frm,pay_rate_details) {
  let msg="";
  let pay_rates=Object.values(pay_rate_details.bill_rate_data);
  pay_rates.forEach((data) => {
    if(data.emp_pay_rate) {
      msg+=
        "Employee Pay Rate of $"+
        data.emp_pay_rate+
        " is greater than the bill rate of $"+
        data.bill_rate+
        " for "+
        frm.doc.job_order+
        ". Please confirm. <br>";
    }
  });

  if(Object.keys(pay_rate_details).includes("employees")) {
    msg+=msg!=""? "<hr>":"";
    msg+=
      "Pay Rate is greater than the bill rate for "+
      frm.doc.job_order+
      " for the below employees. Please confirm.";
    msg+=
      "<br><table style='width:50%'><tr><td><b>Employee Name</b></td><td><b>Pay Rate</b></td></tr>";
    let keys=Object.keys(pay_rate_details.employees);
    keys.forEach((key) => {
      msg+=
        "<tr><td>"+
        key+
        "</td><td>$"+
        pay_rate_details.employees[key]+
        "</td></tr>";
    });
    msg+="</table>";
  }
  return msg;
}

function update_value(frm,r) {
  frm.set_value("claims_approved",r.message[0].approved_no_of_workers);
  frm.set_value("notes",r.message[0].notes);
  if(frm.doc.company != r.message[0].staffing_organization){
    frm.set_value("company",r.message[0].staffing_organization);
    redirected_company = undefined
  }
  frm.set_query("company",function() {
    return {
      filters: [["Company","name","=",r.message[0].staffing_organization]],
    };
  });
  frm.set_df_property("claims_approved","hidden",0);
}
function update_workers_filled(frm) {
  if(frm.doc.__islocal!=1) {
    frappe.call({
      method:
        "tag_workflow.tag_workflow.doctype.assign_employee.assign_employee.update_workers_filled",
      freeze: true,
      freeze_message:"<p><b>please wait while updating data...</b></p>",
      args: {
        job_order_name: frm.doc.job_order,
      },
    });
  }
}

function create_staff_comp_code_new(frm) {
  frm.doc.multiple_job_title_details.forEach((val) => {
    frappe.call({
      method:
        "tag_workflow.tag_workflow.doctype.claim_order.claim_order.create_staff_comp_code_new",
      args: {
        row: val,
        job_title: val.select_job,
        job_site: frm.doc.job_location,
        industry_type: val.category,
        staffing_company: frm.doc.company,
      },
    });
  });
  frm.refresh_fields();
}
function check_class_code(frm) {
  if(frm.doc.__islocal==1) {
    frappe.call({
      method:
        "tag_workflow.tag_workflow.doctype.claim_order.claim_order.check_already_exist_class_code",
      args: {
        job_order: frm.doc.job_order,
        staffing_company: frm.doc.company,
      },
      callback: function(r) {
        if(r.message[0]!="Exist") {
          frm.set_value("staff_class_code",r.message[0]);
          frm.set_value("staff_class_code_rate",r.message[1]);
        }
      },
    });
  }
}
function hide_class_code_rate(frm) {
  if(frm.doc.__islocal==1&&frm.doc.resume_required==0) {
    frm.set_df_property("staff_class_code","hidden",1);
    frm.set_df_property("staff_class_code_rate","hidden",1);
  }
}

function add_notes_button(frm) {
  const role=frappe.boot.tag.tag_user_info.user_type;
  if(
    frm.doc.tag_status=="Approved"&&
    frm.doc.resume_required==1&&
    (role=="Hiring Admin"||role=="Hiring User")
  ) {
    frm.add_custom_button("Update Invoice Notes",() => {
      let d=new frappe.ui.Dialog({
        title: "Update Invoice Notes",
        fields: [
          {
            label: "Invoice Notes",
            fieldname: "modal_notes",
            fieldtype: "Small Text",
            reqd: 1,
          },
        ],
        primary_action_label: "Submit",
        primary_action(values) {
          frappe.call({
            method:
              "tag_workflow.tag_workflow.doctype.assign_employee.assign_employee.update_notes",
            args: {
              name: frm.doc.name,
              notes: values.modal_notes,
              job_order: frm.doc.job_order,
              company: frm.doc.company,
            },
          });
          d.hide();
        },
      });
      d.show();
      populate_notes(frm,d,"modal_notes");
      d.fields_dict["modal_notes"].$wrapper
        .find("textarea")
        .attr("maxlength",160);
    });
  }
}
frappe.realtime.on("sync_data",() => {
  setTimeout(() => {
    frm.reload_doc();
  },200);
});

function check_company_branch(frm) {
  //For Branch Integration
  frappe.db.get_value(
    "Company",
    {name: frm.doc.company},
    ["branch_enabled","branch_org_id","branch_api_key"],
    (res) => {
      if(res.branch_enabled&&res.branch_org_id&&res.branch_api_key) {
        company_branch=1;
      } else {
        company_branch=0;
      }
    }
  );
}

function branch_wallet(frm,company,emp_id,emp_name,cdt,cdn) {
  //For Branch Integration
  if(company_branch==1) {
    frappe.call({
      method: "tag_workflow.utils.branch_integration.get_employee_data",
      args: {
        emp_id: emp_id,
        company: company,
      },
      freeze: true,
      callback: (res) => {
        if(res.message) {
          if(
            res.message.includes("Please")||
            res.message.includes("Branch")
          ) {
            remove_row(frm,res.message,emp_name,cdt,cdn);
            frappe.msgprint(res.message);
            frappe.validated=false;
          } else if(Number(res.message)) {
            frappe.db.set_value(
              "Employee",
              emp_id,
              "account_number",
              res.message
            );
          }
        }
      },
    });
  }
}

function remove_row(frm,message,emp_name,cdt,cdn) {
  //For Branch Integration
  if(message!="Enable Branch for "+emp_name+".") {
    let fields=[
      "employee",
      "employee_name",
      "resume",
      "pay_rate",
      "remove_employee",
      "job_category",
      "company",
    ];
    for(let field in fields) {
      frappe.model.set_value(cdt,cdn,fields[field],"");
    }
    frm.refresh_field("employee_details");
  }
}

function check_mandatory_field(emp_id,emp_name) {
  frappe.call({
    method: "tag_workflow.tag_data.check_mandatory_field",
    args: {emp_id: emp_id,check: 0,emp_name: emp_name},
    callback: function(r) {
      let msg=
        r.message[1]+
        " is missing the below required fields. You will be unable to approve their timesheets unless these fields are populated.<br><br>";
      if(r.message!="success") {
        msg+=r.message[0];
        frappe.msgprint({
          message: __(msg),
          title: __("Warning"),
          indicator: "yellow",
        });
      }
    },
  });
}
function update_claim_approve(frm) {
  if(
    frappe.boot.tag.tag_user_info.company_type=="Staffing"&&
    frm.doc.resume_required==0&&
    frm.doc.job_order
  ) {
    frappe.call({
      method:
        "tag_workflow.tag_workflow.doctype.assign_employee.assign_employee.approved_workers",
      args: {
        job_order: frm.doc.job_order,
        user_email: frappe.session.user_email,
      },
      async: 0,
      callback: function(r) {
        if(r.message.length!=0) {
          update_value(frm,r);
        }
      },
    });
  }
}
jQuery(document).on("click",".grid-remove-rows",function() {
  remove_cache_data();
});

function remove_cache_data() {
  if(cur_frm.doc.company&&cur_frm.doc.job_order) {
    frappe.call({
      method:
        "tag_workflow.tag_workflow.doctype.assign_employee.assign_employee.free_redis",
      args: {company: cur_frm.doc.company,job_order: cur_frm.doc.job_order},
    });
  }
}

function populate_notes(frm,dialog,field) {
  if(frm.doc.notes) {
    if(field=="custom_notes")
      dialog.fields_dict[field].disp_area.querySelector("textarea").value=
        frm.doc.notes;
    else {
      dialog.fields_dict[field].value=frm.doc.notes;
      dialog.fields_dict[field].refresh();
    }
  }
}

function add_notes(frm) {
  if(
    frm.is_new()&&
    frappe.boot.tag.tag_user_info.company_type=="Staffing"&&
    frm.doc.company&&
    frm.doc.job_order
  ) {
    frappe.call({
      method:
        "tag_workflow.tag_workflow.doctype.assign_employee.assign_employee.add_notes",
      args: {company: frm.doc.company,job_order: frm.doc.job_order},
      callback: (r) => {
        if(r.message.length>0) {
          frm.set_value("notes",r.message[0]["notes"]);
          frm.refresh_field("notes");
        }
      },
    });
  }
}

function set_multiple_title_filters(frm) {
  frm.set_query("job_category","employee_details",function(doc,cdt,cdn) {
    return {
      query:
        "tag_workflow.tag_workflow.doctype.assign_employee.assign_employee.get_jobtitle_list_assign_employee",
      filters: {
        resume_required: frm.doc.resume_required,
        job_order: doc.job_order,
        company: frm.doc.company,
      },
    };
  });
}

function multiple_job_title_details_update_data(frm) {
  if(frm.is_local!=1 && frm.doc.resume_required==0) {
    frappe.call({
      method:
        "tag_workflow.tag_workflow.doctype.assign_employee.assign_employee.multiple_job_titles_sql_query",
      args: {
        job_order: frm.doc.job_order,
        resume_required: frm.doc.resume_required,
        staffing_company: frm.doc.company
      },
      callback: function(r) {
        if(r.message.length) {
          let data = r.message
          let updated_count_object = {}
          for(let item of data) {
              let worker_key = item.select_job+"~"+item.job_start_time
              updated_count_object[worker_key] = [item.no_of_workers,item.approved_no_of_workers]
          }
          update_workers_total_and_approved(frm,updated_count_object);
        }
      },
    });
  }
}

function update_workers_total_and_approved(frm,updated_count_object) {
  for(let each_title of frm.doc.multiple_job_title_details) {
    let title_worker_key=each_title.select_job+'~'+each_title.job_start_time;
    let updated_count=updated_count_object[title_worker_key];
    if(updated_count) {
      if(updated_count[0]!=each_title.no_of_workers) {
        frappe.model.set_value(
          each_title.doctype,
          each_title.name,
          "no_of_workers",
          updated_count[0]
        );
      }
      if(updated_count[1]!=each_title.approved_workers) {
        frappe.model.set_value(
          each_title.doctype,
          each_title.name,
          "approved_workers",
          updated_count[1]
        );
      }
      frm.refresh_field("multiple_job_title_details");
    }
  }
}

function set_start_time_filters(frm) {
  frappe.call({
    method:
      "tag_workflow.tag_workflow.doctype.assign_employee.assign_employee.get_start_time_list_assign_employee",
    args: {
      resume_required: frm.doc.resume_required,
      job_order: frm.doc.job_order,
      company: frm.doc.company,
    },
    async: 0,
    callback: function(r) {
      frm.fields_dict["employee_details"].grid.update_docfield_property(
        "job_start_time",
        "options",
        r.message
      );
    },
  });
}

function calculateEndTime(startTime,hours) {
  // Parsing the start time string
  const [startHours,startMinutes]=startTime.split(":").map(Number);

  // Creating a new Date object with the start time
  const startDate=new Date();
  startDate.setHours(startHours);
  startDate.setMinutes(startMinutes);

  // Adding the hours to the start time
  const endDate=new Date(startDate.getTime()+hours*60*60*1000);

  // Formatting the end time
  const endHours=endDate
    .getHours()
    .toString()
    .padStart(2,"0");
  const endMinutes=endDate
    .getMinutes()
    .toString()
    .padStart(2,"0");
  const endTime=`${endHours}:${endMinutes}`;

  return endTime;
}

function compareTimes(time1,time2) {
  const [hours1,minutes1]=time1.split(":").map(Number);
  const [hours2,minutes2]=time2.split(":").map(Number);

  if(hours1<hours2) {
    return false;
  } else if(hours1>hours2) {
    return true;
  } else if(minutes1<minutes2) {
      return false;
    } else if(minutes1>minutes2) {
      return true;
    } else {
      return false;
    }
}

function resume_download(){
  $('[data-fieldtype="Attach"]').on("click", (e) => {
    e.stopPropagation();
    document_download(e);
  });
}