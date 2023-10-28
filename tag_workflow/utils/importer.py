# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
from curses.ascii import isdigit
import os
import io
import frappe
import timeit
import json
from datetime import datetime, date
from frappe import _
from frappe.utils import cint, flt, update_progress_bar, cstr, duration_to_seconds
from frappe.utils.csvutils import read_csv_content, get_csv_content_from_google_sheets
from frappe.utils.xlsxutils import (read_xlsx_file_from_attached_file, read_xls_file_from_attached_file,)
from frappe.model import no_value_fields, table_fields as table_fieldtypes
from frappe.core.doctype.version.version import get_diff
from frappe.utils import validate_email_address,validate_phone_number
import string,re
import requests, time
template_sample_company = "Temporary Assistance Guru LLC"
state_list = {'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas', 'CA': 'California', 'CZ': 'Canal Zone', 'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware', 'DC': 'District of Columbia', 'FL': 'Florida', 'GA': 'Georgia', 'GU': 'Guam', 'HI': 'Hawaii', 'ID': 'Idaho', 'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas', 'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland', 'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi', 'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada', 'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York', 'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma', 'OR': 'Oregon', 'PA': 'Pennsylvania', 'PR': 'Puerto Rico', 'RI': 'Rhode Island', 'SC': 'South Carolina', 'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont', 'VI': 'Virgin Islands', 'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia', 'WI': 'Wisconsin', 'WY': 'Wyoming'}


tag_gmap_key = frappe.get_site_config().tag_gmap_key or ""
GOOGLE_API_URL=f"https://maps.googleapis.com/maps/api/geocode/json?key={tag_gmap_key}&address="

