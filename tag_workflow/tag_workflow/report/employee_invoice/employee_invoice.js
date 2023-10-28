// Copyright (c) 2016, SourceFuse and contributors
// For license information, please see license.txt
/* eslint-disable */
function get_first_sunday(month,year){
	let tempDate = new Date();
    tempDate.setHours(0,0,0,0);
    // first SUNDAY 
    tempDate.setMonth(month);
    tempDate.setYear(year);
    tempDate.setDate(1);

    let day = tempDate.getDay();
    let toNextSun = day !== 0 ? 7 - day : 0;
    tempDate.setDate(tempDate.getDate() + toNextSun);

	let first_sunday = moment(tempDate).format("YYYY-MM-DD")
    
	if(first_sunday < frappe.datetime.get_today()){
		return first_sunday
	}
	else{
		return frappe.datetime.get_today()
	}
}

frappe.query_reports["Employee Invoice"] = {
	"filters": [
		{
			"fieldname":"start_date",
			"label": ("From Date"),
			"fieldtype": "Date",
			"width": "80",
			"reqd": 1,
			"default": get_first_sunday(new Date().getMonth(),new Date().getUTCFullYear())},
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
