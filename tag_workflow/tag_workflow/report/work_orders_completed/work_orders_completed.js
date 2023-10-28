// Copyright (c) 2016, SourceFuse and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Work Orders Completed"] = {
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
		{
			"fieldname": 'status',
            "label": __('Past Order'),
            "fieldtype": 'Select',
            "options": 'Total work orders, Time, and Cost for a staffing agency\nList of employees worked with, count of times, and hours worked\nTotal cost for a staffing company over a period of time',
			"width":200,
			"reqd":0,
			"default":'Total work orders, Time, and Cost for a staffing agency'
		}

		
	]
};
