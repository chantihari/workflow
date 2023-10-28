// Copyright (c) 2022, SourceFuse and contributors
// For license information, please see license.txt
window.draft_start_time='';
window.draft_end_time='';
window.draft_break_start_time='';
window.draft_break_end_time='';
window.pop_up = false;
window.job_title_rate={}
frappe.ui.form.on('Add Timesheet', {
	refresh: function(frm) {
		$('[data-fieldname="items"]').on("keypress", function (event) {
			if (event.key === "Enter") {
			  event.preventDefault();
			}
		  });
		if(frappe.boot.tag.tag_user_info.company_type=='Staffing'){
			frappe.db.get_value("Company", {"parent_staffing": frappe.boot.tag.tag_user_info.company},['name'], function(r){
				if(!r.name){
					window.location.href='/app/job-order'
				}
			});
		}
		frm.disable_save();
		frm.dashboard.set_headline(__(`<div style="display: flex;flex-direction: inherit;"><p>Job Order description will be available here...</p></div>`));
		$(".help-box.small.text-muted").css("display", "none");
		$(".col.layout-main-section-wrapper, .col-md-12.layout-main-section-wrapper").css("max-width", "89%");
		$(".form-message.blue").css("background", "lightyellow");
		$(".form-message.blue").css("color", "black");
		$(".form-message.blue").css("margin-top", "10px");
		$(".editable-form .layout-main-section-wrapper .layout-main-section, .submitted-form .layout-main-section-wrapper .layout-main-section, #page-Company .layout-main-section-wrapper .layout-main-section, #page-Timesheet .layout-main-section-wrapper .layout-main-section, #page-Lead .layout-main-section-wrapper .layout-main-section");
		frm.set_value('date','')
		frm.set_value("from_time", "");
		frm.set_value("to_time", "");
		frm.set_value("break_from_time", "");
		frm.set_value("break_to_time", "");
		frm.add_custom_button(__('Save'), function() {
            if(frm.doc.job_order && frm.doc.date && frm.doc.from_time && frm.doc.to_time && frm.doc.items){
                save_timesheet(frm);
			}
			else{
                update_time_data(frm);
			}
            $('button.btn.btn-default.ellipsis.btn-primary.btn-submit').prop('disabled', false);
		}).addClass("btn-primary");
		frm.add_custom_button(__('Submit Timesheet'), function() {
			submit_timesheet(frm);
		}).addClass("btn-primary btn-submit").prop('disabled', false);

		setTimeout(()=>status_field(frm),1000);
		setTimeout(()=>checking_selected_values(frm),2000);
		if(frm.doc.job_order){
			update_title(frm);
		}
		$(document).on('click', '[data-fieldname="break_from_time"]', function(){
			$('.datepicker').addClass('active');
		});
		$(document).on('click', '[data-fieldname="break_to_time"]', function(){
			$('.datepicker').addClass('active');
		});
		default_time();
	},

	job_order: function(frm){
		$('button.btn.btn-default.ellipsis.btn-primary.btn-submit').prop('disabled', true);
		if(frm.doc.job_order){
			set_def_time(frm);
			show_desc(frm);
			update_title(frm);
		}
		else{
			frm.dashboard.set_headline(__());
			frm.dashboard.set_headline(__(`<div style="display: flex;flex-direction: inherit;"><p>Job Order description will be available here...</p></div>`));
		}
	},
	
	setup:function(frm){
		frm.set_query("job_order", function(){
			return {
				query: "tag_workflow.tag_workflow.doctype.add_timesheet.add_timesheet.job_order_name",
				filters: {
					"company_type": frappe.boot.tag.tag_user_info.company_type,
					"company":frappe.boot.tag.tag_user_info.company
				}	
			}
		});
		/*-------------------------------------*/
		frm.fields_dict['items'].grid.get_field('employee').get_query = function(doc){
			return {
				query: "tag_workflow.utils.timesheet.get_timesheet_employee",
				filters: {
					'job_order': doc.job_order
				}
			}
		};
	},

	date: function(frm){
		$('button.btn.btn-default.ellipsis.btn-primary.btn-submit').prop('disabled', true);
		if(frm.doc.date){
			check_date(frm);
			default_time();
		}
		else{
			set_def_time(frm);
			frm.clear_table("items");
			frm.refresh_field("items");
		}
	},

	from_time: function(frm){
        $('button.btn.btn-default.ellipsis.btn-primary.btn-submit').prop('disabled', true);
		check_break_time(frm, "from_time")
		update_time(frm);
		check_submittable(frm)
	},

	to_time: function(frm){
        $('button.btn.btn-default.ellipsis.btn-primary.btn-submit').prop('disabled', true);
		check_break_time(frm, "to_time")
		update_time(frm);
		check_submittable(frm)
	},

	break_from_time: function(frm){
        $('button.btn.btn-default.ellipsis.btn-primary.btn-submit').prop('disabled', true);
		check_break_time(frm, "break_from_time")
		update_break_time(frm, "break_from");
		check_btn_submittable(frm)
	},

	break_to_time: function(frm){
        $('button.btn.btn-default.ellipsis.btn-primary.btn-submit').prop('disabled', true);
		check_break_time(frm, "break_to_time")
		update_break_time(frm, "break_to");
		check_btn_submittable(frm)
	},
});

/*---------------------------------*/
function update_title(frm){
	frappe.db.get_value("Job Order", {"name": frm.doc.job_order}, ["job_site", "job_order_duration", "from_date", "to_date"], function(r){
		if(r){
			let data = `<div>
					<p><b>Job Site: </b> ${r['job_site']}</p>&nbsp;&nbsp;
					<p><b>Job Duration: </b> ${r['job_order_duration']}</p>&nbsp;&nbsp;
					<p><b>From Date: </b> ${r['from_date']}</p>&nbsp;&nbsp;
					<p><b>To Date: </b> ${r['to_date']}</p>
				</div>`;
			frm.dashboard.set_headline(__());
			frm.dashboard.set_headline(data);
		}
	});
}

