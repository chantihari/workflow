// Copyright (c) 2019, Frappe Technologies and contributors
// For license information, please see license.txt
frappe.ui.form.off("Notification Log", "open_reference_document");
frappe.ui.form.on('Notification Log', {
	open_reference_document: function(frm) {
		const document_type = frm.doc.document_type;
		const document_name = frm.doc.document_name;
		let user_roles = frappe.user_roles;	
        if((document_type == 'Timesheet') && (user_roles.includes("Staffing Admin") || user_roles.includes("Staffing User"))){
			frappe.db.get_value("Timesheet", { name: document_name},"job_order_detail", function(r1){
				let job_order = r1.job_order_detail;
				if (frm.doc.subject.includes("has submitted a timesheet for")){
					frappe.set_route('Form', document_type, document_name);
					
				}
				else{
					localStorage.setItem("order", job_order);
					window.location.href = "/app/timesheet-approval";
					
				}
			})
	}
        else{
            frappe.set_route('Form', document_type, document_name);
        }
		
	}
});