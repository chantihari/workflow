// Copyright (c) 2016, SourceFuse and contributors
// For license information, please see license.txt
/* eslint-disable */
function get_company_list(){
	let company = '\n';
	let user = [null, "TAG"].includes(frappe.boot.tag.tag_user_info.company) ? "admin":"user";
	frappe.call({
		"method": "tag_workflow.tag_workflow.report.employee_timesheet_report.employee_timesheet_report.get_company_list",
		"args": {"company": frappe.boot.tag.tag_user_info.comps, "user":user},
		"async": 0,
		"callback": function(r){
			company += r.message;
		}
	});
	return company
}
frappe.query_reports["Employee Timesheet Report"] = {
	"filters": [
		{
			"fieldname": "employee",
			"label": __("Employee Code"),
			"fieldtype": "Link",
			"options": "Employee"
		},
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Select",
			"options": get_company_list(),
		},
	]
};

$("[data-route='query-report/Employee Timesheet Report'] .sub-heading").html("A report summarizing the hours worked by an employee during a specific period of time.");