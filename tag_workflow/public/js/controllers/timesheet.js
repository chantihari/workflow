frappe.ui.form.off("Timesheet Detail", "from_time");
frappe.ui.form.off("Timesheet Detail", "hours");
frappe.ui.form.on("Timesheet", {
	refresh: function(frm){
		$('[data-fieldname="from_time"], [data-fieldname="to_time"]').on("click", ()=>{
			frm.scroll_to_field("total_hours")
		})
		$('[data-fieldtype="Long Text"]').removeAttr("title");
		$('[data-label="Resume%20Timer"]').hide();
		$('[data-label="Start%20Timer"]').hide();
		$('[data-label="Create%20Salary%20Slip"]').hide();
		$('[data-label="Create%20Sales%20Invoice"]').hide();
		$('[data-label="Cancel"]').hide();
		$('.custom-actions.hidden-xs.hidden-md').show();
		$('[class="btn btn-primary btn-sm primary-action"]').show();
		frm.fields_dict.time_logs.grid.grid_buttons.addClass('hidden');
		add_button_submit(frm);
		fields_label_update(frm)
		hide_action_button(frm)
		$(document).on('click', '[data-fieldname="from_time"]', function(){
			$('.datepicker').show()
		});
		$(document).on('click', '[data-fieldname="to_time"]', function(){
			$('.datepicker').show()
		});
		if(frm.doc.__islocal==1){
			cancel_timesheet(frm);
			frm.set_value("employee","");
			setTimeout(() => {
				frm.set_value("employee","");
				frm.set_df_property("job_details", "options", " ");
			}, 700);
		}
		if(frm.doc.status=='Submitted' && frm.doc.workflow_state == "Approved" && frm.doc.approval_notification == 1){
			if((frappe.user_roles.includes('Staffing Admin') || frappe.user_roles.includes('Staffing User')) && frappe.session.user!='Administrator'){
				approval_timesheet(frm);
			}
		}
		let child_table = ['activity_type','from_time', 'to_time', 'hrs', 'billing_amount']
		for(let i in child_table){
			$( "[data-fieldname="+child_table[i]+"]" ).on('mouseover',function(e) {
				let file=e.target.innerText;
				$(this).attr('title', file);
			});
		}

		public_profile(frm);
		window.start = frm.doc.time_logs[0].break_start_time;
		window.end = frm.doc.time_logs[0].break_end_time;
		window.from_time = frm.doc.time_logs[0].from_time;
		window.to_time = frm.doc.time_logs[0].to_time;
	},
	setup: function(frm){
		frm.set_query("job_order_detail", function(){
			return {
				query: "tag_workflow.utils.timesheet.assigned_job_order",
				filters: {
					"company": frm.doc.company
				}
			}
		});

		frm.set_query('employee', function(doc) {
			return {
				query: "tag_workflow.utils.timesheet.get_timesheet_employee",
				filters: {
					'job_order': doc.job_order_detail
				}
			}
		});
		frm.fields_dict['time_logs'].grid.get_field('activity_type').get_query = function(doc) {
			return {
				query: "tag_workflow.utils.timesheet.job_name",
				filters: {
					'job_name': doc.job_order_detail
				}

			}
		}
	},

	onload:function(frm){
		if(frappe.session.user != 'Administrator'){
			$('.menu-btn-group').hide();
		}

		if(frappe.user.has_role("Tag Admin")){
			frm.set_query("company", function(){
				return {
					filters: [
						["Company", "organization_type", "in",["Hiring", "Exclusive Hiring"]]
					]
				}
			});
		}

		if(!frm.doc.is_employee_rating_done && frm.doc.workflow_state == "Approved" && frm.doc.status == "Submitted"){
			if((frappe.user_roles.includes('Hiring Admin') || frappe.user_roles.includes('Hiring User')) && frappe.session.user!='Administrator'){
				employee_timesheet_rating(frm);
			}
		}
	},

	validate:function(frm){
		check_break_time(frm);
		if(frm.doc.workflow_state === 'Denied' && frappe.boot.tag.tag_user_info.company_type=='Staffing'){
			return new Promise(function(resolve, reject){
				if(frappe.session.user!='Administrator'){
					let pop_up = new frappe.ui.Dialog({
						title: __('Please provide an explanation for the timesheet denial '),
						'fields': [
							{'fieldname': 'Comment', 'fieldtype': 'Long Text','label':'Reason','reqd':1}
						],
						primary_action: function(){
							pop_up.hide();
							let comment=pop_up.get_values();
							frappe.call({
								method:"tag_workflow.utils.timesheet.timesheet_dispute_comment_box",
								freeze:true,
								freeze_message:__("Please Wait ......."),
								args:{
									'comment':comment,
									'timesheet':frm.doc.name, //fetch timesheet name
									'user': frappe.session.user
								},
								callback:function(rm){
									if (rm.message){
										resolve();
										frappe.msgprint('Reason for Denial Submitted Successfully');
										setTimeout(() => {location.reload()}, 3000);
									}
								}
							});
						}
					});
					pop_up.show();
					pop_up.$wrapper.find('.btn.btn-primary').click(function(){
						pop_up.hide();
					});
				}
				const cancelReason = "Cancelled by user";
    			reject(cancelReason);
			});
		}
		check_mandatory_field(frm.doc.employee,frm.doc.employee_name)
	},

	job_order_detail: function(frm){
		job_order_details(frm);
		update_job_detail(frm);
	},

	no_show: function(frm){
		if(!frm.doc.no_show){
			frappe.model.set_value(frm.doc.time_logs[0].doctype, frm.doc.time_logs[0].name, "from_time", window.from_time);
			frappe.model.set_value(frm.doc.time_logs[0].doctype, frm.doc.time_logs[0].name, "to_time", window.to_time); 
			frappe.model.set_value(frm.doc.time_logs[0].doctype, frm.doc.time_logs[0].name, "break_start_time", window.start); 
			frappe.model.set_value(frm.doc.time_logs[0].doctype, frm.doc.time_logs[0].name, "break_end_time", window.end);
		}
		trigger_email(frm, "no_show", frm.doc.no_show, "No Show");
	},

	non_satisfactory: function(frm){
		trigger_email(frm, "non_satisfactory", frm.doc.non_satisfactory, "Non Satisfactory");
	},

	dnr: function(frm){
		trigger_email(frm, "dnr", frm.doc.dnr, "DNR");
	},

	before_load: (frm)=>{
		job_order_details(frm);
		hide_pay_rate(frm);
	},

	before_save: (frm)=>{
		frappe.call({
			'method': 'tag_workflow.tag_workflow.doctype.add_timesheet.add_timesheet.check_old_timesheet',
			'args':{
				'child_from': frm.doc.time_logs[0].from_time,
				'child_to': frm.doc.time_logs[0].to_time,
				'employee': frm.doc.employee,
				'timesheet': frm.doc.name
			},
			'async': 0,
			'callback': (res)=>{
				if(res.message){
					frappe.msgprint("Timesheet is already available for employee <b>"+frm.doc.employee_name+"</b>(<b>"+frm.doc.employee+"</b>) on the given datetime.")
					frappe.validated=false;
				}
			}
		});
	},

	after_save:function(frm){
		if(frm.doc.update_other_timesheet==1 && frm.doc.workflow_state!='Open'){
			frappe.call({
				'method':'tag_workflow.tag_workflow.doctype.add_timesheet.add_timesheet.edit_update_record',
				'args':{
					'timesheet':frm.doc.name,
					'job_order':frm.doc.job_order_detail,
					'date_of_ts':frm.doc.date_of_timesheet,
					'employee':frm.doc.employee
				}
			});
		}
	}
});