/*------------------------------------*/
function check_date(frm){
	if(frm.doc.from_date && frm.doc.to_date){
		if(frm.doc.date > frappe.datetime.now_date()){
			frappe.msgprint("Date can't be future date.");
			frm.set_value("date", "");
		}else if(frm.doc.cancellation_date && frm.doc.date >= frm.doc.cancellation_date){
			frappe.msgprint("Date can't be after cancellation date.");
			frm.set_value("date", "");
		}else if(frm.doc.date >= frm.doc.from_date && frm.doc.date <= frm.doc.to_date){
			frm.set_value('from_time','');
			frm.set_value('to_time','');
			frm.set_value('break_from_time','');
			frm.set_value('break_to_time','');
			show_desc(frm);
		}else{
			frappe.msgprint("Date must be in between Job order start and end date.");
			frm.set_value("date", "");
		}
	}
}

/*------------------------------------*/
function get_employee_data(frm){
	frm.clear_table("items");
	let timesheet_list=localStorage.getItem("timesheet_to_update")
	frappe.call({
		method: "tag_workflow.utils.timesheet.get_timesheet_data",
		args: {
			"job_order": frm.doc.job_order,
			"comp_type": frappe.boot.tag.tag_user_info.company_type,
			'date':frm.doc.date,
			'timesheets_to_update':timesheet_list
		},
		async: 1,
		freeze: true,
		freeze_message: "Please wait while we are fetching data...",
		callback: function(r){
			if(r){
				localStorage.setItem("timesheet_to_update", '');
				frm.clear_table("items");
				let data = r.message[0] || [];
				update_time_values(frm,r.message[1]);
                if(r.message[3]){
                    $('button.btn.btn-default.ellipsis.btn-primary.btn-submit').prop('disabled', false);
                }
				for(let d in data){
					let child = frappe.model.get_new_doc("Timesheet Item", frm.doc, "items");
					$.extend(child, {
						"job_title_time": data[d]['job_title']+", "+data[d]['start_time'],
						"employee": data[d]['employee'],
						"employee_name": data[d]['employee_name'],
						"company": data[d]['company'],
						"status": data[d]['status'],
						"tip_amount": data[d]['tip'],
						"from_time":data[d]['enter_time'],
						"to_time":data[d]['exit_time'],
						"break_from":data[d]['break_from'],
						"break_to":data[d]['break_to'],
						"hours":data[d]['total_hours'],
						"amount":data[d]['billing_amount'],
						"timesheet_value":data[d]['timesheet_name'],
						"overtime_hours":data[d]['overtime_hours'],
						"overtime_rate":data[d]['overtime_rate'],
						"bill_rate": data[d]["bill_rate"],
						"flat_rate": data[d]["flat_rate"],
						"pay_rate": data[d]["pay_rate"]
					});
				}
				frm.refresh_field("items");
                setTimeout(()=>status_field(frm), 700);
			}
		}
	});
}

/*----------------------------------*/
frappe.ui.form.on("Timesheet Item", {
	items_add: function(_frm, cdt, cdn){
		$('button.btn.btn-default.ellipsis.btn-primary.btn-submit').prop('disabled', true);
		let child = frappe.get_doc(cdt, cdn);
		frappe.model.set_value(child.doctype, child.name, "company", "");
	},

	from_time: function(frm, cdt, cdn){
		$('button.btn.btn-default.ellipsis.btn-primary.btn-submit').prop('disabled', true);
		let child = frappe.get_doc(cdt, cdn);
		check_table_break_time(frm, child, "child_from_time");
		update_child_time(child, frm, "from_time");
	},

	to_time: function(frm, cdt, cdn){
		$('button.btn.btn-default.ellipsis.btn-primary.btn-submit').prop('disabled', true);
		let child = frappe.get_doc(cdt, cdn);
		check_table_break_time(frm, child, "child_to_time");
		update_child_time(child, frm, "to_time");
	},

	break_from: function(frm, cdt, cdn){
		$('button.btn.btn-default.ellipsis.btn-primary.btn-submit').prop('disabled', true);
		let child = frappe.get_doc(cdt, cdn);
		check_table_break_time(frm, child, "break_from");
		update_child_time(child, frm, "break_from");
	},

	break_to: function(frm, cdt, cdn){
		$('button.btn.btn-default.ellipsis.btn-primary.btn-submit').prop('disabled', true);
		let child = frappe.get_doc(cdt, cdn);
		check_table_break_time(frm, child, "break_to");
		update_child_time(child, frm, "break_to");
	},

	tip_amount: function(frm, cdt, cdn){
		$('button.btn.btn-default.ellipsis.btn-primary.btn-submit').prop('disabled', true);
		let child = frappe.get_doc(cdt, cdn);
		update_child_time(child, frm, "tip");
	},

	status: function(frm, cdt, cdn){
		$('button.btn.btn-default.ellipsis.btn-primary.btn-submit').prop('disabled', true);
		let child = frappe.get_doc(cdt, cdn);
		update_child_time(child, frm, "status");
	},

	employee: function(frm, cdt, cdn){
		$('button.btn.btn-default.ellipsis.btn-primary.btn-submit').prop('disabled', true);
		let child = frappe.get_doc(cdt, cdn);
		set_job_title(child, frm);
		add_pre_data(child, frm);
        check_replaced_emp(child, frm);
		if(child.job_title_time){
			update_child_time(child, frm, "employee");
		}
		if(!child.bill_rate){
			frappe.model.set_value(cdt, cdn, "bill_rate", 0)
		}
		if(!child.flat_rate){
			frappe.model.set_value(cdt, cdn, "flat_rate", 0)
		}
	},

	job_title_time: function(frm, cdt, cdn){
		$('button.btn.btn-default.ellipsis.btn-primary.btn-submit').prop('disabled', true);
		let child = locals[cdt][cdn];
		if(window.job_title_rate && child.job_title_time in window.job_title_rate){
			frappe.model.set_value(cdt, cdn, "bill_rate", parseFloat(window.job_title_rate[child.job_title_time].split("-")[0]))
			frappe.model.set_value(cdt, cdn, "flat_rate", parseFloat(window.job_title_rate[child.job_title_time].split("-")[1]))
		}
		update_child_time(child, frm, "job_title_name")
	}
});

