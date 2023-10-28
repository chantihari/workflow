import frappe
import json
from haversine import haversine
from tag_workflow.utils.reportview import get_lat_lng
from tag_workflow.tag_workflow.doctype.company.company import check_staffing_reviews
from tag_workflow.utils.whitelisted import check_user_type
from tag_workflow.tag_data import check_permissions

# this file for TG-2607
@frappe.whitelist()
def comp(comp_id=None,company_name=None,filters=None,start=0,end=20):
    user_name = frappe.session.user
    try:
        if user_name == 'Administrator':
            sql = """select name, address, city, state, zip, average_rating from `tabCompany` where organization_type='Staffing'"""
            data = frappe.db.sql(sql, as_dict=True)
            if comp_id:
                data=frappe.db.sql(sql, as_list=True)
                company_name=data[int(comp_id)-1][0]
                return company_data(company_name)
        else:
            sql = ''' select organization_type from `tabUser` where email='{}' '''.format(user_name)
            user_type=frappe.db.sql(sql, as_list=1)
            if user_type[0][0]=='Hiring':
               data = hiring_data(filters,user_name,comp_id,start,end)
            elif(user_type[0][0]=='Exclusive Hiring'): 
                sql=""" select parent_staffing from `tabCompany` where name='{0}'  """.format(company_name)
                staff_comp_name = frappe.db.sql(sql, as_list=1)
                sql = """  select * from `tabCompany` where name='{0}' """.format(staff_comp_name[0][0])
                data = frappe.db.sql(sql, as_dict=True)
                if comp_id:
                    data=frappe.db.sql(sql, as_list=True)
                    company_name=data[int(comp_id)-1][0]
                    return company_data(company_name)
        unique_data = { each['company_name'] : each for each in data }.values()
        return list(unique_data)
    except Exception as e:
        frappe.log_error(e, "Staffing Company Error")

def company_data(company_name):
    det_sql = """ select * from `tabCompany` where name="{}" """.format(company_name)
    company_detail = frappe.db.sql(det_sql,as_dict=True)

    ind_sql = """ select industry_type from `tabIndustry Types` where parent='{}'""".format(company_name)
    company_industry=frappe.db.sql(ind_sql, as_dict=True)

    mem_sql = """ select first_name,last_name from `tabUser` where company='{}' and enabled=1 """.format(company_name)
    team_member=frappe.db.sql(mem_sql, as_dict=True)

    rev_sql = """select `tabUser`.first_name,`tabUser`.last_name,rating,comments,LEFT(`tabCompany Review`.creation,10) as creation from `tabCompany Review`,`tabUser` where staffing_company='{}' and comments IS NOT NULL and `tabUser`.name=`tabCompany Review`.owner""".format(company_name)
    company_review_rating=frappe.db.sql(rev_sql, as_dict=True)

    return company_detail,company_industry,team_member,company_review_rating  

def check_blocked_staffing(user_name, data):
    sql ='''select staffing_company_name from `tabBlocked Staffing Company` where modified_by='{}' '''.format(user_name)
    blocked_staffing = frappe.db.sql(sql, as_dict=True)
    for d in data:
        for blocked in blocked_staffing:
            if blocked['staffing_company_name'] == d['name']:
                d.update({'is_blocked': True})
    return data

@frappe.whitelist(allow_guest=False)
def favourite_company(company_to_favourite, user_company, user):
    """
    The function `favourite_company` adds a company to a user's list of favourite staffing companies,
    and returns "True" if successful.
    
    :param company_to_favourite: The company that the user wants to add to their list of favorite
    staffing companies
    :param user_company: The parameter "user_company" is the name of the company that the user belongs
    to
    :param user: The "user" parameter represents the user who is trying to add a company to their list
    of favorite staffing companies
    :return: a string value of either "True" or "False".
    """
    try:
        comp_doc = frappe.get_doc('Company', user_company)
        check_permissions(company_to_favourite, user_company, user, comp_doc)
        if company_to_favourite in comp_doc.favourite_staffing_company_list:
            return "True"

        comp_doc.append('favourite_staffing_company_list', {'favourite_staffing_company': company_to_favourite})
        comp_doc.save(ignore_permissions=True)
        return "True"
    except Exception as e:
        frappe.log_error(str(e), "favourite_company error")
        return "False" 

