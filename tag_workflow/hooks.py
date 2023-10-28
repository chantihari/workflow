from . import __version__ as app_version


app_name = "tag_workflow"
app_title = "Tag Workflow"
app_publisher = "SourceFuse"
app_description = "App to cater for custom development"
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "shadab.sutar@sourcefuse.com"
app_license = "MIT"
app_logo_url = "/assets/tag_workflow/images/TAG-Logo-Emblem.svg"

# global
sales_invoice="Sales Invoice"
map= "public/js/controllers/doc_map.js"
dialog ="public/js/controllers/dialog.js"
perm ="public/js/controllers/perm.js"
# Includes in <head>
fixtures = ["Workspace", "Website Settings", "Web Page", "Translation", "Workflow", "Workflow State", "Workflow Action Master", "System Settings",
{"dt": "Property Setter",
        "filters": [
	[
		"name","in",
 			[
				"User-document_follow_notifications_section-hidden",
				"User-sb1-hidden",
				"User-email_settings-hidden",
				"User-sb_allow_modules-hidden",
				"User-sb3-hidden",
				"User-gender-depends_on",
				"User-birth_date-depends_on",
				"User-bio-collapsible",
				"User-new_password-mandatory_depends_on",
				"User-email-read_only_depends_on",
				"User-short_bio-collapsible",
				"User-sb2-hidden",
				"User-third_party_authentication-hidden",
				"User-api_access-hidden",
				"User-full_name-hidden",
				"User-language-hidden",
				"User-time_zone-hidden",
				"User-middle_name-hidden",
				"User-username-hidden",
				"User-interest-hidden",
				"User-banner_image-hidden",
				"User-mute_sounds-hidden",
				"User-desk_theme-hidden",
				"User-phone-hidden",
				"User-bio-hidden",
				"Company-section_break_28-hidden",
				"Company-date_of_establishment-hidden",
				"Company-default_letter_head-hidden",
				"Company-default_holiday_list-hidden",
				"Company-tax_id-hidden"
			]
	]
	]},
{"dt": "Custom Fields",
        "filters":[
        [
                "name", "in",
                [
                        "Chat Profile-user",
                        "Chat Message-is_send"
                ]
        ]
        ]}
]

on_login = "tag_workflow.utils.trigger_session.first_login"

on_logout = "tag_workflow.utils.trigger_session.clear_filters"

boot_session = "tag_workflow.utils.trigger_session.update_boot"

on_session_creation = [
        "tag_workflow.utils.trigger_session.on_session_creation"
]

app_include_css = [
        "/assets/tag_workflow/css/tag_custom.css",
        "/assets/tag_workflow/css/media-query.css",
        "login.bundle.css",
        "tag_custom.bundle.css",
        "media-query.bundle.css",
]

app_include_js = [
        "/assets/tag_workflow/js/tag.js",
        "/assets/tag_workflow/js/map.js",
        "/assets/tag_workflow/js/controllers/sortable.js",
        "/assets/tag_workflow/js/frappe/form/controls/attach.js",
        "/assets/tag_workflow/js/twilio_utils.js",
        "/assets/tag_workflow/js/list.js",
        "/assets/tag_workflow/js/emp_functions.js",
        "/assets/tag_workflow/js/staff_invoice_ratings.js",
        "/assets/tag_workflow/js/frappe/data_import/index.js",
        "/assets/tag_workflow/js/frappe/data_import/import_preview.js",
        "/assets/tag_workflow/js/frappe/data_import/data_exporter.js",
        "/assets/tag_workflow/js/user_profile_controller.js",
        "/assets/tag_workflow/js/frappe/form/controls/time.js",
        '/assets/tag_workflow/js/payroll_entry_quick_entry.js',
        "/assets/tag_workflow/js/frappe/views/breadcrumbs.js",
        "/assets/tag_workflow/js/frappe/print.js",
        "/assets/tag_workflow/js/frappe/dashboard.js",
        '/assets/tag_workflow/js/tag_workflow_routing.js',
        'tag.bundle.js',
        "/assets/tag_workflow/js/data.js",
        "/assets/tag_workflow/js/notification.js",
        "/assets/tag_workflow/js/frappe/form/layout.js"        
]

web_include_css = [
        "/assets/tag_workflow/css/web_tag.css"
]

