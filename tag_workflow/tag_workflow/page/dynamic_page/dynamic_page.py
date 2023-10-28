import frappe
from frappe.share import add_docshare as add
from tag_workflow.tag_data import check_permissions

ORD='Job Order'


@frappe.whitelist()
def get_link1(name, userid):
   company = frappe.get_doc("Company", name)
   review=[]
   if company.organization_type == 'Staffing':
      sql= """select * from `tabCompany Review` order by creation desc"""
      data = frappe.db.sql(sql, as_dict=True)
      for i in data:
         if i['staffing_company']== name:
            review.append((i['staffing_ratings'],i['comments'],i['hiring_company']))
   elif company.organization_type == 'Hiring' or company.organization_type == 'Exclusive Hiring':
      sql= """select * from `tabHiring Company Review` order by creation desc"""
      data= frappe.db.sql(sql, as_dict=True)
      for i in data:
         if i['hiring_company']== name:
            review.append((i['rating_hiring'],i['comments'],i['staffing_company']))

   users=[]
   sql1= f'select full_name, enabled from `tabUser` where company="{name}" and enabled=1'
   data1 = frappe.db.sql(sql1, as_dict=True)
   for i in data1:
      users.append(i['full_name'])

   company_logo = create_link(company)

   return company, review, data1, company_logo
#----------showing work order history-----------#
@frappe.whitelist()
def get_link2(name,comp, comp_type, user_id):
   try:
      sql3= f"select company from `tabEmployee` where user_id='{user_id}'"
      data3 = frappe.db.sql(sql3, as_dict=True)
      if len(data3)>1:
         return data3,"exceed"
      else:
         if comp_type== "Staffing":
            sql2 = f'''SELECT
                           job_order,
                           job_category,
                           tag_status,
                           company,
                           hiring_organization,
                           GROUP_CONCAT(DISTINCT mul.select_job ORDER BY mul.select_job ASC SEPARATOR '~ ') AS select_job_array
                        FROM
                           `tabAssign Employee`
                        JOIN
                           `tabMultiple Job Titles` mul ON mul.parent = job_order
                        WHERE
                           company = '{comp}'
                           AND hiring_organization = '{name}'
                           AND tag_status = 'Approved'
                        GROUP BY
                           job_order
                        ORDER BY
                           job_order DESC'''
         elif comp_type == 'TAG' or frappe.session.user=='Administrator':
            sql2 = get_sql_query(name)
         else:
            sql2 = f'''SELECT
                           job_order,
                           job_category,
                           tag_status,
                           company,
                           hiring_organization,
                           GROUP_CONCAT(DISTINCT mul.select_job ORDER BY mul.select_job ASC SEPARATOR '~ ') AS select_job_array
                        FROM
                           `tabAssign Employee`
                        JOIN
                           `tabMultiple Job Titles` mul ON mul.parent = job_order
                        WHERE
                           company = '{name}'
                           AND hiring_organization = '{comp}'
                           AND tag_status = 'Approved'
                        GROUP BY
                           job_order
                        ORDER BY
                           job_order DESC'''
         data2= frappe.db.sql(sql2, as_dict=True)
         job=[]
         invoice=[]
         for j in data2:
            job1= j["job_order"]
            jo= frappe.get_doc("Job Order", j["job_order"])
            job.append(jo)
            
            sql4= f"select job_order, sum(total_billing_amount) as total_billing_amount from `tabSales Invoice` where job_order='{job1}'"
            data4 = frappe.db.sql(sql4, as_dict=True)
            j['multiple_titles'] = j['select_job_array'].split("~")
            for i in data4:
               invoice.append(i)
               
         return job, data2, invoice
   except Exception as e:
      print(e)
      
@frappe.whitelist()
def get_sql_query(name):
   comp_type=frappe.db.get_value('Company', {'name':name},['organization_type'])
   if comp_type == 'Staffing':
      return f'''SELECT
                     job_order,
                     job_category,
                     tag_status,
                     company,
                     hiring_organization,
                     GROUP_CONCAT(DISTINCT mul.select_job ORDER BY mul.select_job ASC SEPARATOR '~ ') AS select_job_array
                  FROM
                     `tabAssign Employee`
                  JOIN
                     `tabMultiple Job Titles` mul ON mul.parent = job_order
                  WHERE
                     company = '{name}'
                     AND tag_status = 'Approved'
                  GROUP BY
                     job_order
                  ORDER BY
                     job_order DESC'''
   else:
      return f'''SELECT
                     job_order,
                     job_category,
                     tag_status,
                     company,
                     hiring_organization,
                     GROUP_CONCAT(DISTINCT mul.select_job ORDER BY mul.select_job ASC SEPARATOR '~ ') AS select_job_array
                  FROM
                     `tabAssign Employee`
                  JOIN
                     `tabMultiple Job Titles` mul ON mul.parent = job_order
                  WHERE
                     hiring_organization = '{name}'
                     AND tag_status = 'Approved'
                  GROUP BY
                     job_order
                  ORDER BY
                     job_order DESC'''
