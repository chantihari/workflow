// Copyright (c) 2023, SourceFuse and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Billing Report by Job Site"] = {
	"filters": [
		{
			"fieldname":"start_date",
			"label": ("From Date"),
			"fieldtype": "Date",
			"width": "100",
			"reqd": 0,
			"default": frappe.datetime.month_start()
		},
		{
			"fieldname":"end_date",
			"label": ("To Date"),
			"fieldtype": "Date",
			"width": "100",
			"reqd": 0,
			"default": frappe.datetime.get_today()
		},
		{
			"fieldname":"job_sites",
			"label": ("Job Site Name"),
			"fieldtype": "Data",
			"width": "100",
			"reqd": 0
		}
	]
};

$("[data-route='query-report/Billing Report by Job Site'] .sub-heading").html("A report showing the billing summary of a specific jobsite.");