/*-----------------------------------------*/
function add_pre_data(child, frm){
	if(frm.doc.from_time && frm.doc.to_time){
		frappe.model.set_value(child.doctype, child.name, "from_time", frm.doc.from_time);
		frappe.model.set_value(child.doctype, child.name, "to_time", frm.doc.to_time);
	}

	if(frm.doc.break_from_time && frm.doc.break_to_time){
		frappe.model.set_value(child.doctype, child.name, "break_from", frm.doc.break_from_time);
		frappe.model.set_value(child.doctype, child.name, "break_to", frm.doc.break_to_time);
	}
}

/*-----------------------------------------*/
function update_child_time(child, frm, event){
	let hours = 0;
	let breaks = 0;
	let time_start = new Date();
	let time_end = new Date();
	let break_start = new Date();
	let break_end = new Date();

	if(child.from_time && child.to_time){
		let value_start = child.from_time.split(':');
		let value_end = child.to_time.split(':');
		
		time_start.setHours(value_start[0], value_start[1], 0, 0);
		time_end.setHours(value_end[0], value_end[1], 0, 0);
		hours = ((time_end - time_start)/(1000*60*60));
		if(hours <= 0){
			hours = 0;
		}
	}else{
		make_from_to_zero(child);
	}

	if(child.break_from && child.break_to && child.from_time && child.to_time){
		let bvalue_start = child.break_from.split(':');
		let bvalue_end = child.break_to.split(':');

		break_start.setHours(bvalue_start[0], bvalue_start[1], 0, 0);
		break_end.setHours(bvalue_end[0], bvalue_end[1], 0, 0);
		let break_s = ((break_end - break_start)/(1000*60*60));
		
		if(break_s < 0){
			make_break_zero(child);
		}else if(break_start >= time_start && break_start <= time_end && break_end <= time_end && break_end >= time_start && break_start <= break_end){
			breaks = break_s;
		}else{
			make_break_zero(child);
		}
	}

	if(child.status != "No Show"){
		get_amount(frm, hours, breaks, child, event);
	}else{
		frappe.model.set_value(child.doctype, child.name, "hours", 0);
		frappe.model.set_value(child.doctype, child.name, "amount", 0);
		frappe.model.set_value(child.doctype, child.name, "tip_amount", 0);
		frappe.model.set_value(child.doctype, child.name, "break_from", "");
		frappe.model.set_value(child.doctype, child.name, "break_to", "");
		frappe.model.set_value(child.doctype, child.name, "from_time", "00:00:00");
		frappe.model.set_value(child.doctype, child.name, "to_time", "00:00:00");
	}
}

function make_from_to_zero(child){
	if(!child.from_time){
		frappe.model.set_value(child.doctype, child.name, "from_time", "");
	}else if(!child.to_time){
		frappe.model.set_value(child.doctype, child.name, "to_time", "");
	}
}

function make_break_zero(child){
	frappe.model.set_value(child.doctype, child.name, "break_from", "");
	frappe.model.set_value(child.doctype, child.name, "break_to", "");
}

/*------------------------------------------*/
function get_amount(frm, hours, breaks, child, event){
	let normal_hours = 0.00;
	let overtime_rate = 0.00;
	let overtime_hours = 0.00;
	let total_hour = hours-breaks;
	let job_order=frm.doc.job_order;
	let timesheet_date=frm.doc.date;
	let emp=child.employee;
	if(total_hour>0){
		frappe.model.set_value(child.doctype, child.name, "hours", Math.round(total_hour * 100) / 100);
		frappe.call({
			method:'tag_workflow.tag_workflow.doctype.add_timesheet.add_timesheet.update_list_page_calculation',
			args:{
				timesheet: "None",
				jo: job_order,
				timesheet_date: timesheet_date,
				employee: emp,
				working_hours: total_hour,
				total_flat_rate: child.flat_rate,
				per_hour_rate: child.bill_rate,
				from_time:child.from_time
			},
			callback:function(r){
				if(r.message[1]>0){
						normal_hours = total_hour-r.message[1];
						overtime_hours = r.message[1];
				}else{
					normal_hours = total_hour;
				}		
				if(r.message[1]>0){
					overtime_rate = (child.bill_rate*1.5)+child.flat_rate;
				}
				frappe.model.set_value(child.doctype, child.name, "working_hours", Math.round(normal_hours * 100) / 100);
				frappe.model.set_value(child.doctype, child.name, "overtime_hours", Math.round(overtime_hours * 100) / 100);
				frappe.model.set_value(child.doctype, child.name, "overtime_rate", Math.round(overtime_rate * 100) / 100);
				frappe.model.set_value(child.doctype, child.name, "amount", r.message[0]);
			}
		})
	}
	else{
		frappe.model.set_value(child.doctype, child.name, "hours", Math.round(total_hour * 100) / 100);
		frappe.model.set_value(child.doctype, child.name, "working_hours", Math.round(normal_hours * 100) / 100);
		frappe.model.set_value(child.doctype, child.name, "overtime_hours", 0);
		frappe.model.set_value(child.doctype, child.name, "overtime_rate", 0);
		frappe.model.set_value(child.doctype, child.name, "amount", 0);
	}
	if(event=="status") status_no_show_to_other(frm,child);
}

