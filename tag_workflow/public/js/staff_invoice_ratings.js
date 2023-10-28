/*---------Sales Invoice Page Rating----------*/
let is_no_show_again = false

function check_staffing_reviews_invoice_page(frm){
	if((frappe.user_roles.includes('Hiring Admin') || frappe.user_roles.includes('Hiring User')) && frappe.session.user!='Administrator' && frappe.boot.tag.tag_user_info.company_type!='TAG'){
		frappe.db.get_value("Sales Invoice",{"job_order":frm.doc.job_order,"rating_no_show":1,"company":frm.doc.company},['name'],(r) =>{
	if(!r.name){
		
		frappe.db.get_value("Company Review", {"name": frm.doc.company+"-"+frm.doc.job_order},['rating'], function(a){
			if(!a.rating){
				let pop_up = new frappe.ui.Dialog({
					title: __('Staffing Company Review'),
					'fields': [
						{'fieldname': 'Rating', 'fieldtype': 'Rating','label':'Rating','reqd':1},
						{'fieldname': 'Comment', 'fieldtype': 'Data','label':'Review'}
					],
					primary_action: function(){
						pop_up.hide();
						rating_submit_action(frm,pop_up);
						
					}
				});
				pop_up.show();
				pop_up.$wrapper.find('.standard-actions>.btn-modal-primary').addClass('disabled')
				pop_up.$wrapper.find('.standard-actions>.btn-modal-primary').css({"pointer-events": "none"})
				let html_field = pop_up.$wrapper.find('.custom-actions')
				rating_field_submit_button_prop(pop_up);

				html_field.append('<span class="input-area" style="display: inline;"><input type="checkbox" autocomplete="off" class="input-with-feedback" data-fieldtype="Check" data-fieldname="is_no_show_again" placeholder="ffdfe"></span><span style="color:grey; font-size:10px; display: inline; margin-top:3px">&nbsp Do not show this again</span>');
				html_field.on('click',()=>{
					is_no_show_again = $('[data-fieldname="is_no_show_again"]').is(":checked")
					let field = pop_up.get_field("Rating");
					no_show_field_submit_button_prop(pop_up,field);
				})
			}
		});
	}
})
	}

}

function no_show_field_submit_button_prop(pop_up,field) {
	if(is_no_show_again||$('.rating>svg>path').hasClass('star-click')) {
		pop_up.$wrapper.find('.standard-actions>.btn-modal-primary').removeClass('disabled');
		pop_up.$wrapper.find('.standard-actions>.btn-modal-primary').css({"pointer-events": "auto"});
		field.df.reqd=false;
		field.refresh();
	} else {
		pop_up.$wrapper.find('.standard-actions>.btn-modal-primary').addClass('disabled');
		pop_up.$wrapper.find('.standard-actions>.btn-modal-primary').css({"pointer-events": "none"});
		field.df.reqd=true;
		field.refresh();
	}
}

function rating_field_submit_button_prop(pop_up) {
	setTimeout(() => {
		$('.rating>svg').on('click',function() {
			if($('.rating>svg>path').hasClass('star-click')) {
				pop_up.$wrapper.find('.standard-actions>.btn-modal-primary').removeClass('disabled');
				pop_up.$wrapper.find('.standard-actions>.btn-modal-primary').css({"pointer-events": "auto"});
			} else {
				pop_up.$wrapper.find('.standard-actions>.btn-modal-primary').addClass('disabled');
				pop_up.$wrapper.find('.standard-actions>.btn-modal-primary').css({"pointer-events": "none"});
			}
		});
	},1000);
}

function rating_submit_action(frm,pop_up) {
	if(is_no_show_again) {
		frappe.call({
			method: "tag_workflow.utils.timesheet.rating_no_show",
			args: {
				'rating_no_show': is_no_show_again,
				'invoice_name': frm.doc.name
			},
			"async": 0,
		});
	}
	else {
		let comp_rating=pop_up.get_values();
		frappe.call({
			method: "tag_workflow.utils.timesheet.company_rating",
			args: {
				'hiring_company': frm.doc.customer,
				'staffing_company': frm.doc.company,
				'ratings': comp_rating,
				'job_order': frm.doc.job_order
			},
			"async": 0,
			callback: function(rm) {
				frappe.msgprint('Review Submitted Successfully');
			}
		});
	}
}