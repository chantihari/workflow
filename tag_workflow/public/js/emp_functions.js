/*---------For Employee and Employee Onboarding Forms----------*/
/*--------------------Address Field Updates--------------------*/
function show_addr(frm){
	if(frm.doc.search_on_maps){
		frm.get_docfield('street_address').label = 'Complete Address';
	}else if(frm.doc.enter_manually){
		frm.get_docfield('street_address').label = 'Street Address';
	}
    if(frm.doc.enter_manually == 1){
        frm.toggle_display("complete_address", 0);
    }else{
        frm.toggle_display("complete_address", 1);
    }
	frm.refresh_field('street_address');
}

/*--------------------Update Complete Address---------------------*/
function update_complete_address(frm){
	if(frm.doc.zip && frm.doc.state && frm.doc.city){
	    let data = {
	        street_number: frm.doc.street_address ? frm.doc.street_address : '',
	        route: frm.doc.suite_or_apartment_no ? frm.doc.suite_or_apartment_no : '',
	        locality: frm.doc.city,
	        administrative_area_level_1 : frm.doc.state,
	        postal_code : frm.doc.zip ? frm.doc.zip : 0,
	    };
		update_comp_address(frm,data);
	}
	else{
	    frm.set_value('complete_address','');
    }
}

function update_comp_address(frm,data){
	frappe.call({
	    method:'tag_workflow.tag_data.update_complete_address',
	    args:{
	        data:data
	    },
	    callback:function(r){
	        if(r.message!='No Data')
	        {
	            if(r.message!=frm.doc.complete_address){
	                frm.set_value('complete_address',r.message);
	            }
	        }
	        else{
	            frm.set_value('complete_address','');
	        }
	    }
	});
}

function show_fields(frm){
	frm.set_df_property('city','hidden',0);
	frm.set_df_property('state','hidden',0);
	frm.set_df_property('zip','hidden',0);
}

function remove_lat_lng(frm){
	if((frm.doc.enter_manually) && (!frm.doc.zip && !frm.doc.city && !frm.doc.state) && (frm.doc.lat || frm.doc.lng)){
		frm.set_value('complete_address',undefined);
		set_lat_lng_undefined(frm);

	}
	else if((frm.doc.search_on_maps) && (!frm.doc.complete_address) && (frm.doc.lat || frm.doc.lng)){
		frm.set_value('state',undefined);
		frm.set_value('city',undefined);
		frm.set_value('zip',undefined);
		set_lat_lng_undefined(frm);
	}
}

function set_lat_lng_undefined(frm){
	frm.set_value('suite_or_apartment_no',undefined);
	frm.set_value('street_address',undefined);
	frm.set_value('lat',undefined);
	frm.set_value('lng',undefined);
}

function update_lat_lng(frm){
	if(frm.doc.complete_address){
		frappe.call({
			method:"tag_workflow.tag_data.set_lat_lng",
			args:{
				'emp_name': frm.doc.name,
				'address': frm.doc.complete_address
			}
		});
	}
}

/*---------------First Letter Uppercase------------------*/
function name_update(string){
	return string.charAt(0).toUpperCase() + string.slice(1);
}

/*-----------------Validate Phone and Zip----------------*/
function validate_phone_zip(frm){
	let contact_number = frm.doc.contact_number;
	let zip = frm.doc.zip;
	if(contact_number){
		if(!validate_phone(contact_number)){
			frappe.msgprint({message: __("Invalid Contact Number!"),indicator: "red"});
			frappe.validated = false;
		}
		else{
			frm.set_value('contact_number', validate_phone(contact_number));
		}
	}
	if (zip){
		frm.set_value('zip', zip.toUpperCase());
		if(!validate_zip(zip)){
			frappe.msgprint({message: __("Invalid Zip!"),indicator: "red"});
			frappe.validated = false;
		}
	}
}

function check_ssn(frm){
	let validate = true;
	if(frm.doc.sssn){
		if(frm.doc.sssn=='•••••••••'){
			frm.set_value('sssn','•••••••••');
		}
		else if(!$.isNumeric(frm.doc.sssn)){
			frappe.msgprint(__('Only numbers are allowed in SSN.'));
			frm.set_value('ssn', '');
			frm.set_value('sssn', '');
			frm.doc.decrypt_ssn = 0;
			validate = false;
		}
		else{
			frm.set_value('ssn', frm.doc.sssn)
			frm.set_value('sssn', '•••••••••');
		}
	}else{
		frm.set_value('ssn', '');
		frm.set_value('sssn', '');
	}
	return validate;
}

function mandatory_fields(fields){
	let message = '<b>Please Fill Mandatory Fields:</b>';
	for (let key in fields) {
		if(key == 'Activities'){
			if(table_reqd(fields[key])){
				message = message + '<br>' + '<span>&bull;</span> Activities';
			}
		}
		else if(fields[key] === undefined || !fields[key]){
			message = message + '<br>' + '<span>&bull;</span> ' + key;
		}
	}
	if (message != '<b>Please Fill Mandatory Fields:</b>') {
		frappe.msgprint({ message: __(message), title: __('Missing Fields'), indicator: 'orange'});
		frappe.validated = false;
	}
}

function table_reqd(table_data){
	let check = false;
	if(table_data){
		table_data.forEach((x) => {
			if(!x.activity_name || (x.activity_name && !x.activity_name.trim()) || (x.document_required && (!x.document || !x.attach))){
				check = true;
			}
		});
	}
	return check;
}

/*----For Employee Onboarding and Employee Onboarding Template Forms----*/
function check_count(frm, cdt, cdn){
	let row = locals[cdt][cdn];
	if(row.document){
		let doc_count = count_doc(frm);
		if(doc_count[row.document]>1){
			frappe.msgprint(__('You can attach ' + row.document + ' only once.'));
			frappe.model.set_value(cdt, cdn, 'document', '');
			frm.refresh_field('activities');
		}
	}
}

