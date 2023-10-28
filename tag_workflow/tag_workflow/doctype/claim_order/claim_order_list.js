window.is_submit=0;
frappe.listview_settings["Claim Order"] = {
  add_fields: ["job_order_status"],
  onload(listview){
    if(!["Hiring","TAG"].includes(frappe.boot.tag.tag_user_info.company_type)){
      listview.columns.splice(4, 1);
      listview.render_header(listview.columns[4]);
    }
    $('[data-original-title="ID"]>input').attr("placeholder", "Name");
    listview.columns[0].df.label="Name";
    listview.render_header(listview);
  },
  refresh(listview) {
    $('[class="btn btn-primary btn-sm primary-action"]').show();
    $(".custom-actions.hidden-xs.hidden-md").show();
    listview.page.clear_primary_action();
    $("button.btn.btn-default.btn-sm.filter-button").hide();
    $("button.btn.btn-sm.filter-button.btn-primary-light").hide();
    if(listview.data.some(obj => !["Canceled", "Completed"].includes(obj["job_order_status"]))){  
      if (
        listview.data.some(obj => obj["approved_no_of_workers"] != 0) &&
        frappe.boot.tag.tag_user_info.company_type != "Staffing"
      ) {
        modify_headcount_dialog(listview);
      } else if (
        listview.filters.length == 1 &&
        frappe.boot.tag.tag_user_info.company_type != "Staffing"
      ) {
        listview.page.set_secondary_action("Select Head Count", () => {
          select_headcount_dialog(listview);
        },"octicon octicon-sync").addClass("btn-primary");
        let sec_btn = $('.btn.btn-secondary.btn-default.btn-sm');
        sec_btn.attr('id', 'popup_inactive');
        sec_btn.click(() => {
          sec_btn.prop('disabled', true);
          if(sec_btn.attr('id')=='popup_inactive'){
            select_headcount_dialog(listview);
          }
        });
      } else if (
        listview.filters.length == 2 &&
        frappe.boot.tag.tag_user_info.company_type != "Staffing"
      ) {
        modify_headcount_dialog(listview);
      }
    }
    listview.page.remove_inner_button("Add Additional Claims")
    add_more_claim(listview);
    hide_buttons(listview);
  },
  hide_name_column: true,
  /*button: {
		show: function(doc) {
			return doc.name;
		},
		get_label: function() {
			return __('View Profile');
		},
		get_description: function(doc) {
			return __('Open {0}', [`"Claim Order" ${doc.name}`]);
		},
		action: function(doc) {
			frappe.set_route('Form', "Claim Order", doc.name);

		}
	},*/
  formatters: {
    staffing_organization(val, d, f) {
      if (val) {
        let link = val.split(" ").join("%");
        return `
        <span class=" ellipsis" title="" id="${val}-${f.name}">
          <a class="ellipsis" data-fieldname="${val}-${f.name}" onclick=dynamic_route('${link}')>${val}</a>
        </span>
        <script>
          function dynamic_route(name){
            var name1= name.replace(/%/g, ' ');
            localStorage.setItem("company", name1);
            window.location.href = "/app/dynamic_page";
          }
        </script>`;
      }
    },
    job_order(val, d, f) {
      if (val) {
        return `<span class=" ellipsis2" title="" id="${val}-${f.name}">
                        <a class="ellipsis" href="/app/job-order/${val}" data-filter="${d.fieldname},=,${val}" data-fieldname="${val}-${f.name}">${val}</a>
                    </span>`;
      }
    },
    approved_no_of_workers(val, d, f) {
      if (typeof val == "number") {
        return `<span class=" ellipsis3" title="" id="${val}-${f.name}">
                <a class="ellipsis" data-filter="${d.fieldname},=,${val}" data-fieldname="${val}-${f.name}">${val}</a>
            </span>`;
      } else {
        return `<span class=" ellipsis3" title="" id="${val}-${f.name}">
						<a class="ellipsis" data-filter="${d.fieldname},=,${val}" data-fieldname="${val}-${f.name}">0</a>
					</span>`;
      }
    },
    staff_claims_no(val, d, f) {
      if (val){
        return `<span class=" ellipsis4" title="" id="${val}-${f.name}">
						<a class="ellipsis" data-filter="${d.fieldname},=,${val}" data-fieldname="${val}-${f.name}">${val}</a>
					</span>`;
      }else{
        return `<span class=" ellipsis4" title="" id="${val}-${f.name}">
						<a class="ellipsis" data-filter="${d.fieldname},=,${val}" data-fieldname="${val}-${f.name}">0</a>
					</span>`;
      }
    },
    staffing_organization_ratings (_val, _d, f) {
      let a = 0;
      frappe.call({
        async:false,
         method:"tag_workflow.tag_workflow.doctype.company.company.check_staffing_reviews",
         args:{
           company_name: f.staffing_organization
         },
         callback:(r)=>{
           a = r;
         }
     })
    return a.message === 0 ? '' :`<span><span class='text-warning'>★</span> ${a.message}<span>`;
    },
  },
};

