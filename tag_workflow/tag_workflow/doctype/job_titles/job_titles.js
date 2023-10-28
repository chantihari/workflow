// Copyright (c) 2021, SourceFuse and contributors
// For license information, please see license.txt

frappe.ui.form.on('Job Titles', {
	refresh: function() {
		$('.form-footer').hide();
		$('[class="btn btn-primary btn-sm primary-action"]').show();
		$('.custom-actions.hidden-xs.hidden-md').show();
	}
});