INVALID_VALUES = ("", None)
MAX_ROWS_IN_PREVIEW = 10
INSERT = "Insert New Records"
UPDATE = "Update Existing Records"
DATA_IMPORT_LOG = "Data Import Log"
JDO_Email = "JDoe@example.com"
Template_error = "Template Error"
DOB_FORMATE = "%Y-%m-%d"
class Importer:
    def __init__(self, doctype, data_import=None, file_path=None, import_type=None, console=False):
        try:
            self.doctype = doctype
            self.console = console
            self.sql = ''
            emp_count = frappe.db.sql(""" select * from `tabSeries` where name = "HR-EMP-" """, as_dict=1)
            if(emp_count):
                self.emp_series = emp_count[0]['current'] + 1
            else:
                self.emp_series = 1

            self.con_series = self.get_contact_series()
            self.data_import = data_import
            if not self.data_import:
                self.data_import = frappe.get_doc(doctype="Data Import")
                if import_type:
                    self.data_import.import_type = import_type

            self.template_options = frappe.parse_json(self.data_import.template_options or "{}")
            self.import_type = self.data_import.import_type

            self.import_file = ImportFile(doctype, file_path or self.data_import.google_sheets_url or self.data_import.import_file, self.template_options, self.import_type,)
            self.name = "No Name"
        except Exception as e:
            print(e,"Importer Error")
            print(frappe.get_traceback())
    
    def get_contact_series(self):
        con_count = frappe.db.sql(""" select * from `tabSeries` where name = "HR-CONTACT-" """, as_dict=1)
        if(con_count):
            con_series = con_count[0]['current'] + 1
        else:
            frappe.db.sql(""" insert into `tabSeries` (name, current) values ('HR-CONTACT-', 1)""", as_dict=1)
            frappe.db.commit()
            con_series = 1
        return con_series

    def get_data_for_import_preview(self):
        out = self.import_file.get_data_for_import_preview()

        out.import_log = frappe.get_all(
			DATA_IMPORT_LOG,
			fields=["row_indexes", "success"],
			filters={"data_import": self.data_import.name},
			order_by="log_index",
			limit=10,
		)

        return out

    def before_import(self):
        # set user lang for translations
        frappe.cache().hdel("lang", frappe.session.user)
        frappe.set_user_lang(frappe.session.user)

        # set flags
        frappe.flags.in_import = True
        frappe.flags.mute_emails = self.data_import.mute_emails
        self.data_import.db_set("status", "Pending")
        self.data_import.db_set("template_warnings", "")

    def upload_record(self):
        try:
            print(self.sql)
            if self.doctype == "Employee" and self.sql:
                self.column = 'insert into `tabEmployee` (name, employee_name, first_name, last_name, email, company, status, date_of_birth, contact_number, employee_gender, sssn, military_veteran, street_address, suite_or_apartment_no, city, state, zip, lat, lng, naming_series, lft, rgt, creation) values ' + self.sql
                frappe.db.sql(""" update `tabSeries` set current = %s where name = "HR-EMP-" """, self.emp_series)
                frappe.db.sql(self.column[0:-1])
            elif self.doctype == "Contact":
                self.column = 'insert into `tabContact` (name, first_name, phone_number, email_address, email_id, owner_company, company, contact_address, city, zip,state, suite_or_apartment_no) values ' + self.sql
                print(self.column)
                frappe.db.sql(""" update `tabSeries` set current = %s where name = "HR-CONTACT-" """, self.con_series)
                frappe.db.sql(self.column[0:-1])
            frappe.db.commit()
        except Exception as e:
            frappe.db.rollback()
            frappe.log_error(e, "bulk import upload_record")

    def import_data(self):
        self.before_import()

        # dont import if there are non-ignorable warnings
        warnings = self.import_file.get_warnings()
        warnings = [w for w in warnings if w.get("type") != "info"]

        if warnings:
            if self.console:
                self.print_grouped_warnings(warnings)
            else:
                self.data_import.db_set("template_warnings", json.dumps(warnings))
            return

        # setup import log
        import_log = (
			frappe.get_all(
				DATA_IMPORT_LOG,
				fields=["row_indexes", "success", "log_index"],
				filters={"data_import": self.data_import.name},
				order_by="log_index",
			)
			or []
		)

        log_index = 0

        # Do not remove rows in case of retry after an error or pending data import
        if (
			self.data_import.status == "Partial Success"
			and len(import_log) >= self.data_import.payload_count
		):
			# remove previous failures from import log only in case of retry after partial success
            import_log = [log for log in import_log if log.get("success")]

        return import_data_contd(self, import_log,log_index)

    def bulk_emp_insert(self, import_log, total_payload_count):
        try:
            # set status
            if self.import_type == INSERT:
                self.upload_record()

            failures = [log for log in import_log if not log.get("success")]
            if len(failures) == total_payload_count:
                status = "Pending"
            elif len(failures) > 0:
                status = "Partial Success"
            else:
                status = "Success" 
            if self.console:
                self.print_import_log(import_log)
            else:
                self.data_import.db_set("status", status)
                self.data_import.db_set("import_log", json.dumps(import_log))

            self.after_import()
            return import_log
        except Exception as e:
            frappe.log_error(e, "bulk_emp_insert")

    def check_import_data(self, doc, current_index, row_indexes, total_payload_count, import_log,log_index):
        try:
            if self.doctype == "Employee":
                self.check_emp_error(doc)

            start = timeit.default_timer()
            y = doc.contact_number or ''
            if '+' not in y and doc.contact_number:
                doc.contact_number = "+" + doc.contact_number

            doc, message = self.process_doc(doc)
            processing_time = timeit.default_timer() - start
            eta = self.get_eta(current_index, total_payload_count, processing_time)

            if self.console:
                update_progress_bar("Importing {0} records".format(total_payload_count), current_index, total_payload_count,)
            elif total_payload_count > 5:
                frappe.publish_realtime("data_import_progress", {"current": current_index, "total": total_payload_count, "docname": doc, "data_import": self.data_import.name, "success": True, "row_indexes": row_indexes, "eta": eta,},)
            
            log_index += 1
            
            if message == "Pass":
                import_log.append(frappe._dict(success=True, docname=doc, row_indexes=row_indexes))
                create_import_log(
						self.data_import.name,
						log_index,
						{"success": True, "docname": doc, "row_indexes": row_indexes},
					)
            else:
                message_log = ['{"title": "Error", "message": "Data Error"}']
                if self.doctype == "Employee":
                    msg_exc = """<b>First Name* and Last Name*</b>: cannot be empty and < , > is not allowed\n<b>Email*</b>: accepts the alphanumeric value in format abc@xyz.com.\n<b>Status*</b>: Active/Inactive/Suspended/Left.\n<b>Company*</b>: You can add data in your company. if kept empty it takes the value of your own company.\n<b>Military Veteran</b>: Please type only 0 or 1, and Yes or NO in Military Veteran.\n<b>Gender</b>: Male, Female or Decline to answer.\n<b>SSN</b>: accepts the 9 digits.\n<b>Contact No.</b>: accepts the 10 to 12 digit.\n<b>Date of birth</b>: is mandatory\n  """
                elif self.doctype == "Contact":
                    msg_exc = """<b>Contact Name*</b>: cannot be empty and < , > is not allowed\n<b>Email*</b>: accepts the alphanumeric value in format abc@xyz.com.\n<b>Owner Company*</b>: You can add data in your company and cannot be empty and < , > is not allowed\n<b>Phone Number</b>: accepts the 10 to 12 digit.\n  """

                import_log.append(frappe._dict(success=False, exception=msg_exc, messages=message_log, docname=doc, row_indexes=row_indexes))
                create_import_log(
						self.data_import.name,
						log_index,
						{
							"success": False,
							"exception": msg_exc,
							"messages": message_log,
							"row_indexes": row_indexes,
						},
					)
            frappe.db.commit()
        except Exception as e:
            messages = frappe.local.message_log
            frappe.clear_messages()
            # rollback if exception
            frappe.db.rollback()
            create_import_log(
						self.data_import.name,
						log_index,
						{
							"success": False,
							"exception": frappe.get_traceback(),
							"messages": messages,
							"row_indexes": row_indexes,
						},
					)

            log_index += 1
            frappe.log_error(e, "check_import_data")
        
        # Logs are db inserted directly so will have to be fetched again
        import_log = (
            frappe.get_all(
                DATA_IMPORT_LOG,
                fields=["row_indexes", "success", "log_index"],
                filters={"data_import": self.data_import.name},
                order_by="log_index",
            )
            or []
        )

    def check_emp_error(self, doc):
        try:
            if(doc.first_name):
                doc.first_name = doc.first_name.title()

            if(doc.last_name):
                doc.last_name = doc.last_name.title()


            if(doc.first_name or doc.last_name):
                if "<" in doc.first_name or ">" in doc.first_name or "<" in doc.last_name or ">" in doc.last_name:
                    doc.first_name = ''



            self.check_email_sssn(doc)
            self.check_ext_fields(doc)
            self.check_rem_emp(doc)
        except Exception as e:
            print(e)

    def check_email_sssn(self,doc):
        if(doc.email):
            regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            if(not re.fullmatch(regex, doc.email)):
                doc.email = ''
            else :
                doc.email = doc.email.lower()

            if((doc.sssn and (not doc.sssn.isdigit() or len(doc.sssn) != 9)) or doc.sssn is None):
                doc.sssn = ''
            if(doc.date_of_birth):
                doc.date_of_birth=str((doc.date_of_birth).strftime('%Y-%m-%d'))
               

    def check_ext_fields(self, doc):

        if(doc.street_address):
            doc.street_address = doc.street_address.title()

        if(doc.suite_or_apartment_no):
            doc.suite_or_apartment_no = doc.suite_or_apartment_no.title()

        if(doc.city):
            doc.city = doc.city.title()

        if(doc.state):
            doc.state = doc.state.title()


    def check_rem_emp(self, doc):
        try:
            if(doc.employee_gender not in ["Female", "Male", "Decline to answer"]):
                doc.employee_gender = ''

            if(doc.status not in ["Active", "Inactive", "Suspended", "Left"]):
                doc.status = ''

            if doc.contact_number and '+' not in doc.contact_number and not doc.contact_number.isdigit():
                doc.contact_number = ''
            elif doc.contact_number:
                if len(doc.contact_number) < 10 or len(doc.contact_number) > 12:
                    doc.contact_number = ''
            elif doc.contact_number is None:
                doc.contact_number = ''

            self.check_rem_emp_data(doc)
        except Exception as e:
            print(e)

    def check_rem_emp_data(self, doc):
        try:
            if((doc.zip and (not doc.zip.isalnum() or (len(doc.zip) < 3 or len(doc.zip) > 15))) or doc.zip is None):
                doc.zip = 0

            if((doc.military_veteran and not doc.military_veteran.isalnum()) or doc.military_veteran is None):
                doc.military_veteran = 0
        except Exception as e:
            print(e)

    def after_import(self):
        frappe.flags.in_import = False
        frappe.flags.mute_emails = False

    def process_doc(self, doc):
        if self.import_type == INSERT:
            if self.doctype == "Contact":
                return self.insert_record_contact(doc)
            return self.insert_record(doc)
        elif self.import_type == UPDATE:
            return self.update_record(doc)
        
    
    
    def insert_record_contact(self, docs):
        try:
            print(docs,"docs"*10,frappe.has_permission(doctype="Company", ptype="read", doc=docs.company),frappe.db.exists("Company", docs.company))
            if frappe.has_permission(doctype="Company", ptype="read", doc=docs.company) and frappe.db.exists("Company", docs.company):
                user_type = frappe.db.get_value("User",frappe.session.user,"role_profile_name")
                if (docs.first_name and docs.email_address and docs.owner_company):
                    if frappe.session.user !="Administrator" and user_type != "Tag Admin" and not frappe.db.sql("SELECT company_name FROM `tabLead` WHERE (lead_owner = '{0}' or owner='{1}') and company_name='{2}'".format(frappe.session.user, frappe.session.user, docs.owner_company), as_list=True):
                        return self.name, "Failed"
                    self.name = "HR-CONTACT-" + str(self.con_series)
                    docs.state = update_doc_state(docs.state)
                    self.sql += create_sql(self.name,docs)
                    print(self.sql)
                    self.con_series += 1
                    time.sleep(0.1)
                    return self.name, "Pass"
                return self.name, "Failed"
            return self.name, "Failed"
        except Exception as e:
            frappe.log_error(e, "insert record for contact")
            return 'No Name', 'Failed'


        
    def insert_record(self, docs):
        try:
            keys = docs.keys()
            if (frappe.has_permission(doctype="Company", ptype="read", doc=docs.company) == True and frappe.db.exists("Company", docs.company) and "first_name" in keys and "last_name" in keys and "email" in keys and "status" in keys):
                self.name = "HR-EMP-"+str(self.emp_series)
                lat, lng = self.update_emp_lat_lng(docs)
                if len(docs.state) == 2:
                    docs.state = state_list.get(docs.state.upper())
                self.sql += str(tuple([self.name, (docs.first_name + " " + docs.last_name), docs.first_name, docs.last_name, docs.email, docs.company, docs.status, str(docs.date_of_birth), docs.contact_number, docs.employee_gender, docs.sssn, docs.military_veteran, (docs.street_address or ''), (docs.suite_or_apartment_no or ''), (docs.city or ''), (docs.state or ''), (docs.zip or ''), lat, lng, 'HR-EMP-', self.emp_series+1, self.emp_series+2, frappe.utils.now()])) + ","
                self.emp_series += 1
                time.sleep(0.1)
                return self.name, "Pass"
            else:
                return self.name, "Failed"
        except Exception as e:
            frappe.log_error(e, "insert_record")
            return 'No Name', 'Failed'


    def update_emp_lat_lng(self, doc):
        try:
            lat, lng = '', ''
            doc.city = doc.city + ", " if doc.city else " "
            doc.state = doc.state + ", " if doc.state else " "
            address = doc.city +  doc.state + (doc.zip if doc.zip != 0 and doc.zip is not None else "")
            google_location_data_url = GOOGLE_API_URL + address
            google_response = requests.get(google_location_data_url)
            location_data = google_response.json()
            if(google_response.status_code == 200 and len(location_data)>0 and len(location_data['results'])>0):
                lat, lng = self.emp_location_data(location_data)
            return lat, lng
        except Exception as e:
            frappe.log_error(e, "longitude latitude error")
            return '', ''

    def emp_location_data(self, address_dt):
        try:
            lat, lng = '', ''
            if(len(address_dt['results']) > 0):
                location = address_dt['results'][0]['geometry']['location']
                lat = str(location['lat'])
                lng = str(location['lng'])
                return lat, lng
        except Exception as e:
            frappe.log_error(e, "Longitude latitude address")
            return '', ''

    def update_record(self, docs):
        try:
            self.check_emp_error(docs)
            keys = docs.keys()
            if(frappe.has_permission(doctype="Company", ptype="read", doc=docs.company) == True and "name" in keys and frappe.db.exists("Company", docs.company) and "first_name" in keys and "last_name" in keys and "email" in keys and "status" in keys):
                if(docs.name and docs.first_name and docs.last_name and docs.email and docs.status and docs.date_of_birth):
                    full_name = (docs.first_name + " " + docs.last_name)
                    lat, lng = self.update_emp_lat_lng(docs)
                    self.sql = """employee_name = '{0}', first_name = '{1}', last_name = '{2}', email = '{3}', company = '{4}', status = '{5}',date_of_birth = '{18}', contact_number = '{6}', employee_gender = '{7}', sssn = '{8}', military_veteran = {9}, street_address = '{10}', suite_or_apartment_no = '{11}', city = '{12}', state = '{13}', zip = '{14}', lat = '{15}', lng = '{16}', creation = '{17}' """.format(full_name, docs.first_name, docs.last_name, docs.email, docs.company, docs.status, docs.contact_number, docs.employee_gender, docs.sssn, docs.military_veteran, (docs.street_address or ''), (docs.suite_or_apartment_no or ''), (docs.city or ''), (docs.state or ''), (docs.zip or ''), lat, lng, frappe.utils.now(),(docs.date_of_birth or ''))
                    sql = """update `tabEmployee` set {0} where name = '{1}'""".format(self.sql, docs.name)
                    frappe.db.sql(sql)
                    frappe.db.commit()
                    return docs.name, "Pass"
                else:
                    return docs.name, "Falied"
            else:
                return docs.name, "Falied"
        except Exception as e:
            print(e)
            return '', 'Failed'

    def get_eta(self, current, total, processing_time):
        self.last_eta = getattr(self, "last_eta", 0)
        remaining = total - current
        eta = processing_time * remaining
        if not self.last_eta or eta < self.last_eta:
            self.last_eta = eta
        return self.last_eta

    def export_errored_rows(self):
        from frappe.utils.csvutils import build_csv_response

        if not self.data_import:
            return

        import_log = (
			frappe.get_all(
				DATA_IMPORT_LOG,
				fields=["row_indexes", "success"],
				filters={"data_import": self.data_import.name},
				order_by="log_index",
			)
			or []
		)
        failures = [log for log in import_log if not log.get("success")]
        row_indexes = []
        for f in failures:
            row_indexes.extend(f.get("row_indexes", []))

        # de duplicate
        row_indexes = list(set(row_indexes))
        row_indexes.sort()

        header_row = [col.header_title for col in self.import_file.columns]
        rows = [header_row]
        rows += [row.data for row in self.import_file.data if row.row_number in row_indexes]

        build_csv_response(rows, self.doctype)

    def export_import_log(self):
        from frappe.utils.csvutils import build_csv_response

        if not self.data_import:
            return

        import_log = frappe.get_all(
            DATA_IMPORT_LOG,
            fields=["row_indexes", "success", "messages", "exception", "docname"],
            filters={"data_import": self.data_import.name},
            order_by="log_index",
        )

        header_row = ["Row Numbers", "Status", "Message", "Exception"]

        rows = [header_row]

        for log in import_log:
            row_number = json.loads(log.get("row_indexes"))[0]
            status = "Success" if log.get("success") else "Failure"
            message = (
                "Successfully Imported {}".format(log.get("docname"))
                if log.get("success")
                else log.get("messages")
            )
            exception = frappe.utils.cstr(log.get("exception", ""))
            rows += [[row_number, status, message, exception]]

        build_csv_response(rows, self.doctype)

    def print_import_log(self, import_log):
        failed_records = [log for log in import_log if not log.success]
        successful_records = [log for log in import_log if log.success]

        if successful_records:
            print()
            print("Successfully imported {0} records out of {1}".format(len(successful_records), len(import_log)))

        if failed_records:
            print("Failed to import {0} records".format(len(failed_records)))
            file_name = "{0}_import_on_{1}.txt".format(self.doctype, frappe.utils.now())
            print("Check {0} for errors".format(os.path.join("sites", file_name)))
            text = ""
            for w in failed_records:
                text += "Row Indexes: {0}\n".format(str(w.get("row_indexes", [])))
                text += "Messages:\n{0}\n".format("\n".join(w.get("messages", [])))
                text += "Traceback:\n{0}\n\n".format(w.get("exception"))

            with open(file_name, "w") as f:
                f.write(text)

    def print_grouped_warnings(self, warnings):
        warnings_by_row = {}
        other_warnings = []
        for w in warnings:
            if w.get("row"):
                warnings_by_row.setdefault(w.get("row"), []).append(w)
            else:
                other_warnings.append(w)

        for row_number, warnings in warnings_by_row.items():
            print("Row {0}".format(row_number))
            for w in warnings:
                print(w.get("message"))

        for w in other_warnings:
            print(w.get("message"))


