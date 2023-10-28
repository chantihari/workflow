frappe.listview_settings["Staffing Email"] = {
    onload:function(){
        if(frappe.session.user != 'Administrator'){
            $('[data-original-title="Refresh"]').hide()
            $('.menu-btn-group').hide()
        }
        $('[data-original-title="ID"]').hide();
        $('[data-original-title = "Name"]').hide();
        $('.list-subject').css("flex", "1");
        $('.list-row .level-right ').css("flex", "0.3"); 
        $('.list-row-head .level-right').css("flex", "0.3");
    },
    refresh: function(){
        if(frappe.session.user != 'Administrator'){
            $('div.custom-actions.hidden-xs.hidden-md > div > button').hide();
        }
        $('[title = "Staffing Email"]').html('Emails');
        $('#navbar-breadcrumbs > li:nth-child(2) > a:nth-child(1)').html('Emails');
        $('[data-label="Add%20Staffing%20Email"]').text('Draft Email');
        $('.list-subject').css("flex", "1");
        $('.list-row .level-right ').css("flex", "0.3");
        $('.list-row-head .level-right').css("flex", "0.3");
    },
    hide_name_column: true
} 