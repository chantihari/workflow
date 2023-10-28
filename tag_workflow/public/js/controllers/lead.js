frappe.require('/assets/tag_workflow/js/twilio_utils.js');
frappe.ui.form.on("Lead", {
  refresh: function (frm) {
    $('.form-footer').show();
    $('[class="btn btn-primary btn-sm primary-action"]').show();
    $('.custom-actions.hidden-xs.hidden-md').show();
    setTimeout(()=>{
      $('[data-label="Create"]').addClass("hide");
      $('[data-label="Action"]').addClass("hide");
    }, 3000);
    view_contract(frm);
    $('[data-original-title="Menu"]').hide()
    cur_frm.clear_custom_buttons();

    if(!frm.is_new()){
      frm.add_custom_button(__("Send Email"), function () {
        email_box(frm);
      });

    }
    reqd_fields(frm);
    hide_details();
    make_contract(frm);

    if(frm.doc.__islocal==1){
			cancel_lead(frm);
		}

    set_map(frm);
    hide_fields(frm);
    show_addr(frm);
    $('[data-fieldname = "phone_no"]>div>div>div>input').attr("placeholder", "Example: +XX XXX-XXX-XXXX");
    frm.set_query("contact_by", function (doc) {
      return {
        query: "tag_workflow.utils.lead.contact_person",
        filters: {
          owner_company: doc.owner_company,
        },
      };
    });
  },
  sign:function(frm){
    if(frm.doc.sign){
			let regex = /[^0-9A-Za-z ]/g;
			if (regex.test(frm.doc.sign) === true){
				frappe.msgprint(__("Signature: Only alphabets and numbers are allowed."));
				frm.set_value('sign','')
				frappe.validated = false;
			}
		}
  },
  status:function(frm){
    if(frm.doc.__islocal!=1){
      frappe.db.get_value('Lead',{name:frm.doc.name},['status'],function(r){
        if(r.status=='Close' && frm.doc.status=='On Hold'){
          frappe.msgprint({
            message: __("You can not change the status from 'Close' to 'On-Hold' "),
            title: __("Error"),
            indicator: "red",
          });
          frappe.validated='False'
          frm.set_value('status',r.status)
        }
      })
    }
  },
  validate: function (frm) {
    let phone = frm.doc.phone_no;
    let email = frm.doc.email_id;
    let zip = frm.doc.zip;
    if(phone){
      if(!validate_phone(phone)){
        frappe.msgprint({message: __("Invalid Phone Number!"),indicator: "red"});
        frappe.validated = false;
      }
      else{
        frm.set_value('phone_no', validate_phone(phone));
      }
    }
    if (email &&(email.length > 120 || !frappe.utils.validate_type(email, "email"))) {
      frappe.msgprint({ message: __("Not A Valid Email"), indicator: "red" });
      frappe.validated = false;
    }
    if (zip){
      frm.set_value('zip', zip.toUpperCase());
      if(!validate_zip(zip)){
        frappe.msgprint({ message: __("Invalid Zip!"), indicator: "red" });
        frappe.validated = false;
      }
    }
  },
  setup: function (frm) {
    if(frappe.session.user!='Administrator' && frm.doc.__islocal==1){
      setting_owner_company(frm);
    }
  },
  organization_type: function (frm) {
    if (frm.doc.organization_type == "Exclusive Hiring") {
      tag_staff_company(frm);
    } else{
      frm.set_query("owner_company", function () {
        return {
          filters: [["Company", "organization_type", "in", ["TAG"]]],
        };
      });
    }
  },

  lead_owner: function (frm) {
    frm.set_query("lead_owner", function (doc) {
      return {
        query: "tag_workflow.utils.lead.lead_owner",
        filters: {
          owner_company: doc.owner_company,
        },
      };
    });
  },
  before_save: function(frm){
    if(frm.doc.contact_first_name && frm.doc.contact_last_name){
      cur_frm.set_value('lead_name',(frm.doc.contact_first_name).trim()+' '+(frm.doc.contact_last_name).trim())
    }
   if (frappe.boot.tag.tag_user_info.company_type=='Staffing') {
    frm.set_value("organization_type", "Exclusive Hiring");}
  },
  after_save: function(frm){
    if(frm.doc.user_notes){
      frappe.call({
        "method": "frappe.desk.form.utils.add_comment",
        'async':0,
        "args": {
          reference_doctype: frm.doctype,
          reference_name: frm.docname,
          content: frm.doc.user_notes,
          comment_email: frappe.session.user,
          comment_by: frappe.session.user_fullname,
          comment_type:'Comment'
        },
        "callback": ()=>{
          frappe.db.set_value('Lead', frm.doc.name, 'user_notes', '');
        }
      });
    }
  },
  dob:function(frm){
    check_bd(frm);
  },
  search_on_maps: function(frm){
    if(cur_frm.doc.search_on_maps == 1){
      tag_workflow.UpdateField(frm, "map");
      hide_fields(frm);
      show_addr(frm);
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
      show_addr(frm)
    }else if(cur_frm.doc.search_on_maps ==0 && cur_frm.doc.enter_manually==0){
      cur_frm.set_df_property('map','hidden',1);
      hide_fields(frm);
      show_addr(frm);
    }
  },
  phone_no: function(frm){
    let phone = frm.doc.phone_no;
		if(phone){
			frm.set_value('phone_no', validate_phone(phone)?validate_phone(phone):phone);
		}
  },
  zip: function(frm){
		let zip = frm.doc.zip;
		frm.set_value('zip', zip?zip.toUpperCase():zip);
	},
  lead_name:function(frm){
    if(frm.doc.lead_name){
			let lead_name = (cur_frm.doc.lead_name).trim();
			cur_frm.set_value("lead_name",lead_name);
		}
  }
});

