// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Holiday List", {
	setup:function(frm){
		frm.set_query("company", function() {
			return {
				"filters":[ ['Company', "organization_type", "in", ["Staffing" ]],['Company',"make_organization_inactive","=",0]]
			}
		});
	},
	refresh:function(frm){
		$("div.form-dashboard").hide();
		if (frm.doc.__islocal==1 && frappe.boot.tag.tag_user_info.company_type == "Staffing") {
            frm.set_value('company',(frappe.boot.tag.tag_user_info.comps.length==1) ? frappe.boot.tag.tag_user_info.company : '')
        }
		if (frm.doc.__islocal==1 && frappe.boot.tag.tag_user_info.company_type == "TAG") {
			frm.set_value('company','')
			frm.refresh_fields();
		}
		if(frm.doc.__islocal!=1){
			cur_frm.set_df_property('company','read_only',1)
		}
		if (frm.doc.holidays) {
			frm.set_value("total_holidays", frm.doc.holidays.length);
		}
		$("#navbar-breadcrumbs > li.disabled > a").html(frm.doc.holiday_list_name) 
		$('h3[title = "'+frm.doc.name+'"]').html(frm.doc.holiday_list_name); 
		

	

	},
	from_date: function(frm) {
		if (frm.doc.from_date && !frm.doc.to_date) {
			let a_year_from_start = frappe.datetime.add_months(frm.doc.from_date, 12);
			frm.set_value("to_date", frappe.datetime.add_days(a_year_from_start, -1));
		}
	},
	before_save: function(frm){
		frm.call({
			'method':"tag_workflow.utils.holiday_list.active_holiday_list",
			'args': {'company_name':frm.doc.company,'holiday_list_name':frm.doc.holiday_list_name,"status":frm.doc.status ,"name":frm.doc.name}
		})
	

	},
	validate: function(frm){
		if(frm.is_new()){
			frappe.db.get_value('Holiday List',{'holiday_list_name':frm.doc.holiday_list_name,'company':frm.doc.company},["name"],function(r){
				if(r.name){
					frappe.msgprint("Holiday List with this name already exists")
					frappe.validated = false; 
				}
		
		})
	}
	},
	to_date:function(frm){
		if(frm.doc.weekly_off){
			frappe.call({
				method:"get_weekly_off_dates",
				doc:frm.doc
			})
		}
		
	}
});

frappe.tour["Holiday List"] = [
	{
		fieldname: "holiday_list_name",
		title: "Holiday List Name",
		description: __("Enter a name for this Holiday List."),
	},
	{
		fieldname: "from_date",
		title: "From Date",
		description: __("Based on your HR Policy, select your leave allocation period's start date"),
	},
	{
		fieldname: "to_date",
		title: "To Date",
		description: __("Based on your HR Policy, select your leave allocation period's end date"),
	},
	{
		fieldname: "weekly_off",
		title: "Weekly Off",
		description: __("Select your weekly off day"),
	},
	{
		fieldname: "get_weekly_off_dates",
		title: "Add Holidays",
		description: __("Click on Add to Holidays. This will populate the holidays table with all the dates that fall on the selected weekly off. Repeat the process for populating the dates for all your weekly holidays"),
	},
	{
		fieldname: "holidays",
		title: "Holidays",
		description: __("Here, your weekly offs are pre-populated based on the previous selections. You can add more rows to also add public and national holidays individually.")
	},
];
