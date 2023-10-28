frappe.listview_settings["Role Profile"] = {
	refresh: function (){
		frappe.msgprint("You don't have enough permissions.");
		frappe.set_route("app");
	}
}
