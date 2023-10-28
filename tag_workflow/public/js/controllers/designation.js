frappe.ui.form.on("Designation", {
	refresh: function(frm){
		if(frm.doc.__islocal){
			console.log(frm.doc.__islocal);
		}
		$('[class="btn btn-primary btn-sm primary-action"]').show();
		$('.custom-actions.hidden-xs.hidden-md').show();
	},
	validate: function (frm) {
		if (frm.doc.__islocal) {

			if (frm.doc.designation_name.indexOf('-') > 0){
				frm.set_value("designation",frm.doc.designation_name.split('-')[0]);
			}else{
				frm.set_value("designation",frm.doc.designation_name);
			}
			cur_frm.refresh_field("designation");
			frappe.call({
				"method": "tag_workflow.tag_data.checkingdesignationandorganization",
				"args": {"designation_name": frm.doc.designation,
						"company": frm.doc.organization
						},
				"async": 0,
				"callback": function(r){
					if (!(r.message)){
						frappe.msgprint({
					        message: __("Designation name already exists for this organization"),
					        title: __("Error"),
					        indicator: "orange",
					      });
						frappe.validated = false
					}
				}
			})
			frappe.call({
				"method": "tag_workflow.utils.doctype_method.checkingdesignation_name",
				"args": {"designation_name": frm.doc.designation_name,

						},
				"async": 0,
				"callback": function(r){
					frm.set_value("designation_name", r.message);
					cur_frm.refresh_field("designation_name");
				}
			});
		}
	}

}); 
	
