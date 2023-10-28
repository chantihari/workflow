frappe.listview_settings["Lead"] = {
    onload:function(listview){
        if(frappe.session.user!='Administrator'){
            $('.custom-actions.hidden-xs.hidden-md').hide();
            $('[data-original-title="Refresh"]').hide();
            $('.menu-btn-group').hide();
        }
        $('div[data-original-title = "ID"]').addClass('hide');
        $('[title = "Lead"]').html('Leads');
        [listview.columns[2],listview.columns[3],listview.columns[4],listview.columns[5]]=[listview.columns[3],listview.columns[4], listview.columns[5],listview.columns[2]]
        listview.render_header(listview.columns)
    },
    hide_name_column: true,
    refresh: ()=>{
        $('#navbar-breadcrumbs > li:nth-child(2) > a:nth-child(1)').html('Leads');
    },
}