#---------------------#

   
@frappe.whitelist()
def get_link3(name,comp, comp_type):
   if comp_type== "Staffing":
      company1= comp
      company2= name

   else:
      company1= name
      company2= comp
   

   sql2 = f'''SELECT
               job_order,
               job_category,
               tag_status,
               company,
               hiring_organization,
               GROUP_CONCAT(DISTINCT mul.select_job ORDER BY mul.select_job ASC SEPARATOR '~ ') AS select_job_array
            FROM
               `tabAssign Employee`
            JOIN
               `tabMultiple Job Titles` mul ON mul.parent = job_order
            WHERE
               company = '{company1}'
               AND hiring_organization = '{company2}'
               AND tag_status = 'Approved'
            GROUP BY
               job_order
            ORDER BY
               job_order DESC'''
   data2= frappe.db.sql(sql2, as_dict=True)
   job=[]
   invoice=[]
   for j in data2:
      job1= j["job_order"]
      jo= frappe.get_doc("Job Order", j["job_order"])
      job.append(jo)
     
      sql4= f"select job_order, sum(total_billing_amount) as total_billing_amount from `tabSales Invoice` where job_order='{job1}'"
      data4 = frappe.db.sql(sql4, as_dict=True)  
      j['multiple_titles'] = j['select_job_array'].split("~")
      for i in data4:
         invoice.append(i)

   return job, data2, invoice

@frappe.whitelist(allow_guest=False)
def block_company(company_blocked, blocked_by, user):
   """
   The function `block_company` is used to block a company by enqueueing a job to be executed
   asynchronously.
   
   :param company_blocked: The parameter "company_blocked" represents the company that is being blocked
   :param blocked_by: The parameter "blocked_by" represents the user who is blocking the company
   :param user: The "user" parameter represents the user who is trying to block the company
   :return: either 1 or False.
   """
   try:
      comp_doc=frappe.get_doc('Company',blocked_by)
      check_permissions(company_blocked, blocked_by, user, comp_doc)
      frappe.enqueue("tag_workflow.tag_workflow.page.dynamic_page.dynamic_page.company_to_blocked", queue='long', job_name='Blocking Company', is_async=True,blocked_by=blocked_by,company_blocked=company_blocked)
      return 1
   except Exception as e:
      frappe.log_error(e, "block_company error")
      frappe.msgprint("Error in blocking the company")
      return False

def company_to_blocked(blocked_by, company_blocked):
   """
   The function `company_to_blocked` adds a company to the blocked list of another company and then
   calls the `delete_order_unclaimed` function.
   
   :param blocked_by: The parameter "blocked_by" is the name of the company that is blocking another
   company
   :param company_blocked: The parameter "company_blocked" is the name of the company that is being
   blocked by another company
   """
   try:
      comp_doc=frappe.get_doc('Company',blocked_by)
      comp_doc.append('blocked_staff_companies_list',{'staffing_company_name':company_blocked})
      comp_doc.save(ignore_permissions = True)
      delete_order_unclaimed(blocked_by,company_blocked)
   except Exception as e:
      frappe.log_error(e, "company_to_blocked error")

def delete_order_unclaimed(blocked_by,company_blocked):
   """
   The function `delete_order_unclaimed` deletes job orders that are not completed and are not claimed by a specific company.
   
   :param blocked_by: The parameter "blocked_by" represents the company that is blocking the orders
   :param company_blocked: The parameter "company_blocked" represents the company that is blocked
   """
   try:
      job_orders=f'select name,claim from `tabJob Order` where order_status!="Completed" and company="{blocked_by}" '
      my_orders=frappe.db.sql(job_orders,as_dict=1)
      if(len(my_orders)>0):
         for i in my_orders:
            if (i.claim and company_blocked not in i.claim) or (not i.claim):
               user_name=f'select name from `tabUser` where company="{company_blocked}"'
               user_data=frappe.db.sql(user_name,as_list=0)
               for j in user_data:
                  del_data=f'''DELETE FROM `tabDocShare` where share_doctype='Job Order' and share_name="{i.name}" and user="{j[0]}"'''
                  del_notification=f''' DELETE from `tabNotification Log` where document_name="{i.name}" and for_user="{j[0]}" '''
                  frappe.db.sql(del_data)
                  frappe.db.sql(del_notification)
                  frappe.db.commit()
   except Exception as e:
      frappe.log_error(e, "delete_order_unclaimed error")