function status_no_show_to_other(frm,child){
	let statuses=['DNR','Non Satisfactory','Replaced'];
	if(child.from_time=="00:00:00" && child.from_time!=frm.doc.from_time && child.hours==0 && (!child.status || statuses.includes(child.status))){
		frappe.model.set_value(child.doctype, child.name, "from_time", frm.doc.from_time);
	}
	if(child.to_time=="00:00:00" && child.to_time!=frm.doc.to_time && child.hours==0 && (!child.status || statuses.includes(child.status))){
		frappe.model.set_value(child.doctype, child.name, "to_time", frm.doc.to_time);
	}
	if((!child.break_from || child.break_from=="00:00:00") && child.break_from!=frm.doc.break_from_time && child.hours==0 && (!child.status || statuses.includes(child.status))){
		frappe.model.set_value(child.doctype, child.name, "break_from", frm.doc.break_from_time);
	}
	if((!child.break_to || child.break_to=="00:00:00") && child.break_to!=frm.doc.break_to_time && child.hours==0 && (!child.status || statuses.includes(child.status))){
		frappe.model.set_value(child.doctype, child.name, "break_to", frm.doc.break_to_time);
	}
}

/*------------------------------------------*/
function update_time(frm){
	let item = frm.doc.items || [];
	for(let i in item){
		if(item[i].__checked){
			if(frm.doc.from_time && frm.doc.to_time){
				set_time_values(frm, i, item);
			}else{
				frappe.model.set_value(item[i].doctype, item[i].name, "from_time", "");
				frappe.model.set_value(item[i].doctype, item[i].name, "to_time", "");
			}
		}
	}
	window.draft_start_time=frm.doc.from_time;
	window.draft_end_time=frm.doc.to_time;
}

function set_time_values(frm, i, item){
	if(frm.doc.from_time !== window.draft_start_time){
		frappe.model.set_value(item[i].doctype, item[i].name, "from_time", frm.doc.from_time);
		if(!item[i].to_time){
			frappe.model.set_value(item[i].doctype, item[i].name, "to_time", frm.doc.to_time);
		}
	}
	if(frm.doc.to_time !== window.draft_end_time){
		frappe.model.set_value(item[i].doctype, item[i].name, "to_time", frm.doc.to_time);
		if(!item[i].from_time){
			frappe.model.set_value(item[i].doctype, item[i].name, "from_time", frm.doc.from_time);
		}
	}
}

function update_break_time(frm,event){
	let item = frm.doc.items || [];
	for(let i in item){
		if(item[i].__checked){
			if(frm.doc.break_from_time && frm.doc.break_to_time){
				set_break_time_values(frm, i, item, event);
			}else{
				frappe.model.set_value(item[i].doctype, item[i].name, "break_from", "");
				frappe.model.set_value(item[i].doctype, item[i].name, "break_to", "");
			}
		}
	}
}

function set_break_time_values(frm, i, item, event){
	if(event=="break_from"){
		if(frm.doc.break_from_time !== window.draft_break_start_time){
			frappe.model.set_value(item[i].doctype, item[i].name, "break_from", frm.doc.break_from_time);
			if(!item[i].break_to){
				frappe.model.set_value(item[i].doctype, item[i].name, "break_to", frm.doc.break_to_time);
			}
		}
	}else if(frm.doc.break_to_time !== window.draft_break_end_time){
			frappe.model.set_value(item[i].doctype, item[i].name, "break_to", frm.doc.break_to_time);
			if(!item[i].break_from){
				frappe.model.set_value(item[i].doctype, item[i].name, "break_from", frm.doc.break_from_time);
			}
		}
}

/*--------------------------------------------------*/
function save_timesheet(frm){
	if(frm.doc.job_order && frm.doc.date && frm.doc.from_time && frm.doc.to_time && frm.doc.items.length>0){
		let cur_selected = frm.get_selected()||[];
		let duplicate_emp = [];
		let duplicate_msg = [];
		if(cur_selected.items && cur_selected.items.length>=1){
			let items = [];
			let empty_row = 0;
			cur_selected.items.forEach(function(item) {
				let row = locals["Timesheet Item"][item];
				let res = duplicate_emp_msg(row, duplicate_emp, duplicate_msg);
				duplicate_emp = res[0];
				duplicate_msg = res[1];
				if(row.from_time && row.to_time && row.employee && row.job_title_time){
					items.push(row);
				}else{
					empty_row+=1;
				}
			});
			save_timesheet_contd(frm, items, empty_row, duplicate_msg)
		}else{
			frappe.msgprint(__("Please select employee(s) to save/submit the timesheet."))
		}
	}else{
		frappe.msgprint({message: __("(*) fields are required"), title: __('Mandatory'), indicator: 'red'});
	}
}

function save_timesheet_contd(frm, items, empty_row, duplicate_msg){
	if(empty_row){
		frappe.msgprint("Please unselect incomplete row(s) to save the timesheet(s).")
	}else if(duplicate_msg.length){
		frappe.msgprint('Duplicate entries for:<br>' + duplicate_msg.join("<br>"))
	}else{
		let job_order = frm.doc.job_order;
		let date = frm.doc.date;
		let from_time = frm.doc.from_time;
		let to_time = frm.doc.to_time;
		let args1 = {
			"items": items,
			"job_order": job_order,
			"date": date,
			"from_time": from_time,
			"to_time": to_time
		};
		let args2= {
			"selected_items": items,
			"job_order": job_order,
			"date": date,
			"from_time": from_time,
			"to_time": to_time,
			"break_from_time": frm.doc.break_from_time,
			"break_to_time": frm.doc.break_to_time
		};
		save_timesheet_contd2(args1, args2);
	}
}

