import frappe
import unittest
import json
from tag_workflow.utils.employee import delete_bulk_employee, delete_data

job_order_data_query = 'select name from `tabJob Order` where company="My Test Hiring Company"'
employee_get_query = 'select name from `tabEmployee` where email="emp1@gmail.com"'

class TestTagData(unittest.TestCase):
    #function to create company
    def create_company(self):
            records_file = open(r'../apps/tag_workflow/tag_workflow/public/js/test_records/test_company_records.json')
            test_records = json.load(records_file)
            for record in test_records:
                company_exists=frappe.db.get_value('Company',{'company_name':record['company_name']},'name')
                if not company_exists:
                    company_doc = frappe.new_doc("Company")
                    company_doc.company_name=record['company_name']
                    company_doc.organization_type=record['organization_type']
                    company_doc.accounts_payable_contact_name=record['accounts_payable_contact_name']
                    company_doc.fein=record['fein']
                    company_doc.title=record['title']
                    company_doc.accounts_payable_email=record['accounts_payable_email']
                    company_doc.accounts_payable_phone_number=record['accounts_payable_phone_number']
                    company_doc.contact_name=record['contact_name']
                    company_doc.phone_no=record['phone_no']
                    company_doc.email=record['email']
                    company_doc.enter_manually=record['enter_manually']
                    company_doc.address=record['address']
                    company_doc.state=record['state']
                    company_doc.city=record['city']
                    company_doc.zip=record['zip']
                    company_doc.default_currency=record['default_currency']
                    company_doc.primary_language=record['primary_language']
                    for industry in record['industry_type']:
                        company_doc.append('industry_type',{'industry_type':industry['industry_type']})
                    company_doc.save()

    #function to create employee
    def create_employee(self):
        records_file = open(r'../apps/tag_workflow/tag_workflow/public/js/test_records/test_employee_records.json')
        employee_data = json.load(records_file)
        for employee in employee_data:
            employee_records=frappe.db.get_value('Employee',{'email':employee['email'],'company':employee['company']},'email')
            if not employee_records:
                emp = frappe.new_doc("Employee")
                emp.name = employee["name"]
                emp.naming_series = employee["naming_series"]
                emp.first_name = employee["first_name"]
                emp.last_name = employee["last_name"]
                emp.email = employee["email"]
                emp.status = employee["status"]
                emp.company = employee["company"]
                emp.date_of_birth = employee["date_of_birth"]
                emp.save()

    #function to create job order
    def create_job_order(self):
        records_file = open(r'../apps/tag_workflow/tag_workflow/public/js/test_records/test_job_order_records.json')
        job_order_data = json.load(records_file)
        for job_order in job_order_data:
            job_order_records=frappe.db.get_value('Job Order',{'staff_org_claimed':job_order['staff_org_claimed']},'staff_org_claimed')
            if not job_order_records:
                jo = frappe.new_doc("Job Order")
                jo.claim = job_order["claim"]
                jo.staff_org_claimed = job_order["staff_org_claimed"]
                jo._assign = job_order["_assign"]
                jo.agree_to_contract = job_order["agree_to_contract"]
                jo.availability = job_order["availability"]
                jo.category = job_order["category"]
                jo.company = job_order["company"]
                jo.estimated_hours_per_day = job_order["estimated_hours_per_day"]
                jo.flat_rate = job_order["flat_rate"]
                jo.from_date = job_order["from_date"]
                jo.job_site = job_order["job_site"]
                jo.job_start_time = job_order["job_start_time"]
                jo.no_of_workers = job_order["no_of_workers"]
                jo.per_hour = job_order["per_hour"]
                jo.rate = job_order["rate"]
                jo.select_job = job_order["select_job"]
                jo.to_date = job_order["to_date"]
                jo.staff_company = job_order["staff_company"]
                jo.order_status = job_order["order_status"]
                jo.job_duration = job_order["job_duration"]
                jo.job_title = job_order["job_title"]
                jo.extra_price_increase = job_order["extra_price_increase"]
                jo.description = job_order["description"]
                jo.e_signature_full_name = job_order["e_signature_full_name"]
                jo.save()


    #function to create data in assign employee job order
    def create_assign_employee(self):
        records_file = open(r'../apps/tag_workflow/tag_workflow/public/js/test_records/test_assign_employee_records.json')
        emp = frappe.db.sql(employee_get_query)
        name = emp[0][0]
        assign_employee_data = json.load(records_file)
        for assign_employee in assign_employee_data:
            job_order_data = frappe.db.sql(job_order_data_query)
            employee_records=frappe.db.get_value('Assign Employee',{'job_order':job_order_data[0][0]},'job_order')
            if not employee_records:
                a_emp = frappe.new_doc("Assign Employee")
                a_emp.naming_series = assign_employee["naming_series"]
                a_emp.job_order = job_order_data[0][0]
                a_emp.no_of_employee_required = assign_employee["no_of_employee_required"]
                a_emp.job_category = assign_employee["job_category"]
                a_emp.claims_approved = assign_employee["claims_approved"]
                a_emp.tag_status = assign_employee["tag_status"]
                a_emp.hiring_organization = assign_employee["hiring_organization"]
                a_emp.company = assign_employee["company"]
                a_emp.job_location = assign_employee["job_location"]
                a_emp.e_signature_full_name = assign_employee["e_signature_full_name"]
                a_emp.append("employee_details",{
                                "approved": 1,
                                "company": "My Test Company",
                                "docstatus": 0,
                                "doctype": "Assign Employee Details",
                                "employee": name,
                                "employee_name": "emp1 emp1",
                                "job_category": "Data Entry",
                                "name": "new-assign-employee-details-2",
                                "owner": "testingstaffadmin@gmail.com",
                                "parent": "new-assign-employee-2",
                                "parentfield": "employee_details",
                                "parenttype": "Assign Employee",
                                "pay_rate": 19
                            })
                a_emp.save()
    

    #function to create timesheet for bove job order
    def create_timesheet(self):
        records_file = open(r'../apps/tag_workflow/tag_workflow/public/js/test_records/test_timesheet_records.json')
        emp = frappe.db.sql(employee_get_query)
        job_order_data = frappe.db.sql(job_order_data_query)
        timesheet_data = json.load(records_file)
        for timesheet in timesheet_data:
            timesheet_records=frappe.db.get_value('Timesheet',{'company':timesheet['company']},'name')
            if not timesheet_records:
                ts = frappe.new_doc("Timesheet")
                ts.company = timesheet["company"]
                ts.estimated_hours_per_day = timesheet["estimated_hours_per_day"]
                ts.flat_rate = timesheet["flat_rate"]
                ts.from_date = timesheet["from_date"]
                ts.job_site = timesheet["job_site"]
                ts.no_of_workers = timesheet["no_of_workers"]
                ts.per_hour = timesheet["per_hour"]
                ts.rate = timesheet["rate"]
                ts.select_job = timesheet["select_job"]
                ts.to_date = timesheet["to_date"]
                ts.staff_company = timesheet["staff_company"]
                ts.job_title = timesheet["job_title"]
                ts.status = timesheet["status"]
                ts.status_of_work_order = timesheet["status_of_work_order"]
                ts.employee = emp[0][0]
                ts.employee_company = timesheet["employee_company"]
                ts.employee_name = timesheet["employee_name"]
                ts.employee_pay_rate = timesheet["employee_pay_rate"]
                ts.currency = timesheet["currency"]
                ts.date_of_timesheet = timesheet["date_of_timesheet"]
                ts.estimated_daily_hours = timesheet["estimated_daily_hours"]
                ts.start_date = timesheet["start_date"]
                ts.end_date = timesheet["end_date"]
                ts.total_hours = timesheet["total_hours"]
                ts.job_order_detail = job_order_data[0][0]
                ts.append("time_logs", {    "activity_type": "Data Entry", 
                                            "from_time": "2022-08-16 11:50:00", 
                                            "to_time": "2022-08-16 23:50:00",
                                            "hrs": "12 hrs",
                                            "hours": 12, 
                                            "parent":"abcdefgh",
                                            "is_billable": 1, 
                                            "billing_rate": 1,
                                            "tip":0, 
                                            "flat_rate": 0, 
                                            "break_start_time": "2022-08-16 06:50:00",
                                            "break_end_time": "2022-08-16 06:55:00", 
                                            "extra_hours": 6, 
                                            "extra_rate": 30, 
                                            "pay_amount":100
                                        })
                ts.save()

    #test case to test delete emplyee functionality
    def test_emp_delete(self):
        self.create_company()
        self.create_employee()
        self.create_job_order()
        self.create_assign_employee()
        self.create_timesheet()
        emp = frappe.db.sql(employee_get_query)
        response = delete_data(emp[0][0])

        #for succeessful data deletion case
        self.assertEqual("Done",response)

        #for verification test case fro data deletion for multiple data according to above created data
        emp_deleted = frappe.db.sql(employee_get_query)
        self.assertEqual(len(emp_deleted),0)

        assign_detail = frappe.db.sql("delete from `tabAssign Employee Details` where company='My Test Company'")
        self.assertEqual(len(assign_detail),0)

        timesheet = frappe.db.sql("delete from `tabTimesheet` where company='My Test Hiring Company'")
        self.assertEqual(len(timesheet),0)


    #test case for bulk employee deletion
    def test_delete_bulk(self):
        emp = frappe.db.sql('select name from `tabEmployee` where company="My Test Company"')
        items = [data[0] for data in emp]
        delete_bulk_employee("Employee", items)

        emps = frappe.db.sql('select name from `tabEmployee` where company="My Test Company"')
        self.assertEqual(len(emps),0)
        self.delete_test_data()


    #function to delete un necessary testing data which added using above mentioned functions
    def delete_test_data(self):
        job_order_data = frappe.db.sql(job_order_data_query)
        assign_emp_name = frappe.db.sql('select name from `tabAssign Employee` where company="My Test Company"')
        frappe.delete_doc('Assign Employee',assign_emp_name[0][0])
        frappe.delete_doc('Job Order',job_order_data[0][0])


