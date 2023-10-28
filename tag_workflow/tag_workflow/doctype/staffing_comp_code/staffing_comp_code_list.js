frappe.listview_settings["Staffing Comp Code"] = {
    hide_name_column: true,
    refresh: function () {
        $('[data-fieldname="name"]').hide();
    },
    onload:function(){
        $('[data-fieldname="name"]').hide();
    }
}