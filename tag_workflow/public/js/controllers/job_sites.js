frappe.require('/assets/tag_workflow/js/twilio_utils.js');
frappe.ui.form.on("Job Site", {
	refresh: function(frm){
		if(frm.doc.__islocal){
			console.log(frm.doc.__islocal);
		}
		$('[class="btn btn-primary btn-sm primary-action"]').show();
		$('.custom-actions.hidden-xs.hidden-md').show();
	},
	validate:function(frm){
		let zip=frm.doc.zip;
		if (zip){
			frm.set_value('zip',zip.toUpperCase());
			if(!validate_zip(zip)){
				frappe.msgprint({message: __('Invalid Zip!'), indicator: 'red'})
				frappe.validated = false;
			}
		}
	},
	zip: function(frm){
		let zip = frm.doc.zip;
		frm.set_value('zip', zip?zip.toUpperCase():zip);
	}
});