function job_order_details(frm){
	if(frm.doc.job_order_detail){
		frappe.db.get_value("Job Order", {"name": frm.doc.job_order_detail}, ["job_site", "job_order_duration", "from_date", "to_date", "order_status"], function(r){
			if(r){
				let data = `<div style="display: flex;flex-direction: column;min-height: 1px;padding: 19px;border-radius: var(--border-radius-md);height: 100%;box-shadow: var(--card-shadow);background-color: var(--card-bg);">
					<p><b>Job Title: </b> ${frm.doc.time_logs[0]['activity_type']}</p>
					<p><b>Job Site: </b> ${r['job_site']}</p>
					<p><b>Job Duration: </b> ${r['job_order_duration']}</p>
					<p><b>Bill Rate Per Hour: </b>$${frm.doc.time_logs[0]['billing_rate'].toFixed(2)}</p>`
				if(!['Hiring', 'Exclusive Hiring'].includes(frappe.boot.tag.tag_user_info.company_type)){
					data += `<p><b>Pay Rate Per Hour: </b>$${(frm.doc.employee_pay_rate).toFixed(2)}</p>`
				}
				data+=`<p><b>Work Order Status: </b> ${r['order_status']}</p></div>`;
				frm.set_df_property("job_details", "options", data);
				if(frm.doc.__islocal == 1){
					frm.set_value('from_date',(r.from_date).slice(0,10));  //.slice(0,10)
					frm.set_value('to_date',(r.to_date).slice(0,10)); //.slice(0,10)
					frm.set_value('job_name',(r.select_job));
					frm.set_value('per_hour_rate',(r.per_hour));
					frm.set_value('flat_rate',(r.flat_rate));
				}

			}
		});
	}else{
		frm.set_df_property("job_details", "options", "");
	}
}

