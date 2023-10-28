frappe.ui.form.on("Contract", {
	refresh: function(frm){
		$('[data-fieldname="industry_type"]').on("click", ()=>{
            $('input[data-fieldname="industry_type"]').removeAttr('disabled');
		})
		hide_and_show_tables(frm);
		$('.form-footer').hide();
		$('[class="btn btn-primary btn-sm primary-action"]').show();
		$('.custom-actions.hidden-xs.hidden-md').show();

		toggle_field();
		update_contract(frm);
		hide_submit_button(frm);
		update_hiring();
		update_user(frm);
		update_contract_labels(frm);
		if(cur_frm.doc.__islocal != 1){
			$('.form-message.blue').hide()
			frappe.db.get_value('Company',{'name':frm.doc.hiring_company},['name'],function(r){
				if(!r.name){
					request_sign(frm);
				}
			})
		}
		$(".menu-btn-group").hide()
		if(frm.doc.__islocal==1){
			cancel_cantract(frm);
		}

		if(cur_frm.doc.lead){
			
			frm.set_df_property('hiring_company','read_only', 1)
			frm.set_df_property('end_party_user','read_only', 1)
			frm.set_df_property('staffing_company','read_only', 1)


		}

		frm.set_df_property('contract_terms', 'read_only', 1);
		let child_table=['industry_type','job_titles','wages'];
		for(let i in child_table){
			$( "[data-fieldname="+child_table[i]+"]" ).on('mouseover',function(e) {
				let file=e.target.innerText;
				$(this).attr('title', file);
			});
		}

		if(frm.doc.__islocal==1 ||(cur_frm.doc.docstatus==0 && frappe.boot.tag.tag_user_info.company!=frm.doc.hiring_company)){
			frm.set_df_property('signe_hiring','hidden',1)
		}
	},

	setup: function(frm){
		frm.set_query("staffing_company", function(){
			return {
				filters: [
					["Company", "organization_type", "in", ["TAG", "Staffing"]]
				]
			}
		});
	},
	start_date:function(){
		$('[data-label = "Save"]').css('display', 'block');
	},
	contract_terms:function(){
		$('[data-label = "Save"]').css('display', 'block');
	},
	end_date:function(){
		$('[data-label = "Save"]').css('display', 'block');
	},

	before_save: function(frm){
		if(!frm.doc.staff_company || !frm.doc.party_name){
			cur_frm.set_value('staffing_company',frappe.boot.tag.tag_user_info.company)
			cur_frm.set_value('party_name',frappe.boot.tag.tag_user_info.company)
		}
		update_lead(frm);
		if(frm.doc.addendums=='<div class="ql-editor read-mode"><p><br></p></div>'){
			frm.set_value('addendums', '')
		}
		let roles = frappe.user_roles;
		if(roles.includes('Staffing Admin')|| roles.includes('Staffing User') || roles.includes('Tag Admin')){
			update_table(frm)
	} 
	},
	signe_company:function(frm){
		$('[data-label = "Save"]').css('display', 'block');
		if(frm.doc.signe_company){
			let regex = /[^0-9A-Za-z ]/g;
			if (regex.test(frm.doc.signe_company) === true){
				frappe.msgprint(__("Signature: Only alphabets and numbers are allowed."));
				frm.set_value('signe_company','')
				frappe.validated = false;
			}
		}
	},
	signe_hiring:function(frm){
		$('[data-label = "Save"]').css('display', 'block');
		if(frm.doc.signe_hiring){
			frm.set_value("sign_date_hiring", frappe.datetime.now_date());
			let regex = /[^0-9A-Za-z ]/g;
			if (regex.test(frm.doc.signe_hiring) === true){
				frappe.msgprint(__("Signature: Only alphabets and numbers are allowed."));
				frm.set_value('signe_hiring','')
				frappe.validated = false;
			}
		}
	},

	onload:function(frm) {
		filter_row(frm);
	},
	addendums: function(){
		$('[data-label = "Save"]').css('display', 'block');
	}
});

/*-----------field-----------*/
function toggle_field(){
	cur_frm.toggle_display("party_name", 0);
	let roles = frappe.user_roles;
	if((roles.includes("Hiring Admin") || roles.includes("Hiring User")) && (!roles.includes("Tag Admin") || !roles.includes("Tag User"))){
		$('[data-label = "Submit"]').hide();
		$('.form-message').hide();
		let fields = ['signe_company', 'contract_terms', 'signee_staffing', 'signe_company', 'requires_fulfilment', 'fulfilment_deadline', 'start_date', 'end_date', 'staffing_company', 'hiring_company', 'end_party_user', 'signe_company', 'lead', 'addendums'];
		for(let f in fields){
			cur_frm.toggle_enable(fields[f], 0);
		}
	}else{
		cur_frm.toggle_enable("signee_hiring", 0)
	}
}

