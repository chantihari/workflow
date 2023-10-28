// Copyright (c) 2016, SourceFuse and contributors
// For license information, please see license.txt
/* eslint-disable */

function get_company_list(){
	let company = '\n';
	frappe.call({
		"method": "tag_workflow.tag_workflow.report.employee_status_report.employee_status_report.get_staffing_company",
		"args": {"company_type": frappe.boot.tag.tag_user_info.company_type,'current_user':frappe.session.user,'user_company':frappe.boot.tag.tag_user_info.company},
		"async": 0,
		"callback": function(r){
			company += r.message;
		}
	});
	return company
}

frappe.query_reports["Employee Status Report"] = {
	
	"filters": [
		{
			'fieldname':'first_name',
			'label':'Employee First Name',
			'fieldtype':'Data',
		},
		{
			'fieldname':'last_name',
			'label':'Employee Last Name',
			'fieldtype':'Data',
		},
		{
			'fieldname': "company",
			"options": get_company_list(),
			'label': "Staffing Company",
			'fieldtype':'Select',
		},
		{
			'fieldname':'job_order',
			'label':'Job Order',
			'fieldtype':'Data',
		},
		{
			'fieldname': 'start_date',
			'label': 'Start Date',
			'fieldtype': 'Date',
		},
		{
			'fieldname': 'status',
			'label': 'Status',
			'fieldtype': 'Select',
			'options':'\nDNR\nUnsatisfactory\nNo Show'
		},
		
	],
	onload:function(){
		
		$('input[data-fieldname="start_date"]').on('change',(e)=>{
			e.preventDefault();
			if(! e.originalEvent){
				console.log($('input[data-fieldname="start_date"]').val());
				$('button[data-original-title="Refresh"]').click()
			}		
		})

		setTimeout(function(){
			$('[data-index="3"]').hide()
		},1000)
	}

};

$("[data-route='query-report/Employee Status Report'] .sub-heading").html("A report to provide management with a clear understanding of the status of employees who are not meeting expectations.");