/**
 * This is an asynchronous JavaScript function that calls a Frappe method to check staffing reviews for
 * a given company and returns the average rate.
 * @param c - The parameter `c` is a string representing the name of a company. It is used as an
 * argument for the `check_staffing_reviews` function which is called using the `frappe.call` method.
 * The function is expected to return the average rate of staffing reviews for the given company.
 * @returns The `get_average_rate` function is returning the result of the `frappe.call` method, which
 * is a Promise object. The actual result of the function will depend on the resolution of the Promise,
 * which will be the value returned by the `callback` function passed to `frappe.call`.
 */
function get_average_rate(c){
 return frappe.call({
   async:false,
		method:"tag_workflow.tag_workflow.doctype.company.company.check_staffing_reviews",
		args:{
			company_name: c
		},
    callback:(r)=>{
      return r.message
    }
  })
}

/**
 * The function refresh retrieves data and displays it in a popup dialog for the user to select
 * headcount and approve claims for a job order.
 * @param listview - The parameter `listview` is a variable that is being passed as an argument to the
 * `refresh` function. It is likely an object that contains data related to a list view in the user
 * interface. The function uses this data to make a server call and display a popup dialog with
 * information related to
 */
function select_headcount_dialog(listview) {
  frappe.call({
    method:
      "tag_workflow.tag_workflow.doctype.claim_order.claim_order.order_details",
    args: {
      doc_name: listview.data[0].job_order,
    },
    freeze:true,
    callback: function (rm) {
      let date_sequence = checking_same_date(rm.message[1])
      let data = rm.message[0];
      let profile_html = `<table id = "select_headcount"><tr id="header"><th>Staffing Company</th><th>Avg. Rating</th><th>Job Title</th><th>Industry</th><th>Start Time</th><th>Available Claims</th><th>Requested Claims</th><th>Approve</th><th>Invoice Notes</th></tr>`;
      profile_html=html_data_select_headcount(data,profile_html);

      let new_pop_up = new frappe.ui.Dialog({
        id: "select_headcount_dialog",
        title: "Select Head Count",
        fields: [
          {
            fieldname: "html_job_order",
            fieldtype: "HTML",
            options: "<label>Job Order:</label>" + listview.data[0].job_order,
          },

          { fieldname: "inputdata2", fieldtype: "Column Break" },

          {
            fieldname: "html_date",
            fieldtype: "HTML",
            options: date_sequence
          },
          { fieldname: "inputdata1", fieldtype: "Section Break" },
          {
            fieldname: "staff_companies",
            fieldtype: "HTML",
            options: profile_html,
          },
        ],
        primary_action: function () {
          window.is_submit = 1;
          let headcount_table = document.getElementById('select_headcount');
          new_pop_up.hide();
          let approved_data = select_headcount_warnings(headcount_table);
          if (approved_data[0] && Object.keys(approved_data[1]).length > 0) {
            frappe.call({
              method:
                "tag_workflow.tag_workflow.doctype.claim_order.claim_order.save_claims",
              args: {
                "approved_data" : approved_data[1],
                "doc_name": listview.data[0].job_order,
              },
              callback: function (r1) {
                if (r1.message) {
                  frappe.msgprint("Email Sent Successfully");
                  setTimeout(function () {
                    window.location.href =
                      "/app/job-order/" + listview.data[0].job_order;
                  }, 3000);
                }
              },
            });
          }
        },
      });
      show_popup(new_pop_up);
    },
  });
}

/**
 * The function generates HTML table rows based on input data and returns the resulting HTML string.
 * @param data - The data parameter is an object containing information about job orders, such as job
 * title, industry, start time, duration, number of workers, staff claims, notes, bill rate, and
 * staffing organization.
 * @param profile_html - The HTML code that will be generated by the function and returned as a string.
 * @returns a string variable `profile_html` which contains an HTML table with data from the `data`
 * parameter and additional HTML elements generated by the function.
 */
