function check_perm(){
    if (frappe.boot.tag.tag_user_info.company_type =="Staffing" && frappe.flags.ats_status.ats ==0){
        frappe.msgprint("You don't have enough permissions.");
        frappe.set_route("app");
    }
}

function check_payroll_perm(){
    if (frappe.boot.tag.tag_user_info.company_type =="Staffing" && frappe.flags.ats_status.payroll ==0){
        frappe.msgprint("You don't have enough permissions.");
        frappe.set_route("app");
    }
}
function check_status(frm){
    if(frm.is_new() && frappe.boot.tag.tag_user_info.company_type =="Staffing" && frappe.boot.tag.tag_user_info.comps.length>0){
        frm.set_value('company','')
        frm.refresh_field('company')
    }
}