function save_timesheet_contd2(args1, args2){
	frappe.call({
		method: "tag_workflow.tag_workflow.doctype.add_timesheet.add_timesheet_new.check_timesheets",
		args: args1,
		async: 1,
		freeze: true,
		freeze_message: "Please wait while we are adding the timesheet(s)...",
		callback: (r)=>{
			if(r.message == "success"){
				frappe.call({
					method: "tag_workflow.tag_workflow.doctype.add_timesheet.add_timesheet_new.create_new_timesheet",
					args: args2,
					freeze: true,
					freeze_message: "Please wait while we are adding the timesheet(s)...",
					callback: function(r){
						frappe.msgprint({message: __("Timesheet(s) has been added successfully"), title: __('Successful'), indicator: 'green'});
						for(let i in r.message){
							frappe.model.set_value("Timesheet Item", r.message[i][0], "timesheet_value", r.message[i][1])
						}
					}
				});
			}else{
				frappe.msgprint(r.message.join("<br>"));
			}
		}
	});
}

async function send_for_approval(timesheets) {
    if (timesheets.length) {
		let staffingUserResults = await timesheets.map(time => send_for_approval_contd(time));
		let distinctEmailsSet = new Set();
		staffingUserResults.forEach(subArray => {
		subArray[0].forEach(email => {
			distinctEmailsSet.add(email);
		});
		});
		let staffing_user_app = Array.from(distinctEmailsSet);
        let msg = '';
        if (timesheets.length === 1) {
            msg = `${timesheets[0]["company"]} has submitted a timesheet for ${timesheets[0]["employee_name"]} on ${frappe.datetime.get_today()} for ${timesheets[0]["job_order"]} for approval.`;
        } else {
            msg = `${timesheets[0]["company"]} has submitted a timesheet on ${frappe.datetime.get_today()} for ${timesheets[0]["job_order"]} for approval.`;
        }

        if (msg && staffing_user_app.length) {
        	frappe.call({
                method: "tag_workflow.utils.notification.make_system_notification",
                args: {
                    "message": msg,
                    "users": staffing_user_app,
                    "doctype": "Timesheet",
                    "docname": timesheets[0]["docname"],
                    "subject": "Timesheet For Approval"
                }
            });
        }
    }
}

function send_for_approval_contd(time) {
	let staffing_user_app = [];
	frappe.call({
		method: "tag_workflow.tag_workflow.doctype.add_timesheet.add_timesheet.send_timesheet_for_approval",
		args: {
			time: time
		},
		async: 0,
		callback: (r) => {
			let res = r.message;
			staffing_user_app.push(res[0]);
			frappe.call({
				method: "tag_workflow.tag_workflow.doctype.add_timesheet.add_timesheet.dnr_notification",
				args: {
					time: time,
					staffing_user_app: res[0]
				}
			});
			frappe.call({
				method: "tag_workflow.utils.notification.sendmail",
				args: {
					emails: res[1],
					message: res[2],
					subject: res[3],
					doctype: "Timesheet",
					docname: time["docname"]
				}
			});
		}
	});
	return staffing_user_app
}


function duplicate_emp_msg(row, duplicate_emp, duplicate_msg){
	let empKey = `${row.employee}~${row.from_time}~${row.to_time}`;
	if (duplicate_emp.includes(empKey)) {
		duplicate_msg.push(`&#x2022 ${row.employee_name} from ${row.from_time.slice(0,5)} to ${row.to_time.slice(0,5)}`);
	}else{
		duplicate_emp.push(empKey);
	}
	return [duplicate_emp, duplicate_msg];
}

function show_desc(frm){
	if(frm.doc.job_order && frm.doc.date){
		update_title(frm);
		get_employee_data(frm);
	}else{
		frm.dashboard.set_headline(__());
		frm.dashboard.set_headline(__(`<div style="display: flex;flex-direction: inherit;"><p>Job Order description will be available here...</p></div>`));
		frm.clear_table("items");
		frm.refresh_field("items");
	}
}

/**
 * The function `status_field` updates the options for the fields "job_title", "start_time", and
 * "status" in a grid based on the values of the "items" array.
 * @param frm - The `frm` parameter is the form object that represents the current document being
 * edited. It contains information about the document and its fields.
 */
function status_field(frm){
    let items = frm.doc.items || [];
    for(let i in items){
		frappe.utils.filter_dict(frm.fields_dict.items.grid.grid_rows_by_docname[items[i].name].docfields, {"fieldname": "job_title_time" })[0].options = items[i].job_title_time;
        if(items[i].status != "Replaced"){
			frappe.utils.filter_dict(frm.fields_dict.items.grid.grid_rows_by_docname[items[i].name].docfields, {"fieldname": "status" })[0].options = "\nDNR\nNo Show\nNon Satisfactory";
        }
		frm.fields_dict['items'].grid.get_grid_row(items[i].name).refresh();
    }
}

/**
 * The function `check_replaced_emp` checks if an employee has been replaced and updates the options
 * for the "status" field accordingly.
 * @param child - The "child" parameter is an object that represents a child document in a parent-child
 * relationship. It contains information about the child document, such as its fields and values.
 * @param frm - The parameter "frm" is likely referring to a form object or document object. It is used
 * to access the fields and values of the form or document.
 */
function check_replaced_emp(child, frm){
    if(child.employee){
        frappe.call({
            "method": "tag_workflow.tag_workflow.doctype.add_timesheet.add_timesheet.checkreplaced_emp",
            "args": {"employee": child.employee, "job_order": frm.doc.job_order},
            "callback": function(r){
                if(r){
                    let result = r.message;
                    if(result == 0){
						frappe.utils.filter_dict(frm.fields_dict.items.grid.grid_rows_by_docname[child.name].docfields, {"fieldname": "status" })[0].options = "\nDNR\nNo Show\nNon Satisfactory";
                        frm.fields_dict['items'].grid.get_grid_row(child.name).refresh();
                        frappe.model.set_value(child.doctype, child.name, "status", "");
                    }else{
                        frappe.utils.filter_dict(frm.fields_dict.items.grid.grid_rows_by_docname[child.name].docfields, {"fieldname": "status" })[0].options = "\nDNR\nNo Show\nNon Satisfactory\nReplaced";
                        frm.fields_dict['items'].grid.get_grid_row(child.name).refresh();
                        frappe.model.set_value(child.doctype, child.name, "status", "Replaced");
                    }
                }
            }
        });
    }
}

