import frappe, json
from frappe import enqueue
from frappe.share import add_docshare as add
from frappe.core.doctype.session_default_settings.session_default_settings import set_session_default_values
from frappe.sessions import Session, get_expiry_period, get_geo_ip_country
from .notification import ses_email_send
USR = "User"

# session update
def on_session_creation():
    try:
        company, comp_type = frappe.db.get_value(USR, {"name": frappe.session.user}, ["company", "organization_type"]) or ["", ""]
        default_values = {"company": company}
        set_session_default_values(default_values)

        if(comp_type == "Staffing"):
            frappe.local.response["home_page"] = "/app/staff-home"
        elif(comp_type in ["Exclusive Hiring", "Hiring"]):
            frappe.local.response["home_page"] = "/app/hiring-home"
        elif(comp_type =="TAG"):
            frappe.local.response["home_page"] = "/app/tagadmin-page"
    except Exception as e:
        print(e)

# boot update
def update_boot(boot):
    try:
        data = frappe._dict({
            "tag_user_info": get_user_info()
        })
        boot.update({"tag":data})
    except Exception as e:
        print(e)
        frappe.log_error(frappe.get_traceback(), "boot error")


def get_user_info():
    try:
        comps, exces, stfs, invoice_view = [], [], [], []
        user = frappe.session.user
        user_doc = frappe.get_doc(USR, user)
        api_key = frappe.get_site_config().tag_gmap_key or ''
        org = frappe.get_site_config()._fs_org or ''
        data = {"user_type": user_doc.tag_user_type, "company": user_doc.company, "company_type": user_doc.organization_type, "api_key": api_key, "sid":frappe.session.sid, 'org':org}
        frappe.cache().set_value("sessions", {user: frappe.session.sid})
        frappe.local.cookie_manager.set_cookie('ctype',data['company_type'])

        sql = ""
        if(user_doc.organization_type == "Hiring"):
            sql = """select name, default_invoice_view from `tabCompany` where organization_type = "Hiring" and name in (select company from `tabEmployee` where user_id = '{0}')""".format(user_doc.name)
        elif(user_doc.organization_type == "Staffing"):
            sql = """select name, default_invoice_view from `tabCompany` where organization_type = "Staffing" and name in (select company from `tabEmployee` where user_id = '{0}')""".format(user_doc.name)
            excs = frappe.db.sql(""" select name from `tabCompany` where organization_type = "Exclusive Hiring" and parent_staffing in (select company from `tabEmployee` where user_id = %s) """,user_doc.name, as_dict=1)
            for e in excs:
                exces.append(e.name)

            stfs_list = frappe.db.get_list("Employee", {"user_id": user_doc.name}, "company")
            for s in stfs_list:
                stfs.append(s.company)
        elif user_doc.organization_type == "Exclusive Hiring":
            sql = """ select parent_staffing as name, default_invoice_view from `tabCompany` where name = '{0}' """.format(user_doc.company)

        if(sql):
            comps, export_ts, invoice_view = get_comp_info(sql, user_doc.organization_type, comps, invoice_view)
        export_ts=1 if user_doc.organization_type=='TAG' or frappe.session.user=='Administrator' else export_ts
        frappe.local.cookie_manager.set_cookie('invoice_view', '|'.join([str(elem) for elem in invoice_view]))
        data.update({"comps": comps, "exces": exces, "stfs": stfs, "export_ts": export_ts})
        return data
    except Exception as e:
        print(e)
        
def get_comp_info(sql, org_type, comps, invoice_view):
    try:
        export_ts = 0
        com_list = frappe.db.sql(sql, as_dict=1)
        for c in com_list:
            comps.append(c.name)
            export_ts = check_export_ts(c.name, export_ts) if org_type=='Staffing' else export_ts
            invoice_view.append(f"{c.name}*{c.default_invoice_view}")
        return comps, export_ts, invoice_view
    except Exception as e:
        print('get_comp_info Error', frappe.get_traceback())
        frappe.log_error(e, 'get_comp_info_error')