class ImportFile:
    def __init__(self, doctype, file, template_options=None, import_type=None):
        self.doctype = doctype
        self.template_options = template_options or frappe._dict(column_to_field_map=frappe._dict())
        self.column_to_field_map = self.template_options.column_to_field_map
        self.import_type = import_type
        self.warnings = []

        self.file_doc = self.file_path = self.google_sheets_url = None
        if isinstance(file, str):
            if frappe.db.exists("File", {"file_url": file}):
                self.file_doc = frappe.get_doc("File", {"file_url": file})
            elif "docs.google.com/spreadsheets" in file:
                self.google_sheets_url = file
            elif os.path.exists(file):
                self.file_path = file

        if not self.file_doc and not self.file_path and not self.google_sheets_url:
            frappe.throw(_("Invalid template file for import"))

        self.raw_data = self.get_data_from_template_file()
        self.parse_data_from_template()

    def get_data_from_template_file(self):
        content = None
        extension = None

        if self.file_doc:
            parts = self.file_doc.get_extension()
            extension = parts[1]
            content = self.file_doc.get_content()
            extension = extension.lstrip(".")

        elif self.file_path:
            content, extension = self.read_file(self.file_path)
        elif self.google_sheets_url:
            content = get_csv_content_from_google_sheets(self.google_sheets_url)
            extension = "csv"

        if not content:
            frappe.throw(_("Invalid or corrupted content for import"))

        if not extension:
            extension = "csv"

        if content:
            return self.read_content(content, extension)

    def parse_data_from_template(self):
        header = None
        data = []
        for i, row in enumerate(self.raw_data):
            if all(v in INVALID_VALUES for v in row):
                # empty row
                continue
            if self.doctype in ["Employee", "Contact"] and JDO_Email in row:
                # sample record
                continue
            if not header:
                header = Header(i, row, self.doctype, self.raw_data, self.column_to_field_map)
            else:
                row_obj = Row(i, row, self.doctype, header, self.import_type)
                data.append(row_obj)

        self.header = header
        self.columns = self.header.columns
        self.data = data

        if len(data) < 1:
            frappe.throw(_("Import template should contain a Header and atleast one row."), title=_(Template_error),)

    def get_data_for_import_preview(self):
        """Adds a serial number column as the first column"""
        columns = [frappe._dict({"header_title": "Sr. No", "skip_import": True})]
        columns += [col.as_dict() for col in self.columns]

        for col in columns:
            # only pick useful fields in docfields to minimise the payload
            if col.df:
                col.df = {
                        "fieldtype": col.df.fieldtype,
                        "fieldname": col.df.fieldname,
                        "label": col.df.label,
                        "options": col.df.options,
                        "parent": col.df.parent,
                        "reqd": col.df.reqd,
                        "default": col.df.default,
                        "read_only": col.df.read_only,
                }

        data = [[row.row_number] + row.as_list() for row in self.data]
        warnings = self.get_warnings()
        out = frappe._dict()
        out.data = data
        out.columns = columns
        out.warnings = warnings
        total_number_of_rows = len(out.data)
        if total_number_of_rows > MAX_ROWS_IN_PREVIEW:
            out.data = out.data[:MAX_ROWS_IN_PREVIEW]
            out.max_rows_exceeded = True
            out.max_rows_in_preview = MAX_ROWS_IN_PREVIEW
            out.total_number_of_rows = total_number_of_rows

        return out

    def get_payloads_for_import(self):
        payloads = []
        # make a copy
        data = list(self.data)
        while data:
            doc, rows, data = self.parse_next_row_for_import(data)
            payloads.append(frappe._dict(doc=doc, rows=rows))
        return payloads

    def parse_next_row_for_import(self, data):
        """
            Parses rows that make up a doc. A doc maybe built from a single row or multiple rows.
            Returns the doc, rows, and data without the rows.
        """
        doctypes = self.header.doctypes

        # first row is included by default
        first_row = data[0]
        rows = [first_row]

        # if there are child doctypes, find the subsequent rows
        if len(doctypes) > 1:
            # subsequent rows that have blank values in parent columns
            # are considered as child rows
            parent_column_indexes = self.header.get_column_indexes(self.doctype)
            parent_row_values = first_row.get_values(parent_column_indexes)
            print(parent_row_values)
            data_without_first_row = data[1:]
            for row in data_without_first_row:
                row_values = row.get_values(parent_column_indexes)
                # if the row is blank, it's a child row doc
                if all([v in INVALID_VALUES for v in row_values]):
                    rows.append(row)
                    continue
                # if we encounter a row which has values in parent columns,
                # then it is the next doc
                break

        return parse_next_row_for_import_contd(self, data, doctypes, rows)

    def get_warnings(self):
        warnings = []
        # ImportFile warnings
        warnings += self.warnings

        # Column warnings
        for col in self.header.columns:
            warnings += col.warnings

        # Row warnings
        for row in self.data:
            warnings += row.warnings

        return warnings
        ######

    def read_file(self, file_path):
        extn = file_path.split(".")[1]
        file_content = None
        with io.open(file_path, mode="rb") as f:
            file_content = f.read()

        return file_content, extn

    def read_content(self, content, extension):
        error_title = _(Template_error)
        if extension not in ("csv", "xlsx", "xls"):
            frappe.throw(_("Import template should be of type .csv, .xlsx or .xls"), title=error_title)

        if extension == "csv":
            data = read_csv_content(content)
        elif extension == "xlsx":
            data = read_xlsx_file_from_attached_file(fcontent=content)
        elif extension == "xls":
            data = read_xls_file_from_attached_file(content)

        return data


