import frappe
from frappe import _
import zipfile, os, shutil
import itertools, re, datetime
import boto3

#-----------------------------#
TM_FT = "%Y-%m-%d %H-%M-%S"
employee_attachments= "Employee Attachments"
my_sql_query='insert into `tabEmployee Attachments` (name, attachments, parent, parentfield, parenttype, idx) values '

@frappe.whitelist()
def update_resume(company, zip_file, name, attachment_name, file_name, file_url):
    try:
        pdfs = []
        if frappe.db.exists("File", {"file_name": file_name, "name": attachment_name, "attached_to_doctype": "Company", "file_url": ["in", [zip_file, file_url]]}):
            file_os_path = os.getcwd() + "/" + frappe.get_site_path() + "/public/" + file_url
            dest_os_path = os.getcwd() + "/" + frappe.get_site_path() + "/public/files/" + company + "-" + name + "-" + file_name
            is_extracted = upzip_file(file_os_path, dest_os_path)
            if(is_extracted == 1):
                pdfs = get_pdf_files(dest_os_path)
                frappe.enqueue("tag_workflow.utils.bulk_upload_resume.upload_to_emps", queue='long', is_async=True, company=company, pdfs=pdfs, dest_os_path=dest_os_path)
            else:
                frappe.msgprint(_("<p>The process of unziping the file is failed.</p> \n<p>Error: <b>{0}</b></p> \n<p>Please re-upload the file and try again!</p>").format(is_extracted))
        else:
            frappe.msgprint(_("Some issues is in the zip file. Please re-upload the file and try again !"))
    except Exception as e:
        frappe.msgprint(e)

#----------extracting files--------------#
def upzip_file(file_os_path, dest_os_path):
    try:
        if not os.path.isfile(dest_os_path):
            with zipfile.ZipFile(file_os_path, "r") as zip_ref:
                zip_ref.extractall(dest_os_path)
                zip_ref.close()
        return 1
    except Exception as e:
        frappe.log_error(e, "upzip_file")
        return str(e)

#---------getting all the pdfs from dir---------#
def get_pdf_files(dest_os_path):
    try:
        pdfs, sub_folders = [], []
        subfolders = [ f.path for f in os.scandir(dest_os_path) if f.is_dir() ]
        if(subfolders):
            sub_folders = [ f.path for f in os.scandir(subfolders[0]) if f.is_dir() ]

        if sub_folders:
            subfolders = sub_folders

        for folder in subfolders:
            for(dirpath, dirnames, filenames) in os.walk(folder):
                pdfs.append({"path": dirpath, "filenames": filenames})
        return pdfs
    except Exception as e:
        frappe.log_error(e,  "get_pdf_files")
        return []

#--------updating link to employee----------#
def upload_to_emps(company=None, pdfs=None, dest_os_path=None):
    try:
        for p in pdfs:
            for fil in p['filenames']:
                pattern = re.compile(f".*{fil.split('-')[0]}")
                newlist = [fil] + list(filter(pattern.match, p['filenames']))
                newlist = list(set(newlist))
                frappe.enqueue("tag_workflow.utils.bulk_upload_resume.upload_to_s3", queue='default', is_async=True, path=p['path'], newlist=newlist)
                frappe.enqueue("tag_workflow.utils.bulk_upload_resume.make_data", queue='default', is_async=True, path=p['path'], company=company, newlist=newlist)
        frappe.enqueue("tag_workflow.utils.bulk_upload_resume.remove_dir", queue='default', is_async=True, path=dest_os_path)
    except Exception as e:
        frappe.msgprint(e)

def remove_dir(path):
    try:
        shutil.rmtree(path)
    except Exception as e:
        frappe.log_error(e, "remove_dir")

def upload_to_s3(path, newlist):
    try:
        s3 = boto3.resource('s3')
        BUC = frappe.get_site_config().s3_bucket or ''
        for res in newlist:
            url = path+"/"+res
            result = get_file_size(url)
            if(BUC and result):
                s3.Bucket(BUC).upload_file(path+"/"+res, res)
    except Exception as e:
        frappe.log_error(e,  "upload_to_s3")

#----------file size------------#
def get_file_size(url):
    try:
        result = 0
        url_size = os.path.getsize(url)/(1024*1024)
        if(url_size <= 10):
            result = 1
        return result
    except Exception:
        return 1