/*-----------timesheet-----------------*/
function check_update_timesheet(frm){
	if(frm.doc.workflow_state == "Approval Request" && frappe.boot.tag.tag_user_info.company_type=='Hiring'){
		frappe.db.get_value("Company Review", {"name": frm.doc.employee_company+"-"+frm.doc.job_order_detail},['rating'], function(r){
			if(!r.rating){
				let pop_up = new frappe.ui.Dialog({
					title: __('Staffing Company Review'),
					'fields': [
						{'fieldname': 'Rating', 'fieldtype': 'Rating','label':'Rating','reqd':1},
						{'fieldname': 'Comment', 'fieldtype': 'Data','label':'Review'}
					],
					primary_action: function(){
						pop_up.hide();
						let comp_rating=pop_up.get_values();
						frappe.call({
							method:"tag_workflow.utils.timesheet.company_rating",
							args:{
								'hiring_company':frm.doc.company,
								'staffing_company':frm.doc.employee_company,
								'ratings':comp_rating,
								'job_order':frm.doc.job_order_detail
							},
							"async": 0,
							callback:function(){
								frappe.msgprint('Review Submitted Successfully');
							}
						});
					}
				});
				pop_up.show();
			}
		});
	}
}

function update_job_detail(frm){
	if (frm.doc.job_order_detail){
		frappe.call({
			method:"tag_workflow.tag_data.update_timesheet",
			args:{'job_order_detail':frm.doc.job_order_detail},
			callback:function(r){
				if(r.message){
					frm.clear_table("time_logs");
					let child = frappe.model.get_new_doc("Timesheet Detail", frm.doc, "time_logs");
					$.extend(child, {"activity_type": r.message[0], "is_billable":1,"billing_rate":r.message[4],"flat_rate":r.message[5],"extra_hours":r.message[6],"extra_rate":r.message[7]});
					frm.refresh_field("time_logs");
				}
			}
		});
	}
}

/*-----------trigger email-----------*/
function trigger_email(frm, key, value, type){
	let order = frm.doc.job_order_detail;
	let local = frm.doc.__islocal;
	if(order && local != 1){
		let message1 = value?'You are about to update this employee <b>'+frm.doc.employee_name+'</b> to <b>'+type+'</b>. Do you want to continue?':'You are unmarking this employee <b>'+frm.doc.employee_name+'</b> from <b>'+type+'</b>. Do you want to continue?';
		let message2 = value?'Employee <b>'+frm.doc.employee_name+'</b> updated as '+type+'.':'Employee <b>'+frm.doc.employee_name+'</b> unmarked from '+type+'.'
		frappe.confirm(
			message1,
			function(){
				update_child_amount(frm);
				frappe.msgprint(message2);
			},function(){
				update_child_amount(frm);
				frm.doc[key] = (value == 1 ? 0 : 1);
				frm.fields_dict[key].refresh_input();
			}
		);
	}else if(order && local && value){
		frappe.update_msgprint({message: __('Please save timesheet first'), title: __('Timesheet'), indicator: 'red'});
		frm.set_value(key, 0);
	}else if(!order && value){
		frappe.update_msgprint({message: __('Please select Job Order'), title: __('Job Order'), indicator: 'red'});
		frm.set_value(key, 0);
	}
}