class Row:
    link_values_exist_map = {}
    def __init__(self, index, row, doctype, header, import_type):
        self.index = index
        self.row_number = index + 1
        self.doctype = doctype
        self.data = row
        self.header = header
        self.import_type = import_type
        self.warnings = []

        len_row = len(self.data)
        len_columns = len(self.header.columns)
        if len_row != len_columns:
            less_than_columns = len_row < len_columns
            message = ("Row has less values than columns" if less_than_columns else "Row has more values than columns")

            self.warnings.append({"row": self.row_number, "message": message,})

    def parse_doc(self, doctype, parent_doc=None, table_df=None):
        col_indexes = self.header.get_column_indexes(doctype, table_df)
        values = self.get_values(col_indexes)

        if all(v in INVALID_VALUES for v in values):
            # if all values are invalid, no need to parse it
            return None

        columns = self.header.get_columns(col_indexes)
        doc = self._parse_doc(doctype, columns, values, parent_doc, table_df)
        return doc

    def _parse_doc(self, doctype, columns, values, parent_doc=None, table_df=None):
        doc = frappe._dict()
        if self.import_type == INSERT:
            # new_doc returns a dict with default values set
            doc = frappe.new_doc(doctype, parent_doc=parent_doc, parentfield=table_df.fieldname if table_df else None, as_dict=True,)

        # remove standard fields and __islocal
        for key in frappe.model.default_fields + ("__islocal",):
            doc.pop(key, None)

        for col, value in zip(columns, values):
            df = col.df
            if value in INVALID_VALUES:
                value = None
            if value is not None:
                value = self.validate_value(value, col)
            if value is not None:
                doc[df.fieldname] = self.parse_value(value, col)

        return _parse_doc_contd(self, doctype, doc)

    def validate_value(self, value, col):
        df = col.df
        if df.fieldtype == "Select":
            select_options = get_select_options(df)
            if select_options and value not in select_options:
                options_string = ", ".join([frappe.bold(d) for d in select_options])
                msg = _("Value must be one of {0}").format(options_string)
                self.warnings.append({"row": self.row_number, "field": df_as_json(df), "message": msg,})
                return

        elif df.fieldtype == "Link":
            exists = self.link_exists(value, df)
            if not exists:
                msg = _("Value {0} missing for {1}").format(frappe.bold(value), frappe.bold(df.options))
                self.warnings.append({"row": self.row_number, "field": df_as_json(df), "message": msg,})
                return

        elif df.fieldtype in ["Date", "Datetime"]:
            value = self.get_date(value, col)
            if isinstance(value, str):
                # value was not parsed as datetime object
                self.warnings.append({"row": self.row_number, "col": col.column_number, "field": df_as_json(df), "message": _("Value {0} must in {1} format").format(frappe.bold(value), frappe.bold(get_user_format(col.date_format))),})
                return

        elif df.fieldtype == "Duration":
            import re
            is_valid_duration = re.match(r"^(?:(\d+d)?((^|\s)\d+h)?((^|\s)\d+m)?((^|\s)\d+s)?)$", value)
            if not is_valid_duration:
                self.warnings.append({"row": self.row_number, "col": col.column_number, "field": df_as_json(df), "message": _("Value {0} must be in the valid duration format: d h m s").format(frappe.bold(value))})

        return value

    def link_exists(self, value, df):
        key = df.options + "::" + cstr(value)
        if Row.link_values_exist_map.get(key) is None:
            Row.link_values_exist_map[key] = frappe.db.exists(df.options, value)
        return Row.link_values_exist_map.get(key)

    def parse_value(self, value, col):
        df = col.df
        if isinstance(value, (datetime, date)) and df.fieldtype in ["Date", "Datetime"]:
            return value

        value = cstr(value)
        # convert boolean values to 0 or 1
        valid_check_values = ["t", "f", "true", "false", "yes", "no", "y", "n"]
        if df.fieldtype == "Check" and value.lower().strip() in valid_check_values:
            value = value.lower().strip()
            value = 1 if value in ["t", "true", "y", "yes"] else 0

        if df.fieldtype in ["Int", "Check"]:
            value = cint(value)
        elif df.fieldtype in ["Float", "Percent", "Currency"]:
            value = flt(value)
        elif df.fieldtype in ["Date", "Datetime"]:
            value = self.get_date(value, col)
        elif df.fieldtype == "Duration":
            value = duration_to_seconds(value)

        return value

    def get_date(self, value, column):
        if isinstance(value, (datetime, date)):
            return value

        date_format = column.date_format
        if date_format:
            try:
                return datetime.strptime(value, date_format)
            except ValueError:
                # ignore date values that dont match the format
                # import will break for these values later
                pass

        return value

    def get_values(self, indexes):
        return [self.data[i] for i in indexes]

    def get(self, index):
        return self.data[index]

    def as_list(self):
        return self.data