/*-------reqd------*/
function reqd_fields(frm) {
  let reqd = ["company_name", "email_id"];
  for (let r in reqd) {
    cur_frm.toggle_reqd(reqd[r], 1);
  }

  let roles = frappe.user_roles;
  if (roles.includes("Tag Admin") || roles.includes("Tag User")) {
    cur_frm.toggle_reqd("organization_type", 1);
    frm.set_query("organization_type", function () {
      return {
        filters: [["Organization Type", "name", "!=", "Tag"]],
      };
    });
  } else {
    cur_frm.toggle_display("organization_type", 0);
  }
}


/*--------makecontract--------*/
let _contract = `<p><b>Staffing/Vendor Contract</b></p>
<p>This Staffing/Vendor Contract (“Contract”) is entered into by and between Staffing Company and Hiring Company as further described and as set forth below. By agreeing to the Temporary Assistance Guru, Inc. (“TAG”) End-User License Agreement, and using the TAG application service and website (the “Service”) Staffing Company and Hiring Company agree that they have a contractual relationship with each other and that the following terms apply to such relationship:</p>

<p>(1) The billing rate Hiring Company shall pay Staffing Company to hire each temporary worker provided by Staffing Company (the “Worker”) is the rate set forth by the TAG Service for the location and position sought to be filled, and this rate includes all wages, worker’s compensation premiums, unemployment insurance, payroll taxes, and all other employer burdens recruiting, administration, payroll funding, and liability insurance.</p>
<p>(2) Hiring Company agrees not to directly hire and employ the Worker until the Worker has completed at least 720 work hours. Hiring Company agrees to pay Staffing Company an administrative placement fee of $3,000.00 if Hiring Company directly employs the Worker prior to completion of 720 work hours.</p>
<p>(3) Hiring Company acknowledges that it has complete care, custody, and control of workplaces and job sites. Hiring Company agrees to comply with all applicable laws, regulations, and ordinances relating to health and safety, and agrees to provide any site/task specific training and/or safety devices and protective equipment necessary or required by law. Hiring Company will not, without prior written consent of Staffing Company, entrust Staffing Company employees with the handling of cash, checks, credit cards, jewelry, equipment, tools, or other valuables.</p>
<p>(4) Hiring Company agrees that it will maintain a written safety program, a hazard communication program, and an accident investigation program. Hiring Company agrees that it will make first aid kits available to Workers, that proper lifting techniques are to be used, that fall protection is to be used, and that Hiring Company completes regular inspections on electrical cords and equipment. Hiring Company represents, warrants, and covenants that it handles and stores hazardous materials properly and in compliance with all applicable laws.</p>
<p>(5) Hiring Company agrees to post Occupational Safety and Health Act (“OSHA”) of 1970 information and other safety information, as required by law. Hiring Company agrees to log all accidents in its OSHA 300 logs. Hiring Company agrees to indemnify and hold harmless Staffing Company for all claims, damages, or penalties arising out of violations of the OSHA or any state law with respect to workplaces or equipment owned, leased, or supervised by Hiring Company and to which employees are assigned.</p>
<p>(6) Hiring Company will not, without prior written consent of Staffing Company, utilize Workers to operate machinery, equipment, or vehicles. Hiring Company agrees to indemnify and save Staffing Company and Workers harmless from any and all claims and expenses (including litigation) for bodily injury or property damage or other loss as asserted by Hiring Company, its employees, agents, the owner of any such vehicles and/or equipment or contents thereof, or by members of the general public, or any other third party, arising out of the operation or use of said vehicles and/or equipment by Workers.</p>
<p>(7) Commencement of work by dispatched Workers, or Hiring Company’s signature on work ticket serves as confirmation of Hiring Company’s agreement to conditions of service listed in or referred to by this Contract.</p>
<p>(8) Hiring Company agrees not to place Workers in a supervisory position except for a Worker designated as a “lead,” and, in that position, Hiring Company agrees to supervise all Workers at all times.</p>
<p>(9) Billable time begins at the time Workers report to the workplace as designated by the Hiring Company.</p>
<p>(10) Jobs must be canceled a minimum of 24 hours prior to start time to avoid a minimum of four hours billing per Worker.</p>
<p>(11) Staffing Company guarantees that its Workers will satisfy Hiring Company, or the first two hours are free of charge. If Hiring Company is not satisfied with the Workers, Hiring Company is to call the designated phone number for the Staffing Company within the first two hours, and Staffing Company will replace them free of charge.</p>
<p>(12) Staffing Company agrees that it will comply with Hiring Company’s safety program rules.</p>
<p>(13) Overtime will be billed at one and one-half times the regular billing rate for all time worked over forty hours in a pay period and/or eight hours in a day as provided by state law.</p>
<p>(14) Invoices are due 30 days from receipt, unless other arrangements have been made and agreed to by each of the parties.</p>
<p>(15) Interest Rate: Any outstanding balance due to Staffing Company is subject to an interest rate of two percent (2%) per month, commencing on the 90th day after the date the balance was due, until the balance is paid in full by Hiring Company.</p>
<p>(16) Severability. If any provision of this Contract is held to be invalid and unenforceable, then the remainder of this Contract shall nevertheless remain in full force and effect.</p>
<p>(17) Attorney’s Fees. Hiring Company agrees to pay reasonable attorney’s fees and/or collection fees for any unpaid account balances or in any action incurred to enforce this Contract.</p>
<p>(18) Governing Law. This Contract is governed by the laws of the state of Florida, regardless of its conflicts of laws rules.</p>
<p>(19) If Hiring Company utilizes a Staffing Company employee to work on a prevailing wage job, Hiring Company agrees to notify Staffing Company with the correct prevailing wage rate and correct job classification for duties Staffing Company employees will be performing. Failure to provide this information or providing incorrect information may result in the improper reporting of wages, resulting in fines or penalties being imposed upon Staffing Company. The Hiring Company agrees to reimburse Staffing Company for any and all fines, penalties, wages, lost revenue, administrative and/or supplemental charges incurred by Staffing Company.</p>
<p>(20) WORKERS' COMPENSATION COSTS: Staffing Company represents and warrants that it has a strong safety program, and it is Staffing Company’s highest priority to bring its Workers home safely every day. AFFORDABLE CARE ACT (ACA): Staffing Company represents and warrants that it is in compliance with all aspects of the ACA.</p>
<p>(21) Representatives. The Hiring Company and the Staffing Company each certifies that its authorized representative has read all of the terms and conditions of this Contract and understands and agrees to the same.</p>
<p>(22) Extra Contract Language.</p>`;