function document_required(frm, cdt, cdn){
	let row = locals[cdt][cdn];
	if(row.document_required == 0){
		frappe.model.set_value(cdt, cdn, 'document', '');
		frappe.model.set_value(cdt, cdn, 'attach', '');
		frm.refresh_field('activities');
	}
}

function document_field(frm, cdt, cdn){
	frappe.model.set_value(cdt, cdn, 'attach', '');
	frm.refresh_field('activities');

	let row = locals[cdt][cdn];
	if(row.document){
		let doc_count = count_doc(frm);
		if(doc_count[row.document]>1){
			frappe.msgprint(__('You can attach ' + row.document + ' only once.'));
			frappe.model.set_value(cdt, cdn, 'document', '');
			frm.refresh_field('activities');
		}
	}
}

function count_doc(frm){
	let table_data = frm.doc.activities;
	let doc_counts = {};
	table_data.forEach((x) => {
		if(x.document && ['Resume','W4','E verify', 'New Hire Paperwork', 'I9'].includes(x.document)){
			doc_counts[x.document] = (doc_counts[x.document] || 0) + 1; 
		}
	});
	return doc_counts;
}

function set_company(frm, fieldname){
	if(frm.doc.__islocal == 1){
		frm.set_value(fieldname,(frappe.boot.tag.tag_user_info.comps.length==1) ? frappe.boot.tag.tag_user_info.company : "");
	}
}

function get_user(frm){
	frm.fields_dict.activities.grid.get_field('user').get_query = ()=>{
		let user_data = frm.doc.activities, user_list = [];
		for (let x in user_data){
			if(user_data[x]['user']){
				user_list.push(user_data[x]['user']);
			}
		}
		let company = frm.doc.doctype == 'Employee Onboarding' ? frm.doc.staffing_company : frm.doc.company;
		return {
			query: 'tag_workflow.tag_data.filter_user',
			filters: {
				'company': company,
				'user_list': user_list
			}
		}
	}
}

function branch_banner(doctype){
	//For Branch Integration
	if(frappe.boot.tag.tag_user_info.company_type=='Staffing'){
		frappe.db.get_value('Company', {'name': frappe.boot.tag.tag_user_info.company}, ['branch_enabled'], (res)=>{
			frappe.db.get_value('User', {'name': frappe.session.user}, ['branch_banner'], (r)=>{
				if(res && r && res.branch_enabled==0 && r.branch_banner==1){
					let banner_html = `
					<div class = 'banner-container'>
						<button id= "close_banner" onclick = close_banner()>
							<span>&times;</span>
						</button>
						<img id = "banner" src= "/assets/tag_workflow/images/branch.jpg">
						<button id="sign_up" onclick="location.href='https://www.branchapp.com/'">Sign Up</button>
						<button id="more_info" onclick="location.href='https://get.branchapp.com/demo'">Request More Information</button>
					</div>
					<script>
					function close_banner(){
						$('#close_banner').hide();
						$('#banner').hide();
						$('#sign_up').hide();
						$('#more_info').hide();
						frappe.db.set_value('User', frappe.session.user, 'branch_banner', 0);
					}</script>
					`
					$('[data-page-route="List/'+doctype+'/List"] .layout-main-section.frappe-card').prepend(banner_html);
				}
			});
		});
	}
}
frappe.views.QueryReport.prototype.get_menu_items = function() {
	let items = [
		{
			label: __('Refresh'),
			action: () => this.refresh(),
			class: 'visible-xs'
		},
		{
			label: __('Print'),
			action: () => {
				let dialog = frappe.ui.get_print_settings(
					false,
					print_settings => this.print_report(print_settings),
					this.report_doc.letter_head,
					this.get_visible_columns()
				);
				this.add_portrait_warning(dialog);
			},
			condition: () => frappe.model.can_print(this.report_doc.ref_doctype),
			standard: true
		},
		{
			label: __('PDF'),
			action: () => {
				let dialog = frappe.ui.get_print_settings(
					false,
					print_settings => this.pdf_report(print_settings),
					this.report_doc.letter_head,
					this.get_visible_columns()
				);

				this.add_portrait_warning(dialog);
			},
			condition: () => frappe.model.can_print(this.report_doc.ref_doctype),
			standard: true
		},
		{
			label: __('Export'),
			action: () => this.export_report(),
			condition: () => frappe.model.can_export(this.report_doc.ref_doctype),
			standard: true
		},
		{
			label: __('User Permissions'),
			action: () => frappe.set_route('List', 'User Permission', {
				doctype: 'Report',
				name: this.report_name
			}),
			condition: () => frappe.model.can_set_user_permissions('Report'),
			standard: true
		}
	];

	if (frappe.user.is_report_manager()) {
		items.push({
			label: __('Save'),
			action: () => {
				let d = new frappe.ui.Dialog({
					title: __('Save Report'),
					fields: [
						{
							fieldtype: 'Data',
							fieldname: 'report_name',
							label: __("Report Name"),
							default: this.report_doc.is_standard == 'No' ? this.report_name : "",
							reqd: true
						}
					],
					primary_action: (values) => {
						frappe.call({
							method: "frappe.desk.query_report.save_report",
							args: {
								reference_report: this.report_name,
								report_name: values.report_name,
								columns: this.get_visible_columns()
							},
							callback: function(r) {
								this.show_save = false;
								d.hide();
								frappe.set_route('query-report', r.message);
							}
						});
					}
				});
				d.show();
			},
			standard: true
		})
	}

	return items;
}