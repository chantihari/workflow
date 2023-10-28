frappe.ui.form.on('Payroll Period',{
    refresh:(frm)=>{
        check_payroll_perm()
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