function denied_timesheet(frm){
	frappe.call({
		"method": "tag_workflow.utils.timesheet.denied_notification",
		freeze:true,
		freeze_message:__("Please Wait......"),
		"args": {
			"job_order": frm.doc.job_order_detail,
			"hiring_company":frm.doc.company,
			"staffing_company": frm.doc.employee_company,
			"timesheet_name":frm.doc.name
		}
	});
}

function employee_timesheet_rating(frm){
	let pop_up = new frappe.ui.Dialog({
		title: __('Employee Rating'),
		'fields': [
			{'fieldname': 'thumbs_up', 'fieldtype': 'Check','label':"<i class='fa fa-thumbs-up' type='radio' style='font-size: 50px;' value='up' id = '1'> "},
			{'fieldtype':"Column Break"},
			{'fieldname': 'thumbs_down', 'fieldtype': 'Check','label':"<i class='fa fa-thumbs-down' style='font-size: 50px;'>"},
			{'fieldtype':"Section Break"},
			{'fieldname': 'Comment', 'fieldtype': 'Data','label':'Review'}
		],
		primary_action: function(){
			let up = pop_up.get_value('thumbs_up');
			let down = pop_up.get_value('thumbs_down');
			if (up === down){
				frappe.msgprint('Both values cannot be selected.');
			}else{
				pop_up.hide();
				frappe.call({
					method:"tag_workflow.utils.timesheet.staffing_emp_rating",
					args:{
						'employee':frm.doc.employee_name, 'id':frm.doc.employee,
						'up':up, 'down':down, 'job_order':frm.doc.job_order_detail,
						'comment':pop_up.get_value('Comment'), 'timesheet_name':frm.doc.name
					},
					callback:function(rm){
						if (rm.message){
							frappe.msgprint('Employee Rating is Submitted');
						}
					}
				});
			}
		}
	});
	pop_up.show();
	$(document).on('click', '[data-fieldname="thumbs_up"]', function(){
		$('[data-fieldname="thumbs_down"]').prop('checked', false);
	});

	$(document).on('click', '[data-fieldname="thumbs_down"]', function(){
		$('[data-fieldname="thumbs_up"]').prop('checked', false);
	});
}

function approval_timesheet(frm){
	frappe.db.get_value("Hiring Company Review", {"name": frm.doc.employee_company+"-"+frm.doc.job_order_detail},['rating'], function(r){
		if(!r.rating){
			let pop_up = new frappe.ui.Dialog({
				title: __('Hiring Company Rating'),
				'fields': [
					{'fieldname': 'Rating', 'fieldtype': 'Rating','label':'Rating','reqd':1},
					{'fieldname': 'Comment', 'fieldtype': 'Data','label':'Review'}
				],
				primary_action: function(){
					pop_up.hide();
					let comp_rating=pop_up.get_values()
					frappe.call({
						method:"tag_workflow.utils.timesheet.hiring_company_rating",
						args:{
							'hiring_company':frm.doc.company,
							'staffing_company':frm.doc.employee_company,
							'ratings':comp_rating,
							'job_order':frm.doc.job_order_detail,
							'timesheet':frm.doc.name
						},
						callback:function(){
								frappe.msgprint('Review Submitted Successfully')	
						}
					})
				}
			});
			pop_up.show();
		}
		
	})
}