function check_submittable(frm){
	if(frm.doc.from_time && frm.doc.to_time){
		$('button.btn.btn-default.ellipsis.btn-primary.btn-submit').prop('disabled', false);
	}
	else if(!(frm.doc.from_time || frm.doc.to_time ) && frm.doc.break_from_time && frm.doc.break_to_time ){
		$('button.btn.btn-default.ellipsis.btn-primary.btn-submit').prop('disabled', false);

	}
	else{
		$('button.btn.btn-default.ellipsis.btn-primary.btn-submit').prop('disabled', true);

	}
}
function check_btn_submittable(frm){
	if(frm.doc.break_from_time && frm.doc.break_to_time ){
		$('button.btn.btn-default.ellipsis.btn-primary.btn-submit').prop('disabled', false);
	}
	else if(!(frm.doc.break_from_time || frm.doc.break_to_time ) && frm.doc.from_time && frm.doc.to_time ){
		$('button.btn.btn-default.ellipsis.btn-primary.btn-submit').prop('disabled', false);

	}
	else{
		$('button.btn.btn-default.ellipsis.btn-primary.btn-submit').prop('disabled', true);

	}
}

/*--------------------------------------------------*/
function update_save_timesheet(frm,save){
	if(frm.doc.job_order && frm.doc.items && frm.doc.date &&(frm.doc.from_time || frm.doc.to_time || frm.doc.break_from_time || frm.doc.break_to_time )){
		let items = frm.doc.items || [];
		let job_order = frm.doc.job_order;
		let date = frm.doc.date;
		let from_time = frm.doc.from_time ? frm.doc.from_time:frm.doc.to_time  ;
		let to_time = frm.doc.to_time ? frm.doc.to_time:frm.doc.from_time;
		update_timesheet_save(items,job_order,date,from_time,to_time,save)
	}else{
		frappe.msgprint({message: __("(*) fields are required"), title: __('Mandatory'), indicator: 'red'});
	}
}

function update_timesheet_save(items,job_order,date,from_time,to_time,save){
	let break_from_time = frm.doc.break_from_time ? frm.doc.break_from_time:'';
	let break_to_time = frm.doc.break_to_time ? frm.doc.break_to_time:'';
	if((!from_time && !to_time) || (from_time.length==0 && to_time.length==0)){
		from_time='0:00:00'
		to_time='0:00:00'
	}
	if(break_from_time && (break_to_time).length==0){
		break_to_time=break_from_time
	}
	if(break_to_time && (break_from_time).length==0){
		break_from_time=break_to_time
	}
	frappe.call({
		method: "tag_workflow.tag_workflow.doctype.add_timesheet.add_timesheet_new.update_timesheet",
		args: {
			"user": frappe.session.user,
			"company_type": frappe.boot.tag.tag_user_info.company_type,
			"items": items,
			"job_order": job_order,
			"date": date,
			"from_time": from_time,
			"to_time": to_time,
			"break_from_time": break_from_time,
			"break_to_time": break_to_time,
			"save":save
		},
		async: 0,
		freeze: true,
		freeze_message: "Please wait while we are adding the timesheet(s)...",
		callback: function(r){
			if(r.message == "success"){
				let ts_name = [];
				items.forEach((item)=>{
					args2["selected_row"]=item;
					frappe.call({
						method: "tag_workflow.tag_workflow.doctype.add_timesheet.add_timesheet_new.create_new_timesheet",
						args: args2,
						freeze: true,
						async:0,
						freeze_message: "Please wait while we are adding the timesheet(s)...",
						callback: function(r){
							ts_name.push(r.message[2]);
						}
					});
				});
				frappe.msgprint({message: __("Timesheet(s) has been added successfully"), title: __('Successful'), indicator: 'green'});
				draft_ts_time(frm, ts_name);
			}else{
				frappe.msgprint(r.message.join("<br>"));
			}
		}
	});
}

/*------------------------------------------*/
function update_time_data(frm,save){
	let err
	err=check_from_to_timesheet_hour_value(frm)
	check_break_from_to_timesheet_value(frm)
	let employees=[]
	let item = frm.doc.items || [];
	if(item.length>0){
		for(let i in item){
			employees.push(item[i].employee_name)
		}
	}	
	let current_date=moment(frm.doc.date)
	if(err==1 && frm.doc.date<frm.doc.to_date){
		let next_date=current_date.add(1, 'days')
		frappe.msgprint({message: __("Timesheet values has crossed midnight. Please create a separate timesheet for "+next_date.date()+"-"+current_date.format('MMMM')+"-"+next_date.year() +" for "+employees), title: __('Midnight Timesheet'), indicator: 'red'});
	}
	else if(err==2 && frm.doc.date>frm.doc.from_date){
		let past_date=current_date.subtract(1, 'days')
		frappe.msgprint({message: __("Timesheet values has crossed midnight. Please create a separate timesheet for "+past_date.date()+"-"+past_date.format('MMMM')+"-"+past_date.year() +" for "+employees), title: __('Midnight Timesheet'), indicator: 'red'});
	}
	setTimeout(function(){
		update_save_timesheet(frm,save)
	},1000)
}

function update_time_values(frm, draft_ts){	
	if(draft_ts.length > 0){
		window.draft_start_time=draft_ts[0]['start_time'];
		window.draft_end_time=draft_ts[0]['end_time'];
		window.draft_break_start_time=draft_ts[0]['break_from'];
		window.draft_break_end_time=draft_ts[0]['break_to'];
		frm.set_value('from_time',draft_ts[0]['start_time']);
		frm.set_value('to_time',draft_ts[0]['end_time']);
		frm.set_value('break_from_time',draft_ts[0]['break_from']);
		frm.set_value('break_to_time',draft_ts[0]['break_to']);
	}
}

