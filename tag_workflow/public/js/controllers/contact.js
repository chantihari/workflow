frappe.require('/assets/tag_workflow/js/twilio_utils.js');
frappe.ui.form.on("Contact", {
	refresh: function(frm){
		lead_fields(frm);
		$('.form-footer').hide()
		$('[data-original-title="Menu"]').hide()
		$('[data-label="Invite%20as%20User"]').hide()
		$('[data-label="Links"]').hide()
		
		init_fields();
		make_field_mandatory();
		if(frm.doc.__islocal==1){
			cancel_cantact(frm);
		}

		set_map(frm);
		hide_fields(frm);
		show_addr(frm)
		$('[data-fieldname = "phone_number"]>div>div>div>input').attr("placeholder", "Example: +XX XXX-XXX-XXXX");
	},
	onload: function (frm) {
		if(frappe.boot.tag.tag_user_info.company_type=='Staffing'){
			cur_frm.fields_dict["company"].get_query = function () {
				return {
					query: "tag_workflow.tag_data.contact_company",
					filters: {
						company: frappe.defaults.get_user_default("Company"),
					},
				};
			};
		}
		if(frm.doc.__islocal==1){
			frm.set_df_property('lead','reqd',1);
		}
		frm.set_df_property('company','hidden',1);
		frm.set_df_property('mobile_no','hidden',1);
	},
	before_save:function(frm){
		if(!frm.doc.company){
			cur_frm.set_value('company',frappe.boot.tag.tag_user_info.company)
		}
		let name = frm.doc.first_name
		let company = frm.doc.company_name
		let email = frm.doc.email_address
		let is_valid = 1;
		if (name && name.length  > 120){
			frappe.msgprint({message: __('Name length exceeds'), indicator: 'red'})
			is_valid = 0;
		}
		if (company && company.length > 120){
			frappe.msgprint({message: __('Company length exceeds'), indicator: 'red'})
			is_valid = 0;
		}
		if (email && (email.length > 120 || !frappe.utils.validate_type(email, "email"))){
			frappe.msgprint({message: __('Not A Valid Email'), indicator: 'red'})
			is_valid = 0;
		}
		if (is_valid == 0){
			frappe.validated = false;
		}
		validate_phone_zip(frm);
	},
	validate: function(frm) {
		if (cur_frm.doc.is_primary == 1){
			frappe.call({
				"method": "tag_workflow.utils.whitelisted.validated_primarykey",
				"args": {"company": frm.doc.company},
				"async": 0,
				"callback": function(r){
					if (r.message.length > 0){
						frappe.msgprint({message: __('Is Primary already exist'), indicator: 'red'})
						frappe.validated = false;
					}
				}
			});
		}
	},
	search_on_maps: function(frm){
		if(cur_frm.doc.search_on_maps == 1){
			tag_workflow.UpdateField(frm, "map");
			hide_fields(frm)
			show_addr(frm)
			update_complete_address(frm)
		}else if(cur_frm.doc.search_on_maps ==0 && cur_frm.doc.enter_manually==0){
			cur_frm.set_df_property('map','hidden',1);
            show_addr(frm);
		}
	},

	enter_manually: function(frm){
		if(cur_frm.doc.enter_manually == 1){
			tag_workflow.UpdateField(frm, "manually");
			show_fields(frm);
			show_addr(frm);
		}else if(cur_frm.doc.search_on_maps ==0 && cur_frm.doc.enter_manually==0){
			hide_fields(frm);
            show_addr(frm);
		}
	},
	phone_number: function(frm){
		let phone = frm.doc.phone_number;
		if(phone){
			frm.set_value('phone_number', validate_phone(phone)?validate_phone(phone):phone);
		}
	},
	zip: function(frm){
		let zip = frm.doc.zip;
		frm.set_value('zip', zip?zip.toUpperCase():zip);
	}
});


/*---------hide field------------*/
function init_fields(){
	let contact_field = ["middle_name","last_name","email_id","user","sync_with_google_contacts","status","salutation","designation","gender","image", "sb_00","sb_01","contact_details","more_info","company_name"];

	for(let field in contact_field){
		cur_frm.toggle_display(contact_field[field], 0);
	}
}

/*--------mandatory field------------*/
function make_field_mandatory(){
	let reqd = ["company", "phone_number", "email_address"];
	for(let r in reqd){
		cur_frm.toggle_reqd(reqd[r], 1);
	}
}

function cancel_cantact(frm){
	frm.add_custom_button(__('Cancel'), function(){
		frappe.set_route("Form", "Contact");
	});
}

function lead_fields(frm){
	if(frm.doc.__islocal!=1){
		frm.set_df_property('lead','read_only',1);
	}
}

function hide_fields(frm){
	frm.set_df_property('city','hidden',frm.doc.city && frm.doc.enter_manually ==1?0:1);
	frm.set_df_property('state','hidden',frm.doc.state && frm.doc.enter_manually ==1?0:1);
	frm.set_df_property('zip','hidden',frm.doc.zip && frm.doc.enter_manually ==1?0:1);
}
function show_fields(frm){
	frm.set_df_property('city','hidden',0);
	frm.set_df_property('state','hidden',0);
	frm.set_df_property('zip','hidden',0);

}

function show_addr(frm){
    if(frm.doc.search_on_maps){
        frm.get_docfield('contact_address').label ='Complete Address';
	}else if(frm.doc.enter_manually){
		frm.get_docfield('contact_address').label ='Contact Address';
	}

    frm.refresh_field('contact_address');
}

const html=`<!doctype html>
  <html>
    <head>
      <meta charset="utf-8">
    </head>
    <body>
      <input class="form-control" placeholder="Search a location" id="autocomplete-address" style="height: 30px;margin-bottom: 15px;">
      <div class="tab-content" title="map" style="text-align: center;padding: 4px;">
        <div id="map" style="height:450px;border-radius: var(--border-radius-md);"></div>
      </div>
    </body>
  </html>
`;
function set_map (frm) {
  	setTimeout(()=>{
		$(frm.fields_dict.map.wrapper).html(html);
		initMap();
	}, 500);

}

function validate_phone_zip(frm){
	let zip = frm.doc.zip;
	let phone = frm.doc.phone_number;
	if (zip){
		frm.set_value('zip', zip.toUpperCase());
		if(!validate_zip(zip)){
			frappe.msgprint({message: __('Invalid Zip!'), indicator: 'red'})
			frappe.validated = false;
		}
	}
	if (phone){
		if(!validate_phone(phone)){
			frappe.msgprint({message: __('Invalid Phone Number!'), indicator: 'red'})
			frappe.validated = false;
		}
		else{
			frm.set_value('phone_number', validate_phone(phone));
		}
	}
}

/*--------------------Update Complete Address---------------------*/
function update_complete_address(frm){
	if(frm.doc.zip && frm.doc.state && frm.doc.city){
	    let data = {
	        street_number: frm.doc.contact_address ? frm.doc.contact_address:'',
	        route: frm.doc.suite_or_apartment_no ? frm.doc.suite_or_apartment_no    :'',
	        locality:frm.doc.city,
	        administrative_area_level_1: frm.doc.state,
	        postal_code: frm.doc.zip ? frm.doc.zip:0,
	    };
		update_comp_address(frm,data)
	}
	else{
	    frm.set_value('complete_address','')
    }
}

function update_comp_address(frm,data){
	frappe.call({
	    method:'tag_workflow.tag_data.update_complete_address',
	    args:{
	        data:data
	    },
	    callback:function(r){
			if(r.message!=frm.doc.complete_address){
				frm.set_value('complete_address',r.message)
			}
	    }
	})
}