// Copyright (c) 2016, SourceFuse and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Unsatisfactory Employees"] = {
	"filters": [
		{
			"fieldname":"start_date",
			"label": ("Start Date"),
			"fieldtype": "Date",
			"width": "80",
			"reqd": 1,
			"default": frappe.datetime.month_start()
		},
		{
			"fieldname":"end_date",
			"label": ("End Date"),
			"fieldtype": "Date",
			"width": "80",
			"reqd": 0,
			"default": frappe.datetime.get_today()
		}
	]
};