# include js in doctype views
doctype_js = {
        "User" : ["public/js/controllers/user.js",dialog],
        "Company": ["public/js/controllers/company.js",map],
        "Designation":"public/js/controllers/designation.js",
        "Item": "public/js/controllers/item.js",
        "Timesheet": "public/js/controllers/timesheet.js",
        "Quotation": "public/js/controllers/quotation.js",
        "Sales Order": "public/js/controllers/sales_order.js",
        "Employee": ["public/js/controllers/employee.js",map],
        sales_invoice: "public/js/controllers/sales_invoice.js",
        "Contact": ["public/js/controllers/contact.js",map],
        "Lead": ["public/js/controllers/lead.js",map],
        "Contract": ["public/js/controllers/contract.js","public/js/controllers/filter.js"],
        "Job Site": "public/js/controllers/job_sites.js",
        "Data Import":"public/js/controllers/data_import.js",
        "Notification Log": "public/js/controllers/notification_log.js",
        "Employee Onboarding Template": ["public/js/controllers/employee_onboarding_template.js",perm],
        "Employee Onboarding": ["public/js/controllers/employee_onboarding.js", map,perm],
        "Job Offer": "public/js/controllers/job_offer.js",
        "Holiday List": "public/js/controllers/holiday_list.js",
        "Salary Component":["public/js/controllers/salary_component.js",perm],
        "Salary Structure":["public/js/controllers/salary_structure.js",perm],
        "Salary Slip":["public/js/controllers/salary_slip.js",perm],
        "Salary Structure Assignment":["public/js/controllers/salary_structure_assignment.js",perm],
        "Claim Order":dialog,
        "Payroll Entry":["public/js/controllers/payroll_entry.js",perm],
        "Payroll Period":["public/js/controllers/payroll_period.js",perm],
        "Chat Message": "public/js/controllers/chat_message.js",
}

# doctype list
doctype_list_js = {
        "User": "public/js/doctype_list/user_list.js",
        "Designation": "public/js/doctype_list/designation_list.js",
        "Employee": "public/js/doctype_list/employee_list.js",
        "Company": "public/js/doctype_list/company_list.js",
        sales_invoice:"public/js/doctype_list/sales_invoice_list.js",
        "Report": "public/js/doctype_list/report_list.js",
        "Timesheet": "public/js/doctype_list/timesheet_list.js",
        "Contact": "public/js/doctype_list/contact_list.js",
        "Lead": "public/js/doctype_list/lead_list.js",
        "Contract": "public/js/doctype_list/contract_list.js",
        "Role Profile": "public/js/doctype_list/role_profile.js",
        "Item": "public/js/doctype_list/item_list.js",
        "Employee Onboarding Template": "public/js/doctype_list/employee_onboarding_template_list.js",
        "Holiday List": "public/js/doctype_list/holiday_list_view.js",
        "Salary Component":["public/js/doctype_list/salary_component_list.js",perm],
        "Salary Slip": ["public/js/doctype_list/salary_slip_list.js",perm],
        "Payroll Entry": ["public/js/doctype_list/payroll_entry_list.js",perm],
        "Salary Structure": ["public/js/doctype_list/salary_structure_list.js",perm],
        "System Setting": "public/js/doctype_list/system_setting.js",
        "Employee Onboarding": "public/js/doctype_list/employee_onboarding_list.js",
        "Payroll Period": ["public/js/doctype_list/payroll_period_list.js",perm],
        "Salary Structure Assignment":["public/js/doctype_list/salary_structure_assignment_list.js",perm],
        "Data Import":["public/js/doctype_list/data_import_list.js"]
}

before_migrate = ["tag_workflow.utils.organization.remove_field"]
# Hook on document methods and events
validate = "tag_workflow.controllers.base_controller.validate_controller"
doc_events = {
        "*":{
            "validate": validate
        },
        "Company": {
            "on_trash": validate,
            "after_insert": 'tag_workflow.tag_workflow.doctype.company.company.create_salary_structure',
            "before_save": 'tag_workflow.tag_workflow.doctype.company.company.validate_saved_fields',
            "before_insert": 'tag_workflow.tag_workflow.doctype.company.company.set_comp_id'
        },
        "User": {
            "on_update": validate,
            "before_save": 'tag_workflow.tag_data.validate_user'
        },
        "Designation":{
                "after_insert":'tag_workflow.tag_data.designation_activity_data'
        },
       "Contact":{
                "on_update":'tag_workflow.utils.lead.update_contact'
       },
       "Lead":{
               "after_insert":'tag_workflow.utils.lead.lead_contact'
       },
       "Job Site":{
               "after_insert":'tag_workflow.tag_data.job_site_add'
       },
       "Item":{
               "after_insert":'tag_workflow.tag_data.job_title_add'
       },
       'Assign Employee':{
               "before_save":'tag_workflow.tag_workflow.doctype.assign_employee.assign_employee.validate_employee'
       },
       'Job Order':{
               "before_save":'tag_workflow.tag_workflow.doctype.job_order.job_order.validate_company'
	},
        "Chat Message":{
                "after_insert":'tag_workflow.chat_tag_data.email_notification'
        }
}