@frappe.whitelist()
def sorted_favourite_companies(user_name):
    try:
        comp_doc=frappe.get_doc('Company',user_name)
        comp=[]
        for i in comp_doc.favourite_staffing_company_list:
            comp.append(i.favourite_staffing_company)
        comp.sort()
        return comp          

    except Exception as e:
        frappe.log_error(e, "company sorting")
        frappe.msgprint("Company favourites checking")
        return "False"  


@frappe.whitelist(allow_guest=False)
def unfavourite_company(company_to_favourite, user_company, user):
    """
    The function `unfavourite_company` removes a specified company from a user's list of favourite
    staffing companies.
    
    :param company_to_favourite: The company that the user wants to unfavourite
    :param user_company: The user's company that is currently logged in
    :param user: The "user" parameter represents the user who is performing the action of unfavouriting
    a company
    :return: a string value. If there is an exception, it returns "True". If there is no exception, it
    returns "False".
    """
    try:
        comp_doc = frappe.get_doc('Company', user_company)
        check_permissions(company_to_favourite, user_company, user, comp_doc)

        if len(comp_doc.favourite_staffing_company_list)!=0:
            for i in comp_doc.favourite_staffing_company_list:
                if i.favourite_staffing_company==company_to_favourite:
                    remove_row = i
                    comp_doc.remove(remove_row)
                    comp_doc.save(ignore_permissions=True) 
        return "False"
    except Exception as e:
        frappe.log_error(str(e), "unfavourite_company error")
        return "True"

@frappe.whitelist()
def checking_favourites_list(company_to_favourite,user_name):
   try:
        comp_doc=frappe.get_doc('Company',user_name)
        if len(comp_doc.favourite_staffing_company_list)!=0:
            for i in comp_doc.favourite_staffing_company_list:
                if i.favourite_staffing_company==company_to_favourite:
                    return "True"
        return "False"

   except Exception as e:
      frappe.log_error(e, "company checkig")
      frappe.msgprint("Company favourites checking")
      return "False" 

@frappe.whitelist()
def get_industries(cur_user):
    try:
        user = check_user_type(cur_user)
        sql  = """ select distinct(industry_type) from `tabJob Titles` where parent in (select assign_multiple_company from `tabCompanies Assigned` where parent="{0}") """.format(user)
        industries = frappe.db.sql(sql, as_dict=True)
        accreditation = frappe.db.sql(""" select attribute from `tabCertificate and Endorsement` """,as_dict=1)
        accreditation = [acr['attribute'] for acr in accreditation]
        data = [ind['industry_type'] for ind in industries]
        org_type, comp=frappe.db.get_value('User', {'name': frappe.session.user}, ['organization_type', 'company'])
        if org_type == 'Exclusive Hiring':
            parent_comp=frappe.db.get_value('Company', {'name': comp}, ['parent_staffing'])
            comps = f'{parent_comp}'
        else:
            comps = frappe.db.sql(""" select name from `tabCompany` where organization_type="Staffing" """,as_dict=1)
            comps = [c['name'] for c in comps]
            comps = '\n'.join(comps)
        return data,accreditation,comps
    except Exception as e:
        frappe.log_error(e, "Industries error")
        print(e)

def get_conditions(filters):
    cond1= cond2= cond3=''
    industry_data = ""
    accreditation_data = ""
    if filters.get('company',None) not in [None,""]:
        cond1 += """ and c.name  like '%{0}%' """.format(filters.get('company'))
    if filters.get('industry',None) not in [None,""]:
        industry = filters.get('industry').split(",")
        industry_data = tuple(map(str.strip,industry))
        cond3 += """ and i.industry_type in  {industry} """.format(industry=industry_data)
    if filters.get('city',None) not in [None,""]:
        cond1 += """ and c.city like '%{0}%' """.format(filters.get('city'))
    if filters.get('rating',None) not in [None,""]:
        cond1 += """ and  c.average_rating >={rating}  and (select count(*) from `tabCompany Review` r where c.name=r.staffing_company)>=10   """.format(rating=filters.get('rating'))
    if filters.get('accreditation',None) not in [None,""]:
        accreditation = filters.get('accreditation').split(",")
        accreditation_data= tuple(map(str.strip,accreditation))
        cond2 += """  and ce.certificate_type in  {accreditation} """.format(accreditation=accreditation_data)
    return cond1,cond2,cond3