function make_contract(frm) {
  if (
    cur_frm.is_dirty() != 1 &&
    frm.doc.status == "Contract Negotiation" &&
    !["Hiring", "Exclusive Hiring"].includes(frappe.boot.tag.tag_user_info.company_type)
  ) {
    frm
      .add_custom_button("Prepare Contract", function () {
        run_contract(frm);
      })
      .addClass("btn-primary");
  }
}

function run_contract(frm) {
  frappe.db.get_value('Contract',{'staffing_company':cur_frm.doc.company,'hiring_company':cur_frm.doc.company_name,'lead':frm.doc.name},['name'],function(r){
    if(r.name){
      window.location.href='/app/contract/'+r.name
    }
    else{
      let contract = frappe.model.get_new_doc("Contract");
      contract.lead = frm.doc.name;
      contract.contract_prepared_by = frm.doc.lead_owner;
      contract.party_type = "Customer";
      contract.contract_terms = _contract;
      contract.staffing_company = cur_frm.doc.company;
      contract.hiring_company=cur_frm.doc.company_name;
      contract.end_party_user=cur_frm.doc.email_id;
      contract.party_name=cur_frm.doc.company;
      contract.contact_name = frm.doc.lead_name;
      frappe.set_route("form", contract.doctype, contract.name);
    }
  })
  
}

