import frappe
from frappe.desk.reportview import execute, get_form_params, compress
from geopy.geocoders import Nominatim
import frappe
import json
import frappe.permissions
from frappe.model.base_document import get_controller
import json
import requests
from haversine import haversine
from tag_workflow.tag_workflow.doctype.job_order.job_order import claims_left
from tag_workflow.tag_workflow.doctype.job_order.job_order import my_used_job_orders
from frappe.model.db_query import DatabaseQuery
from tag_workflow.tag_data import update_lat_lng_gmap
tag_gmap_key = frappe.get_site_config().tag_gmap_key or ""
GOOGLE_API_URL = f"https://maps.googleapis.com/maps/api/geocode/json?key={tag_gmap_key}&address="
distance_value = {"5": 5, "10": 10, "25": 25, "50": 50, "100": 100}
distance = ['5', '10', '25', '50', '100']
JOB = 'Job Order'
CUSTOM = 'Custom Address'
get_table_columns=DatabaseQuery.get_table_columns
tab_job_order = "`tabJob Order`."
statusfieldname = "`disabled`"
@frappe.whitelist()
@frappe.read_only()
def get():
    try:
        args = get_form_params()
        '''# organization_type = frappe.db.get_value(
        #         "User", frappe.session.user, "organization_type") or '''''
        organization_type = frappe.db.sql('''select organization_type from `tabUser` where name = "{0}"'''.format(frappe.session.user))[0][0] or ''
        args = set_salary_component_status(args,organization_type)
        args = set_status_data(args,organization_type)
        # If virtual doctype get data from clat, lng = emp_location_data(location_data)ontroller het_list method
        radius = args.radius or ''
        order_status = args.order_status or ''
        custom_address = args.custom_address or ''
        filter_loc = filter_data(args)
        doc_data = frappe.db.sql(f'''select is_virtual from `tabDocType` where name="{args.doctype}"''')
        if doc_data and doc_data[0][0]:
            controller = get_controller(args.doctype)
            data = compress(controller(args.doctype).get_list(args))
        else:
            if(args.doctype == JOB and organization_type == "Staffing"):        
                args = update_order_by(args)
                args = industry_filedname(args,organization_type)
                page_length = int(args['page_length']) + int(args['start'])
                args['start'] = '0'
                args['page_length'] = str(
                    page_length*(int(args['page_length']) + int(args['page_length'])))
                try:
                    data = compress(execute(**args),args)
                except Exception as e:
                    print('e-----------',e)
                data = staffing_user_check_data(data,order_status,radius, page_length,filter_loc,custom_address)
            else:
                data = compress(execute(**args), args=args)
        return data
    except Exception as e:
        frappe.msgprint(e)


def set_salary_component_status(args,organization_type):
    '''# if organization_type == "TAG" or organization_type == "Staffing": '''
    if organization_type in ["TAG", "Staffing"]:
        args = industry_filedname(args,organization_type)
        return args
    return args


def industry_filedname(args,organization_type):
    if(args["doctype"] == JOB):
        str_order = args["order_by"]
        splitted_order_by = str_order.split(".")
        order = splitted_order_by[1].split(" ")
        if order[0] ==  "`no_of_workers`":
            order[0] = "`category`"
            '''# new_str = tab_job_order + (" ").join(order)
            # args["order_by"] = new_str'''
            args["order_by"] = tab_job_order + " ".join(order)
            return args
        '''# elif(args["doctype"] == "Salary Component" and organization_type == "TAG" or organization_type == "Staffing"):'''
    elif args["doctype"] == "Salary Component" and organization_type in ["TAG", "Staffing"]:
        str_order = args["order_by"]
        splitted_order_by = str_order.split(".")
        order = splitted_order_by[1].split(" ")
        '''# if order[0]== statusfieldname and order[1] == "asc":
        #     order[1] = "desc"
        #     new_str = "`tabSalary Component`."+(" ").join(order)
        #     args["order_by"] = new_str
        #     return args
        # elif order[0] == statusfieldname and order[1] == "desc":
        #     order[1] = "asc"
        #     new_str =  "`tabSalary Component`."+(" ").join(order)
        #     args["order_by"] = new_str
        #     return args'''
        if order[0] == statusfieldname:
            if order[1] == "asc":
                order[1] = "desc"
            elif order[1] == "desc":
                order[1] = "asc"
            args["order_by"] = "`tabSalary Component`." + (" ").join(order)
    return args


