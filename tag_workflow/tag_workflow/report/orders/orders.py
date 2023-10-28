# Copyright (c) 2013, SourceFuse and contributors
# For license information, please see license.txt

import frappe
import datetime
job_id = 'Job ID'
job_title = 'Job Title'
jobOrder = 'Job Order'
date_time = 'Date & Time'
no_of_workers = 'No Of Workers'
staffing_company = 'Staffing Company'
bids_received = 'Bids Received'
claimed_by = 'Claimed By'

def execute(filters=None):
    try:
        if not filters:
            filters={}
        columns,data=[],[]
        today = datetime.datetime.now()
        user_name=frappe.session.user
        sql = ''' select organization_type from `tabUser` where email='{}' '''.format(user_name)
        user_type=frappe.db.sql(sql, as_list=1)
        if frappe.session.user=="Administrator" or user_type[0][0]=='TAG':
            if filters.get('status')==None:
                columns=[
                    {'fieldname':'name','label':(job_id),'fieldtype':'Link','options':jobOrder,'width':150},
                    {'fieldname':'select_job','label':(job_title),'fieldtype':'Data','width':150},
                    {'fieldname':'from_date','label':(date_time),'fieldtype':'Data','width':150},
                    {'fieldname':'job_site','label':('Location'),'fieldtype':'Data','width':150},
                    {'fieldname':'total_no_of_workers','label':(no_of_workers),'fieldtype':'Int','width':150},
                    {'fieldname':'bid','label':(bids_received),'fieldtype':'Int','width':150},
                    {'fieldname':'claim','label':(claimed_by),'fieldtype':'Data','width':150},
                    {'fieldname':'staff_org_claimed','label':(staffing_company),'fieldtype':'Data','width':150},
                ]
                sql = '''
                    SELECT jo.name,
                    GROUP_CONCAT(DISTINCT mjt.select_job ORDER BY mjt.select_job SEPARATOR ', ') AS select_job,
                    CONCAT(jo.from_date, ', ', MIN(TIME_FORMAT(mjt.job_start_time, '%H:%i'))) AS from_date, jo.job_site, jo.total_no_of_workers, jo.bid, REPLACE(jo.claim, '~', ', ') AS claim, jo.staff_org_claimed
                    FROM `tabJob Order` AS jo, `tabMultiple Job Titles` AS mjt
                    WHERE jo.name = mjt.parent
                    GROUP BY jo.name
                '''
                data=frappe.db.sql(sql, as_dict=1)
            elif filters.get('status')=='Completed':
                columns=[
                    {'fieldname':'name','label':(job_id),'fieldtype':'Link','options':jobOrder,'width':200},
                    {'fieldname':'select_job','label':(job_title),'fieldtype':'Data','width':150},
                    {'fieldname':'from_date','label':(date_time),'fieldtype':'Data','width':200},
                    {'fieldname':'job_site','label':('Location'),'fieldtype':'Data' ,'width':200},
                    {'fieldname':'total_no_of_workers','label':(no_of_workers),'fieldtype':'Int','width':200},
                    {'fieldname':'staff_org_claimed','label':(staffing_company),'fieldtype':'Data','width':200}             
                ]
                sql = f'''
                    SELECT jo.name,
                    GROUP_CONCAT(DISTINCT mjt.select_job ORDER BY mjt.select_job SEPARATOR ', ') AS select_job,
                    CONCAT(jo.from_date, ', ', MIN(TIME_FORMAT(mjt.job_start_time, '%H:%i'))) AS from_date, jo.job_site, jo.total_no_of_workers, jo.staff_org_claimed
                    FROM `tabJob Order` AS jo, `tabMultiple Job Titles` AS mjt
                    WHERE jo.name = mjt.parent AND jo.to_date < '{today}' AND jo.order_status="Completed"
                    GROUP BY jo.name
                '''
                data=frappe.db.sql(sql, as_dict=1)
            elif filters.get('status')=='Ongoing':
                columns=[
                    {'fieldname':'name','label':(job_id),'fieldtype':'Link','options':jobOrder,'width':200},
                    {'fieldname':'select_job','label':(job_title),'fieldtype':'Data','width':150},
                    {'fieldname':'from_date','label':(date_time),'fieldtype':'Data','width':200},
                    {'fieldname':'job_site','label':('Location'),'fieldtype':'Data' ,'width':200},
                    {'fieldname':'total_no_of_workers','label':(no_of_workers),'fieldtype':'Int','width':200},
                    {'fieldname':'staff_org_claimed','label':(staffing_company),'fieldtype':'Data','width':200}
                ]
                sql = f'''
                    SELECT jo.name,
                    GROUP_CONCAT(DISTINCT mjt.select_job ORDER BY mjt.select_job SEPARATOR ', ') AS select_job,
                    CONCAT(jo.from_date, ', ', MIN(TIME_FORMAT(mjt.job_start_time, '%H:%i'))) AS from_date, jo.job_site, jo.total_no_of_workers, jo.staff_org_claimed
                    FROM `tabJob Order` AS jo, `tabMultiple Job Titles` AS mjt
                    WHERE jo.name = mjt.parent AND jo.from_date<'{today}' AND jo.to_date >'{today}' AND jo.order_status="Ongoing"
                    GROUP BY jo.name
                '''
                data=frappe.db.sql(sql, as_dict=1)
            elif filters.get('status')=='Upcoming':
                columns=[
                    {'fieldname':'name','label':(job_id),'fieldtype':'Link','options':jobOrder,'width':200},
                    {'fieldname':'select_job','label':(job_title),'fieldtype':'Data','width':150},
                    {'fieldname':'from_date','label':(date_time),'fieldtype':'Data','width':200},
                    {'fieldname':'job_site','label':('Location'),'fieldtype':'Data','width':200},
                    {'fieldname':'bid','label':(bids_received),'fieldtype':'Int','width':200},
                    {'fieldname':'claim','label':(claimed_by),'fieldtype':'Data','width':200},
                ]
                sql = f'''
                    SELECT jo.name,
                    GROUP_CONCAT(DISTINCT mjt.select_job ORDER BY mjt.select_job SEPARATOR ', ') AS select_job,
                    CONCAT(jo.from_date, ', ', MIN(TIME_FORMAT(mjt.job_start_time, '%H:%i'))) AS from_date, jo.job_site, jo.bid, REPLACE(jo.claim, '~', ', ') AS claim,
                    CONCAT('<button type="button" class="btn-primary" onClick="view_joborder(\''', jo.name, \''')">View</button>')
                    FROM `tabJob Order` AS jo, `tabMultiple Job Titles` AS mjt
                    WHERE jo.name = mjt.parent AND jo.to_date > '{today}' AND jo.order_status="Upcoming"
                    GROUP BY jo.name
                '''
                data=frappe.db.sql(sql, as_list=1)
        else:
            if filters.get('status')==None:
                columns=[
                    {'fieldname':'name','label':(job_id),'fieldtype':'Link','options':jobOrder,'width':150},
                    {'fieldname':'select_job','label':(job_title),'fieldtype':'Data','width':150},
                    {'fieldname':'from_date','label':(date_time),'fieldtype':'Data','width':150},
                    {'fieldname':'job_site','label':('Location'),'fieldtype':'Data','width':150},
                    {'fieldname':'total_no_of_workers','label':(no_of_workers),'fieldtype':'Int','width':150},
                    {'fieldname':'bid','label':(bids_received),'fieldtype':'Int','width':150},
                    {'fieldname':'claim','label':(claimed_by),'fieldtype':'Data','width':150},
                    {'fieldname':'staff_org_claimed','label':(staffing_company),'fieldtype':'Data','width':150}
                ]
                sql = f'''
                    SELECT jo.name,
                    GROUP_CONCAT(DISTINCT mjt.select_job ORDER BY mjt.select_job SEPARATOR ', ') AS select_job,
                    CONCAT(jo.from_date, ', ', MIN(TIME_FORMAT(mjt.job_start_time, '%H:%i'))) AS from_date, jo.job_site, jo.total_no_of_workers, jo.bid, REPLACE(jo.claim, '~', ', ') AS claim, jo.staff_org_claimed
                    FROM `tabJob Order` AS jo, `tabMultiple Job Titles` AS mjt
                    WHERE jo.name = mjt.parent AND jo.company IN (SELECT company FROM `tabEmployee` WHERE email = "{user_name}")
                    GROUP BY jo.name
                '''
                data=frappe.db.sql(sql, as_dict=1)
            elif filters.get('status')=='Completed':
                columns=[
                    {'fieldname':'name','label':(job_id),'fieldtype':'Link','options':jobOrder,'width':200},
                    {'fieldname':'select_job','label':(job_title),'fieldtype':'Data','width':150},
                    {'fieldname':'from_date','label':(date_time),'fieldtype':'Data','width':200},
                    {'fieldname':'job_site','label':('Location'),'fieldtype':'Data' ,'width':200},
                    {'fieldname':'total_no_of_workers','label':(no_of_workers),'fieldtype':'Int','width':200},
                    {'fieldname':'staff_org_claimed','label':(staffing_company),'fieldtype':'Data','width':200},
                    {'fieldname': 'view', 'label':('View'),'width': 60}, 
                    {'fieldname': 'repeat', 'label':('Repeat'),'width': 75}    
                ]
                sql = f'''
                    SELECT jo.name,
                    GROUP_CONCAT(DISTINCT mjt.select_job ORDER BY mjt.select_job SEPARATOR ', ') AS select_job,
                    CONCAT(jo.from_date, ', ', MIN(TIME_FORMAT(mjt.job_start_time, '%H:%i'))) AS from_date, jo.job_site, jo.total_no_of_workers, jo.staff_org_claimed,
                    CONCAT('<button type="button" class="btn-primary" onClick="view_joborder(\''', jo.name ,\''')">View</button>'),
                    CONCAT('<button type="button" class="btn-primary" onClick="repeat_joborder(\''', jo.name ,\''')">Repeat</button>')
                    FROM `tabJob Order` AS jo, `tabMultiple Job Titles` AS mjt
                    WHERE jo.name = mjt.parent AND jo.to_date < '{today}' AND jo.order_status="Completed"
                    AND jo.company IN (SELECT company FROM `tabEmployee` WHERE email = '{user_name}')
                    GROUP BY jo.name
                '''
                data=frappe.db.sql(sql, as_list=1)
            elif filters.get('status')=='Ongoing':
                columns=[
                    {'fieldname':'name','label':(job_id),'fieldtype':'Link','options':jobOrder,'width':200},
                    {'fieldname':'select_job','label':(job_title),'fieldtype':'Data','width':150},
                    {'fieldname':'from_date','label':(date_time),'fieldtype':'Data','width':200},
                    {'fieldname':'job_site','label':('Location'),'fieldtype':'Data' ,'width':200       },
                    {'fieldname':'total_no_of_workers','label':(no_of_workers),'fieldtype':'Int','width':200},
                    {'fieldname':'staff_org_claimed','label':(staffing_company),'fieldtype':'Data','width':200}
                ]
                sql = f'''
                    SELECT jo.name,
                    GROUP_CONCAT(DISTINCT mjt.select_job ORDER BY mjt.select_job SEPARATOR ', ') AS select_job,
                    CONCAT(jo.from_date, ', ', MIN(TIME_FORMAT(mjt.job_start_time, '%H:%i'))) AS from_date, jo.job_site, jo.total_no_of_workers, jo.staff_org_claimed
                    FROM `tabJob Order` AS jo, `tabMultiple Job Titles` AS mjt
                    WHERE jo.name = mjt.parent AND jo.from_date<'{today}' AND jo.to_date>'{today}' AND jo.order_status="Ongoing"
                    AND jo.company IN (SELECT company FROM `tabEmployee` WHERE email ="{user_name}")
                    GROUP BY jo.name
                '''
                data=frappe.db.sql(sql, as_dict=1)
            elif filters.get('status')=='Upcoming':
                columns=[
                    {'fieldname':'name','label':(job_id),'fieldtype':'Link','options':jobOrder,'width':200},
                    {'fieldname':'select_job','label':(job_title),'fieldtype':'Data','width':150},
                    {'fieldname':'from_date','label':(date_time),'fieldtype':'Data','width':200},
                    {'fieldname':'job_site','label':('Location'),'fieldtype':'Data','width':200},
                    {'fieldname':'bid','label':(bids_received),'fieldtype':'Int','width':200},
                    {'fieldname':'claim','label':(claimed_by),'fieldtype':'Data','width':200},
                    {'fieldname': 'view', 'label':('View'),'width': 60}
                ]
                sql = f'''
                    SELECT jo.name,
                    GROUP_CONCAT(DISTINCT mjt.select_job ORDER BY mjt.select_job SEPARATOR ', ') AS select_job,
                    CONCAT(jo.from_date, ', ', MIN(TIME_FORMAT(mjt.job_start_time, '%H:%i'))) AS from_date, jo.job_site, jo.bid, REPLACE(jo.claim, '~', ', ') AS claim,
                    CONCAT('<button type="button" class="btn-primary" onClick="view_joborder(\''', jo.name, \''')">View</button>')
                    FROM `tabJob Order` AS jo, `tabMultiple Job Titles` AS mjt
                    WHERE jo.name = mjt.parent AND jo.to_date > '{today}' AND jo.order_status="Upcoming"
                    AND jo.company IN (SELECT company FROM `tabEmployee` WHERE email = '{user_name}')
                    GROUP BY jo.name
                '''
                data=frappe.db.sql(sql, as_list=1)
        data = remove_duplicate(data)
        return columns,data
    except Exception as e:
        print(e, frappe.get_traceback())

def remove_duplicate(data):
    for row in data:
        if isinstance(row, list) and len(row) == 8 and '<button type="button" class="btn-primary" onClick="repeat_joborder(' in row[7]:
            staff_org_claimed = list(set(row[5].split("~"))) if row[5] else []
            staff_org_claimed.sort()
            row[5] = ", ".join(staff_org_claimed)
        else:
            if "staff_org_claimed" in row and row["staff_org_claimed"]:
                staff_org_claimed = list(set(row["staff_org_claimed"].split("~")))
                staff_org_claimed.sort()
                row["staff_org_claimed"] = ", ".join(staff_org_claimed)
    return data
