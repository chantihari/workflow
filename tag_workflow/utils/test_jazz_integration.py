import frappe
import unittest
from tag_workflow.utils.jazz_integration import  jazzhr_fetch_applicants,jazzhr_update_applicants
from rq import Queue, Worker
from frappe.utils.background_jobs import get_redis_conn
from rq.command import send_stop_job_command
USER ="gourav_staffing@yopmail.com"
Company = "Korecent-sf"

class TestEvents(unittest.TestCase):
    def test_jazz_integration(self):
        try:
            self.create_company()
            self.create_user()
            self.grab_new_records()
            self.update_new_records()
            self.terminate_job()
            self.remove_test_data()
        except Exception as e:
            self.remove_test_data()
            frappe.db.rollback()
            print(e)
    
    def create_company(self):
        if not frappe.db.exists('Company',Company):
            self.company = frappe.get_doc({
                'doctype':'Company',
                'company_name':Company,
                'organization_type':'Staffing',
                'default_currency':'USD',
                'title':'test',
                'primary_language':'en',
                'contact_name':'Gourav',
                'phone_no':'+917051154514',
                'email':USER,
                'accounts_receivable_contact_name':'Gourav',
                'accounts_receivable_email':USER,
                'accounts_receivable_phone_number':'+917051154514',
                'jazzhr_api_key':'CFkUAJm5TJ0fAs09LOGzXVSGbxwyi3Az'
            }).insert()

    def create_user(self):
        try:
            if not frappe.db.exists('User',USER):
                frappe.get_doc({
                'doctype':'User',
                'organization_type':'Staffing',
                'email':USER,
                'first_name':"Test",
                'last_name':'User',
                'tag_user_type':'Staffing Admin',
                'company':Company,
                'date_of_joining':frappe.utils.getdate()
                }).insert(ignore_permissions=True)
        except Exception as e:
            frappe.log_error(e,'test_user error')
    
    def grab_new_records(self):
        frappe.set_user(USER)
        if frappe.db.exists('Company',{'name':Company}):
            jazzhr_fetch_applicants(self.company.get_password('jazzhr_api_key'),Company)
    
    def update_new_records(self):
         if frappe.db.exists('Company',{'name':Company}):
            jazzhr_update_applicants(self.company.get_password('jazzhr_api_key'),Company)
    
    def terminate_job(self):
        try:
            conn = get_redis_conn()
            workers = Worker.all(conn)
            queues = Queue.all(conn)
            for queue in queues:
                for job in queue.jobs:
                    if job and job.kwargs.get('job_name') == Company:
                        job.cancel()
                        job.delete()
            

            for worker in workers:
                job = worker.get_current_job()
                if job and job.kwargs.get('job_name') == Company:
                    send_stop_job_command(conn,job.id)
                    
        except Exception as e:
            print(e)

    def remove_test_data(self):
        try:
            frappe.db.sql(""" delete from `tabUser` where name="{0}" """.format(USER))
            frappe.db.sql(""" delete from `tabCompany` where name="Korecent-sf" """)
        except Exception as e:
            frappe.log_error(e,'test_data_error')
        