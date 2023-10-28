frappe.require('/assets/tag_workflow/js/emp_functions.js');
frappe.ui.form.on('Job Offer', {
    setup: (frm) => {
        frm.set_query('company', function(){
            return {
                filters: [
                    ['Company', 'organization_type', '=', 'Staffing'],
                    ['Company','make_organization_inactive','=',0]
                ]
            }
        });
        set_company(frm, 'company');
	}
});