@frappe.whitelist(allow_guest=False)
def unblock_company(company_blocked,blocked_by,user):
   """
   The function `unblock_company` is used to unblock a company that has been blocked by a user, and it
   performs various checks and enqueues a job to handle the unblocking process.
   
   :param company_blocked: The parameter "company_blocked" represents the company that is currently
   blocked and needs to be unblocked
   :param blocked_by: The "blocked_by" parameter is the name of the user or company that has blocked
   the company
   :param user: The "user" parameter represents the user who is trying to unblock the company
   :return: either 1 or False.
   """
   try:
      comp_doc=frappe.get_doc('Company', blocked_by)
      check_permissions(company_blocked, blocked_by, user, comp_doc)
      frappe.enqueue("tag_workflow.tag_workflow.page.dynamic_page.dynamic_page.company_to_unblocked", queue='long', job_name='Blocking Company', is_async=True,blocked_by=blocked_by,company_blocked=company_blocked)
      return 1
   except Exception as e:
      frappe.log_error(e, "unblock_company error")
      frappe.msgprint("Error in unblocking the company")
      return False

def company_to_unblocked(blocked_by, company_blocked):
   """
   The function `company_to_unblocked` unblocks a company that was previously blocked.
   
   :param blocked_by: The parameter "blocked_by" represents the name of the company that is blocking
   other companies
   :param company_blocked: The parameter "company_blocked" represents the name of the company that is
   currently blocked
   """
   try:
      comp_doc=frappe.get_doc('Company',blocked_by)
      unclaimed_noresume_by_company=[]
      if len(comp_doc.blocked_staff_companies_list)!=0:
         for i in comp_doc.blocked_staff_companies_list:
            if i.staffing_company_name==company_blocked:
               remove_row = i
         comp_doc.remove(remove_row)
         comp_doc.save(ignore_permissions=True)     
      unclaimed_resume_by_comp=f'select name from `tabJob Order` where (claim not like "%{company_blocked}%" or claim is Null) and order_status!="Completed" and company="{blocked_by}" and resumes_required=1 and total_workers_filled!=total_no_of_workers'
      my_aval_claims=frappe.db.sql(unclaimed_resume_by_comp,as_list=1)
      my_claims=check_avail(blocked_by,company_blocked,unclaimed_noresume_by_company)
      z=[]
      if(len(my_aval_claims)>0):
         for i in my_aval_claims:
            z.append(i[0])
      if(len(my_claims)>0):
         for i in my_claims:
            z.append(i)
      my_job_order= list(set(z)) 
      share_job_order(my_job_order,company_blocked)
   except Exception as e:
      frappe.log_error(e, "company_to_unblocked error")

@frappe.whitelist()
def checking_blocked_list(company_blocked,blocked_by):
   try:
      comp_doc=frappe.get_doc('Company',blocked_by)
      if len(comp_doc.blocked_staff_companies_list)!=0:
         for i in comp_doc.blocked_staff_companies_list:
            if i.staffing_company_name==company_blocked:
               break
         else:
            return 1
      else:
         return 1

   except Exception as e:
      frappe.log_error(e, "company checkig")
      frappe.msgprint("Company Blocked checking")
      return False  

def check_avail(blocked_by,company_blocked,unclaimed_noresume_by_company):
   try:
      unclaimed_noresume_by_comp=f'select name from `tabJob Order` where (claim not like "%{company_blocked}%" or claim is Null) and order_status!="Completed" and company="{blocked_by}" and resumes_required=0'
      my_unaval_claims=frappe.db.sql(unclaimed_noresume_by_comp,as_list=1)
      for i in my_unaval_claims:
         data=frappe.get_doc(ORD,i[0])
         claims=f'select sum(approved_no_of_workers) from `tabClaim Order` where job_order="{data.name}"'
         data1=frappe.db.sql(claims,as_list=1)
         if(data1[0][0]!=None):
            if int(data.no_of_workers)-int(data1[0][0])!=0:
                  unclaimed_noresume_by_company.append(data.name)
         else:
            unclaimed_noresume_by_company.append(data.name)
      return unclaimed_noresume_by_company
   except Exception as e:
      frappe.log_error(e, "Checking order")
      frappe.msgprint("Company unBlocked order checking")

def share_job_order(my_job_order,company_blocked):
   try:
      sql = f''' select email from `tabUser` where organization_type='staffing' and company ="{company_blocked}" '''
      user_list=frappe.db.sql(sql, as_list=1)
      l = [l[0] for l in user_list]
      for user in l:
         for job in my_job_order:
            add(ORD, job, user, read=1, write = 0, share = 0, everyone = 0)
   except Exception as e:
      frappe.log_error(e, "company unblock order sharing")
      frappe.msgprint("company unblock order sharing")

def create_link(company):
   if company.upload_company_logo:
      logo = frappe.get_site_config().env_url + company.upload_company_logo
      return logo
   else:
      return "/assets/tag_workflow/images/default_logo.png"

@frappe.whitelist()
def get_accreditations(company):
   sql = '''select name,attached_certificate, sequence,certificate_type from `tabCertificate and Endorsement Details` where company = "{0}" order by sequence'''.format(company)
   records = frappe.db.sql(sql,as_dict =True)
   return records