#-----------------------#
def make_data(path, company, newlist):
    try:
        dates, name = [], []
        name = check_name(newlist)
        dates = check_file_and_get_dates(newlist)
        if name and dates:
            frappe.enqueue("tag_workflow.utils.bulk_upload_resume.update_emp_record", queue='default', is_async=True, path=path, emp_name=name, company=company, newlist=newlist, dates=dates)
    except Exception as e:
        frappe.log_error(e, "make_data")

#----------------#
def check_name(newlist):
    try:
        name = []
        check_email = re.compile(".*@")
        for res in newlist:
            if(list(filter(check_email.match, res))):
                data = res.split("_")[0]
            else:
                data = res.split(" - ")[0]

            if data not in name:
                name.append(data)
        return name
    except Exception as e:
        frappe.log_error(e, "checking name")
        return []

def check_file_and_get_dates(newlist):
    try:
        dates = []
        check_email = re.compile(".*@")
        for new in newlist:
            try:
                if(list(filter(check_email.match, new))):
                    data = new.split("_")[-1].split(".")[0]
                else:
                    data = new.split(" - ")[-1].split(".")[0]

                dte = datetime.datetime.strptime(data, "%Y-%m-%d %H-%M-%S")
                if dte not in dates:
                    dates.append(dte)
            except Exception:
                continue
        return dates
    except Exception as e:
        frappe.log_error(e, "file_error")
        return [], []


#-----------------------------------------------------#
def update_emp_record(path, emp_name, company, newlist, dates):
    try:
        if(len(emp_name) == 1 and len(emp_name[0].split(", ")) == 2):
            update_single_emps(path, company, emp_name, dates, newlist)
        else:
            update_multiple_emps(path, company, emp_name,newlist)
    except Exception as e:
        frappe.log_error(e,  "update_emp_record")

def update_single_emps(path, company, emp_name, dates, newlist):
    try:
        print(path)
        name = emp_name[0].split(", ")[1] + " " + emp_name[0].split(", ")[0]
        dates.sort()
        employees = frappe.db.sql("""select name, employee_name from `tabEmployee` where employee_name like '{0}%' and company = '{1}' """.format(name, company), as_dict=1)
        for e in employees:
            for d in dates:
                if(len(dates) > 1):
                    try:
                        update_multiple(d, e.name, newlist)
                    except Exception:
                        continue
                else:
                    emp_and_date_data_one(newlist, e.name, dates)
    except Exception as e:
        print(e)
        frappe.log_error(str(frappe.get_traceback()), "single emp update")

def emp_and_date_data_one(newlist, emp, dates):
    try:
        resume = ""
        for new in newlist:
            url = frappe.get_site_config().s3_url +"/"+ new
            if(new.find(str(dates).replace(":", "-")) > 0 and not frappe.db.get_value("Employee", emp, "resume")):
                resume = url
                frappe.db.set_value("Employee", emp, "resume", url)

        if not resume:
            resume = frappe.db.get_value("Employee", emp, "resume")
            
        for new in newlist:
            sub_employee_and_date_data_one(new, resume, emp)
    except Exception as e:
        print(e)
        frappe.log_error(str(frappe.get_traceback()), "emp_and_date_data_one")

def update_miscellaneous(url, name):
    try:
        if('@' in url):
            l=frappe.get_doc('Employee',name)
            if l.email in url:
                count = frappe.db.sql("""select count(name) as count from `tabEmployee Attachments` where parent = %s """, name, as_dict=1)
                count_idx = count[0]['count'] if(count) else 0
                sql = my_sql_query
                sql += str(tuple([str(name)+"-"+str(count_idx), url,name, "miscellaneous", "Employee", (count_idx+1)])) + ","
                frappe.db.sql(sql[0:-1])
                frappe.db.commit()
        else:
            count = frappe.db.sql("""select count(name) as count from `tabEmployee Attachments` where parent = %s """, name, as_dict=1)
            count_idx = count[0]['count'] if(count) else 0
            sql = my_sql_query
            sql += str(tuple([str(name)+"-"+str(count_idx), url,name, "miscellaneous", "Employee", (count_idx+1)])) + ","
            frappe.db.sql(sql[0:-1])
            frappe.db.commit()
    except Exception as e:
        frappe.log_error(e, "update_miscellaneous")


