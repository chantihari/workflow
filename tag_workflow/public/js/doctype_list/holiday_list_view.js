frappe.listview_settings["Holiday List"] = {
    hide_name_column: true,
    onload: function(frm){
        $('div[data-original-title = "ID"]').addClass('hide');
        $('[data-fieldname="holiday_list_name"]').attr("placeholder", "Name");
        cur_list.columns[0].df.label = "Name";
        cur_list.render_header(cur_list.columns);
    }
}