function html_data_select_headcount(data,profile_html) {
  for(let p in data) {
    let time = data[p].start_time.split(":")

    profile_html+=`<tr>
    <td>${data[p].staffing_organization}</td>
    <td>${data[p].avg_rate==0?'':`<span class='text-warning'>★ </span> ${parseFloat(data[p].avg_rate).toFixed(1)}`}</td>
    <td style="margin-right:20px;">${data[p].job_title}</td>
    <td>${data[p].industry}</td>
    <td>${time[0].padStart(2, '0')+":"+time[1]}</td>
    <td style="text-align: center;">${data[p].no_of_workers_joborder}</td>
    <td style="text-align: center;">${data[p].staff_claims_no}</td>
    <td><input type="number" min="0" max=${data[p].staff_claims_no}></td>
    <td><textarea class="head_count_title" data-comp="${data[p].staffing_organization}" maxlength="160">${(data[p].notes)? data[p].notes:""}</textarea></td>
    </tr>`;
  }
  profile_html+=`</table>`;
  return profile_html;
}

/**
 * The function shows a popup and adds a listener to it if a certain button is active.
 * @param new_pop_up - The parameter `new_pop_up` is likely an object that represents a popup window or
 * modal that can be displayed on a web page. The function `show_popup` takes this object as an
 * argument and sets up an event listener to detect when the popup is closed. It then checks if another
 * popup is
 */
function show_popup(new_pop_up){
  let sec_btn = $('.btn.btn-secondary.btn-default.btn-sm');
  new_pop_up.$wrapper.on('hidden.bs.modal', () => {
    sec_btn.prop('disabled', false).attr('id', 'popup_inactive');
    if(!window.is_submit) location.reload();
  });
  if(sec_btn.attr('id')=='popup_inactive'){
    sec_btn.attr('id', 'popup_active');
    new_pop_up.show();
    add_listener(new_pop_up,'staff_companies');
  }
}

/**
 * The function selects headcount warnings based on data from a headcount table and returns a
 * dictionary of approved data and a boolean indicating if the data is valid.
 * @param headcount_table - The input parameter is a table containing headcount data, which includes
 * information such as job title, industry, required number of workers, number of workers claimed by
 * staffing company, number of workers approved by hiring, and notes.
 * @returns an array with two elements: a boolean value indicating whether the headcount warnings are
 * valid or not, and an object containing approved headcount data for each staffing company.
 */
function select_headcount_warnings(headcount_table){
  let approved_data = {};
  let more_claim_dict = {};
  let valid = true;
  let total_approved = 0;
  let messages = {
    'No Of Workers cannot be less than 0 for:': [],
    'Claims approved cannot be greater than the no. of workers claimed by Staffing Company for:': [],
    'You cannot approve workers greater than the no. of workers required for:': []
  }
  for(let row=1; row<headcount_table.rows.length; row++){
    let data = headcount_table.rows[row];
    if(data?.id == "header"){ continue;}

    let total_reqd_workers = parseInt(data.cells[5].innerText); //Total required
    let staff_claims_no = parseInt(data.cells[6].innerText); //Number Claimed by Staffing
    let hiring_approved_no = parseInt(data.cells[7].lastChild.value) || 0; //Number getting approved by hiring
    let notes = data.cells[8].firstChild.value; //Notes by hiring
    let staffing_comp = data.cells[0].innerText;
    let job_title = data.cells[2].innerText;
    let start_time = data.cells[4].innerText;
    let msg = `${job_title} at ${start_time} by ${staffing_comp}`;

    check_notes_length(notes,staffing_comp);
    more_claim_dict[job_title + " at " + start_time] = (more_claim_dict[job_title + " at " + start_time] || 0) + hiring_approved_no;
    total_approved += hiring_approved_no;
    if (hiring_approved_no < 0) {
      valid = false;
      messages['No Of Workers cannot be less than 0 for:'].push(`&#x2022 <b>Row ${row}</b>: ${msg}`)
    }else if(hiring_approved_no > staff_claims_no){
      valid = false;
      messages['Claims approved cannot be greater than the no. of workers claimed by Staffing Company for:'].push(`&#x2022 <b>Row ${row}</b>: ${msg}`)
    }else if(more_claim_dict[job_title+" at "+start_time] > total_reqd_workers){
      valid = false;
      messages['You cannot approve workers greater than the no. of workers required for:'].push(`&#x2022 <b>Row ${row}</b>: ${msg}`)
    }else if (staff_claims_no != 0) {
      let my_data = {
        "job_title" : job_title,
        "industry" : data.cells[1].innerText,
        "start_time" : start_time,
        "approved_no_of_workers" : hiring_approved_no,
        "notes" : notes,
      };
      approved_data = update_dict(approved_data, staffing_comp, my_data);
    }
  }
  if(!total_approved){
    frappe.msgprint({
      message: __("Approve at least one claim to submit."),
      title: __("Error"),
      indicator: "red",
    });
    setTimeout(()=>{
      location.reload();
    }, 5000);
    return [false, {}]
  }else if(Object.values(messages).some(value => value.length>0)){
      display_msg(messages);
    }else{
      return [valid, approved_data]
    }
}

