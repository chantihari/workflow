frappe.listview_settings["Payroll Period"] = {
    refresh:()=>{
        check_payroll_perm()
    }
}