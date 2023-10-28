import frappe
import unittest
import json
import datetime
from tag_workflow.controllers.master_controller import check_employee
from tag_workflow.tag_data import claim_order_insert
from frappe.utils.data import getdate
from tag_workflow.tag_data import staff_email_notification,receive_hire_notification
from tag_workflow.tag_workflow.doctype.add_timesheet.add_timesheet import update_timesheet
from tag_workflow.utils.timesheet import notify_email,company_rating,hiring_company_rating,get_timesheet_data,check_employee_editable,approval_notification,denied_notification,staffing_emp_rating,timesheet_dispute_comment_box,submit_staff_timesheet,checking_same_values_timesheet
Hire_Company = "Genpact Hire Test5"
Staff_Comp="Genpact Staff Test5"
Hire_Admin="genpact_test_hiring5@yopail.com"
Staff_Admin="genpact_test_staffing5@yopmail.com"
inds_type='Administrative/Clerical'
job_title="Auditor"
job_site="New York, NY 10016, USA"
state='New York'
city='New York'
zip='10016'
emp="Genpact Staffing Emp1"
jobOrder='Job Order'
files="/files/testing doc.pdf"
asnEmp='Assign Employee'
excComp='Genpact Exc Comp Test5'
exc_admin='genpact_exc_admin_test5@yopmail.com'
exc_job_site="New York, NY 10017, USA"
jbSite='Job Site'
rating='{"Rating":4,"Comment":"Good"}'
usrPerm='User Permission'