function set_def_time(frm){
	frm.set_value("from_time", "");
	frm.set_value("to_time", "");
	frm.set_value("break_from_time", "");
	frm.set_value("break_to_time", "");
}

function checking_selected_values(frm){
	frm.set_value('date','');
	if(localStorage.getItem('date')!='' && localStorage.getItem('date')!= null){
		let jo=localStorage.getItem("job_order")
		let date=localStorage.getItem("date")
		frm.set_value('job_order',jo);
		frm.set_value('date',date);
        localStorage.setItem("date", '');
	}
	let jo=localStorage.getItem("order");
	let len_history = frappe.route_history.length;
	if((frappe.route_history.length>=3 && (frappe.route_history[len_history-1][1]=='Add Timesheet') && frappe.boot.tag.tag_user_info.company_type!='Staffing' ) ||  frappe.boot.tag.tag_user_info.company_type=='Staffing' ){
		if(localStorage){
			frm.set_value("job_order", jo);
		}
	}
	else{
		frm.set_value("job_order", '');
	}
	localStorage.setItem("job_order", '');
    localStorage.setItem("date", '');
}

function check_break_time(frm, event){
	let def_date = "01 Jan 2011 ";
	if(frm.doc.from_time && frm.doc.to_time){
		check_time(frm, [], def_date, frm.doc.from_time, frm.doc.to_time, event)
		if(frm.doc.break_from_time && (Date.parse(def_date+frm.doc.break_from_time)<Date.parse(def_date+frm.doc.from_time) || Date.parse(def_date+frm.doc.break_from_time)>Date.parse(def_date+frm.doc.to_time)) ){
			$('.datepicker.active').removeClass('active');
			setTimeout(()=>{
				frm.set_value('break_from_time','')
			},1)
			error_pop_up(frm,"Break Start Time should be between Start time and End time.")
			frappe.validated=false;
		}
		if(frm.doc.break_to_time && (Date.parse(def_date+frm.doc.break_to_time)<Date.parse(def_date+frm.doc.from_time) || Date.parse(def_date+frm.doc.break_to_time)>Date.parse(def_date+frm.doc.to_time)) ){
			$('.datepicker.active').removeClass('active');
			setTimeout(()=>{
				frm.set_value('break_to_time','')
			},1)
			error_pop_up(frm,"Break End Time should be between Start time and End time.");
			frappe.validated=false;
		}
		if(frm.doc.break_from_time && frm.doc.break_to_time && (Date.parse(def_date+frm.doc.break_to_time)<Date.parse(def_date+frm.doc.break_from_time))){
			$('.datepicker.active').removeClass('active');
			setTimeout(()=>{
				frm.set_value('break_to_time','');
			},1)
			error_pop_up(frm, "Break End Time should be after Break Start Time.");
			frappe.validated=false;
		}
	}
}

function error_pop_up(frm,message){
	let dialog = new frappe.ui.Dialog({
		title:__('Time Error'),
		onhide: ()=>{
			window.pop_up=false;
		}
	})
	dialog.msg_area = $(`<div class="msgprint" id="${frm.doctype}-msgprint">`).appendTo(dialog.body);
	dialog.msg_area.append(message);
	dialog.indicator = dialog.header.find('.indicator');
	dialog.indicator.removeClass().addClass('indicator red');
	dialog.set_title('Time Error');
	if(!window.pop_up){
		dialog.show();
		window.pop_up = true;
		$('.datepicker.active').removeClass('active');
	}
}

function check_from_to_timesheet_hour_value(frm){
	let est_hours=frm.doc.estimated_daily_hours
	let daily_hrs
	if(Number.isInteger(est_hours)){
		daily_hrs=(est_hours).toString()+'.00'
	}
	else{
		daily_hrs=est_hours.toFixed(2)
	}
	let dat=(daily_hrs.toString()).split('.')
	let my_hours=parseInt(dat[0]*60)
	let my_minutes=parseFloat(dat[1])*.60
	let minutes_value=my_hours+my_minutes
	let midnight
	if(frm.doc.from_time && !frm.doc.to_time){
		let new_end_time=moment(frm.doc.from_time, 'HH:mm').add(minutes_value, 'minutes').format('HH:mm:ss')
		if(new_end_time<frm.doc.from_time){
			frm.set_value('to_time','23:59:00');
			midnight=1
		}
		else{
			frm.set_value('to_time',new_end_time);

		}
	}
	else if(frm.doc.to_time && !frm.doc.from_time){
		let new_from_time=moment(frm.doc.to_time, 'HH:mm').subtract(minutes_value, 'minutes').format('HH:mm:ss')
		if(new_from_time>frm.doc.to_time){
			frm.set_value('from_time','00:00:00');
			midnight=2
		}
		else{
			frm.set_value('from_time',new_from_time);

		}
	}
	return midnight
}

function check_break_from_to_timesheet_value(frm){
	let extra_break_time=15
	if(frm.doc.break_from_time && !frm.doc.break_to_time){
		let new_break_end_time=moment(frm.doc.break_from_time, 'HH:mm').add(extra_break_time, 'minutes').format('HH:mm:ss')
		if(new_break_end_time<frm.doc.break_from_time){
			frm.set_value('break_to_time','23:59:00');
		}
		else{
			frm.set_value('break_to_time',new_break_end_time);
		}
	}
	else if(frm.doc.break_to_time && !frm.doc.break_from_time){
		let new_break_from_time=moment(frm.doc.break_to_time, 'HH:mm').subtract(extra_break_time, 'minutes').format('HH:mm:ss')
		if(new_break_from_time>frm.doc.break_to_time){
			frm.set_value('break_from_time','00:00:00');
		}
		else{
			frm.set_value('break_from_time',new_break_from_time);
		}
	}
	if(frm.doc.break_from_time && frm.doc.break_to_time && !(frm.doc.from_time && frm.doc.to_time)){
		frm.set_value('from_time',frm.doc.break_from_time);
		frm.set_value('to_time',frm.doc.break_to_time);
	}
}