def  staffing_user_check_data(data,order_status,radius, page_length,filter_loc,custom_address):
    if(data):
        data['order_length'] = 0
        based_list = compare_order(order_status)
        data = get_actual_number(data, based_list)
        data = staffing_data(data, radius, page_length,filter_loc,custom_address)
        data = claim_left(data)
        return data
    return data

def set_status_data(args,organization_type):
    if(args["doctype"] == "Item" and organization_type == "Staffing"):
        str_order = args["order_by"]
        splitted_order_by = str_order.split(".")
        order = splitted_order_by[1].split(" ")
        '''# if order[0]== statusfieldname and order[1] == "asc":
        #     order[1] = "desc"
        #     new_str = "`tabItem`."+(" ").join(order)
        #     args["order_by"] = new_str
        #     return args
        # elif order[0] == statusfieldname and order[1] == "desc":
        #     order[1] = "asc"
        #     new_str =  "`tabItem`."+(" ").join(order)
        #     args["order_by"] = new_str
        #     return args'''
        if order[0] == statusfieldname:
            if order[1] == "asc":
                order[1] = "desc"
            elif order[1] == "desc":
                order[1] = "asc"
            args["order_by"] = "`tabItem`."+(" ").join(order)
    return args
     

def update_order_by(args):
    if(args["doctype"] == JOB):
        str_order =args["order_by"]
        splitted_order_by = str_order.split(".")
        order = splitted_order_by[1].split(" ")
        '''# if order[0]== "`order_status`" and order[1] == "asc":
        #     order[1] = "desc"
        #     new_str = tab_job_order+(" ").join(order)
        #     args["order_by"] = new_str
        #     return args
        # elif order[0] == "`order_status`" and order[1] == "desc":
        #     order[1] = "asc"
        #     new_str = tab_job_order+(" ").join(order)
        #     args["order_by"] = new_str
        #     return args'''
        if order[0] == "`order_status`":
            if order[1] == "asc":
                order[1] = "desc"
            elif order[1] == "desc":
                order[1] = "asc"
            args["order_by"] = tab_job_order+(" ").join(order)
        else:
            return args
    return args
                
def staffing_data(data, radius, page_length,filter_loc,custom_address):
    try:
        '''# result = []'''
        l = len(filter_loc)
        user_company = frappe.db.get_list(
            "Employee", {"user_id": frappe.session.user}, "company")
        if(radius in distance and l==0 and custom_address==''):
            data = get_data(user_company, radius, data, page_length)
        elif (custom_address!=''):
            data = filter_location_with_custom_address(custom_address,radius,data,page_length)
        elif(radius and l>0 and radius not in ['All',CUSTOM]):
            data = get_data(user_company, radius, data, page_length,filter_loc = filter_loc)
        elif(radius and l>0 and radius in ['All',CUSTOM]):
            data = filter_location_with_radius(user_company, radius, data, page_length,filter_loc)
        else:
            '''# for d in data['values']:
            #     if(len(result) < page_length):
            #         result.append(d)
            # data["values"] = result'''
            data["values"] = data["values"][:page_length]
       
        return data
    except Exception as e:
        frappe.msgprint(e)
        return data


def get_actual_number(data, based_list):
    old_data = data
    try:
        '''# result = []
        # for d in data['values']:
        #     if(d[0] in based_list):
        #         result.append(d)'''
        result = [d for d in data['values'] if d[0] in based_list]
        data["values"] = result
        data['order_length'] = len(result)
        return data
    except Exception as e:
        print(e)
        return old_data


