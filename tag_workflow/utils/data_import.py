import os
import frappe
from frappe import _
from frappe.core.doctype.data_import.exporter import Exporter
from frappe.model.document import Document
from frappe.modules.import_file import import_file_by_path
from frappe.utils.background_jobs import enqueue
from frappe.utils.csvutils import validate_google_sheets_url
from frappe.core.page.background_jobs.background_jobs import get_info
from frappe.utils.scheduler import is_scheduler_inactive

@frappe.whitelist()
def form_start_import(data_import):
    try:
        doc = frappe.get_doc("Data Import", data_import)

        if is_scheduler_inactive() and not frappe.flags.in_test:
            frappe.throw(_("Scheduler is inactive. Cannot import data."), title=_("Scheduler Inactive"))

        enqueued_jobs = [d.get("job_name") for d in get_info()]
        if doc.name not in enqueued_jobs:
            enqueue(start_import, queue="long", timeout=60000, event="data_import", job_name=doc.name, data_import=doc.name, now=frappe.conf.developer_mode or frappe.flags.in_test,)
            return True

        return False
    except Exception as e:
        print(e)
        frappe.log_error(e, "bulk import")


def start_import(data_import):
    """This method runs in background job"""
    data_import = frappe.get_doc("Data Import", data_import)
    try:
        if(data_import.reference_doctype not in ["Employee", "Contact"]):
            from frappe.core.doctype.data_import.importer import Importer
        else:
            from tag_workflow.utils.importer import Importer
        i = Importer(data_import.reference_doctype, data_import=data_import)
        i.import_data()
    except Exception:
        print(frappe.get_traceback())
        frappe.db.rollback()
        data_import.db_set("status", "Error")
        frappe.log_error(title=data_import.name)
    finally:
        frappe.flags.in_import = False

    frappe.publish_realtime("data_import_refresh", {"data_import": data_import.name})

@frappe.whitelist()
def get_import_list(doctype, txt, searchfield, page_len, start, filters):
    company_type=filters.get('user_type')
    if company_type=='Staffing':
        sql = ''' select name from `tabDocType` where name in("Employee","Contact") and name like "%%{0}%%" '''.format('%s' %txt)
        return frappe.db.sql(sql)
    else:
        sql = ''' select name from `tabDocType` where name like "%%{0}%%" '''.format('%s' % txt)
        return frappe.db.sql(sql)



@frappe.whitelist()
def download_template(doctype, export_fields=None, export_records=None, export_filters=None, file_type="CSV"):
    
    export_fields = frappe.parse_json(export_fields)
    export_filters = frappe.parse_json(export_filters)
    export_data = export_records != "blank_template"


    if doctype in ["Contact", "Employee"]:
        export_data = True
    
    e = Exporter(
        doctype,
        export_fields=export_fields,
        export_data=export_data,
        export_filters=export_filters,
        file_type=file_type,
        export_page_length=5 if export_records == "5_records" else None,
    )
    e.build_response()