/**
 * The function modifies the head count of a job order and displays a pop-up window to update the head
 * count data.
 * @param listview - The `listview` parameter is an object that represents a list view in the Frappe
 * framework. It is used as an input to the `modify_head_count` function to set a secondary action on
 * the page and to the `modify_claims` function to retrieve data for a specific job order from
 */
function modify_headcount_dialog(listview) {
  listview.page.set_secondary_action("Modify Head Count", () => {
    modify_claims(listview);
  },"octicon octicon-sync").addClass("btn-primary");
  let sec_btn = $('.btn.btn-secondary.btn-default.btn-sm');
  sec_btn.attr('id', 'popup_inactive');
  sec_btn.click(function() {
    if(sec_btn.attr('id')=='popup_inactive'){
      sec_btn.prop('disabled', true);
      modify_claims(listview);
    }
  });
}

/**
 * The function modifies the headcount of a job order and displays a pop-up window to update the claims
 * approved and invoice notes.
 * @param listview - The `listview` parameter is likely an object that contains data about a list view
 * in the user interface. It is used as an input to the `modify_claims` function to retrieve the
 * `job_order` value from the first item in the list view data.
 */
function modify_claims(listview) {
  frappe.call({
    method:
      "tag_workflow.tag_workflow.doctype.claim_order.claim_order.modify_heads",
    args: {
      doc_name: listview.data[0].job_order,
    },
    freeze:true,
    callback: function (rm) {
      let job_data = rm.message[0];
      let date_value = checking_same_date(rm.message[1])
      let profile_html = `<table id = "modify_headcount" class="table-responsive"><tr id="header"><th>Claim No.</th><th>Staffing Company</th><th>Avg. Rating</th><th>Job Title</th><th>Start Time</th><th>Available Claims</th><th>Requested Claims</th><th>Claims Approved</th><th>Modify Claims Approved</th><th>Invoice Notes</th><th style="display:none;">Worker filled</th></tr>`;
      profile_html= html_data_modify_claims(job_data,profile_html);
      profile_html += `</table><style>th, td {padding: 10px;} input{width:100%;}</style>`;

      let modified_pop_up = new frappe.ui.Dialog({
        title: "Modify Head Count",
        id: "modify_headcount",
        fields: [
          {
            fieldname: "html_job_title",
            fieldtype: "HTML",
            options: "<label>Job Order:</label>" + listview.data[0].job_order,
          },
          {
            fieldname: "html_job_title",
            fieldtype: "HTML",
            options: "<label>Total Required:</label>" + rm.message[1][0][3],
          },
          { fieldname: "inputdata3", fieldtype: "Column Break" },
          {
            fieldname: "html_date1",
            fieldtype: "HTML",
            options: date_value
          },
          {
            fieldname: "html_job_title",
            fieldtype: "HTML",
            options: "<label>Remaining Workers Needed:</label>" + (rm.message[1][0][3]-rm.message[2]),
          },
          { fieldname: "inputdata2", fieldtype: "Section Break" },
          {
            fieldname: "staff_companies1",
            fieldtype: "HTML",
            options: profile_html,
          },
        ],
        primary_action: function () {
          window.is_submit=1;
          let headcount_table = document.getElementById('modify_headcount');
          modified_pop_up.hide();
          let updated_data = modified_headcount_warnings(headcount_table);
          update_db_modified(updated_data, listview.data[0].job_order);
        },
      });
      let sec_btn = $('.btn.btn-secondary.btn-default.btn-sm');
      modified_pop_up.$wrapper.on('hidden.bs.modal', () => {
        sec_btn.prop('disabled', false).attr('id', 'popup_inactive');
        if(!window.is_submit) location.reload();
      });
      if(sec_btn.attr('id')=='popup_inactive'){
        sec_btn.attr('id', 'popup_active');
        modified_pop_up.show();
        add_listener(modified_pop_up,'staff_companies1');
      }
    },
  });
}

/**
 * The function modifies HTML data by iterating through job data and adding relevant information to a
 * table.
 * @param job_data - An array of objects containing job data such as job name, staffing organization,
 * average rate, job title, start time, duration, number of workers for the job order, staff claims
 * number, approved number of workers, notes, and worker filled status.
 * @param profile_html - The HTML code that will be modified and returned by the function.
 * @returns the modified `profile_html` string after iterating through the `job_data` array and
 * appending HTML table rows to it.
 */