frappe.ui.form.on("Timesheet Detail", {
	activity_type:function(frm,cdt,cdn){
		frappe.model.set_value(cdt,cdn,"is_billable",1);
		frappe.model.set_value(cdt, cdn, "billing_rate", frm.doc.per_hour_rate);
		frappe.model.set_value(cdt, cdn, "flat_rate", frm.doc.flat_rate);
	},

	is_billable:function(frm,cdt,cdn){
		let child=locals[cdt][cdn];
		if(child.is_billable==1){
			frappe.model.set_value(cdt, cdn, "billing_rate", frm.doc.per_hour_rate);
			frappe.model.set_value(cdt, cdn, "flat_rate", frm.doc.flat_rate);
		}
	},

	from_time:function(frm,cdt,cdn){
		let child = locals[cdt][cdn];
		let from_date = child.from_time.slice(0, 10);
		if(!child.from_time){
			$('.datepicker.active').removeClass('active')
			frappe.msgprint("From Time can't be empty.");
			frappe.model.set_value(cdt, cdn, "from_time", window.from_time);
		}
		else if(frm.doc.no_show && child.from_time != frm.doc.date_of_timesheet+" 00:00"){
			$('.datepicker.active').removeClass('active')
			frappe.msgprint("You can't set time if the employee's status is No Show.");
			frappe.model.set_value(cdt, cdn, "from_time", frm.doc.date_of_timesheet+" 00:00");
			frappe.model.set_value(cdt, cdn, "to_time", frm.doc.date_of_timesheet+" 00:00");
			frappe.model.set_value(cdt, cdn, "break_start_time", undefined);
			frappe.model.set_value(cdt, cdn, "break_end_time", undefined);
		}else if(from_date != frm.doc.date_of_timesheet){
			$('.datepicker.active').removeClass('active')
			frappe.msgprint("Timesheet can't be of multiple days.");
			frappe.model.set_value(cdt, cdn, "from_time", frm.doc.date_of_timesheet+child.from_time.slice(10));
		}else if(child.from_time && child.to_time && child.from_time>child.to_time){
			$('.datepicker.active').removeClass('active')
			frappe.msgprint("From Time should be before To Time.");
			frappe.model.set_value(cdt, cdn, "from_time", window.from_time);
			frappe.model.set_value(cdt, cdn, "to_time", window.to_time);
		}
		check_table_break_time(frm, child, cdt, cdn, "from_time");
		update_time(frm, cdt, cdn);
	},

	to_time:function(frm,cdt,cdn){
		let child=locals[cdt][cdn];
		let to_date = child.to_time.slice(0, 10);
		if(!child.to_time){
			$('.datepicker.active').removeClass('active')
			frappe.msgprint("To Time can't be empty.");
			frappe.model.set_value(cdt, cdn, "to_time", window.to_time);
		}
		else if(frm.doc.no_show && child.from_time != frm.doc.date_of_timesheet+" 00:00"){
			$('.datepicker.active').removeClass('active')
			frappe.msgprint("You can't set time if the employee's status is No Show.");
			frappe.model.set_value(cdt, cdn, "from_time", frm.doc.date_of_timesheet+" 00:00");
			frappe.model.set_value(cdt, cdn, "to_time", frm.doc.date_of_timesheet+" 00:00");
		}else if(to_date != frm.doc.date_of_timesheet){
			$('.datepicker.active').removeClass('active');
			frappe.msgprint("Timesheet can't be of multiple days.");
			frappe.model.set_value(cdt, cdn, "to_time", frm.doc.date_of_timesheet+child.to_time.slice(10));
		}else if(child.from_time && child.to_time && child.from_time>child.to_time){
			$('.datepicker.active').removeClass('active');
			frappe.msgprint("To Time should be after From Time.");
			frappe.model.set_value(cdt, cdn, "from_time", window.from_time);
			frappe.model.set_value(cdt, cdn, "to_time", window.to_time);
		}
		check_table_break_time(frm, child, cdt, cdn, "to_time");
		update_time(frm, cdt, cdn);
	},

	break_start_time:function(frm,cdt,cdn){
		let child=locals[cdt][cdn];
		check_table_break_time(frm, child, cdt, cdn, "break_start_time");
		update_time(frm,cdt,cdn)
	},

	break_end_time:function(frm,cdt,cdn){
		let child=locals[cdt][cdn];
		check_table_break_time(frm, child, cdt, cdn, "break_end_time");
		update_time(frm,cdt,cdn);
	},

	flat_rate: function(frm, cdt, cdn){
		update_time(frm,cdt,cdn);
	},

	tip: function(frm, cdt, cdn){
		frappe.db.get_value("Job Order", {name: frm.doc.job_order_detail}, ["flat_rate"], function(d){
			let child = locals[cdt][cdn];
			let flat_rate1 = d.flat_rate + child.tip;
			frappe.model.set_value(cdt, cdn, "flat_rate", flat_rate1);
		});
	},

	billing_rate: function(frm, cdt, cdn){
		update_time(frm,cdt,cdn);
	},

	form_render: function(){
		$(".row-actions, .grid-footer-toolbar").hide();
	}
});