class Header(Row):
    def __init__(self, index, row, doctype, raw_data, column_to_field_map=None):
        self.index = index
        self.row_number = index + 1
        self.data = row
        self.doctype = doctype
        column_to_field_map = column_to_field_map or frappe._dict()

        self.seen = []
        self.columns = []

        for j, header in enumerate(row):
            column_values = [get_item_at_index(r, j) for r in raw_data]
            map_to_field = column_to_field_map.get(str(j))
            column = Column(j, header, self.doctype, column_values, map_to_field, self.seen)
            self.seen.append(header)
            self.columns.append(column)

        doctypes = []
        for col in self.columns:
            if not col.df:
                continue
            if col.df.parent == self.doctype:
                doctypes.append((col.df.parent, None))
            else:
                doctypes.append((col.df.parent, col.df.child_table_df))

        self.doctypes = sorted(list(set(doctypes)), key=lambda x: -1 if x[0] == self.doctype else 1)

    def get_column_indexes(self, doctype, tablefield=None):
        def is_table_field(df):
            if tablefield:
                return df.child_table_df.fieldname == tablefield.fieldname
            return True

        return [
                col.index
                for col in self.columns
                if not col.skip_import
                and col.df
                and col.df.parent == doctype
                and is_table_field(col.df)
        ]

    def get_columns(self, indexes):
        return [self.columns[i] for i in indexes]


class Column:
    seen = []
    fields_column_map = {}

    def __init__(self, index, header, doctype, column_values, map_to_field=None, seen=None):
        if seen is None:
            seen = []

        self.index = index
        self.column_number = index + 1
        self.doctype = doctype
        self.header_title = header
        self.column_values = column_values
        self.map_to_field = map_to_field
        self.seen = seen

        self.date_format = None
        self.df = None
        self.skip_import = None
        self.warnings = []

        self.meta = frappe.get_meta(doctype)
        self.parse()
        self.validate_values()

    def parse(self):
        header_title = self.header_title
        column_number = str(self.column_number)
        skip_import = False

        if self.map_to_field and self.map_to_field != "Don't Import":
            df = get_df_for_column_header(self.doctype, self.map_to_field)
            if df:
                self.warnings.append({"message": _("Mapping column {0} to field {1}").format(frappe.bold(header_title or "<i>Untitled Column</i>"), frappe.bold(df.label)), "type": "info",})

            else:
                self.warnings.append({"message": _("Could not map column {0} to field {1}").format(column_number, self.map_to_field), "type": "info",})

        else:
            df = get_df_for_column_header(self.doctype, header_title)
            # df is equal df by labels and fieldnames get header_title

        if not df:
            skip_import = True
        else:
            skip_import = False

        if header_title in self.seen:
            self.warnings.append({"col": column_number, "message": _("Skipping Duplicate Column {0}").format(frappe.bold(header_title)), "type": "info",})
            df = None
            skip_import = True

        elif self.map_to_field == "Don't Import":
            skip_import = True
            self.warnings.append({"col": column_number, "message": _("Skipping column {0}").format(frappe.bold(header_title)), "type": "info",})

        elif header_title and not df:
            self.warnings.append({"col": column_number, "message": _("Cannot match column {0} with any field").format(frappe.bold(header_title)), "type": "info",})
        elif not header_title and not df:
            self.warnings.append({"col": column_number, "message": _("Skipping Untitled Column"), "type": "info"})

        self.df = df
        self.skip_import = skip_import

    def guess_date_format_for_column(self):
        """Guesses date format for a column by parsing all the values in the column,
            getting the date format and then returning the one which has the maximum frequency
        """

        def guess_date_format(d):
            if isinstance(d, (datetime, date)):
                if self.df.fieldtype == "Date":
                    return DOB_FORMATE
                if self.df.fieldtype == "Datetime":
                    return "%Y-%m-%d %H:%M:%S"
            if isinstance(d, str):
                return frappe.utils.guess_date_format(d)

        date_formats = [guess_date_format(d) for d in self.column_values]
        date_formats = [d for d in date_formats if d]
        if not date_formats:
            return

        unique_date_formats = set(date_formats)
        max_occurred_date_format = max(unique_date_formats, key=date_formats.count)
        if len(unique_date_formats) > 1:
            # fmt: off
            message = _("The column {0} has {1} different date formats. Automatically setting {2} as the default format as it is the most common. Please change other values in this column tothis format.")
            # fmt: on
            user_date_format = get_user_format(max_occurred_date_format)
            self.warnings.append({"col": self.column_number, "message": message.format(frappe.bold(self.header_title), len(unique_date_formats), frappe.bold(user_date_format),), "type": "info",})

        return max_occurred_date_format

    def validate_values(self):
        if not self.df or self.skip_import:
            return

        if self.df.fieldtype == "Link":
            # find all values that dont exist
            values = list(set([cstr(v) for v in self.column_values[1:] if v]))
            exists = [d.name for d in frappe.db.get_all(self.df.options, filters={"name": ("in", values)})]
            not_exists = list(set(values) - set(exists))

            if not_exists:
                missing_values = ", ".join(not_exists)
                self.warnings.append({"col": self.column_number, "message": ("The following values do not exist for {}: {}".format(self.df.options, missing_values)), "type": "warning",})

        elif self.df.fieldtype in ("Date", "Time", "Datetime"):
            # guess date format
            self.date_format = self.guess_date_format_for_column()
            if not self.date_format:
                self.date_format = DOB_FORMATE
                self.warnings.append({"col": self.column_number, "message": _("Date format could not be determined from the values in this column. Defaulting to yyyy-mm-dd."), "type": "info",})

        elif self.df.fieldtype == "Select":
            self.fieldtype_select_check()

        elif self.df.fieldtype == "Data":
            self.fieldtype_data_check()

    def fieldtype_select_check(self):
        options = get_select_options(self.df)
        if options:
            values = list(set([cstr(v) for v in self.column_values[1:] if v]))
            invalid = list(set(values) - set(options))
            if invalid:
                valid_values = ", ".join([frappe.bold(o) for o in options])
                invalid_values = ", ".join([frappe.bold(i) for i in invalid])
                self.warnings.append({"col": self.column_number, "message": ("The following values are invalid: {0}. Values must be one of {1}".format(invalid_values, valid_values)),})

    def fieldtype_data_check(self):
        if self.df.name == "Employee-email":
            values = list(set([cstr(v) for v in self.column_values[1:] if v]))
            for email in values:
                if not validate_email_address(email):
                    self.warnings.append({"col": self.column_number, "message": ("The Email address is Invalid")})
        self.fieldtype_data_check_remaining()

    def fieldtype_data_check_remaining(self):
        if self.df.name == "Employee-contact_number":
            values = list(set([cstr(v) for v in self.column_values[1:] if v]))
            for phone in values:
                if not is_valid(phone):
                    self.warnings.append({"col": self.column_number, "message": ("The Mobile number is invalid")})

    def as_dict(self):
        d = frappe._dict()
        d.index = self.index
        d.column_number = self.column_number
        d.doctype = self.doctype
        d.header_title = self.header_title
        d.map_to_field = self.map_to_field
        d.date_format = self.date_format
        d.df = self.df
        if hasattr(self.df, "is_child_table_field"):
            d.is_child_table_field = self.df.is_child_table_field
            d.child_table_df = self.df.child_table_df
        d.skip_import = self.skip_import
        d.warnings = self.warnings
        return d