/*--------makecontract--------*/

let _contract = `<p><b>Staffing/Vendor Contract</b></p>
<p>This Staffing/Vendor Contract (“Contract”) is entered into by and between Staffing Company and Hiring Company as further described and as set forth below. By agreeing to the Temporary Assistance Guru, Inc. (“TAG”) End-User License Agreement, and using the TAG application service and website (the “Service”) Staffing Company and Hiring Company agree that they have a contractual relationship with each other and that the following terms apply to such relationship:</p>

<p>(1) The billing rate Hiring Company shall pay Staffing Company to hire each temporary worker provided by Staffing Company (the “Worker”) is the rate set forth by the TAG Service for the location and position sought to be filled, and this rate includes all wages, worker’s compensation premiums, unemployment insurance, payroll taxes, and all other employer burdens recruiting, administration, payroll funding, and liability insurance.</p>
<p>(2) Hiring Company agrees not to directly hire and employ the Worker until the Worker has completed at least 720 work hours. Hiring Company agrees to pay Staffing Company an administrative placement fee of $3,000.00 if Hiring Company directly employs the Worker prior to completion of 720 work hours.</p>
<p>(3) Hiring Company acknowledges that it has complete care, custody, and control of workplaces and job sites. Hiring Company agrees to comply with all applicable laws, regulations, and ordinances relating to health and safety, and agrees to provide any site/task specific training and/or safety devices and protective equipment necessary or required by law. Hiring Company will not, without prior written consent of Staffing Company, entrust Staffing Company employees with the handling of cash, checks, credit cards, jewelry, equipment, tools, or other valuables.</p>
<p>(4) Hiring Company agrees that it will maintain a written safety program, a hazard communication program, and an accident investigation program. Hiring Company agrees that it will make first aid kits available to Workers, that proper lifting techniques are to be used, that fall protection is to be used, and that Hiring Company completes regular inspections on electrical cords and equipment. Hiring Company represents, warrants, and covenants that it handles and stores hazardous materials properly and in compliance with all applicable laws.</p>
<p>(5) Hiring Company agrees to post Occupational Safety and Health Act (“OSHA”) of 1970 information and other safety information, as required by law. Hiring Company agrees to log all accidents in its OSHA 300 logs. Hiring Company agrees to indemnify and hold harmless Staffing Company for all claims, damages, or penalties arising out of violations of the OSHA or any state law with respect to workplaces or equipment owned, leased, or supervised by Hiring Company and to which employees are assigned.</p>
<p>(6) Hiring Company will not, without prior written consent of Staffing Company, utilize Workers to operate machinery, equipment, or vehicles. Hiring Company agrees to indemnify and save Staffing Company and Workers harmless from any and all claims and expenses (including litigation) for bodily injury or property damage or other loss as asserted by Hiring Company, its employees, agents, the owner of any such vehicles and/or equipment or contents thereof, or by members of the general public, or any other third party, arising out of the operation or use of said vehicles and/or equipment by Workers.</p>
<p>(7) Commencement of work by dispatched Workers, or Hiring Company’s signature on work ticket serves as confirmation of Hiring Company’s agreement to conditions of service listed in or referred to by this Contract.</p>
<p>(8) Hiring Company agrees not to place Workers in a supervisory position except for a Worker designated as a “lead,” and, in that position, Hiring Company agrees to supervise all Workers at all times.</p>
<p>(9) Billable time begins at the time Workers report to the workplace as designated by the Hiring Company.</p>
<p>(10) Jobs must be canceled a minimum of 24 hours prior to start time to avoid a minimum of four hours billing per Worker.</p>
<p>(11) Staffing Company guarantees that its Workers will satisfy Hiring Company, or the first two hours are free of charge. If Hiring Company is not satisfied with the Workers, Hiring Company is to call the designated phone number for the Staffing Company within the first two hours, and Staffing Company will replace them free of charge.</p>
<p>(12) Staffing Company agrees that it will comply with Hiring Company’s safety program rules.</p>
<p>(13) Overtime will be billed at one and one-half times the regular billing rate for all time worked over forty hours in a pay period and/or eight hours in a day as provided by state law.</p>
<p>(14) Invoices are due 30 days from receipt, unless other arrangements have been made and agreed to by each of the parties.</p>
<p>(15) Interest Rate: Any outstanding balance due to Staffing Company is subject to an interest rate of two percent (2%) per month, commencing on the 90th day after the date the balance was due, until the balance is paid in full by Hiring Company.</p>
<p>(16) Severability. If any provision of this Contract is held to be invalid and unenforceable, then the remainder of this Contract shall nevertheless remain in full force and effect.</p>
<p>(17) Attorney’s Fees. Hiring Company agrees to pay reasonable attorney’s fees and/or collection fees for any unpaid account balances or in any action incurred to enforce this Contract.</p>
<p>(18) Governing Law. This Contract is governed by the laws of the state of Florida, regardless of its conflicts of laws rules.</p>
<p>(19) If Hiring Company utilizes a Staffing Company employee to work on a prevailing wage job, Hiring Company agrees to notify Staffing Company with the correct prevailing wage rate and correct job classification for duties Staffing Company employees will be performing. Failure to provide this information or providing incorrect information may result in the improper reporting of wages, resulting in fines or penalties being imposed upon Staffing Company. The Hiring Company agrees to reimburse Staffing Company for any and all fines, penalties, wages, lost revenue, administrative and/or supplemental charges incurred by Staffing Company.</p>
<p>(20) WORKERS' COMPENSATION COSTS: Staffing Company represents and warrants that it has a strong safety program, and it is Staffing Company’s highest priority to bring its Workers home safely every day. AFFORDABLE CARE ACT (ACA): Staffing Company represents and warrants that it is in compliance with all aspects of the ACA.</p>
<p>(21) Representatives. The Hiring Company and the Staffing Company each certifies that its authorized representative has read all of the terms and conditions of this Contract and understands and agrees to the same.</p>`

