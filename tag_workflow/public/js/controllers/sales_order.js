frappe.provide("tag_workflow.controllers");


tag_workflow.controllers.SalesOrderController = Class.extend({
	init: function(args){
		$.extend(this, args);
	},

	refresh: function(){
		let me = this;
		if(me.frm.doc.docstatus == 1){
			me.frm.add_custom_button(__("Make Sales Invoice"), function() {
				frappe.model.open_mapped_doc({
					method: "tag_workflow.utils.whitelisted.make_sales_invoice",
					frm: me.frm
				});
			}, __("Create"));
			cur_frm.page.set_inner_btn_group_as_primary(__('Create'));
		}
	},
});
let controller = tag_workflow.controllers.SalesOrderController.extend();
cur_frm.script_manager.make(controller);
