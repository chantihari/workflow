frappe.provide('frappe.ui.form')
frappe.ui.form.PayrollPeriodQuickEntryForm = class PayrollPeriodQuickEntryForm extends frappe.ui.form.QuickEntryForm{
	constructor(doctype, after_insert, init_callback, doc, force) {
		super(doctype, after_insert, init_callback, doc, force);
		this.skip_redirect_on_error = true; 
	}
    render_dialog() {
		this.mandatory = this.mandatory.concat();
		super.render_dialog();
        check_status(this.dialog)
        this.dialog.get_field("company").get_query = function() {
            return {
                filters: {
                    organization_type:"Staffing",
                    make_organization_inactive:0,
                    enable_payroll: 1
    
                    }
    
                }
    
        }
	}
}

function check_status(dialog){
    if(frappe.boot.tag.tag_user_info.company_type =="Staffing" && frappe.boot.tag.tag_user_info.comps.length>0){
        dialog.get_field('company').set_value('null')
    }
}