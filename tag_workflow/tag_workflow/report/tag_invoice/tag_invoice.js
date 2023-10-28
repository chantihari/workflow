// Copyright (c) 2016, SourceFuse and contributors
// For license information, please see license.txt
/* eslint-disable */
function get_staffing_company_list(){
	let company = '\n';
	frappe.call({
		"method": "tag_workflow.utils.whitelisted.get_staffing_company_list",
		"args": {"company_type": "Hiring"},
		"async": 0,
		"callback": function(r){
			company += r.message;
		}
	});
	return company
}
frappe.query_reports["Tag Invoice"] = {
	"filters": [
		{
				"fieldname": "company",
				"label": __("Staffing Company"),
				"fieldtype": "Select",
				"options": get_staffing_company_list(),
		},
		{
			"fieldname": 'status',
            "label": __('Status'),
            "fieldtype": 'Select',
            "options": '\nCompleted\nOngoing\nUpcoming',
			"width":100,
			"reqd":0,
		},
		{
			"fieldname":"month",
			"label":"Month",
			"fieldtype": "Select",
			"options":'January\nFebruary\nMarch\nApril\nMay\nJune\nJuly\nAugust\nSeptember\nOctober\nNovember\nDecember',
			"width":"80",
			"default": "January"
			
		},
		{
			"fieldname":"from_fiscal_year",
			"label": __("Start Year"),
			"fieldtype": "Select",
			"options": year_list(),
			"reqd": 1,
			"default": new Date().getUTCFullYear()

		},
	],
	onload:function(){
		if (!frappe.user_roles.includes('Tag Admin')){
			// setTimeout(hide_field,100)
			hide_field()
		}
	}	
};

function hide_field(){
	frappe.query_report.get_filter("company").toggle(false)

}

function  year_list(){
	let year_opt = '2021'
	let start_year = 2021
	let current_year = new Date().getUTCFullYear()

	for (let i = start_year +1;i <=current_year;i++){
		year_opt += '\n' + i
	}
return year_opt
}