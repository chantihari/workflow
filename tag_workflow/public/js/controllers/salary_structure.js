frappe.ui.form.on('Salary Structure', {
	refresh: function(frm){
		let name = frm.doc.name.split("_")
		$("#navbar-breadcrumbs > li.disabled > a").html(name[0]) 
		$('h3[title = "'+frm.doc.name+'"]').html(name[0]) 
		check_payroll_perm()
		setTimeout(()=>{
			check_status(frm)
			frm.set_value("company",(frappe.boot.tag.tag_user_info.comps.length==1) ? frappe.boot.tag.tag_user_info.company :"")
			},800)
			setTimeout(()=>{
				cur_frm.fields_dict["earnings"].grid.get_field("salary_component").get_query = function (doc) {
					return {
						filters: {
							company: doc.company,
						},
					};
				};
				cur_frm.fields_dict["deductions"].grid.get_field("salary_component").get_query = function (doc) {
					return {
						filters: {
							company: doc.company,
						},
					};
				};
	
				},2000)
			
	},
	setup:function(frm){
		frm.set_query("company", function() {
			return {
				"filters":[ ['Company', "organization_type", "in", ["Staffing" ]],['Company',"make_organization_inactive","=",0],['Company',"enable_payroll","=",1]]
			}
		});
		setTimeout(()=>{
			cur_frm.fields_dict["earnings"].grid.get_field("salary_component").get_query = function (doc) {
				return {
					filters: {
						company: doc.company,
					},
				};
			};
			cur_frm.fields_dict["deductions"].grid.get_field("salary_component").get_query = function (doc) {
				return {
					filters: {
						company: doc.company,
					},
				};
			};

			},2000)
	},
});