function html_data_modify_claims(job_data,profile_html) {
  window.total_filled_dict_comp = {};
  window.total_required_dict = {};
  for(let p in job_data) {
    let time = job_data[p].start_time.split(":");
    window.total_required_dict[`${job_data[p].job_title} at ${time[0].padStart(2, '0')+":"+time[1]}`] = job_data[p].no_of_workers_joborder;
    window.total_filled_dict_comp[`${job_data[p].job_title} at ${time[0].padStart(2, '0')+":"+time[1]} by ${job_data[p].staffing_organization}`] = job_data[p].worker_filled;

    profile_html+=`<tr>
      <td>${job_data[p].name}</td>
      <td style="margin-right:20px;">${job_data[p].staffing_organization}</td>
      <td>${job_data[p].avg_rate==0? '':`<span class='text-warning'>★</span> ${parseFloat(job_data[p].avg_rate).toFixed(1)}`}</td>
      <td>${job_data[p].job_title}</td>
      <td>${time[0].padStart(2, '0')+":"+time[1]}</td>
      <td style="text-align: center;">${job_data[p].no_of_workers_joborder}</td>
      <td style="text-align: center;">${job_data[p].staff_claims_no}</td>
      <td style="text-align: center;">${job_data[p].approved_no_of_workers}</td>
      <td><input type="number" min="0" max=${job_data[p].staff_claims_no}></td>
      <td><textarea class="head_count_title" data-comp="${job_data[p].staffing_organization}" maxlength="160">${(job_data[p].notes)?(job_data[p].notes).trim():""}</textarea></td>
      <td style="display:none;">${job_data[p].worker_filled}</td>
    </tr>`;
  }
  return profile_html;
}

/**
 * The function `modified_headcount_warnings` checks and updates data related to hiring and staffing,
 * and returns relevant information.
 * @param headcount_table - A table containing data about the headcount, including the number of
 * workers required, claimed by staffing, approved by hiring, and modified by hiring.
 * @param data - The `data` parameter is an input to the `modified_headcount_warnings` function. It is
 * likely an object or an array that contains information about the headcount table and is used to
 * perform various calculations and checks within the function. However, without seeing the full code
 * and context, it is difficult
 * @returns an array with three elements: updated_data, valid, and notes_dict.
 */
function modified_headcount_warnings(headcount_table){
  let updated_data = {};
  let total_claim_dict_comp = {};
  let updated_claim_dict = {};
  let notes_dict = {};
  let messages = {
    'No Of Workers are same as previously assigned for:': [],
    'No Of Workers cannot be less than 0 for:': [],
    'Claims approved cannot be greater than the no. of workers claimed by Staffing Company for:': [],
    'You cannot approve workers greater than the no. of workers required for:': []
  };
  let valid = true;
  let total_approved = 0;
  let total_approved_old = 0;
  for(let row=1; row<headcount_table.rows.length; row++){
    let data = headcount_table.rows[row];
    if(data?.id == "header"){ continue;}

    let claim_name = "~"+data.cells[0].innerText;
    let staffing_comp = data.cells[1].innerText;
    let job_title = data.cells[3].innerText;
    let start_time = data.cells[4].innerText;
    let staff_claims_no = parseInt(data.cells[6].innerText); //Number Claimed by Staffing
    let hiring_approved_no = parseInt(data.cells[7].innerText); //Number approved by hiring
    let hiring_updated_no = data.cells[8].lastChild.value; //Number getting modified by hiring
    let notes = data.cells[9].firstChild.value; //Notes by hiring
    let msg = `${job_title} at ${start_time} by ${staffing_comp}`;
    check_notes_length(notes, staffing_comp);

    if (hiring_updated_no.length && parseInt(hiring_updated_no) == hiring_approved_no) {
      valid = false;
      messages['No Of Workers are same as previously assigned for:'].push(`&#x2022 <b>Row ${row}</b>: ${msg}`);
      total_approved = parseInt(hiring_updated_no);
    }

    hiring_updated_no = hiring_updated_no.length?parseInt(hiring_updated_no):hiring_approved_no;
    updated_claim_dict[job_title+" at "+start_time] = (updated_claim_dict[job_title+" at "+start_time] || 0) + hiring_updated_no;
    total_claim_dict_comp[msg] = (total_claim_dict_comp[msg] || 0) + hiring_updated_no;
    notes_dict[data.cells[0].innerText] = notes.trim();
    total_approved_old += hiring_approved_no;
    if(hiring_updated_no < 0){
      valid = false;
      messages['No Of Workers cannot be less than 0 for:'].push(`&#x2022 <b>Row ${row}</b>: ${msg}`);
    }else if(hiring_updated_no > staff_claims_no){
      valid=false;
      messages['Claims approved cannot be greater than the no. of workers claimed by Staffing Company for:'].push(`&#x2022 <b>Row ${row}</b>: ${msg}`);
    }else {
      let my_data = {
        "job_title" : job_title,
        "industry" : data.cells[1].innerText,
        "start_time" : start_time,
        "updated_approved_no" : hiring_updated_no,
        "workers_filled": parseInt(data.cells[10].innerText),
        "notes" : notes,
      };
      updated_data = update_dict(updated_data, staffing_comp, my_data, claim_name)
    }
  }
  if(total_approved_old==total_approved){
    frappe.msgprint({
      message: __("Update at least one claim to submit."),
      title: __("Error"),
      indicator: "red",
    });
    setTimeout(()=>{
      location.reload();
    }, 5000);
    return [{}, false, {}]
  }
  valid = display_msg(messages, total_claim_dict_comp, updated_claim_dict);
  return [updated_data, valid, notes_dict]
}


