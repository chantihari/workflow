const u_type = frappe.boot.tag.tag_user_info.user_type ? frappe.boot.tag.tag_user_info.user_type.toLowerCase():null
const comp =frappe.boot.tag.tag_user_info.company_type;
const u_roles = ['staffing admin','tag admin']
function hide_and_show_tables(frm){
	setTimeout(()=>{
	if((u_type=='tag admin' && frm.get_docfield('hiring_company').label !='Staffing Company') || (u_type=='staffing admin' && frm.get_docfield('hiring_company').label !='Staffing Company')){
		
			frm.set_df_property('job_order_detail','options',update_inner_html('Job Titles'));
			frm.set_df_property('_industry_types','hidden',1)
			frm.set_df_property('job_titles','hidden',0)
		}	
		else{
			frm.set_df_property('job_order_detail','options',update_inner_html('Job Industry(ies)'))
			frm.set_df_property('_industry_types','hidden',0)
			frm.set_df_property('job_titles','hidden',1)
		}
	},3000) 
}

function filter_row(frm){
	frm.fields_dict['job_titles'].grid.get_field('job_titles').get_query = function(doc,cdt,cdn) {
		const row = locals[cdt][cdn];
		let jobtitle = frm.doc.job_titles, title_list = [];
			for (let t in jobtitle){
				if(jobtitle[t]['job_titles']){
					title_list.push(jobtitle[t]['job_titles']);
				}
			}	
		if (row.industry_type){
			return {
				query: "tag_workflow.tag_data.get_jobtitle_based_on_industry",
				filters: {
					industry:row.industry_type,
					company:frm.doc.staffing_company,
					title_list:title_list
				},
			};
		}else{
			return{
				query: "tag_workflow.tag_data.get_jobtitle_based_on_company",
				filters: {
					company:frm.doc.staffing_company,
					title_list:title_list
				},
			}
		}
		
	}
}
function update_table(frm){
	if(frm.get_docfield('hiring_company').label !='Staffing Company' && frm.doc.job_titles && frm.doc.job_titles.length>0){
		frappe.run_serially([
			()=>frm.clear_table('_industry_types'),
			()=>{
				const industries = frm.doc.job_titles.map(title=>title.industry_type).
				filter((value, index, self) => self.indexOf(value) === index)
				if (industries.length>0){
				industries.map(i=>{
					let row = frm.add_child('_industry_types');
					row.industry_type = i;
				})
			}
				frm.refresh_field('_industry_types')
			},
		])
	}
}

function update_inner_html(phrase){
	const inner_html= `\n\t\t\t${phrase}\n\t\t\t<span class="ml-2 collapse-indicator mb-1 tip-top" style="display: inline;"><svg class="icon  icon-sm" style="">\n\t\t\t<use class="mb-1" id="up-down" href="#icon-down"></use>\n\t\t</svg></span>\n\t\t`;
	$(".frappe-control[data-fieldname='job_titles']").parent().parent().parent('.section-body').siblings('.section-head').html(inner_html)
	return 1
}	

if (frappe.boot.tag.tag_user_info.company_type=='Hiring' || frappe.boot.tag.tag_user_info.company_type =='Exclusive Hiring' || u_roles.includes(u_type)){
jQuery(document).on("click",`.tip-top,.${$(".frappe-control[data-fieldname='job_titles']").parent().parent().parent('.section-body').siblings('.section-head').attr('class')}`,function(){
	const cls = $(".frappe-control[data-fieldname='job_titles']").parent().parent().parent('.section-body').siblings('.section-head').hasClass('collapsed')
	cls ? $('#up-down').attr('href',"#icon-down") : $('#up-down').attr('href',"#icon-up-line")
	});
}