function cancel_timesheet(frm){
	frm.add_custom_button(__('Cancel'), function(){
		frappe.set_route("Form", "Timesheet");
	});
}

/*-----------------------------------*/
function update_child_amount(frm){
	let items = frm.doc.time_logs || [];
	if(frm.doc.no_show == 1){
		for(let i in items){
			frappe.model.set_value(items[i].doctype, items[i].name, "is_billable", 0);
			frappe.model.set_value(items[i].doctype, items[i].name, "billing_rate", 0);
			frappe.model.set_value(items[i].doctype, items[i].name, "flat_rate", 0);
			frappe.model.set_value(items[i].doctype, items[i].name, "hrs", 0);
			frm.set_value("total_hours", 0);
			frappe.model.set_value(items[i].doctype, items[i].name, "from_time", frm.doc.date_of_timesheet+" 00:00");
			frappe.model.set_value(items[i].doctype, items[i].name, "to_time", frm.doc.date_of_timesheet+" 00:00");
			frappe.model.set_value(items[i].doctype, items[i].name, "break_start_time", undefined);
			frappe.model.set_value(items[i].doctype, items[i].name, "break_end_time", undefined);
		}
	}else{
		for(let i in items){
			frappe.model.set_value(items[i].doctype, items[i].name, "is_billable", 1);
			frappe.model.set_value(items[i].doctype, items[i].name, "billing_rate", frm.doc.per_hour_rate);
			frappe.model.set_value(items[i].doctype, items[i].name, "flat_rate", frm.doc.flat_rate);
		}
	}
}

function update_time(frm, cdt, cdn){
	let child = locals[cdt][cdn];
	if(child.from_time && child.to_time){
		let sec = (moment(child.to_time).diff(moment(child.from_time), "seconds"));
		let break_sec = 0;
		let def_date = frm.doc.date_of_timesheet+" ";
		if(child.break_start_time && child.break_end_time && Date.parse(def_date+child.break_start_time) >= Date.parse(child.from_time) && Date.parse(def_date+child.break_end_time) <= Date.parse(child.to_time)){
			let break_start = new Date(def_date + child.break_start_time);
			let break_end = new Date(def_date + child.break_end_time);
  			break_sec = (break_end.getTime() - break_start.getTime()) / 1000;
		}

		let time_diff = sec - break_sec
		let hour = Math.floor(time_diff / 3600);
		let minutes = Math.floor((time_diff - (hour * 3600)) / 60); // get minutes
		
		let mnt = minutes/60;
		let hours = hour+mnt;
		
		frappe.model.set_value(cdt, cdn, "hours", hours);
		frappe.model.set_value(cdt, cdn, "billing_hours", hours);
		frappe.model.set_value(cdt, cdn, "hrs", (hour+'hr '+minutes+'min'));
		
		frappe.call({
			'method':'tag_workflow.tag_workflow.doctype.add_timesheet.add_timesheet.update_billing_calculation',
			'args':{
				'timesheet':frm.doc.name,
				'jo':frm.doc.job_order_detail,
				'timesheet_date':frm.doc.date_of_timesheet,
				'employee':frm.doc.employee,
				'working_hours':hours,
				'total_flat_rate':child.flat_rate,
				'per_hour_rate':child.billing_rate
			},
			callback:function(r){
				setTimeout(() => {
					frappe.model.set_value(cdt, cdn, "base_billing_amount", r.message[0][0]);
					frappe.model.set_value(cdt, cdn, "billing_amount", r.message[0][0]);
					frappe.model.set_value(cdt, cdn, "pay_amount", r.message[2][0]);
					frm.set_value('timesheet_billable_amount',r.message[0][0]);
					frm.set_value('timesheet_billable_overtime_amount',r.message[0][1]);
					frm.set_value('total_job_order_amount',r.message[0][2]);
					frm.set_value('total_job_order_billable_overtime_amount_',r.message[0][3])
					update_hourly_data(frm, r)
					frm.set_value('update_other_timesheet',1)
				}, 10);
			}
		});
		if(!frm.doc.no_show){
			window.from_time = child.from_time;
			window.to_time = child.to_time;
			window.start = child.break_start_time;
			window.end = child.break_end_time;
		}
	}
}