# check company share
def add_company_share_permission(users):
    try:
        for usr in users:
            if not frappe.db.exists("DocShare", {"share_doctype": "Company", "user":usr['name'], "share_name":usr['company'], "read":1, "write":1, "share": 1}):
                add("Company", usr['company'], user=usr['name'], read=1, write=1, share=1, flags={"ignore_share_permission": 1})
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "doc share error")
        print(e)

def share_company_with_user(users=None):
    try:
        if not users:
            sql = """ select name, company from `tabUser` where enabled = 1 and company != '' """
            users = frappe.db.sql(sql, as_dict=1)
        add_company_share_permission(users)
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(e, "sharing company")
        print(e)

def welcome_email():
    try:
        user = frappe.session.user
        last_login = frappe.db.get_value("User", {"name" : user}, ['last_login'])
        if not last_login:
            env_url = frappe.get_site_config().env_url
            link = env_url + '/login'
            sub = "Welcome to TAG!"
            # enqueue(method = frappe.sendmail, recipients = user, template = "welcome_email", subject = sub, args = { "subject": sub, "sitename": env_url, "link": link })
            args = { "subject": sub, "sitename": env_url, "link": link }
            template = "welcome_email"
            enqueue(method = ses_email_send,emails=user,template=template,subject=sub,args=args)
    except Exception as e:
        frappe.log_error(e, 'Welcome Email Error')
        print(e)

def start(self):
    """start a new session"""
    # generate sid
    if self.user=='Guest':
        sid = 'Guest'
    else:
        sid = frappe.generate_hash()

    self.data.user = self.user
    self.data.sid = sid
    self.data.data.user = self.user
    self.data.data.session_ip = frappe.local.request_ip
    if self.user != "Guest":
        self.data.data.update({
            "last_updated": frappe.utils.now(),
            "session_expiry": get_expiry_period(self.device),
            "full_name": self.full_name,
            "user_type": self.user_type,
            "device": self.device,
            "session_country": get_geo_ip_country(frappe.local.request_ip) if frappe.local.request_ip else None,
        })

    # insert session
    if self.user!="Guest":
        self.insert_session_record()

        # update user
        welcome_email()
        user = frappe.get_doc("User", self.data['user'])
        frappe.db.sql("""UPDATE `tabUser`
            SET
                last_login = %(now)s,
                last_ip = %(ip)s,
                last_active = %(now)s
            WHERE name=%(name)s""", {
                'now': frappe.utils.now(),
                'ip': frappe.local.request_ip,
                'name': self.data['user']
            })
        user.run_notifications("before_change")
        user.run_notifications("on_update")
        frappe.db.commit()

def first_login():
    Session.start = start

@frappe.whitelist()
def check_export_ts(comp_name, export_ts):
    try:
        staff_complete = frappe.db.get_value('Company', {'name': comp_name, 'organization_type': 'Staffing'}, ['staff_complete_enable', 'office_code'])
        return 1 if staff_complete[0] == 1 and staff_complete[1] and len(staff_complete[1])==5 else export_ts
    except Exception as e:
        print("check_export_ts Error",frappe.get_traceback())
        frappe.log_error(e, "check_export_ts Error")

@frappe.whitelist()
def clear_filters():
    try:
        sql=f'''SELECT data, doctype FROM `__UserSettings` WHERE user="{frappe.session.user}"'''
        user_filters = frappe.db.sql(sql, as_dict=1)
        user_company, comp_type = frappe.db.get_value("User", frappe.session.user, ["company", "organization_type"])
        for i in user_filters:
            if "List" in i.get("data"):
                data = json.loads(i["data"])
                if i["doctype"]=="Employee" and user_company and comp_type!='TAG':
                    data["List"]["filters"]=[["Employee", "user_id", "is", "not set", False], ["Employee", "status", "=", "Active", False], ["Employee", "company", "=", user_company, False]]
                else:
                    data["List"]["filters"]=[]
                data=json.dumps(data)
                sql=f'''UPDATE `__UserSettings` SET data='{data}' WHERE user="{frappe.session.user}" AND doctype="{i.get("doctype")}"'''
                frappe.cache().hset("_user_settings", f"{i.get('doctype')}::{frappe.session.user}", data)
                frappe.db.commit()
    except Exception as e:
        print(e, frappe.get_traceback())