def claim_left(data):
    try:
        data_list = data
        ''' # company_name = frappe.db.get_value("User", frappe.session.user, "company")'''
        company_name = frappe.db.sql('''select company from `tabUser` where name = "{0}"'''.format(frappe.session.user))[0][0]
        if(data):
            for d in data['values']:
                d[-10] = claims_left(d[0], company_name)
        return data
    except Exception as e:
        print(e)
        return data_list


def compare_order(order_status):
    try:
        '''# company = frappe.db.get_value("User", frappe.session.user, "company")'''
        company = frappe.db.sql('''select company from `tabUser` where name = "{0}"'''.format(frappe.session.user))[0][0]
        based_on_my_list = my_used_job_orders(company, order_status)
        return based_on_my_list
    except Exception as e:
        print(e)
        return []


def get_data(user_company, radius, data, page_length,filter_loc = None):
    try:
        company_address = []
        result = []
        if not filter_loc:
            for com in user_company:
                lat, lng, add = frappe.db.get_value("Company", com.company, ["lat", "lng", "address"])
                result = get_radius_filtered_data(radius, data, company_address, lat, lng, add)
            data['values'] = result[0:page_length] if result else []
        else:
            for loc in filter_loc:
                lat, lng, add = frappe.db.get_value("Job Site", loc, ["lat", "lng", "address"])
                result = get_radius_filtered_data(radius, data, company_address, lat, lng, add)
            data['values'] = result[0:page_length] if result else []
        return data
    except Exception:
        return data

def get_radius_filtered_data(radius, data, company_address, lat, lng, add):
    if lat and lng and lat!="0" and lng!="0":
        company_address.append(tuple([float(lat),float(lng)]))
    elif add and add not in company_address:
        lat, lng = get_lat_lng(add)
        lat_lng = tuple([lat,lng])
        if lat!=0 and lng!=0 and lat_lng not in company_address:
            company_address.append(lat_lng)
    if(check_distance):
        result = check_distance(company_address, data, radius)
    return result


def check_distance(company_address, data, radius):
    try:
        result, orders = [], []
        for add in company_address:
            for d in data['values']:
                try:
                    geo_data = frappe.db.sql('''select lat, lng from `tabJob Site` where name = "{0}"'''.format(d[-9]), as_list=True)
                    rds = haversine(add, tuple(
                        [float(geo_data[0][0]), float(geo_data[0][1])]), unit='mi')
                    if(rds <= distance_value[radius] and d[0] not in orders):
                        result.append(d)
                        orders.append(d[0])
                except Exception:
                    continue
        return result
    except Exception as e:
        frappe.msgprint(e)


def get_loc(data):
    '''# doc_args = set()
    # for j in data:
    #     doc_args.update([j[-2]+'#'+j[-1]])
    # doc_args =  sorted(doc_args)'''
    doc_args = sorted({f"{x[-2]}#{x[-1]}" for x in data})
    return doc_args