class TestTimesheet(unittest.TestCase):
    ## unit test 1 -- send timesheet for approval -- function called from hooks when timesheet created-send_timesheet_for_approval
    def test_send_timesheet_for_approval(self):
        self.create_basic_data()
        job_order=self.create_job_order(Hire_Company,getdate())
        self.assign_emp(job_order,Hire_Company)
        self.create_timesheet(job_order,0) 
        self.delete_data(job_order)      


    ## unit test 2---get_timesheet_data---exist_data
    def test_get_timesheet_data(self):
        self.create_basic_data()
        job_order=self.create_job_order(Hire_Company,getdate()+datetime.timedelta(days=1))
        self.assign_emp(job_order,Hire_Company)
        frappe.set_user(Hire_Admin)
        res=get_timesheet_data(job_order, Hire_Admin, 'Hiring',getdate(),timesheets_to_update=None)
        self.assertEqual(res[0]['employee_name'],'emp1 emp1')
        self.delete_data(job_order)      

     


    ## unit test 3-- notify_email- dnr_notification,unsatisfied_organization,show_satisfactory_notification,employee_unsatisfactory,remove_job_title,removing_unsatisfied_employee,no_show,employee_no_show,removing_no_show,no_show_org,job_category_remove,removing_dnr_employee,employee_dnr,do_not_return
    def test_notify_email(self):
        self.create_basic_data()
        job_order=self.create_job_order(Hire_Company,getdate()+datetime.timedelta(days=2))
        self.assign_emp(job_order,Hire_Company)
        self.create_timesheet(job_order,0)
        doc=frappe.db.sql('select name,job_order_detail,employee,company,employee_name,creation,employee_company from `tabTimesheet` where company="{0}" and employee_company="{1}" and job_order_detail="{2}"'.format(Hire_Company,Staff_Comp,job_order),as_dict=1)
        notify_email(doc[0].job_order_detail,doc[0].employee,1,"No Show",doc[0].company,doc[0].employee_name,doc[0].creation,doc[0].employee_company,doc[0].name)
        self.delete_data(job_order)      


    ## unit test 4-- deny notification
    def test_denied_notification(self):
        self.create_basic_data()
        job_order=self.create_job_order(Hire_Company,getdate()+datetime.timedelta(days=3))
        self.assign_emp(job_order,Hire_Company)
        self.create_timesheet(job_order,0)
        doc=frappe.db.sql('select name,job_order_detail,company,employee_company from `tabTimesheet` where company="{0}" and employee_company="{1}" and job_order_detail="{2}" and workflow_state="Approval Request"'.format(Hire_Company,Staff_Comp,job_order),as_dict=1)
        frappe.set_user(Staff_Admin)
        frappe.db.set_value('Timesheet',doc[0].name,'workflow_state',"Denied")
        frappe.db.set_value('Timesheet',doc[0].name,'status',"Denied")
        denied_notification(doc[0].job_order_detail,doc[0].company,doc[0].employee_company,doc[0].name)        
        self.delete_data(job_order)      
    

    ## unit test 5-- check_employee_editable
    def test_check_employee_editable(self):
        self.create_basic_data()
        job_order=self.create_job_order(Hire_Company,getdate()+datetime.timedelta(days=4))
        self.assign_emp(job_order,Hire_Company)
        self.create_timesheet(job_order,0)
        frappe.set_user(Staff_Admin)
        ass_doc=frappe.db.get_value(asnEmp,{'job_order':job_order,'company':Staff_Comp},'name')
        employee_records_val=frappe.get_doc(asnEmp,ass_doc)
        date_create=employee_records_val.creation
        data=check_employee_editable(job_order,employee_records_val.name,str(date_create)) 
        self.assertEqual(data,0)   
        self.delete_data(job_order)      

    ## unit test 6-- company_rating
    def test_company_rating(self):
        self.create_basic_data()
        job_order=self.create_job_order(Hire_Company,getdate()+datetime.timedelta(days=5))
        self.assign_emp(job_order,Hire_Company)
        comp_rev=frappe.db.get_list('Company Review', filters={'name':Staff_Comp+'-'+job_order}, fields={'name'})
        if not comp_rev:
            self.create_timesheet(job_order,0)
            data=company_rating(Hire_Company,Staff_Comp,rating,job_order)
            self.assertEqual(data,1)
        self.delete_data(job_order)      
           

    ## unit test 7-- approval_notification
    def test_approval_notification(self):
        self.create_basic_data()
        job_order=self.create_job_order(Hire_Company,getdate()+datetime.timedelta(days=6))
        self.assign_emp(job_order,Hire_Company)
        self.create_timesheet(job_order,0)
        doc=frappe.db.sql('select name,job_order_detail,company,employee_company,modified from `tabTimesheet` where company="{0}" and employee_company="{1}" and job_order_detail="{2}" and workflow_state="Approval Request"'.format(Hire_Company,Staff_Comp,job_order),as_dict=1)
        if(doc):
            frappe.set_user(Staff_Admin)
            frappe.db.set_value('Timesheet',doc[0].name,'workflow_state',"Approved")
            frappe.db.set_value('Timesheet',doc[0].name,'status',"Submitted")
            frappe.db.set_value('Timesheet',doc[0].name,'docstatus',1)
            approval_notification(job_order=doc[0].job_order_detail, staffing_company=doc[0].employee_company, date=None, hiring_company=doc[0].company, timesheet_name=doc[0].name, timesheet_approved_time=doc[0].modified, current_time=frappe.utils.now())
            frappe.db.set_value('Timesheet',doc[0].name,"docstatus",2)
            frappe.db.set_value('Timesheet',doc[0].name,'status',"Cancelled")  
            self.delete_data(job_order,doc[0].name)      
        self.delete_data(job_order)


    ## unit test 8-- hiring_company_rating
    def test_hiring_company_rating(self):
        self.create_basic_data()
        job_order=self.create_job_order(Hire_Company,getdate()+datetime.timedelta(days=7))
        self.assign_emp(job_order,Hire_Company)
        self.create_timesheet(job_order,0)
        doc=frappe.db.sql('select name,job_order_detail,company,employee_company,modified from `tabTimesheet` where company="{0}" and employee_company="{1}" and job_order_detail="{2}" and workflow_state="Approval Request"'.format(Hire_Company,Staff_Comp,job_order),as_dict=1)
        if(doc):
            frappe.set_user(Staff_Admin)
            comp_rev=frappe.db.get_list('Hiring Company Review', filters={'name':Staff_Comp+'-'+job_order}, fields={'name'})
            if not comp_rev:
                frappe.db.set_value('Timesheet',doc[0].name,'workflow_state',"Approved")
                frappe.db.set_value('Timesheet',doc[0].name,'status',"Submitted")
                frappe.db.set_value('Timesheet',doc[0].name,'docstatus',1)
                frappe.set_user(Staff_Admin)
                data=hiring_company_rating(hiring_company=doc[0].company,staffing_company=doc[0].employee_company,ratings=rating,job_order=doc[0].job_order_detail,timesheet=doc[0].name)
                self.assertEqual(data,'success')
                frappe.db.set_value('Timesheet',doc[0].name,"docstatus",2)
                frappe.db.set_value('Timesheet',doc[0].name,'status',"Cancelled")   
            self.delete_data(doc[0].job_order_detail,doc[0].name)

    ## unit test 9--staffing_emp_rating
    def test_staffing_emp_rating(self):
        self.create_basic_data()
        job_order=self.create_job_order(Hire_Company,getdate()+datetime.timedelta(days=8))
        self.assign_emp(job_order,Hire_Company)
        self.create_timesheet(job_order,0)
        doc=frappe.db.sql('select name,job_order_detail,company,employee_company,modified,employee_name,employee from `tabTimesheet` where company="{0}" and employee_company="{1}" and job_order_detail="{2}" and workflow_state="Approval Request"'.format(Hire_Company,Staff_Comp,job_order),as_dict=1)
        frappe.set_user(Staff_Admin)
        frappe.db.set_value('Timesheet',doc[0].name,'workflow_state',"Approved")
        frappe.db.set_value('Timesheet',doc[0].name,'status',"Submitted")
        frappe.db.set_value('Timesheet',doc[0].name,'docstatus',1)
        frappe.set_user(Hire_Admin)
        data=staffing_emp_rating(doc[0].employee_name,doc[0].employee,0,1,doc[0].job_order_detail,'Not Good',doc[0].name)
        self.assertEqual(data,True)
        frappe.db.set_value('Timesheet',doc[0].name,"docstatus",2)
        frappe.db.set_value('Timesheet',doc[0].name,'status',"Cancelled")   
        self.delete_data(doc[0].job_order_detail,doc[0].name)    

    ## unit test 10-- timesheet_dispute_comment_box 
    def test_timesheet_dispute_comment_box(self):
        self.create_basic_data()
        job_order=self.create_job_order(Hire_Company,getdate()+datetime.timedelta(days=9))
        self.assign_emp(job_order,Hire_Company)
        self.create_timesheet(job_order,0)
        doc=frappe.db.sql('select name,job_order_detail,company,employee_company from `tabTimesheet` where company="{0}" and employee_company="{1}" and workflow_state="Approval Request"'.format(Hire_Company,Staff_Comp),as_dict=1)
        frappe.set_user(Staff_Admin)
        frappe.db.set_value('Timesheet',doc[0].name,'workflow_state',"Denied")
        frappe.db.set_value('Timesheet',doc[0].name,'status',"Denied")
        denied_notification(doc[0].job_order_detail,doc[0].company,doc[0].employee_company,doc[0].name)
        comment='{"Comment":"Wrong Time added"}'
        dat=timesheet_dispute_comment_box(comment,doc[0].name)
        self.assertEqual(dat,True)
        self.delete_data(doc[0].job_order_detail,doc[0].name)
         

    ## unit test 11-- submit_staff_timesheet
    def test_submit_staff_timesheet(self):
        self.create_industry()
        self.create_job_title()
        self.create_staffing_comp()
        self.create_job_site_exc()
        self.create_exc_hiring_comp()
        job_order=self.create_job_order(excComp,getdate()+datetime.timedelta(days=10))
        self.assign_emp(job_order,excComp)
        self.create_timesheet(job_order,'1',exc_admin)
        res=self.submit_timesheets(job_order)
        self.assertEqual(res,'success')
        self.delete_data(job_order)      
   

    ## unit test 12-- checking_same_values_timesheet
    def test_checking_same_values_timesheet(self):
        self.create_industry()
        self.create_job_title()
        self.create_staffing_comp()
        self.create_job_site_exc()
        self.create_exc_hiring_comp()
        job_order=self.create_job_order(Hire_Company,getdate()+datetime.timedelta(days=11))
        self.assign_emp(job_order,Hire_Company)
        self.create_timesheet(job_order,0)
        self.check_same_data(job_order)
        self.delete_data(job_order)    

    def create_basic_data(self):
        self.create_industry()
        self.create_job_title()
        self.create_job_site()
        self.create_hiring_comp()
        self.create_staffing_comp()
    def create_industry(self):
        if not frappe.db.exists('Industry Type',inds_type):
            frappe.get_doc({
                'doctype':'Industry Type',
                'industry':inds_type
            }).insert()
    def create_job_title(self):
        if not frappe.db.exists('Item',job_title):
            frappe.get_doc({
                'doctype':'Item',
                'industry':inds_type,
                'job_titless':job_title,
                'rate':20,
                'descriptions':job_title,
                "item_code": job_title,
		        'item_group':'All Item Groups',
		        'stock_uom':'Nos'
            }).insert()
    def create_job_site(self):
        if not frappe.db.exists(jbSite,job_site):
            if not frappe.db.exists('Company',Hire_Company):
                self.create_hiring_comp()
            frappe.get_doc({
                'doctype':jbSite,
                'job_site_name':job_site,
                'job_site':job_site,
                'company':Hire_Company,
                'manually_enter':1,
                'state':state,
                'city':city,
                'zip':zip,
                'address':job_site,
                "job_titles":[{
                    "industry_type":inds_type,
                    "job_titles":job_title,
                    "bill_rate":20,
                    "description":job_title
                }]
            }).insert()
    def create_hiring_comp(self):
        if not frappe.db.exists('Company',Hire_Company):
            frappe.get_doc({
                'doctype':'Company',
                'company_name':Hire_Company,
                "organization_type":'Hiring',
                "accounts_payable_contact_name":Hire_Admin,
                "fein":"909090909",
                "title":'Hire',
                "accounts_payable_email":Hire_Admin,
                "accounts_payable_phone_number":'9090909090',
                "contact_name":Hire_Admin,
                "phone_no":'9090909090',
                "email":Hire_Admin,
                "enter_manually":1,
                "address":job_site,
                "state":state,
                "city":city,
                "zip":zip,
                "default_currency":'USD',
                "primary_language":'en',
                "industry_type":[{
                    "industry_type":inds_type
                }],
                "job_titles":[{
                    "industry_type":inds_type,
                    "job_titles":job_title,
                    "wages":20,
                    "description":job_title
                }]
            }).insert()
            user_exists=frappe.db.get_value('User',{'name':Hire_Admin},'name')
            if not user_exists:
                self.create_user(role="Hiring Admin",org_type='Hiring',email=Hire_Admin,comp_name=Hire_Company)


    def create_staffing_comp(self):
        if not frappe.db.exists('Company',Staff_Comp):
            frappe.get_doc({
                'doctype':'Company',
                'company_name':Staff_Comp,
                "organization_type":'Staffing',
                "accounts_payable_contact_name":Staff_Admin,
                "fein":"909090909",
                "title":'Hire',
                "accounts_payable_email":Staff_Admin,
                "accounts_payable_phone_number":'9090909090',
                "contact_name":Staff_Admin,
                "phone_no":'9090909090',
                "email":Staff_Admin,
                "enter_manually":1,
                "address":job_site,
                "state":state,
                "city":city,
                "zip":zip,
                "default_currency":'USD',
                "primary_language":'en',
                "industry_type":[{
                    "industry_type":inds_type
                }],
               "accounts_receivable_rep_email":Staff_Admin,
                "accounts_receivable_name":Staff_Admin,
                "accounts_receivable_phone_number":"9876543211",
                "cert_of_insurance":files,
                "safety_manual":files,
                "w9":files
            }).insert()
            user_exists=frappe.db.get_value('User',{'name':Staff_Admin},'name')
            if not user_exists:
                self.create_user(role="Staffing Admin",org_type='Staffing',email=Staff_Admin,comp_name=Staff_Comp)

    def create_user(self,role,org_type,email,comp_name):
        user_doc=frappe.new_doc("User")
        user_doc.organization_type=org_type
        user_doc.role_profile_name=role
        user_doc.module_profile=org_type
        user_doc.email=email
        user_doc.first_name='kanchan'
        user_doc.last_name='sharma'
        user_doc.enabled=1
        user_doc.company=comp_name
        user_doc.date_of_joining='2022-11-04'
        user_doc.tag_user_type=role
        user_doc.save()
        user=frappe.get_doc('User',email)
        check_employee(user.name, user.first_name, user.company, user.last_name, gender=None, date_of_birth=None, date_of_joining=None, organization_type=None)
    def create_job_order(self,hire_company,job_date):
        frappe.set_user('Administrator')
        job_order = frappe.new_doc(jobOrder)
        job_order.company = hire_company
        job_order.select_job = job_title
        job_order.from_date = job_date
        job_order.job_start_time = '09:59:00.000000'
        job_order.availability ='Everyday'
        job_order.rate = 20
        job_order.to_date = job_date
        job_order.category = inds_type
        job_order.job_site = job_site
        job_order.no_of_workers = 4
        job_order.e_signature_full_name = 'kanchan'
        job_order.agree_to_contract = 1
        job_order.estimated_hours_per_day=4
        job_order.staff_company=Staff_Comp
        job_order.per_hour=10
        job_order.flat_rate=10
        job_order.save() 
        staff_email_notification(hire_company,job_order.name,job_title,Staff_Comp)
        return job_order.name
    def assign_emp(self,job_order,hire_company):
        job_order=frappe.get_doc(jobOrder,job_order)
        claim_order_insert('10', job_order.company,job_order.name,job_order.no_of_workers,job_order.e_signature_full_name,job_order.staff_company)
        self.assign_employee(job_order,hire_company)
    def assign_employee(self,job_order,hire_company):
        self.create_temp_employee()
        employee_records=frappe.db.get_value(asnEmp,{'job_order':job_order},'job_order')
        emp=frappe.db.sql('select name,employee_name from `tabEmployee` where company="{0}" and user_id is null'.format(Staff_Comp),as_dict=1)
        if not employee_records:
            a_emp = frappe.new_doc("Assign Employee")
            a_emp.job_order = job_order.name
            a_emp.no_of_employee_required = job_order.no_of_workers
            a_emp.job_category = job_order.select_job
            a_emp.claims_approved = job_order.no_of_workers
            a_emp.hiring_organization = hire_company
            a_emp.company = Staff_Comp
            a_emp.job_location = job_order.job_site
            a_emp.e_signature_full_name = job_order.e_signature_full_name
            a_emp.append("employee_details",{
                "company": Staff_Comp,
                "employee": emp[0].name,
                "employee_name": emp[0].employee_name,
                "pay_rate": 5
            })
            a_emp.save()
            assi_emp=frappe.get_doc(asnEmp,a_emp.name)
            frappe.set_user(Staff_Admin)
            receive_hire_notification(user=Staff_Admin, company_type="Staffing", hiring_org=hire_company, job_order=job_order.name, staffing_org=Staff_Comp, emp_detail=assi_emp.employee_details, doc_name=assi_emp.name,worker_fill=1)
            frappe.db.set_value(jobOrder, job_order.name, "worker_filled", 1)
    def create_temp_employee(self):
        records_file = open('assets/tag_workflow/js/test_record/test_temp_emps.json')
        test_records = json.load(records_file)
        for employee in test_records:
            employee_records=frappe.db.get_value('Employee',{'email':employee['email'],'company':Staff_Comp},'email')
            if not employee_records:
                emp = frappe.new_doc("Employee")
                emp.first_name = employee["first_name"]
                emp.last_name = employee["last_name"]
                emp.email = employee["email"]
                emp.status = employee["status"]
                emp.company = Staff_Comp
                emp.owner=Staff_Admin
                emp.date_of_birth = employee["date_of_birth"]
                emp.save()
    def create_timesheet(self,job_order,save,hire_admin=Hire_Admin):
        job_order=frappe.get_doc(jobOrder,job_order)
        frappe.set_user(hire_admin)
        employee_records=frappe.db.get_value(asnEmp,{'job_order':job_order.name,'company':Staff_Comp},'name')
        employee_records=frappe.get_doc(asnEmp,employee_records)
        emp=employee_records.employee_details[0].employee
        emp_name=employee_records.employee_details[0].employee_name
        items=[{"docstatus": 0, "doctype": "Timesheet Item", "name": "new-timesheet-item-1", "__islocal": 1, "__unsaved": 1, "owner": hire_admin, "company": Staff_Comp, "hours": 1, "amount": 20, "status": "", "working_hours": 1, "overtime_hours": 0, "parent": "Add Timesheet", "parentfield": "items", "parenttype": "Add Timesheet", "idx": 1, "employee": emp, "employee_name": emp_name, "from_time": "00:00:00", "to_time": "01:00:00", "break_from": "", "break_to": "", "timesheet_value": "", "overtime_rate": 0}]
        date=job_order.from_date
        date=str(date)
        update_timesheet(user=frappe.session.user, company_type='Hiring', items=str(items), cur_selected='[]', job_order=job_order.name, date=date, from_time="00:00:00", to_time="01:00:00", break_from_time=None, break_to_time=None,save=save)
    def create_job_site_exc(self):
        if not frappe.db.exists(jbSite,exc_job_site):
            if not frappe.db.exists('Company',excComp):
                self.create_exc_hiring_comp()
            frappe.get_doc({
                'doctype':jbSite,
                'job_site_name':exc_job_site,
                'job_site':exc_job_site,
                'company':excComp,
                'manually_enter':1,
                'state':state,
                'city':city,
                'zip':'10017',
                'address':exc_job_site,
                "job_titles":[{
                    "industry_type":inds_type,
                    "job_titles":job_title,
                    "bill_rate":20,
                    "description":job_title
                }]
            }).insert()
    def create_exc_hiring_comp(self):
        if not frappe.db.exists('Company',excComp):
            frappe.get_doc({
                'doctype':'Company',
                'company_name':excComp,
                "organization_type":'Exclusive Hiring',
                "parent_staffing": Staff_Comp,
                "accounts_payable_contact_name":exc_admin,
                "fein":"909090909",
                "title":'Hire',
                "accounts_payable_email":exc_admin,
                "accounts_payable_phone_number":'9090909090',
                "contact_name":exc_admin,
                "phone_no":'9090909090',
                "email":exc_admin,
                "enter_manually":1,
                "address":job_site,
                "state":state,
                "city":city,
                "zip":zip,
                "default_currency":'USD',
                "primary_language":'en',
                "industry_type":[{
                    "industry_type":inds_type
                }],
                "job_titles":[{
                    "industry_type":inds_type,
                    "job_titles":job_title,
                    "wages":20,
                    "description":job_title
                }]
            }).insert()
            user_exists=frappe.db.get_value('User',{'name':exc_admin},'name')
            if not user_exists:
                self.create_user(role="Hiring Admin",org_type='Hiring',email=exc_admin,comp_name=excComp)
    def submit_timesheets(self,job_order):
        doc=frappe.db.get_value('Timesheet',{'job_order_detail':job_order},'name')
        if(doc):
            doc=frappe.get_doc('Timesheet',doc)
            res=submit_staff_timesheet(doc.job_order_detail,doc.date_of_timesheet,doc.employee,doc.name)
            frappe.db.set_value('Timesheet',doc.name,"docstatus",2)
            frappe.db.set_value('Timesheet',doc.name,'status',"Cancelled") 
            return res
    def check_same_data(self,job_order):
        doc=frappe.db.get_value('Timesheet',{'job_order_detail':job_order},'name')
        if(doc):
            doc=frappe.get_doc('Timesheet',doc)
            data_select=[doc.name]
            data=checking_same_values_timesheet(str(data_select))
            self.assertEqual(data,'Different Status')
    def delete_data(self,job_order,timesheet_name=None):
        frappe.set_user('Administrator')
        timesheet=frappe.db.get_list('Timesheet', filters={'job_order_detail':job_order}, fields={'name','docstatus'})
        if timesheet_name:
            user_permission=frappe.db.get_list(usrPerm,filters={'allow':'Timesheet','for_value':timesheet_name},fields={'name'})
            for user in user_permission:
                frappe.delete_doc(usrPerm,user.name)
            frappe.db.sql('delete from `tabTimesheet` where name = "{0}" '.format(timesheet_name))
        if timesheet:
            for order in timesheet:  
                user_permission=frappe.db.get_list(usrPerm,filters={'allow':'Timesheet','for_value':order.name},fields={'name'})
                for user in user_permission:
                    frappe.delete_doc(usrPerm,user.name)
                frappe.delete_doc('Timesheet',order.name)
        assign_emp=frappe.db.get_list('Assign Employee', filters={'job_order':job_order}, fields={'name'})
        if assign_emp:
            for order in assign_emp:
                frappe.delete_doc("Assign Employee",order.name)
        claim_orders= frappe.db.get_list('Claim Order', filters={'job_order':job_order}, fields={'name'})
        if claim_orders:
            for order in claim_orders:
                frappe.delete_doc('Claim Order',order.name)
        frappe.delete_doc(jobOrder,job_order)
