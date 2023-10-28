frappe.listview_settings['Job Titles'] = { 
	let roles = frappe.user.organization;
	filters : [["disabled","=",0],["organization","=", "roles"]]]
	onload: function(listview) { 

		// listview.$page.find(`div[data-fieldname='name']`).addClass('hide');
		
		} 
	};