@frappe.whitelist()
def get_location(organization_type):
    try:
        """# based_list = compare_order('All')
        # args = {
        #         'doctype': JOB,
        #         'fields': [
        #             '`tabJob Order`.`name`',
        #             '`tabJob Order`.`job_site`',
        #             '`tabJob Order`.`company`'
        #         ],
        #         # 'filters': [{"name": ("in", tuple(based_list))}],
        #         'filters': [],
        #         'order_by': '`tabJob Order`.`modified` desc',
        #         'group_by': '`tabJob Order`.`name`',
        #         # 'order_status': 'All',
        #         'save_user_settings': True,
        #         'strict': None
        #     }"""
        merge_query = f'''
            select jo.name,jo.no_of_workers ,cl.approved_no_of_workers as app from `tabJob Order` jo left join `tabClaim Order` cl on jo.name = cl.job_order where (claim not like CONCAT('%', (
                SELECT company
                FROM `tabUser`
                where name="{frappe.session.user}"), '%'
                ) or claim is Null) and order_status!="Completed" and resumes_required=0 group by cl.name having cl.approved_no_of_workers is null or jo.no_of_workers > sum(cl.approved_no_of_workers)
            union
            select name,creation,modified from `tabJob Order` where claim like CONCAT('%', (
                SELECT company
                FROM `tabUser`
                where name="{frappe.session.user}"), '%'
                )  or ((claim not like CONCAT('%', (
                    SELECT company
                    FROM `tabUser`
                    where name="{frappe.session.user}"), '%'
                ) or claim is Null) and order_status!="Completed" and resumes_required=1 and total_workers_filled!=total_no_of_workers)
        '''

        merged_list = frappe.db.sql(merge_query,as_list=True)
        based_list = [i[0] for i in merged_list]
        if based_list:
            data = frappe.db.sql(f'''SELECT `job_site`,`name`,`company` FROM `tabJob Order` WHERE `name` IN {tuple(based_list)} and (owner = '{frappe.session.user}' or (name in (select `share_name` from `tabDocShare` where `read` = '1.0' and `share_doctype` = 'Job Order' and (`user` = '{frappe.session.user}' or `everyone` = '1.0'))) )GROUP BY job_site ORDER BY job_site ASC''',as_list=True)
            """# data = frappe.db.sql(f'''SELECT `name`,`job_site`,`company` FROM `tabJob Order` WHERE `name` IN (select name from (select jo.name,jo.no_of_workers ,cl.approved_no_of_workers as app from `tabJob Order` jo left join `tabClaim Order` cl on jo.name = cl.job_order where (claim not like CONCAT('%', (
            #     SELECT company
            #     FROM `tabUser`
            #     where name="{frappe.session.user}"), '%'
            # ) or claim is Null) and order_status!="Completed" and resumes_required=0 group by cl.name having cl.approved_no_of_workers is null or jo.no_of_workers > sum(cl.approved_no_of_workers)
            #         union
            #         select name,creation,modified from `tabJob Order` where claim like CONCAT('%', (
            #     SELECT company
            #     FROM `tabUser`
            #     where name="{frappe.session.user}"), '%'
            # )  or ((claim not like CONCAT('%', (
            #     SELECT company
            #     FROM `tabUser`
            #     where name="{frappe.session.user}"), '%'
            # ) or claim is Null) and order_status!="Completed" and resumes_required=1 and worker_filled!=no_of_workers)) sub) and (owner = '{frappe.session.user}' or (name in (select `share_name` from `tabDocShare` where `read` = '1.0' and `share_doctype` = 'Job Order' and (`user` = '{frappe.session.user}' or `everyone` = '1.0') order by `modified` DESC)) )GROUP BY name ORDER BY job_site ASC''',as_list=True)"""
        else:
            data = []

            """# doc_data = frappe.db.sql(f'''select is_virtual from `tabDocType` where name="{args.get('doctype')}"''')

            # if doc_data and doc_data[0][0]:
            #     controller = get_controller(args.get('doctype'))
            #     data = compress(controller(args.get('doctype')).get_list(args))
            # else:
                
            # organization_type = frappe.db.sql('''select organization_type from `tabUser` where name = "{0}"'''.format(frappe.session.user))[0][0] or ''"""
        if(data and organization_type == "Staffing"):
            data = [f"{x[-3]}#{x[-1]}" for x in data]
        else:
            data = []
        return data
    except Exception as e:
        frappe.msgprint(e)
        return []

@frappe.whitelist()
def get_location_staff_company_list(comps):
    try:
        args = {
            'doctype': 'Job Site',
            'fields': [
                '`tabJob Site`.`name`',
                '`tabJob Site`.`job_site_name`',
                '`tabJob Site`.`company`'
            ],
            'filters': [],
            'order_by': '`tabJob Site`.`modified` desc',
            'group_by': '`tabJob Site`.`job_site_name`'
        }
        
        if frappe.db.get_value("DocType", filters={"name": args.get('doctype')}, fieldname="is_virtual"):

            controller = get_controller(args.get('doctype'))
            data = compress(controller(args.get('doctype')).get_list(args))
        else:
            
            import json
            if len(json.loads(comps))==1:
                 
                data = frappe.db.sql(f'''select job_site_name,name,company from `tabJob Site` where company="{json.loads(comps)[0]}"''',as_list=True)
            else:
                data = frappe.db.sql(f'''select job_site_name,name,company from `tabJob Site` where company in {tuple(json.loads(comps))}''',as_list=True)
            if(data):
                data = get_loc(data)
            else:
                data = []
        return data 
    
    except Exception as e:
        frappe.msgprint(e)
        return []
    