# logo
website_context = {
        "favicon": "/assets/tag_workflow/images/TAG-Logo-Emblem.png",
        "splash_image": "/assets/tag_workflow/images/TAG-Logo.png"
}

override_doctype_dashboards = {
        "Item": "tag_workflow.dashboard_data.item_dashboard.get_data",
        "Company": "tag_workflow.dashboard_data.company_dashboard.get_data",
        sales_invoice: "tag_workflow.dashboard_data.sales_invoice_dashboard.get_data",
        "Lead": "tag_workflow.dashboard_data.lead_dashboard.get_data",
        "Customer": "tag_workflow.dashboard_data.customer_dashboard.get_data"
}
scheduler_events={
        "all":  [
                "tag_workflow.tag_data.update_job_order_status"
	],
        "daily": [
	        "tag_workflow.tag_data.lead_follow_up"
	],
        "weekly":[
                "tag_workflow.utils.jazz_integration.schedule_job"
        ]
}

override_whitelisted_methods = {
        "frappe.desk.query_report.run": "tag_workflow.utils.whitelisted.run",
        "frappe.desk.desktop.get_desktop_page": "tag_workflow.utils.whitelisted.get_desktop_page",
        "frappe.desk.reportview.delete_items": "tag_workflow.utils.employee.delete_items",
        "frappe.desk.search.search_link": "tag_workflow.utils.whitelisted.search_link",
        "frappe.core.doctype.data_import.data_import.form_start_import": "tag_workflow.utils.data_import.form_start_import",
        "frappe.core.doctype.data_import.data_import.download_template": "tag_workflow.utils.data_import.download_template",
        "frappe.desk.form.save.savedocs": "tag_workflow.utils.whitelisted.savedocs",
        "frappe.desk.form.save.cancel": "tag_workflow.utils.whitelisted.cancel",
        "frappe.client.save": "tag_workflow.utils.whitelisted.save",
        "erpnext.accounts.party.get_due_date": "tag_workflow.utils.invoice.get_due_date",
        "frappe.model.workflow.bulk_workflow_approval":"tag_workflow.utils.workflow.bulk_workflow_approval",
        "hrms.controllers.employee_boarding_controller.get_onboarding_details": "tag_workflow.utils.whitelisted.get_onboarding_details",
        "hrms.overrides.employee_master.get_retirement_date":"tag_workflow.utils.whitelisted.get_retirement_date",
        "frappe.handler.upload_file": "tag_workflow.utils.whitelisted.upload_file",
        "frappe.deferred_insert.deferred_insert": "tag_workflow.utils.whitelisted.deferred_insert",
        "frappe.desk.reportview.get_list": "tag_workflow.utils.reportview.get_list",
        "frappe.desk.doctype.notification_settings.notification_settings.set_seen_value": "tag_workflow.utils.whitelisted.set_seen_value",
        "chat.api.message.mark_as_read": "tag_workflow.utils.whitelisted.mark_as_read",
        "chat.api.message.set_typing": "tag_workflow.utils.whitelisted.set_typing",
        "chat.api.message.send": "tag_workflow.utils.whitelisted.send",
        "chat.api.message.get_all": "tag_workflow.utils.whitelisted.get_all",
        "frappe.desk.doctype.tag.tag.add_tags": "tag_workflow.utils.whitelisted.add_tags",
        "frappe.desk.page.user_profile.user_profile.get_energy_points_percentage_chart_data": "tag_workflow.utils.whitelisted.get_energy_points_percentage_chart_data",
        "frappe.desk.page.user_profile.user_profile.get_user_rank": "tag_workflow.utils.whitelisted.get_user_rank",
        "frappe.desk.form.load.getdoc":"tag_workflow.utils.whitelisted.getdoc",
        "frappe.client.get_value":"tag_workflow.utils.whitelisted.get_value",
}


override_doctype_class = {
    "Designation":"tag_workflow.dashboard_data.designation.DesignationOverride",
    "Company": "tag_workflow.tag_workflow.doctype.company.company.CustomCompany"
}

