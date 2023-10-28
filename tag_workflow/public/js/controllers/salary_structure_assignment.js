frappe.ui.form.off("Salary Structure Assignment", "employee");
frappe.ui.form.on('Salary Structure Assignment', {
    setup:function(frm){
        frm.set_value('company',"")
		frm.set_query("company", function() {
			return {
				"filters":[ ['Company', "organization_type", "in", ["Staffing" ]],['Company',"make_organization_inactive","=",0],['Company',"enable_payroll","=",1]]
			}
		});
		frm.set_query("employee",function(){
			return {
				filters:[ ['Employee', 'company', '=', frm.doc.company]]
			}
		})
	},
	refresh:function(frm){
		check_payroll_perm()
        frm.set_df_property('company','read_only',0);
        frm.set_df_property('company','hidden',0);
        frm.set_query("company", function() {
			return {
				"filters":[ ['Company', "organization_type", "in", ["Staffing" ]],['Company',"make_organization_inactive","=",0],['Company',"enable_payroll","=",1]]
			}
		});
		if (frm.doc.__islocal==1 && frappe.boot.tag.tag_user_info.company_type == "Staffing") {
            frm.set_value('company',(frappe.boot.tag.tag_user_info.comps.length==1) ? frappe.boot.tag.tag_user_info.company : '')
        }
		if (frm.doc.__islocal==1 && (frappe.boot.tag.tag_user_info.company_type == "TAG" || frappe.session.user=='Administrator')) {
			frm.set_value('company','')
			frm.refresh_fields();
		}
		check_status(frm)

    },
    company:function(frm){
        if(frm.doc.__islocal==1 && (frappe.boot.tag.tag_user_info.company_type == "TAG" || frappe.session.user=='Administrator')){
            console.log(1)
            frm.set_query("employee", function() {
                return {
                    filters: [
                        ['Employee', 'company', '=', frm.doc.company],
                    ]
                }
            });
        }
    }
})