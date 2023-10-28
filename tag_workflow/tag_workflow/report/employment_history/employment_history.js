// Copyright (c) 2016, SourceFuse and contributors
// For license information, please see license.txt
/* eslint-disable */
function get_data(filter_name){
	let data = ['\n'];
	frappe.call({
		'method' : 'tag_workflow.utils.whitelisted.fetch_data',
		'args': {
			'filter_name': filter_name
		},
		'callback': function(r){
			if(r.message){
				for (let i in r.message){
					data.push(r.message[i])
				}
			}
		},
		freeze: true,
		freeze_message: "<b>Please wait while report is being prepared!</b>"
	})
	return data
}

frappe.query_reports['Employment History'] = {
	'filters': [
		{
			'fieldname': 'emp_id',
			'label': __('Employee ID'),
			'fieldtype': 'Select',
			'options': get_data('emp_id')
		},
		{
			'fieldname': 'emp_name',
			'label': __('Employee Name'),
			'fieldtype': 'Select',
			'options': get_data('emp_name')
		},
		{
			'fieldname': 'company',
			'label': __('Staffing Company'),
			'fieldtype': 'Select',
			'options': get_data('company')
		},
		{
			'fieldname': 'job_order',
			'label': __('Job Order'),
			'fieldtype': 'Select',
			'options': get_data('job_order')
		},
		{
			'fieldname': 'job_title',
			'label': __('Job Title'),
			'fieldtype': 'Select',
			'options': get_data('job_title')
		},
		{
			'fieldname': 'start_date',
			'label': __('Start Date'),
			'fieldtype': 'Date'
		},
		{
			'fieldname': 'total_hours',
			'fieldtype': 'Data',
			'label': 'Total Hours Worked'
		},
		{
			'fieldname': 'emp_status',
			'label': __('Status'),
			'fieldtype': 'Select',
			'options': '\nDNR\nNo Show\nNon Satisfactory'
		},
	],
	onload: function(){
		$(document).on('input', '[data-fieldname="total_hours"]', function(){
			this.value = this.value.replace(/[^0-9.]/g, '').replace(/(\..*?)\..*/g, '$1');
		});
	}
};

$("[data-route='query-report/Employment History'] .sub-heading").html("A report detailing the employees that your company has hired for job orders.");