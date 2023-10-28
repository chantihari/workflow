frappe.listview_settings['Designation'] = { 
    filters : [["organization","=",'']],
    onload:function(){
        frappe.route_options = {
            "organization": ''
        }; 
    }
};