function update_contract(frm){
	if(frm.doc.end_party_user == frappe.session.user){
		frm.set_df_property('addendums', 'hidden', 1);
		frm.doc.addendums?frm.set_value('contract_terms', _contract+`<br><b>Addendums</b><br>`+frm.doc.addendums):frm.set_value("contract_terms", _contract);
	}
	else{
		cur_frm.set_value("contract_terms", _contract);
	}
}

/*-------update hiring-------*/
function update_hiring(){
	frappe.call({
		method: "tag_workflow.utils.whitelisted.get_company_list",
		args: {"company_type": "Hiring"},
		callback: function(r){
			if(r){
				let data = r.message || '';
				cur_frm.set_df_property("hiring_company", "options", data);
			}
		}
	});
}

/*-------update user----------*/
function update_user(frm){
	if(frm.doc.hiring_company){
		frappe.call({
			method: "tag_workflow.utils.whitelisted.get_user",
			args: {"company": frm.doc.hiring_company},
			callback: function(r){
				if(r){
					let data = r.message;
					cur_frm.set_df_property("end_party_user", "options", data);
				}
			}
		});
	}else{
		cur_frm.set_df_property("end_party_user", "options", "");
		cur_frm.set_value("end_party_user", "");
	}
}
/*------signature------*/
function request_sign(frm){
	if(cur_frm.doc.__islocal != 1 && cur_frm.doc.owner == frappe.session.user){
		frm.add_custom_button("Finalize & Request Signature", function() {
			company_onboard_sign(frm)
		}).addClass("btn-primary");
	}
}


/*------update lead status-------*/
function update_lead(frm){
	update_contract_labels(cur_frm);
	if(frm.doc.signe_hiring && frm.doc.lead && frm.doc.sign_date_hiring){
		cur_frm.set_value("sign_date_hiring", frappe.datetime.now_date());
		frappe.call({
			method: "tag_workflow.utils.whitelisted.update_lead",
			freeze:true,
			freeze_message:'Preparing Notification Of Staffing',
			args: {"lead": frm.doc.lead, "staff_company": frm.doc.staffing_company, "date": frappe.datetime.now_date(), "staff_user": frm.doc.contract_prepared_by, "name": frm.doc.name,"hiring_signee":frm.doc.signe_hiring,"hiring_sign_date":frappe.datetime.now_date()},
			callback:function(){
				window.location.reload()
			}
		});
	}
}