def employee_email_filter(email):
    sql = """SELECT company from `tabEmployee` where user_id="{}" """.format(
        email)
    data = frappe.db.sql(sql, as_dict=True)
    for i in data:
        return i["company"]


def check_staffing(doc_name):
    try:
        datas = ''' select no_of_workers_joborder,approved_no_of_workers,job_order from `tabClaim Order` where job_order = "{}"  '''.format(
            doc_name)
        data_list = frappe.db.sql(datas)
        approved_no_of_workers = []
        for j in data_list:
            approved_no_of_workers.append(j[1])
        if (data_list[0][0]-sum(approved_no_of_workers)) > 0:
            return True
        return False

    except Exception as e:
        print(e, frappe.get_traceback())
        frappe.db.rollback()
#-------------------------------#

def get_lat_lng(address):
    try:
        loc = Nominatim(user_agent="GetLoc")
        get_loc = loc.geocode(address, exactly_one=True, timeout=15)
        if not get_loc:
            address_list = address.split(",")
            if len(address_list)>=4:
                address_list.pop(0)
                address = "".join(address_list)
            get_loc = loc.geocode(address)
            if not get_loc:
                lat, lng = update_lat_lng_gmap(address)
            else:
                lat = get_loc.latitude
                lng = get_loc.longitude
        else:
            lat = get_loc.latitude
            lng = get_loc.longitude
        return lat, lng
    except Exception:
        return update_lat_lng_gmap(address)

def filter_location_with_radius(user_company, radius, data, page_length,filter_loc):
    try:
        '''# for d in data['values']:
        #     if(len(d) > 3 and d[-9] in filter_loc):
        #         result.append(d)
        # data["values"] = result'''
        data["values"] = [d for d in data['values'] if len(d) > 3 and d[-9] in filter_loc]
        if radius not in ['All',CUSTOM]:
            data = get_data(user_company, radius, data, page_length)
        return data
    except Exception as e:
        frappe.msgprint(e)
        return data

def filter_data(args):
    try: 
        filter_loc = args.filter_loc
        filter_loc = json.loads(filter_loc)
        filter_loc = list(set(filter_loc))
        if 'radius' in args.keys():
            del args["radius"]

        if 'order_status' in args.keys():
            del args['order_status']

        if 'filter_loc' in args.keys():
            del args['filter_loc']

        if 'custom_address' in args.keys():
            del args['custom_address']

        return filter_loc
    except Exception as e:
        print(e)
        return []

def filter_location_with_custom_address(custom_address,radius,data,page_length):
    try:
        custom_location = get_custom_location(custom_address)
        result, orders = [], []
        if custom_location:
            for d in data['values']:
                filter_location_contd(d, custom_location, radius, orders, result)
            if(result):
                data['values'] = result[0:page_length]
            else:
                data['values'] = []
        return data
    except Exception as e:
        frappe.msgprint(e)

def filter_location_contd(d, custom_location, radius, orders, result):
    try:
        geo_data = frappe.db.sql('''select lat, lng from `tabJob Site` where name = "{0}"'''.format(d[-9]), as_list=True)
        rad = haversine(custom_location, tuple(
                [float(geo_data[0][0]), float(geo_data[0][1])]), unit='mi')
        if(radius in ['All',CUSTOM] and (rad <=5 or rad<=10 or rad<=25 or rad<=50  or rad<=100 and d[0] not in orders)) or (radius not in['All',CUSTOM] and rad<=distance_value[radius] and d[0] not in orders):
            result.append(d)
            orders.append(d[0])
    except Exception:
        pass