/**
 * The function checks if the number of assigned employees is greater than the required number of
 * workers for each claim and generates error messages accordingly.
 * @param messages - The `messages` parameter is an object that stores error messages. It is initially
 * empty and will be updated with error messages based on certain conditions in the code.
 * @param total_claim_dict_comp - The `total_claim_dict_comp` parameter is a dictionary that represents
 * the total number of workers required for each claim. The keys of the dictionary are the claim
 * numbers, and the values are the corresponding total number of workers required for each claim.
 * @param updated_claim_dict - The `updated_claim_dict` parameter is a dictionary that contains the
 * updated number of workers required for each claim. The keys of the dictionary are the claim names,
 * and the values are the updated number of workers required for each claim.
 * @returns the updated "messages" object.
 */
function worker_filled(messages, total_claim_dict_comp, updated_claim_dict){
  for(let claim in total_claim_dict_comp){
    if(window.total_filled_dict_comp[claim] > total_claim_dict_comp[claim]){
      if(Object.values(messages).indexOf(claim) > -1){
        messages[`${window.total_filled_dict_comp[claim]} Employees are assigned to this order. Number of required workers must be greater than or equal to number of assigned employees. Please modify the number of workers required or work with the staffing companies to remove an assigned employee.`].push(`&#x2022 ${claim}`)
      }else{
        messages[`${window.total_filled_dict_comp[claim]} Employees are assigned to this order. Number of required workers must be greater than or equal to  number of assigned employees. Please modify the number of workers required or work with the staffing companies to remove an assigned employee.`]=[`&#x2022 ${claim}`];
      }
    }
  }
  for(let claim in updated_claim_dict){
    if(window.total_required_dict[claim] < updated_claim_dict[claim]){
      messages['You cannot approve workers greater than the no. of workers required for:'].push(`&#x2022 ${claim}`);
    }
  }
  return messages;
}

/**
 * The function displays an error message using the Frappe framework and reloads the page after 5
 * seconds.
 * @param message - The message parameter is the text that will be displayed in the pop-up message box.
 * It can be any string or variable that contains a string.
 */
function display_msg(messages, total_claim_dict_comp, updated_claim_dict){
  let valid = true;
  if(Object.values(messages).some(value => value.length>0)){
    valid = false;
  }else{
    messages = worker_filled(messages, total_claim_dict_comp, updated_claim_dict);
    if(Object.values(messages).some(value => value.length>0)){
      valid = false;
    }
  }
  if(!valid){
    let message='';
    for(let key in messages){
      if(messages[key].length>0){
        message+=key+"<br>"+messages[key].join("<br>")+"<hr>"
      }
    }
    frappe.msgprint({
      message: __(message),
      title: __("Error"),
      indicator: "red",
    });
    setTimeout(()=>{
      location.reload();
    }, 5000);
  }
  return valid;
}

/**
 * The function updates a dictionary by adding a new data entry to a list associated with a given key,
 * or creating a new list if the key does not exist.
 * @param dict - This parameter is a dictionary (or object in JavaScript) that will be updated with new
 * data.
 * @param staffing_comp - The name of the staffing company that the data belongs to.
 * @param my_data - It is a variable that represents the data that needs to be added to the dictionary.
 * It could be any type of data such as a string, number, list, or dictionary.
 * @returns the updated dictionary with the new data added to the corresponding staffing company key.
 */
