frappe.ui.form.on('Salary Component',{
    setup:function(frm){
		frm.set_query("company", function() {
			return {
				"filters":[ ['Company', "organization_type", "in", ["Staffing" ]],['Company',"make_organization_inactive","=",0],['Company',"enable_payroll","=",1]]
			}
		});
	},
	refresh:function(frm){
		check_payroll_perm()
		if (frm.doc.__islocal==1 && frappe.boot.tag.tag_user_info.company_type == "Staffing") {
			frappe.call({
				'method': "tag_workflow.tag_data.lead_org",
				'args': { 'current_user': frappe.session.user },
				'callback': function (r) {
					if (r.message == 'success') {
						if(frappe.boot.tag.tag_user_info.comps.length>0)
							frm.set_value('company','')
						else
							frm.set_value('company', frappe.boot.tag.tag_user_info.company)
						frm.refresh_fields();
					}
					else {
						frm.set_value('company','')
						frm.refresh_fields();
					}
				}
			});
		}
		if (frm.doc.__islocal==1 && frappe.boot.tag.tag_user_info.company_type == "TAG") {
			frm.set_value('company','')
			frm.refresh_fields();
		}
		if(frm.doc.__islocal!=1){
			cur_frm.set_df_property('company','read_only',1)
		}
		cur_frm.set_df_property('salary_component','unique',0)

		if(frm.doc.salary_component_abbr){
			let abbr = frm.doc.salary_component_abbr.split("_");
			frm.set_value('salary_component_abbr',abbr[0]);
		}
        $(".btn-translation").hide();
		$("#navbar-breadcrumbs > li.disabled > a").html(frm.doc.salary_component_name) 
		$('h3[title = "'+frm.doc.name+'"]').html(frm.doc.salary_component_name) 
	},
	salary_component_name: function(frm){
        frm.doc.salary_component = frm.doc.salary_component_name + "_"+ frappe.boot.tag.tag_user_info.company
		let name = frm.doc.salary_component_name.split(" ");
		let abbr = ""
		name.forEach(element => {
			if(element != ""){
				abbr += element[0];
			}

		});
		if(abbr === "undefined"){
			abbr = "";
		}
		frm.set_value('salary_component_abbr',abbr.toUpperCase());
	},
	before_save: function(frm){
		if(frm.doc.salary_component_abbr){
		frm.doc.salary_component_abbr +=   "_"+  frappe.boot.tag.tag_user_info.company

		}
	}



});