/*------update contract labels-------*/
function update_contract_labels(frm){
	if(frappe.boot.tag.tag_user_info.user_type == 'TAG Admin'){
		frappe.db.get_value('Lead', {'name' : cur_frm.doc.lead}, ['organization_type'],function(r){
			let organization_type = r.organization_type;
			if(organization_type =='Staffing'){
				frm.set_df_property('staffing_company', 'label', 'TAG Company');
				frm.set_df_property('hiring_company', 'label', 'Staffing Company');
				frm.set_df_property('signee_staffing', 'label', 'Signee (TAG Admin)');
				frm.set_df_property('signe_company', 'label', 'Signee TAG Admin');
				frm.set_df_property('signe_hiring', 'label', 'Signee Staffing');
				frm.set_df_property('sign_date_staffing', 'label', 'TAG Admin Signature Date');
				frm.set_df_property('sign_date_hiring', 'label', 'Stafing Signature Date');
			}
			else if(organization_type =='Hiring'||organization_type =='Exclusive Hiring'){
				frm.set_df_property('staffing_company', 'label', 'TAG Company');
				frm.set_df_property('signee_staffing', 'label', 'Signee (TAG Admin)');
				frm.set_df_property('signe_company', 'label', 'Signee TAG Admin');
				frm.set_df_property('sign_date_staffing', 'label', 'TAG Admin Signature Date');
			}
			  })

	}
	else{
		frappe.call({
			method: "tag_workflow.utils.whitelisted.get_contract_prepared_by",
			args: {
				"contract_prepared_by": frm.doc.contract_prepared_by,
			},
			callback: function(r) {
				let organization_type = r.message;
				if(frappe.boot.tag.tag_user_info.user_type  == 'Staffing Admin' && organization_type=='TAG'){
					frm.set_df_property('staffing_company', 'label', 'TAG Company');
					frm.set_df_property('hiring_company', 'label', 'Staffing Company');
					frm.set_df_property('signe_company', 'label', 'TAG Admin Company');
					frm.set_df_property('sign_date_staffing', 'label', 'TAG Admin Signature Date');
					frm.set_df_property('signe_hiring', 'label', 'Signee Staffing');
					frm.set_df_property('sign_date_hiring', 'label', 'Stafing Signature Date');
	
				}
				else if(frappe.boot.tag.tag_user_info.user_type  == 'Hiring Admin' && organization_type=='TAG'){
					frm.set_df_property('staffing_company', 'label', 'TAG Company');
					frm.set_df_property('signee_staffing', 'label', 'TAG Admin Company');
					frm.set_df_property('signe_company', 'label', 'TAG Admin Company');
					frm.set_df_property('sign_date_staffing', 'label', 'TAG Admin Signature Date');
				}
	
				else if(frappe.boot.tag.tag_user_info.user_type  == 'Hiring Admin' && organization_type=='Staffing'){
					frm.set_df_property('staffing_company', 'label', 'Staffing Company');
					frm.set_df_property('signee_staffing', 'label', 'Staffing Company');
					frm.set_df_property('signe_company', 'label', 'Staffing Company');
					frm.set_df_property('sign_date_staffing', 'label', 'Staffing Signature Date');
				}
			}
			});

	}


}

function cancel_cantract(frm){
	frm.add_custom_button(__('Cancel'), function(){
		frappe.set_route("Form", "Contract");
	});
}

function hide_submit_button(frm){
	if(frm.doc.__islocal!=1 && !frm.doc.signe_hiring){
		$('[data-label = "Submit"]').css('display', 'none');

	}	

}

frappe.ui.form.on("Job Titles", {
	job_titles:function(){
		$('[data-label = "Save"]').css('display', 'block');
	},
	job_titles_add:()=>{
		$('[data-fieldname="industry_type"]').on("click", ()=>{
			$('input[data-fieldname="industry_type"]').removeAttr('disabled');
		})
	}
})
frappe.ui.form.on("Industry Types", {
	industry_type:function(){
		$('[data-label = "Save"]').css('display', 'block');
	},
})
function company_onboard_sign(frm)
{
	if(frm.is_dirty()){
		frappe.msgprint({message: __('Firstly Save the doc'), title: __('Error'), indicator: 'orange'});
		frappe.validated=false;
	}else if(frm.doc.signe_company){
		frappe.call({
			method: "tag_workflow.controllers.crm_controller.onboard_org",
			freeze: true,
			freeze_message:
				"<p><b>Onboarding Company, Please wait.</b></p>",
			args: {
				"lead":frm.doc.lead,"contract_number":frm.doc.name
			},
			callback: function (r) {
				if(r.message!='user not created'){
					frappe.msgprint("Email Sent Successfully")
					frappe.msgprint("Signature Request Sent Successfully");
					setTimeout(()=>{
						window.location.reload();
					}, 2000);
				}
			}
		});
	}else{
		frappe.msgprint({message: __('Sign is required for onboarding the organization'), title: __('Error'), indicator: 'orange'});
		frappe.validated=false;
	}
}