function add_button_submit(frm){
	if(frm.doc.__islocal!=1 && frappe.boot.tag.tag_user_info.company_type=='Staffing' && frm.doc.workflow_state=='Open'){
		frm.add_custom_button(__('Submit Timesheet'), function() {
			submit_timesheet(frm);
		}).addClass("btn-primary");
	}
}

function submit_timesheet(frm){
	frappe.call({
		method: "tag_workflow.utils.timesheet.submit_staff_timesheet",
		args: {
			"jo":frm.doc.job_order_detail,
			"timesheet_date":frm.doc.date_of_timesheet,
			"employee":frm.doc.employee,
			"timesheet":frm.doc.name,
			"date":frm.doc.creation,
			"company":frm.doc.company,
			"dnr":frm.doc.dnr,
			"job_title":frm.doc.job_name
		},
		async: 1,
		freeze: true,
		freeze_message: "Please wait while we are updating timesheet status...",
		callback: function(r){
			if(r){
				frappe.msgprint('Status Updated Successfully')
				window.location.reload()
			}
		}
	});
}

function public_profile(frm){
	if(frm.doc.__islocal!=1){
		Array.from($('[data-doctype="Company"]')).forEach(field =>{
			localStorage.setItem("company", frm.doc.company);
			field.href= '/app/dynamic_page';
		});
	}
}

 
function fields_label_update(frm){
	if(frm.doc.__islocal!=1){
		let usd="(USD)"
		frm.set_df_property("timesheet_billable_amount",'label',"Timesheet Billable Amount "+usd)
		frm.set_df_property("total_job_order_amount",'label',"Total Job Order Amount "+usd)
		frm.set_df_property("timesheet_billable_overtime_amount",'label',"Timesheet Billable Overtime Amount "+usd)
		frm.set_df_property("total_job_order_billable_overtime_amount_",'label',"Total Job Order Billable Overtime Amount  "+usd)
		frm.set_df_property("timesheet_billable_overtime_amount_staffing", "label", "Timesheet Billable Overtime Amount "+usd)
	}
	let pay_amount = frappe.meta.get_docfield('Timesheet Detail','pay_amount', frm.doc.name);
	pay_amount.label = 'Pay Amount (USD)'
	frm.refresh_field('time_logs');
}
 

function hide_pay_rate(frm){
	if(['Hiring', 'Exclusive Hiring'].includes(frappe.boot.tag.tag_user_info.company_type) && frm.doc.time_logs){
		$('#timesheet-pay-tab').html("Notes")
		let pay_amount = frappe.meta.get_docfield("Timesheet Detail", "pay_amount",frm.doc.name);
        pay_amount.hidden = 1;
		frm.refresh_fields();
	}
}

function update_hourly_data(frm, r){
	frm.set_value('timesheet_hours',r.message[1][0]);
	frm.set_value('total_weekly_hours',r.message[1][1]);
	frm.set_value('current_job_order_hours',r.message[1][2][0]);
	frm.set_value('overtime_timesheet_hours',r.message[1][3][0])
	frm.set_value('total_weekly_overtime_hours',r.message[1][4][0]);
	frm.set_value('cuurent_job_order_overtime_hours',r.message[1][5][0]);
	frm.set_value('total_weekly_hiring_hours',r.message[1][6][0]);
	frm.set_value('total_weekly_overtime_hiring_hours',r.message[1][7][0])
	frm.set_value('overtime_timesheet_hours1',r.message[1][8][0]);
	frm.set_value('billable_weekly_overtime_hours',r.message[1][9][0]);
	frm.set_value('unbillable_weekly_overtime_hours',r.message[1][10]);
	frm.set_value('todays_overtime_hours',r.message[1][11]);
	frm.set_value('timesheet_payable_amount',r.message[2][0]);
	frm.set_value('timesheet_billable_overtime_amount_staffing',r.message[2][1]);
	frm.set_value('timesheet_unbillable_overtime_amount',r.message[2][2]);
	frm.set_value('total_job_order_payable_amount',r.message[2][3]);
	frm.set_value('total_job_order_billable_overtime_amount',r.message[2][4]);
	frm.set_value('total_job_order_unbillable_overtime_amount',r.message[2][5]);
}