def filter_location(radius,comp,data,slectedlocation=None,custom_location=None):
    try:
        filter_data = []
        if slectedlocation:
                for i in slectedlocation:
                    address = frappe.db.sql('''select address from `tabJob Site` where name = "{0}"'''.format(i))
                    
                    lat_lng_address=frappe.db.sql('''select lat, lng from `tabJob Site` where name = "{0}"'''.format(i), as_list=True)
                    get_filter_by_radius_companies(radius, data, filter_data, address, lat_lng_address)
        elif custom_location:
            address = tuple([tuple(custom_location)])
            lat,lng = get_lat_lng(custom_location[0])
            lat_lng_address = [[str(lat),str(lng)]]
            get_filter_by_radius_companies(radius, data, filter_data, address, lat_lng_address)

        else:
            address = frappe.db.sql('''select address from `tabCompany` where name = "{0}"'''.format(comp[0][0]), as_list=True)
            lat_lng_address=frappe.db.sql('''select lat, lng from `tabCompany` where name = "{0}"'''.format(comp[0][0]), as_list=True)
        
            get_filter_by_radius_companies(radius, data, filter_data, address, lat_lng_address)
        return filter_data
    except Exception as e:
        print(e)

def get_filter_by_radius_companies(radius, data, filter_data, address, lat_lng_address):
    lat, lng = 0, 0
    if lat_lng_address[0][0]!=None or lat_lng_address[0][0]!='':
        lat=lat_lng_address[0][0]
    if lat_lng_address[0][1]!=None or lat_lng_address[0][0]!='':
        lng=lat_lng_address[0][1]
    if address:
        location = tuple([float(lat), float(lng)])
        for d in data:
            try:
                staff_location = get_staff_lat_lng(d.name)
                rad = haversine(location, staff_location, unit='mi')
                if rad<=radius:
                    filter_data.append(d)
            except Exception:
                continue

def get_staff_lat_lng(name):
    staff_add_sql = frappe.db.sql('''select lat,lng from tabCompany where name = "{0}"'''.format(name), as_list=True)
    lat1, lng1 = 0, 0
    if staff_add_sql[0][0]!=None or staff_add_sql[0][0]!='':
        lat1=staff_add_sql[0][0]
    if staff_add_sql[0][1]!=None or staff_add_sql[0][0]!='':
        lng1=staff_add_sql[0][1]
    return tuple([float(lat1), float(lng1)])

def get_custom_location(address):
    lat, lng = get_lat_lng(address)
    return tuple([lat, lng])

