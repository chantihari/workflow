frappe.ui.form.on('Chat Message', {
	refresh: function(frm){
        frm.set_df_property("room", "hidden", 1);
        frm.disable_save();
	}
});