/*---------hide details----------*/
function hide_details() {
  let fields = [
    "source",
    "campaign_name",
    "mobile_no",
  ];
  for (let data in fields) {
    cur_frm.toggle_display(fields[data], 0);
  }
}

function setting_owner_company(frm) {
  if (frappe.user.has_role("Tag User")) {
    tag_staff_company(frm);
  } 
  else if(frappe.boot.tag.tag_user_info.company_type=='Staffing'){
    frm.set_value("organization_type", "Exclusive Hiring")
    frm.set_query("owner_company", function () {
      return {
        filters: [["Company", "organization_type", "in", ["Staffing"]],["Company", "make_organization_inactive", "=", 0]],
      };
    });
    frappe.call({
      method: "tag_workflow.tag_data.lead_org",
      args: { current_user: frappe.session.user },
      callback: function (r) {
        if (r.message == "success") {
          frm.set_value("owner_company", frappe.boot.tag.tag_user_info.company);
        } else {
          frm.set_value("owner_company", "");
        }
      },
    });
  }
}

function tag_staff_company(frm) {
  frm.set_query("owner_company", function () {
    return {
      filters: [["Company", "organization_type", "in", ["Staffing", "TAG"]]],
    };
  });
}


function cancel_lead(frm){
	frm.add_custom_button(__('Cancel'), function(){
		frappe.set_route("Form", "Lead");
	});
}
function view_contract(frm){
  if(frm.doc.__islocal!=1){
    frappe.db.get_value('Contract',{'staffing_company':cur_frm.doc.company,'hiring_company':cur_frm.doc.company_name,'lead':frm.doc.name},['name'],function(r){
      if(r.name){
          cur_frm.page.set_secondary_action(__('View Contract'), function(){
                window.location.href='/app/contract/'+r.name;
          })
        }
    })
  }
}

