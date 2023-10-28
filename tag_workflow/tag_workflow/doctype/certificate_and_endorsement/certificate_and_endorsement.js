// Copyright (c) 2022, SourceFuse and contributors
// For license information, please see license.txt

frappe.ui.form.on('Certificate and Endorsement', {
	before_save: function(frm){
		// frm.doc.certificate_types = frm.doc.certification_name
		console.log(cur_frm.doc.certification_name)
		frm.doc.certificate_types =  frm.doc.certification_name
	}

});
