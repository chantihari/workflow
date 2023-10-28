frappe.listview_settings["Report"] = {
	refresh: function (){
		let roles = frappe.user_roles;
		if(!(roles.includes("Tag Admin") || roles.includes("Tag User"))){
			frappe.msgprint("You don't have enough permissions.");
			frappe.set_route("app");
		}
	}
}
