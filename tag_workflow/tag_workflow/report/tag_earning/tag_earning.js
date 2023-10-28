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
frappe.query_reports["TAG Earning"] = {
	"filters": [
		{
				"fieldname": "company",
				"label": __("Staffing Company"),
				"fieldtype": "Select",
				"options": get_staffing_company_list(),
		},
		{
			"fieldname":"start_date",
			"label": ("From Date"),
			"fieldtype": "Date",
			"width": "80",
			"reqd": 1,
			"default": frappe.datetime.month_start()
		},
		{
			"fieldname":"end_date",
			"label": ("To Date"),
			"fieldtype": "Date",
			"width": "80",
			"reqd": 1,
			"default": frappe.datetime.get_today()
		}
	]
};