def hiring_data(filters,user_name,comp_id,start,end):
    """
    The `hiring_data` function retrieves hiring data based on various filters and user preferences,
    including company name, address, rating, accreditation, industry type, and more.
    
    :param filters: The `filters` parameter is a JSON object that contains various filter criteria for
    the hiring data. It can include filters such as radius, location, custom location, etc
    :param user_name: The username of the user for whom the hiring data is being fetched
    :param comp_id: The `comp_id` parameter is used to specify the ID of a specific company. If a
    `comp_id` is provided, the function will return the data for that specific company
    :param start: The start parameter is used to specify the starting index of the data to be returned.
    It determines the position from which the data will be fetched from the list or database query
    result
    :param end: The "end" parameter is used to specify the number of records to return from the query
    result. It determines the maximum number of records to include in the returned data
    :return: The function `hiring_data` returns a list of dictionaries containing hiring data for
    companies.
    """
    cond1 =cond2 =cond3 = ''
    try:
        if filters:
            filters = json.loads(filters)
            cond1,cond2,cond3 = get_conditions(filters)
        sql = ''' select company from `tabUser` where email='{}' '''.format(user_name)
        user_comp = frappe.db.sql(sql, as_list=1)
        sql = """  select c.name,c.company_name,c.address,c.complete_address,c.average_rating,c.title,c.rating,count(ce.name) as count,ce.certificate_type as accreditation,i.industry_type,bs.staffing_company_name as is_blocked from `tabCompany` c 
        inner join `tabIndustry Types` i on c.name=i.parent
        left join `tabCertificate and Endorsement Details` ce 
        on c.name = ce.company 
        left join `tabBlocked Staffing Company` bs
        on c.name = bs.staffing_company_name and bs.parent="{0}"
        where c.name in (select parent from `tabIndustry Types` where parent in (select name from `tabCompany` where organization_type='Staffing' {1}) 
        and industry_type in (select industry_type  from `tabIndustry Types` where parent="{0}"  ))  {2}  {3}   group by c.name 
        """.format(user_comp[0][0],cond1,cond2,cond3)

        data = frappe.db.sql(sql, as_dict=True)

        comp_doc=frappe.get_doc('Company',user_comp[0][0])
        comp=[]
        fav_data = []
        non_fav_data = []
        comp = [ i.favourite_staffing_company for i in comp_doc.favourite_staffing_company_list ]
        for i in data:
            if i.name in comp:
                i["LikeStatus"]=True
                fav_data.append(i)             
            else:
                i["LikeStatus"]=False
                non_fav_data.append(i)
        fav_data.extend(non_fav_data)

        if filters.get('radius',None) not in [None,""]:
            radius = filters.get('radius')
            slectedlocation = filters.get('location')
            custom_location = filters.get('custom_location')
            fav_data = filter_location(radius,user_comp,fav_data,slectedlocation,custom_location)

        for d in fav_data:
            response = get_count(d.name, d.accreditation)
            d.update(dict(count=response['count'],blocked_count=response['blocked_count'],title=response['title'],rating = check_staffing_reviews(d.name), all_industries=response['all_industries'], industry_type=response['industry_type']))
                    
        if comp_id:
            fav_data=frappe.db.sql(sql, as_list=True)
            company_name=fav_data[int(comp_id)-1][0]
            return company_data(company_name)
        if (fav_data):
            fav_data = fav_data[0:int(end)]
        return fav_data
    except Exception as e:
        print(e,start)

@frappe.whitelist()
def get_count(company, accreditation):
    try:
        data = frappe.db.sql(""" select count(*) as count from `tabCertificate and Endorsement Details` where company ="{0}" """.format(company),as_dict=1)
        data1 = frappe.db.sql(""" select count(*) as blocked_count from `tabIndustry Types` where parent ="{0}" and parenttype="Company" order by industry_type desc """.format(company),as_dict=1)
        data2 = frappe.db.sql(""" select certificate_type as type from `tabCertificate and Endorsement Details` where company="{0}" and certificate_type!="{1}" order by certificate_type asc """.format(company, accreditation),as_dict=1)
        title = ['&#x2022 '+d['type']+"<br>" for d in data2]
        rating = check_staffing_reviews(company)
        data3 = frappe.db.sql(""" select industry_type from `tabIndustry Types` where parent ="{0}" and parenttype="Company" and industry_type is not NULL order by industry_type asc """.format(company),as_dict=1)
        all_industries = ['&#x2022 '+d['industry_type']+"<br>" for d in data3]
        if all_industries: all_industries.pop(0)
        result={
            'count':data[0]['count'] if len(data) else 0,
            'blocked_count': data1[0]['blocked_count'] if len(data1) else 0,
            'title': '\n'.join(title) if title else '',
            'rating': rating if float(rating)>0 else '',
            'all_industries': '\n'.join(all_industries) if all_industries else '',
            'industry_type': data3[0]['industry_type'] if data3 else ''
        }
        return  result
    except Exception as e:
        print(e)
