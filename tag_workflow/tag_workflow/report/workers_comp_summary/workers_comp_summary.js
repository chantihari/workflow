// Copyright (c) 2016, SourceFuse and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Workers Comp Summary"] = {
	"filters": [
		{
			'fieldname': 'start_date',
			'label': __('Start Date'),
			'fieldtype': 'Date',
			'reqd': 1
		},
		{
			'fieldname': 'end_date',
			'label': __('End Date'),
			'fieldtype': 'Date',
			'reqd': 1
		},
		{
			'fieldname': "company",
			'fieldtype': "Link",
			'options': 'Company',
			'label': "Company",
			'reqd': 1,
			'default': (frappe.boot.tag.tag_user_info.company_type=='Staffing' && frappe.boot.tag.tag_user_info.comps.length==1) ? frappe.boot.tag.tag_user_info.company : '',
			"get_query" : function(){
				return {
					"filters":[ ['Company', "organization_type", "in", ["Staffing" ]],['Company',"make_organization_inactive","=",0]]
				}
			}
		},
		{
			'fieldname': 'state',
			'label': __('State'),
			'fieldtype': 'Select',
			'options':'\nAlabama\nAlaska\nArizona\nArkansas\nCalifornia\nColorado\nConnecticut\nDelaware\nFlorida\nGeorgia\nHawaii\nIdaho\nIllinois\nIndiana\nIowa\nKansas\nKentucky\nLouisiana\nMaine\nMaryland\nMassachusetts\nMichigan\nMinnesota\nMississippi\nMissouri\nMontana\nNebraska\nNevada\nNew Hampshire\nNew Jersey\nNew Mexico\nNew York\nNorth Carolina\nNorth Dakota\nOhio\nOklahoma\nOregon\nPennsylvania\nRhode Island\nSouth Carolina\nSouth Dakota\nTennessee\nTexas\nUtah\nVermont\nVirginia\nWashington\nWest Virginia\nWisconsin\nWyoming'

		}
	],
};
