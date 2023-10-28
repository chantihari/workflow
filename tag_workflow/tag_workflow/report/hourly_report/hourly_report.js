// Copyright (c) 2016, SourceFuse and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Hourly Report"] = {
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
			"fieldname":"companies",
			"label": ("Staffing Company Name"),
			"fieldtype": "Data",
			"width": "100",
			"reqd": 0,
		},	
	]
};