function update_dict(dict, staffing_comp, my_data, claim_name=""){
  if(staffing_comp+claim_name in dict){
    dict[staffing_comp+claim_name].push(my_data);
  }else{
    dict[staffing_comp+claim_name] = []
    dict[staffing_comp+claim_name].push(my_data);
  }
  return dict;
}

/**
 * This function calls a Frappe method to update notes in a claim order.
 * @param notes_dict - The parameter `notes_dict` is a dictionary (an object in JavaScript) that
 * contains data to be passed as an argument to the `update_notes` method. The contents of the
 * dictionary depend on the requirements of the `update_notes` method.
 */
function update_notes(notes_dict){
  frappe.call({
    method: "tag_workflow.tag_workflow.doctype.claim_order.claim_order.update_notes",
    args:{data:notes_dict}
   })
}

/**
 * The function updates a database with modified claims and sends an email notification if successful.
 * @param updated_data - This is a parameter that contains an array of data that has been updated and
 * needs to be saved to the database. The array contains three elements:
 * @param job_order - The job order is a variable that represents the unique identifier of a specific
 * job order in the system. It is used as an argument in the function to identify which job order's
 * data needs to be updated in the database.
 */
function update_db_modified(updated_data,job_order){
  if (updated_data[1]){
    if(Object.keys(updated_data[0]).length > 0){
      frappe.call({
        method:
          "tag_workflow.tag_workflow.doctype.claim_order.claim_order.save_modified_claims",
        args: {
          "doc_name": job_order,
          "updated_data": updated_data[0]
        },
        callback: function (r2) {
          if (r2.message == 1) {
            frappe.msgprint("Email Sent Successfully");
            setTimeout(function () {
              window.location.href =
                "/app/job-order/" + job_order;
            }, 5000);
          }
        },
      });
    }else{
      update_notes(updated_data[2]);
      setTimeout(() => {
       window.location.href =
         "/app/job-order/" + job_order;
     },5000);
    }
  }
}

function check_multi_staffcomp(job_data, data_len,valid1){
  if (valid1!="False"){
  let comp_list = [];
  let second_list = [];
  for (let i = 0; i < data_len; i++){
    if(!comp_list.includes(job_data[i].staffing_organization)){
      comp_list.push(job_data[i].staffing_organization);
    }
    else if(!second_list.includes(job_data[i].staffing_organization)){ 
      second_list.push(job_data[i].staffing_organization)
      }
  }
  if(comp_list.length == second_list.length){
    return check_count(second_list,job_data,data_len);
  }else{
    return check_count_comp_list(comp_list,job_data,data_len);
    
  }
}
}

function check_count(second_list,job_data,data_len){
  for (let i in  second_list){
      let counter = 0 ;
      let assign_worker = 0;
      for(let j=0 ;j<data_len; j++){
        if(second_list[i]==job_data[j].staffing_organization){
          let y = document.getElementById(job_data[j].name).value;
          if (y.length == 0) {
            counter += job_data[j].approved_no_of_workers;
          }
          else{
            counter+= parseInt(y);
            assign_worker = parseInt(job_data[j].assigned_worker);
          }
        }
      }
      // check errror
      if (assign_worker!= 0 &&  counter<assign_worker) {
        frappe.msgprint({
          message: __(`${assign_worker} Employees are assigned to this order. Number of required workers must be greater than or equal to number of assigned employees. Please modify the number of workers required or work with the staffing companies to remove an assigned employee.`),
          title: __("Error"),
          indicator: "red",
        });
        setTimeout(function () {
          location.reload();
        }, 3000);
        return 0
      }
      
    }
    //Success
    return 1;
}

function check_count_comp_list(comp_list,job_data,data_len){
  for (let i in comp_list) {
    let counter = 0;
    let assign_worker = 0;
    for (let j = 0; j < data_len; j++) {
        if (comp_list[i] == job_data[j].staffing_organization) {
            let y = document.getElementById(job_data[j].name).value;
            if (y.length == 0) {
                counter += job_data[j].approved_no_of_workers;
            } else {
                counter += parseInt(y);
                assign_worker = parseInt(job_data[j].assigned_worker);
            }
        }
    }
    //check error
    if (assign_worker != 0 && counter < assign_worker) {
        frappe.msgprint({
            message: __(`${assign_worker} Employees are assigned to this order. Number of required workers must be greater than or equal to number of assigned employees. Please modify the number of workers required or work with the staffing companies to remove an assigned employee.`),
            title: __("Error"),
            indicator: "red",
        });
        setTimeout(function() {
            location.reload();
        }, 3000);
        return 0
    }
  }
  //success
  return 1
}


