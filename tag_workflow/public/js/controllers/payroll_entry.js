frappe.ui.form.on('Payroll Entry',{
    refresh:(frm)=>{
        check_payroll_perm()
        check_status(frm)
        frm.set_value("company",(frappe.boot.tag.tag_user_info.comps.length==1) ? frappe.boot.tag.tag_user_info.company :"")
    },
    setup:function(frm){
		frm.set_query("company", function() {
			return {
				"filters":[ 
                    ['Company', "organization_type", "in", ["Staffing" ]],
                    ['Company',"make_organization_inactive","=",0],
                    ['Company',"enable_payroll","=",1]                
                ]
			}
		});

	},
})