def build_fields_dict_for_column_matching(parent_doctype):
    """
        Build a dict with various keys to match with column headers and value as docfield
        The keys can be label or fieldname
        {
            'Customer': df1,
            'customer': df1,
            'Due Date': df2,
            'due_date': df2,
            'Item Code (Sales Invoice Item)': df3,
            'Sales Invoice Item:item_code': df3,
        }
    """

    parent_meta = frappe.get_meta(parent_doctype)
    out = {}
    # doctypes and fieldname if it is a child doctype
    doctypes = [[parent_doctype, None]] + [[df.options, df] for df in parent_meta.get_table_fields()]

    sub_build_fields_for_column(doctypes,parent_doctype,parent_meta)    # if autoname is based on field
    # add an entry for "ID (Autoname Field)"
    autoname_field = get_autoname_field(parent_doctype)
    if autoname_field:
        out["ID ({})".format(autoname_field.label)] = autoname_field
        # ID field should also map to the autoname field
        out["ID"] = autoname_field
        out["name"] = autoname_field
    return out

def get_df_for_column_header(doctype, header):
    def build_fields_dict_for_doctype():
        return build_fields_dict_for_column_matching(doctype)

    df_by_labels_and_fieldname = frappe.cache().hget("data_import_column_header_map", doctype, generator=build_fields_dict_for_doctype)
    return df_by_labels_and_fieldname.get(header)

# utilities
def get_id_field(doctype):
    autoname_field = get_autoname_field(doctype)
    if autoname_field:
        return autoname_field
    return frappe._dict({"label": "ID", "fieldname": "name", "fieldtype": "Data"})

def get_autoname_field(doctype):
    meta = frappe.get_meta(doctype)
    if meta.autoname and meta.autoname.startswith("field:"):
        fieldname = meta.autoname[len("field:") :]
        return meta.get_field(fieldname)

def get_item_at_index(_list, i, default=None):
    try:
        a = _list[i]
    except IndexError:
        a = default
    return a

def get_user_format(date_format):
    return (date_format.replace("%Y", "yyyy").replace("%y", "yy").replace("%m", "mm").replace("%d", "dd"))

def df_as_json(df):
    return {"fieldname": df.fieldname, "fieldtype": df.fieldtype, "label": df.label, "options": df.options, "parent": df.parent, "default": df.default,}

def get_select_options(df):
    return [d for d in (df.options or "").split("\n") if d]

import re
def is_valid(s):
    pattern = re.compile("(0|91)?[7-9][\d]{9}")
    if  pattern.match(s) and len(s) == 10:
        return True
    return False

import re
def zip_valid(s):
    return bool(re.match(r'^[1-9][\d]{4}$',s) and len(re.findall(r'(\d)(?=\d\1)',s))<2)

def import_data_contd(self, import_log, log_index):


    # parse docs from rows
    payloads = self.import_file.get_payloads_for_import()

    # get successfully imported rows
    imported_rows = []
    for log in import_log:
        log = frappe._dict(log)
        if log.success or len(import_log) < self.data_import.payload_count:
            imported_rows += json.loads(log.row_indexes)

        log_index = log.log_index


    # start import
    total_payload_count = len(payloads)
    batch_size = frappe.conf.data_import_batch_size or 1000

    for batch_index, batched_payloads in enumerate(frappe.utils.create_batch(payloads, batch_size)):
        for i, payload in enumerate(batched_payloads):
            doc = payload.doc
            row_indexes = [row.row_number for row in payload.rows]
            current_index = (i + 1) + (batch_index * batch_size)

            if set(row_indexes).intersection(set(imported_rows)):
                print("Skipping imported rows", row_indexes)
                if total_payload_count > 5:
                    frappe.publish_realtime("data_import_progress", {"current": current_index, "total": total_payload_count, "skipping": True, "data_import": self.data_import.name,},)
                continue

            self.check_import_data(doc, current_index, row_indexes, total_payload_count, import_log,log_index)

    import_log = self.bulk_emp_insert(import_log, total_payload_count)
    return import_log

def parse_next_row_for_import_contd(self, data, doctypes, rows):
    parent_doc = None
    for row in rows:
        for doctype, table_df in doctypes:
            if doctype == self.doctype and not parent_doc:
                parent_doc = row.parse_doc(doctype)

            if doctype != self.doctype and table_df:
                child_doc = row.parse_doc(doctype, parent_doc, table_df)
                if child_doc is None:
                    continue

                parent_doc[table_df.fieldname] = parent_doc.get(table_df.fieldname, [])
                parent_doc[table_df.fieldname].append(child_doc)

    doc = parent_doc
    return doc, rows, data[len(rows) :]

def _parse_doc_contd(self, doctype, doc):
    is_table = frappe.get_meta(doctype).istable
    is_update = self.import_type == UPDATE
    if is_table and is_update:
        # check if the row already exists
        # if yes, fetch the original doc so that it is not updated
        # if no, create a new doc
        id_field = get_id_field(doctype)
        id_value = doc.get(id_field.fieldname)
        if id_value and frappe.db.exists(doctype, id_value):
            existing_doc = frappe.get_doc(doctype, id_value)
            existing_doc.update(doc)
            doc = existing_doc
        else:
            # for table rows being inserted in update
            # create a new doc with defaults set
            new_doc = frappe.new_doc(doctype, as_dict=True)
            new_doc.update(doc)
            doc = new_doc

    return doc