function check_notes_length(notes,staffing_org){
  let valid1
  if(notes && ((notes).trim()).length>160){
    frappe.msgprint({
      message: __(
        "Only 160 characters are allowed in Notes for "+ staffing_org
      ),
      title: __("Error"),
      indicator: "red",
    });
    valid1 = "False";

    setTimeout(function () {
      location.reload();
    }, 4000);
  }
  return valid1
}


/**
 * The function checks if two dates are the same and returns a formatted string indicating the date
 * range or single date.
 * @param r - The parameter "r" is expected to be an array of length 1 or 2, where each element is a
 * tuple representing a date range. The first element of the tuple is the start date and the second
 * element is the end date.
 * @returns a string that contains the label "Date:" and the formatted date(s) based on the input
 * parameter `r`. If the start and end dates in `r` are the same, the function returns a string with
 * the label and the formatted date. If the start and end dates are different, the function returns a
 * string with the label and the formatted start and end dates separated by
 */
function checking_same_date(r){
  let date_order = "";
  if(frappe.format(r[0][0], { fieldtype: "Date" })==frappe.format(r[0][1], { fieldtype: "Date" })){
    date_order=`<label>Date:</label>${frappe.format(r[0][0],{ fieldtype: "Date" })}`
  }
  else{
    date_order =`<label>Date:</label>${frappe.format(r[0][0], { fieldtype: "Date" })} to ${frappe.format(r[0][1], { fieldtype: "Date" })}`
  }
  return date_order
}

function add_listener(dialog,field){
  dialog.fields_dict[field].disp_area.querySelectorAll('textarea').
  forEach(area=>area.
    addEventListener('keyup',e=>update_textarea(e,field))
  )
}


function update_textarea(e,field){
  cur_dialog.fields_dict[field].disp_area.querySelectorAll('textarea').
  forEach(area=>{
    if(area.attributes['data-comp'].value == e.currentTarget.attributes['data-comp'].value){
      area.value = e.currentTarget.value
    }
  })
}

function add_more_claim(listview){
  if(listview.filters.length>0 && frappe.boot.tag.tag_user_info.company_type == "Staffing"){
    let job_order='';
    for(let i in listview.filters){
      if(listview.filters[i][1]=='job_order'){
        job_order=listview.filters[i][3];
      }
    }
    if(job_order){
      frappe.call({
        method: "tag_workflow.tag_workflow.doctype.claim_order.claim_order.additional_claim",
        args:{"job_order": job_order, "staff_comp": frappe.boot.tag.tag_user_info.comps},
        callback: (res)=>{
          if(res.message && res.message!='no_button'){
            listview.page.add_inner_button('Add Additional Claims', ()=>{
              get_joborder_data(job_order, res.message);
            }).addClass("btn-primary");
          }
        }
      });
    }
  }
}


function get_joborder_data(job_order, message){
  if(message=='new_claim'){
    frappe.call({
      method: "tag_workflow.tag_workflow.doctype.claim_order.claim_order.get_joborder_data",
      args:{"job_order": job_order},
      callback:(s)=>{
        if (s.message) {
          let doc = frappe.model.get_new_doc("Claim Order")
          doc.staffing_organization = frappe.boot.tag.tag_user_info.comps.length > 1?'':frappe.boot.tag.tag_user_info.comps[0];
          doc.job_order = job_order;
          doc.hiring_organization = s.message[1];
          doc.contract_add_on = s.message[2];
          s.message[0].forEach((row)=>{
            if(row.no_of_remaining_employee){
              let row_child = frappe.model.add_child(doc, "Multiple Job Title Claim", "multiple_job_titles");
              row_child.job_title = row.job_title;
              row_child.industry = row.industry
              row_child.start_time = row.start_time;
              row_child.duration = row.duration;
              row_child.no_of_workers_joborder = row.no_of_workers_joborder;
              row_child.no_of_remaining_employee = row.no_of_remaining_employee;
              row_child.bill_rate = row.bill_rate;
            }
          })
          frappe.set_route("Form", "Claim Order", doc.name);
        }
      }
    })
  }else{
    frappe.set_route("Form", "Claim Order", message);
  }
}

function hide_buttons(listview){
  if(!listview.filters.length){
    $('#popup_inactive').hide();
  }
  else if(listview.filters[0].includes("job_order")){
    let job_order = listview.filters[0][3]
    frappe.db.get_value("Job Order", job_order, "order_status").then((res)=>{
      if(res.message["order_status"]=='Completed'){
        $('#popup_inactive').hide();
      }
    });
  }
}
