// Copyright (c) 2022, SourceFuse and contributors
// For license information, please see license.txt

frappe.ui.form.on('Staffing Comp Code', {
	setup:function(frm){
		frm.set_query("staffing_company", function() {
			return {
				"filters":[ ['Company', "organization_type", "in", ["Staffing" ]],['Company',"make_organization_inactive","=",0]]
			}
		});
		frm.set_query("job_title", function(doc) {
			let industry_type=frm.doc.job_industry?frm.doc.job_industry:''
			let company=cur_frm.doc.staffing_company?frm.doc.staffing_company:''
			return {
				query: "tag_workflow.tag_workflow.doctype.staffing_comp_code.staffing_comp_code.get_title_industry_list",
				filters: {
						'industry_type':industry_type,
						'company':company
				},
			};
		});
		frm.set_query("job_industry", function(doc) {
			let job_title=frm.doc.job_title?frm.doc.job_title:''
			return {
				query: "tag_workflow.tag_workflow.doctype.staffing_comp_code.staffing_comp_code.get_industry_title_list",
				filters: {
						'job_title':job_title
				},
			};
		});
			
	},
	refresh:function(frm){
		$('.form-footer').hide();
		if (frm.doc.__islocal==1 && frappe.boot.tag.tag_user_info.company_type == "Staffing") {
			frappe.call({
				'method': "tag_workflow.tag_data.lead_org",
				'args': { 'current_user': frappe.session.user },
				'callback': function (r) {
					if (r.message == 'success') {
						frm.set_value('staffing_company', frappe.boot.tag.tag_user_info.company)
						frm.refresh_fields();
					}
					else {
						frm.set_value('staffing_company','')
						frm.refresh_fields();
					}
				}
			});
		}
		if (frm.doc.__islocal==1 && (frappe.boot.tag.tag_user_info.company_type == "TAG" || frappe.session.user=='Administrator')) {
			frm.set_value('staffing_company','')
			frm.refresh_fields();
		}
		if(frm.doc.__islocal!=1){
			let fields = ['job_industry', 'job_title', 'staffing_company'];
			for(let i in fields){
				frm.set_df_property(fields[i],'read_only',1)
			}
		}
	},
	job_industry:function(frm){
		if(frm.doc.job_title && frm.doc.industry_type){
			check_previous_staffing_data(frm)
		}
	},
	job_title:function(frm){
		if(frm.doc.job_title && frm.doc.industry_type){
			check_previous_staffing_data(frm)
		}
	},
	before_save:function(frm,cdt,cdn){
		check_previous_staffing_data(frm)
		check_all_values_add(frm)
		check_same_state(frm,cdt,cdn)
	}
});
function check_previous_staffing_data(frm){
	frappe.call({
		method:'tag_workflow.tag_workflow.doctype.staffing_comp_code.staffing_comp_code.check_previous_used_job_titles',
		args:{'industry_type':frm.doc.job_industry,'company':frm.doc.staffing_company,'job_title':frm.doc.job_title},
		"async": 0,
		"callback": function(r){
			if(r.message==1){
				frappe.msgprint({
				message: __("Comp Code is already created for "+frm.doc.job_title+" for "+ frm.doc.staffing_company),
				title: __("Error"),
				indicator: "orange",
				});
				frm.set_value("job_title",'');
				frappe.validated = false
			}
		}
	});
}
frappe.ui.form.on('Class Code', {
	state: (frm, cdt, cdn)=>{
		let row = locals[cdt][cdn];
		let state=row.state
		let state_indx=row.idx-1
		if(row.state){
			let table_data = frm.doc.class_codes;
			check_similar_state(frm,table_data,state,state_indx,cdt,cdn)
		}
	},
	class_code:function(frm,cdt,cdn){
		let child1=locals[cdt][cdn]
		let value=child1['class_code']
		if((value.length)>10){
			frappe.msgprint({
			message: __("Maximum Characters allowed for Class Code are 10."),
			title: __("Error"),
			indicator: "orange",
			});
			frappe.model.set_value(cdt,cdn,"class_code",'');
			frappe.validated = false        
		}
	}
});
function check_similar_state(frm,table_data,state,state_indx,cdt,cdn){
	for(let i=0;i<state_indx;i++){
		if(table_data[i].state==state){
			frappe.msgprint(__('Comp code already exist for ' + state));
			frappe.model.set_value(cdt, cdn, 'state', '');
			frm.refresh_field('class_codes');
			frappe.validated=false
		}
	}
}

function check_all_values_add(frm){
	let table_data = frm.doc.class_codes ;
	if(table_data){
		table_data.forEach((x) => {
			if(!x.state || !x.class_code || !x.rate){
				frappe.msgprint(__('All fields are required to add in Class Code Table to store the value'));
				frappe.validated=false;
			}
		})
	}
	
}
function check_same_state(frm,cdt,cdn){
	let table_data = frm.doc.class_codes ;
	if(table_data){
		for(let i=(table_data.length)-1;i>0;i--){
			let state=table_data[i].state
			let state_indx=i
			check_similar_state(frm,table_data,state,state_indx,cdt,cdn)
		}
	}
}