def get_standard_fields(doctype):
    meta = frappe.get_meta(doctype)
    if meta.istable:
        standard_fields = [{"label": "Parent", "fieldname": "parent"}, {"label": "Parent Type", "fieldname": "parenttype"}, {"label": "Parent Field", "fieldname": "parentfield"}, {"label": "Row Index", "fieldname": "idx"},]

    else:
        standard_fields = [{"label": "Owner", "fieldname": "owner"}, {"label": "Document Status", "fieldname": "docstatus", "fieldtype": "Int"},]

    out = []
    for df in standard_fields:
        df = frappe._dict(df)
        df.parent = doctype
        out.append(df)
    return out

def sub_build_fields_for_column(doctypes,parent_doctype,parent_meta):
    out = {}
    for doctype, table_df in doctypes:
        # name field
        name_by_label = ("ID" if doctype == parent_doctype else "ID ({0})".format(table_df.label))

        name_by_fieldname = ("name" if doctype == parent_doctype else "{0}.name".format(table_df.fieldname))

        name_df = frappe._dict({"fieldtype": "Data", "fieldname": "name", "label": "ID", "reqd": 1, "parent": doctype,})

        if doctype != parent_doctype:
            name_df.is_child_table_field = True
            name_df.child_table_df = table_df

        out[name_by_label] = name_df
        out[name_by_fieldname] = name_df

        # other fields
        fields = get_standard_fields(doctype) + frappe.get_meta(doctype).fields
        for df in fields:
            new_sub_build_fields_for_column(df,parent_doctype,doctype,parent_meta,out)
def new_sub_build_fields_for_column(df,parent_doctype,doctype,parent_meta,out):
    label = (df.label or "").strip()
    fieldtype = df.fieldtype or "Data"
    parent = df.parent or parent_doctype
    if fieldtype not in no_value_fields and parent_doctype == doctype:
        # for parent doctypes keys will be
        # Label
        # label
        # Label (label)
        new_sub_build_fields_for_column_match(out,label,df,parent_meta,parent)
def new_sub_build_fields_for_column_match(out,label,df,parent_meta,parent):
    if not out.get(label):
        # if Label is already set, don't set it again
        # in case of duplicate column headers
        out[label] = df
        out[df.fieldname] = df
        label_with_fieldname = "{0} ({1})".format(label, df.fieldname)
        out[label_with_fieldname] = df
    else:
        # in case there are multiple table fields with the same doctype
        # for child doctypes keys will be
        # Label (Table Field Label)
        # table_field.fieldname
        table_fields = parent_meta.get("fields", {"fieldtype": ["in", table_fieldtypes], "options": parent})
        for table_field in table_fields:
            by_label = "{0} ({1})".format(label, table_field.label)
            by_fieldname = "{0}.{1}".format(table_field.fieldname, df.fieldname)
            # create a new df object to avoid mutation problems
            if isinstance(df, dict):
                new_df = frappe._dict(df.copy())
            else:
                new_df = df.as_dict()

            new_df.is_child_table_field = True
            new_df.child_table_df = table_field
            out[by_label] = new_df
            out[by_fieldname] = new_df

def create_import_log(data_import, log_index, log_details):
	frappe.get_doc(
		{
			"doctype": DATA_IMPORT_LOG,
			"log_index": log_index,
			"success": log_details.get("success"),
			"data_import": data_import,
			"row_indexes": json.dumps(log_details.get("row_indexes")),
			"docname": log_details.get("docname"),
			"messages": json.dumps(log_details.get("messages", "[]")),
			"exception": log_details.get("exception"),
		}
	).db_insert()

import frappe
import os
from frappe.utils.csvutils import read_csv_content
from frappe.utils import validate_email_address
import re

reqd_emp = ["First Name","Last Name","Email","Company","Status","Date of Birth","Contact Number","Gender","SSN","Military Veteran","Street Address","Suite or Apartment No","City","State","Zip"]
reqd_contact = ["Contact Name","Phone Number","Email","Owner Company","Contact Address","City","Zip","State","Suite or Apartment No"]

@frappe.whitelist()
def read_file(file, doctype, comps, event,user_type):
    try:
        error_in_fields ={}
        data = get_content(file)
        if data:
            update_required_emp(event)
            for row_no, row in enumerate(data):
                msg = check_return(row_no, row, event,doctype)
                if msg == "Wrong Columns":
                    return msg
                elif msg == "Continue":
                    continue
                row_message = get_row_error(row,doctype, comps, event,data,row_no,user_type)
                if len(row_message)>0:
                    error_in_fields["Row "+str(row_no+1)]=row_message
        return error_in_fields
    except Exception as e:
        print(e, frappe.get_traceback())
def check_return(row_no, row, event,doctype):
    if row_no == 0 and not check_columns(row, doctype):
        return "Wrong Columns"
    elif row_no==0:
        return "Continue"
    elif row_no == 1 and event=='insert' and doctype =="Employee" and row[0] == "John" and row[1]=="Doe" and row[2]==JDO_Email and row[3]==template_sample_company:
        return  "Continue"
    elif row_no ==1 and event =='insert' and doctype == "Contact" and row[0] == "John Doe" and row[2] == "JDoe@example.com" and row[3] == template_sample_company:
        return "Continue"
    elif row_no == 1 and event=='update' and row[1] == "John" and row[2]=="Doe" and row[3]==JDO_Email and row[4]==template_sample_company:
        return "Continue"
    
def get_row_error(row,doctype, comps, event,data,row_no,user_type):
    if event == 'insert':
        row_message = check_fields(row, doctype, comps, data,row_no,user_type,event)
        return row_message
    else:
        row_message = check_fields(row[1:], doctype, comps,data,row_no,user_type,event)
        return row_message
def get_content(file):
    if frappe.db.exists("File", {"file_url": file}):
            file_doc = frappe.get_doc("File", {"file_url": file})
            if file_doc:
                parts = file_doc.get_extension()
                extension = parts[1]
                content = file_doc.get_content()
                extension = extension.lstrip(".")
            if not content:
                frappe.throw(_("Invalid or corrupted content for import"))
                return
            if not extension:
                extension = "csv"
            data=read_content(content, extension)
            return data
def update_required_emp(event):
    if event == 'update' and doctype == 'Employee':
        reqd_emp.insert(0, 'ID')
        
def check_columns(row, doctype):
    if(doctype == 'Employee' and row != reqd_emp) or (doctype == 'Contact' and row != reqd_contact):
        return False
    return True

def check_fields(row, doctype, comps,data,row_index,user_type,event):
    message=[]
    if doctype == "Employee":
        check_mandatory_fields(row,message,doctype)
        check_duplicate_row(data,message,row,row_index,event)
        check_email(row[2],message)
        if event == "insert":
            check_db_exist(row[2],message,"Employee",row[3])
        if frappe.session.user != "Administrator" and user_type != "TAG Admin":
            check_company(comps, row[3],message)
        check_status(row[4],message)
        check_dob(row[5],message)
        check_phone_number(str(row[6]),message)
        check_gender(row[7],message)
        check_ssn(row[8],message)
        check_m_v(row[9],message)
        check_state(row[13], message)
        check_zip(row[14], message)
    elif doctype == "Contact":
        check_lead_for_contact(message,row[3],user_type)
        check_mandatory_fields(row, message,doctype)
        check_phone_number(row[1],message)
        check_email(row[2],message)
        check_db_exist(row[2],message,"Contact",row[3])
        check_zip(row[6], message)
        check_state(row[7], message)

    return message
