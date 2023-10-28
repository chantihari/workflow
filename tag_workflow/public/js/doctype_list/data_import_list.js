frappe.listview_settings["Data Import"] = {
    refresh:()=>{
        $('[data-original-title="ID"]>input').attr('placeholder', 'Name');
        cur_list.columns[0].df.label = "Name";
        cur_list.render_header(cur_list.columns);
    }
}