function check_table_break_time(frm,child, event){
	let def_date = "01 Jan 2011 ";
	if(child.from_time && child.to_time){
		check_time(frm, child, def_date, child.from_time, child.to_time, event)
		if(child.break_from && (Date.parse(def_date+child.break_from)<Date.parse(def_date+child.from_time) || Date.parse(def_date+child.break_from)>Date.parse(def_date+child.to_time)) ){
			$('.datepicker.active').removeClass('active');
			setTimeout(()=>{
				frappe.model.set_value(child.doctype, child.name, "break_from", "");
			},1)
			error_pop_up(frm,"Break Start Time should be between Start time and End time.");
			frappe.validated=false;
		}
		if(child.break_to && (Date.parse(def_date+child.break_to)<Date.parse(def_date+child.from_time) || Date.parse(def_date+child.break_to)>Date.parse(def_date+child.to_time)) ){
			$('.datepicker.active').removeClass('active');
			setTimeout(()=>{
				frappe.model.set_value(child.doctype, child.name, "break_to", "");
			},1)
			error_pop_up(frm,"Break End Time should be between Start time and End time.");
			frappe.validated=false;
		}
		if(child.break_from && child.break_to && (Date.parse(def_date+child.break_to)<Date.parse(def_date+child.break_from))){
			$('.datepicker.active').removeClass('active');
			setTimeout(()=>{
				frappe.model.set_value(child.doctype, child.name, "break_to", "");
			},1)
			error_pop_up(frm, "Break End Time should be before Break Start Time.");
			frappe.validated=false;
		}
	}
}

function check_time(frm, child, def_date, from_time, to_time, event){
	if(Date.parse(def_date+from_time)>Date.parse(def_date+to_time)){
		$('.datepicker.active').removeClass('active');
		if(event=="child_from_time"){
			error_pop_up(frm,"Start Time should be before End time.")
			setTimeout(()=>{
				frappe.model.set_value(child.doctype, child.name, "from_time", "");
				frappe.model.set_value(child.doctype, child.name, "to_time", "");
			},1)
		}else if(event=="child_to_time"){
			error_pop_up(frm,"End Time should be after Start time.")
			setTimeout(()=>{
				frappe.model.set_value(child.doctype, child.name, "from_time", "");
				frappe.model.set_value(child.doctype, child.name, "to_time", "");
			},1)
		}else if(event=="from_time"){
			error_pop_up(frm,"Start Time should be before End time.")
			setTimeout(()=>{
				frm.set_value("from_time", "");
			},1)
		}else if(event=="to_time"){
			error_pop_up(frm,"End Time should be after Start time.")
			setTimeout(()=>{
				frm.set_value("to_time", "");
			},1)
		}
		frappe.validated=false;
	}
}

function default_time(){
	window.draft_start_time='';
	window.draft_end_time='';
	window.draft_break_start_time='';
	window.draft_break_end_time='';
}

/**
 * The function "set_job_title" sets the job title and start time options for a child document based on
 * the selected employee and job order.
 * @param child - The "child" parameter is an object that represents a child document in a form. It
 * contains information about the child document, such as its name, doctype, and fields.
 * @param frm - The `frm` parameter is the current form object. It represents the current document
 * being edited or viewed.
 */
function set_job_title(child, frm){
	if(child.employee){
		frappe.call({
			"method": "tag_workflow.tag_workflow.doctype.add_timesheet.add_timesheet.set_job_title",
			"args": {
				"job_order": frm.doc.job_order,
				"employee": child.employee
			},
			"async": 0,
			"callback": (res)=>{
				frappe.utils.filter_dict(frm.fields_dict.items.grid.grid_rows_by_docname[child.name].docfields, {"fieldname": "job_title_time" })[0].options = res.message[0].join("\n");
				window.job_title_rate = {...window.job_title_rate, ...res.message[1]}
				frm.fields_dict['items'].grid.get_grid_row(child.name).refresh();
				frappe.model.set_value(child.doctype, child.name, "job_title", undefined);
				frappe.model.set_value(child.doctype, child.name, "start_time", undefined);
			}
		});
	}
}

function draft_ts_time(frm, ts_name){
	if(ts_name.length){
		frappe.call({
			method:"tag_workflow.tag_workflow.doctype.add_timesheet.add_timesheet.draft_ts_time",
			args: {
				start_time: frm.doc.from_time,
				end_time: frm.doc.to_time,
				break_from: frm.doc.break_from_time,
				break_to: frm.doc.break_to_time,
				date_of_ts: frm.doc.date,
				ts_name: ts_name,
				job_order: frm.doc.job_order
			}
		});
	}
}

function submit_timesheet(frm){
	let selected_items = frm.doc.items || [];
	let items = [];
	let empty_row = 0;
	selected_items.forEach(function(row) {
		if(row.__checked){
			if(row.timesheet_value){
				items.push(row);
			}else{
				empty_row+=1;
			}
		}
	});
	if(empty_row){
		frappe.msgprint(__("Please save all the selected timesheets before submitting."))
	}else{
		frappe.call({
			method: "tag_workflow.tag_workflow.doctype.add_timesheet.add_timesheet_new.submit_timesheet",
			freeze: true,
			freeze_message: "Please wait while we are submitting the timesheet(s)...",
			args: {
				selected_items: items,
				date: frm.doc.date,
				job_order: frm.doc.job_order,
				from_time: frm.doc.from_time,
				to_time: frm.doc.to_time,
				company_type: frappe.boot.tag.tag_user_info.company_type
			},
			callback: (res)=>{
				send_for_approval(res.message);
				frappe.msgprint(__("Timesheet(s) submitted successfully."));
				get_employee_data(frm);
			}
		});
	}
}
