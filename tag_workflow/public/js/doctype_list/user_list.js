frappe.listview_settings['User'] = {
	onload: function(listview){		
		$('h3[title="User"]').html('Company Users');
		cur_list.columns[4].df.label = 'Role'
		cur_list.render_header(cur_list.columns[4])
		$('[data-original-title="Role Profile"]').attr('data-original-title',"Role")
		$('[data-fieldname="role_profile_name"]').attr('placeholder',"Role")
		if(frappe.session.user!='Administrator'){
			$('.custom-actions.hidden-xs.hidden-md').hide();
			$('[data-original-title="Refresh"]').hide();
			$('.menu-btn-group').hide();
		}

		const df = {
            condition: "=",
            default: null,
            fieldname: "organization_type",
            fieldtype: "Select",
            input_class: "input-xs",
            is_filter: 1,
            onchange: function() {
                cur_list.refresh();
            },
			options: ["","Exclusive Hiring", "Hiring", "Staffing", "TAG"],
            placeholder: "Company Type"
        };		

		const df1 = {
            condition: "=",
            default: null,
            fieldname: "role_profile_name",
            fieldtype: "Select",
            input_class: "input-xs",
            is_filter: 1,
            onchange: function() {
                cur_list.refresh();
            },
			options: get_role_profile1(),
            placeholder: "Role"
        };
		
		const df2 = {
            condition: "=",
            default: null,
            fieldname: "company",
            fieldtype: "Select",
            input_class: "input-xs",
            is_filter: 1,
            onchange: function() {
                cur_list.refresh();
            },
			options: get_organization_type(),
            placeholder: "Company"
        };

		let standard_filters_wrapper = listview.page.page_form.find('.standard-filter-section');
        listview.page.add_field(df, standard_filters_wrapper);
		listview.page.add_field(df1, standard_filters_wrapper);
        listview.page.add_field(df2, standard_filters_wrapper);

    },
	hide_name_column: true,
	refresh: function(listview){

	$('#navbar-breadcrumbs > li > a').html('Company Users');
	listview.$page.find(`div[data-fieldname="name"]`).addClass("hide");
	$('.primary-action').attr('id','user-add-new');
	$('.filter-button').find('.button-label').attr('id','user-filtericon')
	}
	
};

frappe.ui.form.ControlPassword = class ControlData extends frappe.ui.form.ControlData{
	static input_type= "password";
	make() {
		super.make();
	}
	make_input() {
		super.make_input();
		if (this.$input[0].dataset.fieldname === "new_password"){
			this.$wrapper.find(":input[type='password'][data-fieldname='new_password']").addClass("hidepassword");
			this.$input.parent().append($('<span class="input-area" > <input type="checkbox"  id="showPassword"  data-fieldtype=Check autocomplete="off" class="input-with-feedback-showPassword" ></span>'));
		}else{
			this.$wrapper.find(":input[type='password'][data-fieldname='old_password']").addClass("datapassword");
			this.$input.parent().append($('<span class="input-area" > <input type="checkbox"  id="oldPassword"  data-fieldtype=Check autocomplete="off" class="input-with-feedback-showPassword" ></span>'));
		}
		this.$input.parent().append($('<span class="label-area">Show Password</span>'));
		

		$("#oldPassword").unbind('click').bind('click', function() {
			if($(".datapassword").attr("type") == "password"){
				$(".datapassword").attr("type", "text")
			}else{
				$(".datapassword").attr("type", "password")
			}
		});
		
		$("#showPassword").click( function() {
			if ($(".hidepassword").attr("type") == "password") {
				$(".hidepassword").attr("type", "text");
			} else {
				$(".hidepassword").attr("type", "password");
			}
		});
	}
};

function get_organization_type(){
	let text='\n'

	frappe.call({
		"method": "tag_workflow.utils.whitelisted.get_organization_type",
		args: {
			"user_type":frappe.boot.tag.tag_user_info.company_type
		},
		"async": 0,
		"callback": function(r){
			if(r.message){
				text += r.message
			}
		}
	});
	return text

}

function get_role_profile1(){
	let text='\n'

	frappe.call({
		"method": "tag_workflow.utils.whitelisted.get_role_profile",
		"async": 0,
		"callback": function(r1){
			if(r1.message){
				text += r1.message
			}
		}
	});
	return text

}

frappe.ui.FilterGroup.prototype.get_filter_area_template= function() {
	/* eslint-disable indent */
	return $(`
		<div class="filter-area">
			<div class="filter-edit-area">
				<div class="text-muted empty-filters text-center">
					${__('No filters selected')}
				</div>
			</div>
			<hr class="divider"></hr>
			<div class="filter-action-buttons">
				<button class="text-muted add-filter btn btn-xs">
					+ ${__('Add a Filter')}
				</button>
				<div>
					<button class="btn btn-secondary btn-xs clear-filters" id="user-clear-filtericon">
						${__('Clear Filters')}
					</button>
					${this.filter_button ?
						`<button class="btn btn-primary btn-xs apply-filters">
							${__('Apply Filters')}
						</button>`
						: ''
					}
				</div>
			</div>
		</div>`
	);
	/* eslint-disable indent */
}