def update_multiple(date, emp, newlist):
    try:
        sql = my_sql_query
        count, is_value = 0, 0
        _, resume = '', ''
        resume=update_sub_empss(newlist,date,emp,resume)
        if not resume:
            resume = frappe.db.get_value("Employee", emp, "resume")
            
        for new in newlist:
            url = frappe.get_site_config().s3_url +"/"+ new
            if(resume != url and not frappe.db.exists(employee_attachments, {"parent": emp, "attachments": url})):
                if(frappe.db.get_value("Employee", emp, "resume") or "") < url:
                    frappe.db.set_value("Employee", emp, "resume", url)
                    resume = url
                
                if(resume != url and not frappe.db.exists(employee_attachments, {"parent": emp, "attachments": url})):
                    is_value = 1
                    sql,count=new_functionss(url,emp,count,sql)
        if(is_value > 0):
            frappe.db.sql(sql[0:-1])
            frappe.db.commit()
    except Exception as e:
        frappe.log_error(e,  "update_multiple")

def update_multiple_emps(path, company, emp_name, newlist):
    try:
        for emp in emp_name:
            if(len(emp.split(", ")) == 2):
                try:
                    name = emp.split(", ")[1] + " " + emp.split(", ")[0]
                    employees = frappe.db.sql("""select name, employee_name from `tabEmployee` where employee_name like '{0}%' and company = '{1}' """.format(name, company), as_dict=1)
                    updatemultiple(path, employees, newlist)
                except Exception:
                    continue
    except Exception as e:
        frappe.log_error(e, "multiple emp update")

def updatemultiple(path, employees=None, newlist=None):
    try:
        for e in employees:
            for new in newlist:
                url_check = path + new
                result = get_file_size(url_check)
                if(new.find(str(e)) > 0 and result and not frappe.db.get_value("Employee", e.name, "resume")):
                    url = frappe.get_site_config().s3_url +"/"+ new
                    frappe.db.set_value("Employee", e.name, "resume", url)
    except Exception as e:
        frappe.log_error(e, "updatemultiple")


#----------------resume download-----------------------#
@frappe.whitelist()
def download_resume(resume):
    try:
        resume = resume.split("/")[-1]
        file_os_path = os.getcwd() + "/" + resume
        dest_os_path = os.getcwd() + "/" + frappe.get_site_path() + "/public/files/" + resume

        s3 = boto3.resource('s3')
        BUC = frappe.get_site_config().s3_bucket or ''
        if(BUC):
            my_bucket = s3.Bucket(BUC)
            for s3_object in my_bucket.objects.all():
                if(s3_object.key == resume):
                    my_bucket.download_file(s3_object.key, resume)
                    shutil.move(file_os_path, dest_os_path)
            return 1
        else:
            return "AWS S3 Bucket is not defined in config."
    except Exception as e:
        frappe.log_error(e,  "upload_to_s3")
        return str(e)


def sub_employee_and_date_data_one(new, resume, emp,):
    url = frappe.get_site_config().s3_url + "/" + new
    if resume != url and not frappe.db.exists(employee_attachments, {"parent": emp, "attachments": url}):
        if (frappe.db.get_value("Employee", emp, "resume") or "") < url:
            resume=check_emails(emp,url)
        if resume != url and not frappe.db.exists(employee_attachments, {"parent": emp, "attachments": url}):
            update_miscellaneous(url, emp)

def update_sub_empss(newlist,date,emp,resume):
    for new in newlist:
        url = frappe.get_site_config().s3_url +"/"+ new
        if(new.find(str(date).replace(":", "-")) > 0 and not frappe.db.get_value("Employee", emp, "resume")):
            resume = url
            frappe.db.set_value("Employee", emp, "resume", url)
    return resume

def check_emails(emp,url):
    resume=''
    if('@' in url):
        l=frappe.get_doc('Employee',emp)
        if(l.email in url):
            frappe.db.set_value("Employee", emp, "resume", url)
            resume = url
    else:
        frappe.db.set_value("Employee", emp, "resume", url)
        resume = url
    return resume
def new_functionss(url,emp,count,sql):
    if('@' in url):
        l=frappe.get_doc('Employee',emp)
        if l.email in url:
            sql += str(tuple([str(emp)+"-"+str(count)+"-"+str(url), url, emp, "miscellaneous", "Employee", (count+1)])) + ","
            count += 1
    else:
        sql += str(tuple([str(emp)+"-"+str(count)+"-"+str(url), url, emp, "miscellaneous", "Employee", (count+1)])) + ","
        count += 1
    return sql,count