function hide_action_button(frm){
	if(frm.doc.__islocal!=1 && ['Staffing', 'TAG'].includes(frappe.boot.tag.tag_user_info.company_type) && frm.doc.workflow_state=='Open'){
		$('.actions-btn-group').hide();
		frm.add_custom_button(__('Submit Timesheet'), function() {
			approve_timesheet(frm);
		}).addClass("btn-primary");
	}
}

function approve_timesheet(frm){
	frappe.call({
		method: "tag_workflow.tag_workflow.doctype.add_timesheet.add_timesheet.update_todays_timesheet",
		args: {"jo":frm.doc.job_order_detail, "timesheet_date":frm.doc.date_of_timesheet, "employee":frm.doc.employee,"timesheet":frm.doc.name,"company":frm.doc.company},
		callback: function(r){
			if(r.message==1){
				frappe.msgprint('Timesheet Submitted Successfully')
				window.location.reload()
			}
		}
	});
}

function check_mandatory_field(emp_id,emp_name){
	frappe.call({
	  method:"tag_workflow.tag_data.check_mandatory_field",
	  args:{emp_id: emp_id,check: 0,emp_name:emp_name},
	  callback: function(r){
		let msg = r.message[1] + " is missing the below required fields. You will be unable to approve their timesheets unless these fields are populated.<br><br>"
		if(r.message != "success"){
			frappe.validated = false
			msg += r.message[0]
		  	frappe.msgprint({message: __(msg), title: __("Warning"), indicator: "yellow",});
		}
	  }
	});
}

function check_break_time(frm){
	if((frm.doc.time_logs[0].break_start_time && !frm.doc.time_logs[0].break_end_time) || (frm.doc.time_logs[0].break_end_time && !frm.doc.time_logs[0].break_start_time)){
		frappe.msgprint('Please fill both the break time fields or clear them.');
		frappe.validated=false;
	}
}

function check_table_break_time(frm, child, cdt, cdn, event){
	if(child.from_time && child.to_time){
		let def_date=frm.doc.date_of_timesheet+" ";
		//Cond 1: Break Start Time < From Time or Break Start Time > To Time
		if(child.break_start_time && (Date.parse(def_date+child.break_start_time) < Date.parse(child.from_time) || Date.parse(def_date+child.break_start_time) > Date.parse(child.to_time))){
			$('.datepicker.active').removeClass('active');
			frappe.msgprint("Break Start Time should be between From Time and To Time.");
			frappe.model.set_value(cdt, cdn, "break_start_time", undefined);
			clear_times(cdt, cdn, event);
		}
		//Cond 2: Break End Time < From Time or Break End Time > To Time
		if(child.break_end_time && (Date.parse(def_date+child.break_end_time) < Date.parse(child.from_time) || Date.parse(def_date+child.break_end_time) > Date.parse(child.to_time))){
			$('.datepicker.active').removeClass('active');
			frappe.msgprint("Break End Time should be between From Time and To Time.");
			frappe.model.set_value(cdt, cdn, "break_end_time", undefined);
			clear_times(cdt, cdn, event);
		}
		check_table_break_time_contd(child, def_date, cdt, cdn, event);
	}
}

function check_table_break_time_contd(child, def_date, cdt, cdn, event){
	//Cond 3: Break End Time < Break Start Time
	if(child.break_start_time && child.break_end_time && Date.parse(def_date+child.break_end_time) < Date.parse(def_date+child.break_start_time)){
		$('.datepicker.active').removeClass('active');
		if(event == "break_start_time"){
			frappe.msgprint("Break Start Time should be before Break End Time.");
			frappe.model.set_value(cdt, cdn, "break_start_time", undefined);
		}else if(event == "break_end_time"){
			frappe.msgprint("Break End Time should be after Break Start Time.");
			frappe.model.set_value(cdt, cdn, "break_end_time", undefined);
		}
	}
}

function clear_times(cdt, cdn, event){
	if(["from_time", "to_time"].includes(event)){
		frappe.model.set_value(cdt, cdn, "break_start_time", undefined);
		frappe.model.set_value(cdt, cdn, "break_end_time", undefined);
	}
}