def get_custom_location(custom_address):
    lat, lng = get_lat_lng(custom_address)
    return tuple([lat, lng]) if lat!=0 and lng!=0 else None

@frappe.whitelist()
@frappe.read_only()
def get_list():
    args = get_form_params()
    if args.get('or_filters') and args['or_filters'][0][0]=='for_user' and args['or_filters'][0][2]!=frappe.session.user:
            frappe.throw('Invalid request')

	# uncompressed (refactored from frappe.model.db_query.get_list)
    return execute(**get_form_params())

def execute_custom(doctype, *args, **kwargs):
	return DatabaseQueryCustom(doctype).execute(*args, **kwargs)

from frappe.utils import (
	add_to_date,
	cint
)
import copy
class DatabaseQueryCustom:
	get_table_columns=DatabaseQuery.get_table_columns
	prepare_args=DatabaseQuery.prepare_args
	parse_args=DatabaseQuery.parse_args
	sanitize_fields=DatabaseQuery.sanitize_fields
	extract_tables=DatabaseQuery.extract_tables
	set_optional_columns=DatabaseQuery.set_optional_columns
	build_conditions=DatabaseQuery.build_conditions
	build_filter_conditions=DatabaseQuery.build_filter_conditions
	build_match_conditions=DatabaseQuery.build_match_conditions
	get_permission_query_conditions=DatabaseQuery.get_permission_query_conditions
	get_share_condition=DatabaseQuery.get_share_condition
	set_field_tables=DatabaseQuery.set_field_tables
	cast_name_fields=DatabaseQuery.cast_name_fields
	set_order_by=DatabaseQuery.set_order_by
	validate_order_by_and_group_by=DatabaseQuery.validate_order_by_and_group_by
	add_limit=DatabaseQuery.add_limit
	add_comment_count=DatabaseQuery.add_comment_count
	update_user_settings=DatabaseQuery.update_user_settings

	def __init__(self, doctype, user=None):
		self.doctype = doctype
		self.tables = []
		self.link_tables = []
		self.conditions = []
		self.or_conditions = []
		self.fields = None
		self.user = user or frappe.session.user
		self.ignore_ifnull = False
		self.flags = frappe._dict()
		self.reference_doctype = None

	def execute(
		self,
		fields=None,
		filters=None,
		or_filters=None,
		docstatus=None,
		group_by=None,
		order_by="KEEP_DEFAULT_ORDERING",
		limit_start=False,
		limit_page_length=None,
		as_list=False,
		with_childnames=False,
		debug=False,
		ignore_permissions=False,
		user=None,
		with_comment_count=False,
		join="left join",
		distinct=False,
		start=None,
		page_length=None,
		limit=None,
		ignore_ifnull=False,
		save_user_settings=False,
		save_user_settings_fields=False,
		update=None,
		add_total_row=None,
		user_settings=None,
		reference_doctype=None,
		run=True,
		strict=True,
		pluck=None,
		ignore_ddl=False,
		*,
		parent_doctype=None,
	) -> list:

		if (
			not ignore_permissions
			and not frappe.has_permission(self.doctype, "select", user=user, parent_doctype=parent_doctype)
			and not frappe.has_permission(self.doctype, "read", user=user, parent_doctype=parent_doctype)
		):
			frappe.flags.error_message = _("Insufficient Permission for {0}").format(
				frappe.bold(self.doctype)
			)
			raise frappe.PermissionError(self.doctype)
		# filters and fields swappable
		# its hard to remember what comes first
		if isinstance(fields, dict) or (
			fields and isinstance(fields, list) and isinstance(fields[0], list)
		) or fields and isinstance(filters, list) and len(filters) > 1 and isinstance(filters[0], str):
			# if fields is given as dict/list of list, its probably filters
			filters, fields = fields, filters
    
		if fields:
			self.fields = fields
		else:
			self.fields = [f"`tab{self.doctype}`.`{pluck or 'name'}`"]

		if start:
			limit_start = start
		if page_length:
			limit_page_length = page_length
		if limit:
			limit_page_length = limit

		self.filters = filters or []
		self.or_filters = or_filters or []
		self.docstatus = docstatus or []
		self.group_by = group_by
		self.order_by = order_by
		self.limit_start = cint(limit_start)
		self.limit_page_length = cint(limit_page_length) if limit_page_length else None
		self.with_childnames = with_childnames
		self.debug = debug
		self.join = join
		self.distinct = distinct
		self.as_list = as_list
		self.ignore_ifnull = ignore_ifnull
		self.flags.ignore_permissions = ignore_permissions
		self.user = user or frappe.session.user
		self.update = update
		self.user_settings_fields = copy.deepcopy(self.fields)
		self.run = run
		self.strict = strict
		self.ignore_ddl = ignore_ddl

		# for contextual user permission check
		# to determine which user permission is applicable on link field of specific doctype
		self.reference_doctype = reference_doctype or self.doctype

		if user_settings:
			self.user_settings = json.loads(user_settings)

		self.columns = self.get_table_columns()

		# no table & ignore_ddl, return
		if not self.columns:
			return []

		result = self.build_and_run()

		if with_comment_count and not as_list and self.doctype:
			self.add_comment_count(result)

		if save_user_settings:
			self.save_user_settings_fields = save_user_settings_fields
			self.update_user_settings()

		if pluck:
			return [d[pluck] for d in result]
		print(add_total_row)
		return result

	def build_and_run(self):
		args = self.prepare_args()
		args.limit = self.add_limit()
		company_name = frappe.db.get_value("User", frappe.session.user, "company")
		unclaimed_noresume_by_company=[]
		unclaimed_noresume_by_comp=f'select name from `tabJob Order` where (claim not like "%{company_name}%" or claim is Null) and order_status!="Completed" and resumes_required=0'
		my_unaval_claims=frappe.db.sql(unclaimed_noresume_by_comp,as_list=1)
		for i in my_unaval_claims:
			data=frappe.get_doc(JOB,i[0])
			claims=f'select sum(approved_no_of_workers) from `tabClaim Order` where job_order="{data.name}"'
			data1=frappe.db.sql(claims,as_list=1)
			if(data1[0][0]!=None):
				if int(data.no_of_workers)-int(data1[0][0])>0:
					unclaimed_noresume_by_company.append(data.name)
			else:
				unclaimed_noresume_by_company.append(data.name)
		unclaimed_jo=()
		for jo in unclaimed_noresume_by_company:
			unclaimed_jo=unclaimed_jo+(jo,)
		str_unclaimed_jo=str(unclaimed_jo)
		str_unclaimed_job=str_unclaimed_jo[:-2] + str_unclaimed_jo[-1]
		if args.conditions:
			args.conditions = "where "+ args.conditions+ " and ((`tabJob Order`.claim like '%"+company_name+"%') or ((`tabJob Order`.claim not like '%"+company_name+"%' or `tabJob Order`.claim is Null) and `tabJob Order`.order_status!='Completed' and `tabJob Order`.resumes_required=1 and `tabJob Order`.total_workers_filled!=`tabJob Order`.total_no_of_workers) or (`tabJob Order`.name in "+str_unclaimed_job+"))"
		if self.distinct:
			args.fields = "distinct " + args.fields
			args.order_by = "" 

		# Postgres requires any field that appears in the select clause to also
		# appear in the order by and group by clause
		if frappe.db.db_type == "postgres" and args.order_by and args.group_by:
			args = self.prepare_select_args(args)

		query = (
			"""select %(fields)s
			from %(tables)s
			%(conditions)s
			%(group_by)s
			%(order_by)s
			%(limit)s"""
			% args
		)

		return frappe.db.sql(
			query,
			as_dict=not self.as_list,
			debug=self.debug,
			update=self.update,
			ignore_ddl=self.ignore_ddl,
			run=self.run,
		)