/*------birth date-------*/
function check_bd(frm){
  let date = frm.doc.dob || "";
  if(date && date >= frappe.datetime.now_date()){
    frappe.msgprint({message: __('<b>DOB</b> Cannot be Today`s date or Future date'), title: __('Error'), indicator: 'orange'});
    cur_frm.set_value("dob", "");
  }
}

function email_box(frm){
      let pop_up = new frappe.ui.Dialog({
        title: __('Send Email '),
        'fields': [
          {'fieldname': 'Email', 'fieldtype': 'Data','label':'To','reqd':1},
          {'fieldname': 'CC', 'fieldtype': 'Data','label':'CC'},
          {'fieldname': 'BCC', 'fieldtype': 'Data','label':'BCC'},
          {'fieldname': 'Subject', 'fieldtype': 'Data','label':'Subject'},
          {'fieldname': 'Content', 'fieldtype': 'Long Text','label':'Message'},
        ],
        primary_action: function(){
          pop_up.hide();
          let comment=pop_up.get_values();
          frappe.call({
            method:"tag_workflow.tag_data.send_email1",
            freeze:true,
            freeze_message:__("Please Wait ......."),
            args:{
              "user": frappe.session.user, "company_type": frappe.boot.tag.tag_user_info.company_type, "sid": frappe.boot.tag.tag_user_info.sid,
              "name": frm.doc.name, "recepients":comment["Email"], "subject":comment["Subject"], "content":comment["Content"], "cc":comment["CC"],
              "bcc":comment["BCC"],"doctype": frm.doc.doctype
            },
            callback: function() {
              frm.reload_doc()
            }
          });
        
        }
      });
      pop_up.show();
}

function hide_fields(frm){
  frm.set_df_property('address_lines_2','hidden',frm.doc.address_lines_2 && frm.doc.enter_manually ==1?0:1);
  frm.set_df_property('county_2','hidden',frm.doc.county_2 && frm.doc.enter_manually ==1?0:1);
  frm.set_df_property('city_or_town','hidden',frm.doc.city_or_town && frm.doc.enter_manually ==1?0:1);
  frm.set_df_property('state_2','hidden',frm.doc.state2 && frm.doc.enter_manually ==1?0:1);
  frm.set_df_property('zip','hidden',frm.doc.zip && frm.doc.enter_manually ==1?0:1);
  frm.set_df_property('country_2','hidden',frm.doc.country_2 && frm.doc.enter_manually ==1?0:1);
}
function show_fields(frm){
  frm.set_df_property('address_lines_2','hidden',0);
  frm.set_df_property('city_or_town','hidden',0);
  frm.set_df_property('state_2','hidden',0);
  frm.set_df_property('zip','hidden',0);
  frm.set_df_property('country_2','hidden',0);
}

function show_addr(frm){
    if(frm.doc.search_on_maps){
        frm.get_docfield('address_lines_1').label ='Complete Address';
    }else if(frm.doc.enter_manually){
        frm.get_docfield('address_lines_1').label ='Address Line 1';
    }
    frm.refresh_field('address_lines_1');
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


/*--------------------Update Complete Address---------------------*/
function update_complete_address(frm){
	if(frm.doc.zip && frm.doc.state_2 && frm.doc.city_or_town){
	    let data = {
	        street_number: frm.doc.address_lines_1 ? frm.doc.address_lines_1:'',
	        route: frm.doc.suite_or_apartment_no ? frm.doc.suite_or_apartment_no    :'',
	        locality:frm.doc.city_or_town,
	        administrative_area_level_1: frm.doc.state_2,
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
	        if(r.message!='No Data')
	        {
	            if(r.message!=frm.doc.complete_address){
	                frm.set_value('complete_address',r.message)
	            }
	        }
	        else{
	            frm.set_value('complete_address','')
	        }
	    }
	})
}
	