def check_lead_for_contact(message,company,user_type):
    if frappe.session.user != "Administrator" and user_type != "TAG Admin" and not frappe.db.sql("SELECT company_name FROM `tabLead` WHERE (lead_owner = '{0}' or owner='{1}') and company_name='{2}'".format(frappe.session.user, frappe.session.user, company), as_list=True):
        return message.append("Create a <b>Lead</b> to import <b>Contact</b>")
  
def check_db_exist(email,message, doctype,company):
    if doctype == "Employee" and company:
        check = frappe.db.exists("Employee",{"email":email,"company":company})
        if check:message.append("Employee with this Email Already exist")
    elif doctype == "Contact":
        check = frappe.db.exists("Contact",{"email_id":email})
        if check:message.append("Contact with this Email Already exist")
          
def check_duplicate_row(data,message,row,row_index,event):
    duplicate_row= []
    duplicate_email =[]
    duplicate_ssn =[]
    for row_no, row_val in enumerate(data):
        if row_no ==0 or row_no == row_index :
            continue
        if row_no ==1:
            check = check_example_row(event,row_val,row_index)
            if check:
                continue
        duplicate_records(row,row_val,duplicate_row,duplicate_email,duplicate_ssn,row_no)  
    if duplicate_row:
        error_rows = ', '.join(duplicate_row)
        msg = "Duplicate row detected " + error_rows
        message.append(msg)
    check_duplicate_email_and_ssn(message,duplicate_email,duplicate_ssn)

def check_example_row(event,row,row_no):
    if (event=='insert' and  row[0] == "John" and row[1]=="Doe" and row[2]==JDO_Email and row[3]==template_sample_company) or row_no == 1 and event=='update' and row[1] == "John" and row[2]=="Doe" and row[3]==JDO_Email and row[4]==template_sample_company:
        return  1
    
def duplicate_records(row,row_val,duplicate_row,duplicate_email,duplicate_ssn,row_no):
    if row[0]==row_val[0] and row[1] == row_val[1] and row[2]==row_val[2] and row[5]==row_val[5] and  row[8]==row_val[8]:
        duplicate_row.append(str(row_no +1))
    if row[2] != "" and row[2] and row[2] == row_val[2] :
        duplicate_email.append(str(row_no +1))
    if row[8] !="" and row[8] and row[8] == row_val[8]:
        duplicate_ssn.append(str(row_no + 1))

def check_duplicate_email_and_ssn(message,duplicate_email,duplicate_ssn):
    if duplicate_email:
        duplicate_email_rows = ', '.join(duplicate_email)
        msg = "Duplicate Email detected " + duplicate_email_rows
        message.append(msg)
    if duplicate_ssn:
        duplicate_ssn_rows = ', '.join(duplicate_ssn)
        msg = "Duplicate SSN detected " + duplicate_ssn_rows
        message.append(msg)
        
        
    
def check_company(user_comp_list, company_in_row, message):
    if company_in_row and company_in_row not in user_comp_list: message.append("Invalid Entry for Company")

def check_status(status,message):
    if status and status.lower() not in ["active", "inactive"]: message.append("Status")
        
def check_dob(dob, message):
    date_formate = DOB_FORMATE
    if isinstance(dob, float) and dob:
        dob =  datetime.fromordinal(datetime(1900, 1, 1).toordinal() + int(dob) - 2)
        try:
            res = bool(datetime.strptime(str(dob).split(" ")[0], date_formate))
        except ValueError:
            res = False
        if not res: message.append("Date of Birth is not a valid Date")
        
    else:
        if dob:
            try:
                res = bool(datetime.strptime(str(dob).split(" ")[0], date_formate))
            except ValueError:
                res = False
            if not res: message.append("Date of Birth is not a valid Date")

def check_phone_number(phone,message):
    if phone and phone!="None" and not validate_phone_number(phone): message.append("Invalid Phone Number")

def check_gender(gender, message):
    if gender and gender.lower() not in ["male", "female"]: message.append("Gender")

def check_email(email, message):
    if email and not validate_email_address(email): message.append("Formate for Email is incorrect")

def check_ssn(ssn, message):
    if ssn and (len(str(int(ssn)))!=9 or not str(int(ssn)).isdigit()): message.append("Invalid <b>SSN</b>")

def check_m_v(militrary_veteran, message):
    if militrary_veteran and militrary_veteran not in ["0", "1"]: message.append("Invalid Entry for Military Veteran valid values are 0 or 1")

def check_state(state, message):
    state_list = {
        'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR', 'California': 'CA', 'Canal Zone': 'CZ',
        'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE', 'District of Columbia': 'DC', 'Florida': 'FL',
        'Georgia': 'GA', 'Guam': 'GU', 'Hawaii': 'HI', 'Idaho': 'ID', 'Illinois': 'IL', 'Indiana': 'IN',
        'Iowa': 'IA', 'Kansas': 'KS', 'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME', 'Maryland': 'MD',
        'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN', 'Mississippi': 'MS', 'Missouri': 'MO', 'Montana': 'MT',
        'Nebraska': 'NE', 'Nevada': 'NV', 'New Hampshire': 'NH', 'New Jersey': 'NJ', 'New Mexico': 'NM', 'New York': 'NY', 'North Carolina': 'NC',
        'North Dakota': 'ND', 'Ohio': 'OH', 'Oklahoma': 'OK', 'Oregon': 'OR', 'Pennsylvania': 'PA', 'Puerto Rico': 'PR', 'Rhode Island': 'RI',
        'South Carolina': 'SC', 'South Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT', 'Vermont': 'VT',
        'Virgin Islands': 'VI', 'Virginia': 'VA', 'Washington': 'WA', 'West Virginia': 'WV', 'Wisconsin': 'WI', 'Wyoming': 'WY'
    }
    if state and state not in state_list.keys() and state not in state_list.values():message.append('Invalid <b>State</b>')
    
def check_zip(zip, message):
    pattern = r'^\d{5}(-\d{4})?$'
    if zip and not re.match(pattern, str(int(zip))):message.append('Invalid <b>Zip</b>')

def check_mandatory_fields(row, message,doctype):
    fields_missing=[]
    check_is_valid = 0
    for i in range(len(row)):
        if row[i] is None or row[i] == "":
            if doctype == 'Employee' and i in [0, 1, 2, 3, 5]:
                check_is_valid =1
                fields_missing.append("<b>" + reqd_emp[i] + "</b>")
            elif doctype == 'Contact' and  i in [0,1,2,3]:
                check_is_valid =1
                fields_missing.append(reqd_contact[i])

    if check_is_valid:
        message.append("Missing Required Fields: "+", ".join(fields_missing))
def create_sql(name,docs):
        return str(tuple([name, docs.first_name, docs.phone_number, docs.email_address,docs.email_address, docs.owner_company , (docs.company or ""), (docs.contact_address or ""), (docs.city or ""), (docs.zip or ""),(docs.state or ""), (docs.suite_or_apartment_no or "")])) + ","
    
def read_content(content, extension):
    error_title = _(Template_error)
    if extension not in ("csv", "xlsx", "xls"):
        frappe.throw(_("Import template should be of type .csv, .xlsx or .xls"), title=error_title)

    if extension == "csv":
        data = read_csv_content(content)
    elif extension == "xlsx":
        data = read_xlsx_file_from_attached_file(fcontent=content)
    elif extension == "xls":
        data = read_xls_file_from_attached_file(content)

    return data
def update_doc_state(contact_state):
        if len(contact_state) == 2:
            return state_list.get(contact_state.upper())
        else:
            return contact_state