import frappe
from frappe import _, msgprint, throw
import json, requests, time
from rq import Queue, Worker
from rq.command import send_stop_job_command
from frappe.utils.background_jobs import get_redis_conn
from frappe.utils.doctor import purge_pending_jobs
from frappe.utils import now_datetime
from tag_workflow.utils.notification import make_system_notification
SYS_SETTING = 'System Settings'
tag_gmap_key = frappe.get_site_config().tag_gmap_key or ""

JAZZHR_API_URL="https://api.resumatorapi.com/v1/applicants/"
JAZZHR_API_KEY_PARAM = "?apikey="
GOOGLE_API_URL=f"https://maps.googleapis.com/maps/api/geocode/json?key={tag_gmap_key}&address="
JAZZHR_APPLICANT_DETAIL = "tag_workflow.utils.jazz_integration.jazzhr_fetch_applicant_details"
JAZZHR_RATE_LIMIT_CALLS = 80
JAZZHR_RATE_LIMIT_SECONDS = 40
JAZZHR_MAX_ITR = 1500

DATE_FORMAT = "%m-%d-%Y"
TIME_FORMAT = "%H:%M"
DATETIME_FORMAT = DATE_FORMAT + " " + TIME_FORMAT

NOTIFY_METHOD ="tag_workflow.utils.jazz_integration.notify_user"


@frappe.whitelist()
def jazzhr_fetch_applicants(api_key, company):
    comp = frappe.get_doc("Company",company)
    decrypted_api_key = comp.get_password('jazzhr_api_key')
    frappe.cache().set('Insert'+str(company),0)
    try:
        notify_user(company,f'Request to Grab New Records from JazzHR started at {now_datetime().strftime(DATETIME_FORMAT)}. This process will run in the background. A notification will be received when the job completes.')
        frappe.enqueue("tag_workflow.utils.jazz_integration.jazzhr_fetch_applicants_data", queue='default', is_async=True, job_name=company, timeout=25000, api_key=decrypted_api_key, company=company)
    except Exception as e:
        frappe.log_error(e, "JazzHR - jazzhr_fetch_applicants fail long")
        check_sent_notification(company,2)

#------------JAZZHR applicants----------------------#
def jazzhr_fetch_applicants_data(api_key, company):
    try:
        redis = frappe.cache()
        page_no, count, fetch_applicants = 1, 0, 1
        key = "jazz_"+str(company)

        while(fetch_applicants > 0):
            if(page_no % JAZZHR_RATE_LIMIT_CALLS == 0):
                print("sleeping....")
                time.sleep(JAZZHR_RATE_LIMIT_SECONDS)

            applicants_data_url = JAZZHR_API_URL + "page/" + str(page_no) + JAZZHR_API_KEY_PARAM + api_key
            response = requests.get(applicants_data_url)
            page_no += 1

            if(response.status_code == 200 and len(response.json()) > 0):
                for a in response.json():
                    if not frappe.db.exists("Employee", {"employee_number": a['id'], "company": company}):
                        redis.hset(key, count, a['id'])
                        count += 1
            elif(len(response.json()) <= 0):
                fetch_applicants = 0

        #-------------jazzhr applicant data long queue function-------------#
        jazzhr_applicant_data(api_key, company)
    except Exception as e:
        frappe.log_error(e, "JazzHR - jazzhr_fetch_applicants data fail")
        check_sent_notification(company,2)


#---------------long queue------------------#
def jazzhr_applicant_data(api_key, company):
    try:
        key = "jazz_"+str(company)
        redis = frappe.cache()
        applicant_list = redis.hgetall(key)
        rng = int(len(applicant_list)/JAZZHR_MAX_ITR) + 1
        start = 0
        end = JAZZHR_MAX_ITR
        for i in range(0, rng):
            print(i)
            frappe.enqueue("tag_workflow.utils.jazz_integration.jazzhr_fetch_applicant_other_info", queue='long', job_name=company, is_async=True, api_key=api_key, company=company, start=start, end=end)
            start += JAZZHR_MAX_ITR
            end += JAZZHR_MAX_ITR

        #--------sql update---------------#
        frappe.enqueue("tag_workflow.utils.jazz_integration.jazzhr_make_sql", queue='long', job_name=company, is_async=True, api_key=api_key, company=company)
    except Exception as e:
        frappe.log_error(e, "JazzHR - start_log_queue")
        check_sent_notification(company,2)

#--------------applicant info----------------#
def jazzhr_fetch_applicant_other_info(api_key, company, start, end):
    try:
        redis = frappe.cache()
        key = "jazz_"+str(company)
        count, exce = 1, 1
        for i in range(start, end):
            try:
                applicant_id = redis.hget(key, i)
                # enqueue with increasing time to take care of rate limiting
                if(count % JAZZHR_RATE_LIMIT_CALLS == 0):
                    time.sleep(60)
                if(applicant_id):
                    frappe.enqueue(JAZZHR_APPLICANT_DETAIL, job_name=company, is_async=True, timeout=900, api_key=api_key, applicant_id=applicant_id, company=company, action=2)
                count += 1
                exce = 1
            except Exception as e:
                frappe.log_error(e, "JazzHR - jazzhr_fetch_applicant_other_info per user")
                count -= 1
                exce += 1
                if(exce <= 3):
                    continue
    except Exception as e:
        frappe.log_error(e, "JazzHR - jazzhr_fetch_applicant_other_info")
        check_sent_notification(company,2)


#--------------------------------------#
@frappe.whitelist()
def jazzhr_fetch_applicant_details(api_key, applicant_id, company, action):
    try:
        applicant_details_url = JAZZHR_API_URL + applicant_id + JAZZHR_API_KEY_PARAM + api_key
        response = requests.get(applicant_details_url)
        update_redis(applicant_id, company, response, action)
    except Exception as e:
        frappe.log_error(e, "JazzHR applicant detail")
        check_sent_notification(company,action)

def update_redis(applicant_id, company, response, action):
    try:
        applicant_details = response.json()
        applicant_key = f"{company}-{applicant_id}"
        if(len(applicant_details) > 0):
            # save entire applicant record to redis
            redis = frappe.cache()
            redis.hset(applicant_key, 'employee_number', applicant_id)
            redis.hset(applicant_key, 'first_name', applicant_details['first_name'].strip('"'))
            redis.hset(applicant_key, 'last_name', applicant_details['last_name'].strip('"'))
            redis.hset(applicant_key, 'company', company)
            redis.hset(applicant_key, 'contact_number', applicant_details['phone'] or "")
            redis.hset(applicant_key, 'employee_gender', applicant_details['eeo_gender'] if applicant_details['eeo_gender'] in ["Male", "Female", "Decline to answer"] else '')
            redis.hset(applicant_key, 'military_veteran', 1 if applicant_details['eeoc_veteran'] == 'I AM A PROTECTED VETERAN' else 0)
            redis.hset(applicant_key, 'street_address', applicant_details['address'] if applicant_details['address'] != 'Unavailable' and applicant_details['address'] != '' else '')
            redis.hset(applicant_key, 'email', applicant_details['email'] or "")
            redis.hset(applicant_key, 'city', '')
            redis.hset(applicant_key, 'state', '')
            redis.hset(applicant_key, 'zip', 0)
            redis.hset(applicant_key, 'lat', '')
            redis.hset(applicant_key, 'lng', '')

            # fetch location data from google
            fetch_google_location_data(applicant_details, applicant_key, redis)
            if action == 1:
                update_emp_to_db(applicant_id, company)
    except Exception as e:
        frappe.log_error(e, "JazzHR redis update")
        check_sent_notification(company,action)

#-------------------google data------------#
def fetch_google_location_data(applicant_details, applicant_key, redis):
    try:
        if((applicant_details['location'] and applicant_details['location']) != '(No City Provided) (No State Provided) (No Postal Code Provided)'):
            google_location_data_url = GOOGLE_API_URL + applicant_details['location']
            google_response = requests.get(google_location_data_url)
            location_data = google_response.json()
            if(google_response.status_code == 200 and len(location_data)>0 and len(location_data['results'])>0):
                city, state, zip_code, lat, lng = emp_location_data(location_data)
                redis.hset(applicant_key, 'city', city)
                redis.hset(applicant_key, 'state', state)
                redis.hset(applicant_key, 'zip', zip_code)
                redis.hset(applicant_key, 'lat', lat)
                redis.hset(applicant_key, 'lng', lng)
    except Exception as e:
        frappe.log_error(e, "JazzHR Google Data")


def emp_location_data(address_dt):
    try:
        city, state, zip_code, lat, lng = '', '', 0, '', ''
        state_data = address_dt['results'][0]['address_components']
        for i in state_data:
            if 'administrative_area_level_1' in i['types']:
                state = i['long_name'] if i['long_name'] else ''
            elif 'postal_code' in i['types']:
                zip_code = int(i['long_name']) if i['long_name'].isdigit() else 0

        city_zip = address_dt['results'][0]['formatted_address'].split(',')
        city = city_zip[-3].strip() if len(city_zip)>2 and city_zip[-3].strip() else ''

        if(len(address_dt['results']) > 0):
            location = address_dt['results'][0]['geometry']['location']
            lat = location['lat']
            lng = location['lng']

        return city, state, zip_code, lat, lng
    except Exception as e:
        #frappe.msgprint('Some Error Occured while fetching address')
        frappe.log_error(e, "JazzHR address")
        return '', '', 0, '', ''


#------------sql/-----------------#
def jazzhr_make_sql(api_key, company):
    try:
        print(api_key)
        _key = "jazz_"+str(company)
        redis = frappe.cache()
        emp_last_number, count = 0, 0

        emp_count = frappe.db.sql(""" select * from `tabSeries` where name = "HR-EMP-" """, as_dict=1)
        if(emp_count):
            emp_last_number = emp_count[0]['current'] + 1

        sql = 'insert into `tabEmployee` (name, employee_number, employee_name, first_name, last_name, company, contact_number, employee_gender, military_veteran, street_address, email, city, state, zip, lat, lng, naming_series, lft, rgt, creation) values '

        records = [redis.hget(_key, e.decode("utf-8")) for e in redis.hgetall(_key)]
        records = list(dict.fromkeys(records))
        for r in records:
            applicant_id = company+"-"+r
            data = get_frm_redis_cache(applicant_id)
            if any(data):
                emp_name = ["HR-EMP-"+str(emp_last_number)]
                sql += str(tuple(emp_name + data + ["HR-EMP-", emp_last_number, emp_last_number+1, frappe.utils.now()])) + ","
                emp_last_number += 1
                count += 1

            redis.hdel(_key, r)
        if count > 0:
            frappe.db.sql(""" update `tabSeries` set current = %s where name = "HR-EMP-" """, emp_last_number)
            frappe.db.sql(sql[0:-1])
            frappe.db.commit()
            insert = redis.get('Insert'+str(company)) if redis.get('Insert'+str(company)) is not None else None
            if insert is not None and int(insert)>0:
                frappe.enqueue(NOTIFY_METHOD,company=company,msg=f'Grab New Records from JazzHR has completed with errors at {now_datetime().strftime(DATETIME_FORMAT)}. Please reach out to customer support for troubleshooting.',action=2)
            else:
                frappe.enqueue(NOTIFY_METHOD,company=company,msg=f'Grab New Records from JazzHR has completed successfully at {now_datetime().strftime(DATETIME_FORMAT)}.',action=2)
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(e, "JazzHR sql query")
        check_sent_notification(company,1)

def get_frm_redis_cache(applicant_id):
    try:
        redis = frappe.cache()

        if(frappe.cache().hgetall(applicant_id)):
            employee_number = redis.hget(applicant_id, 'employee_number')
            first_name = redis.hget(applicant_id, 'first_name')
            last_name = redis.hget(applicant_id, 'last_name')
            company = redis.hget(applicant_id, 'company')
            employee_name = first_name + " " + last_name
            contact_number = redis.hget(applicant_id, 'contact_number')
            employee_gender = redis.hget(applicant_id, 'employee_gender')
            military_veteran = redis.hget(applicant_id, 'military_veteran')
            street_address = redis.hget(applicant_id, 'street_address')
            email = redis.hget(applicant_id, 'email')
            city = redis.hget(applicant_id, 'city')
            state = redis.hget(applicant_id, 'state')
            zip_code = redis.hget(applicant_id, 'zip')
            lat = redis.hget(applicant_id, 'lat')
            lng = redis.hget(applicant_id, 'lng')
            return [employee_number, employee_name, first_name, last_name, company, contact_number, employee_gender, military_veteran, street_address, email, city, state, zip_code, lat, lng]
        else:
            return []
    except Exception as e:
        frappe.log_error(e, "JazzHR data from redis")
        return []

#--------------------------update emp records------------------#
@frappe.whitelist()
def jazzhr_update_applicants(api_key, company):
    try:
        frappe.cache().set('Update'+str(company),0)
        notify_user(company,f'Request to Update Existing Records from JazzHR started at {now_datetime().strftime(DATETIME_FORMAT)}. This process will run in the background. A notification will be received when the job completes.')
        emp_list = frappe.db.sql(""" select name, employee_number from `tabEmployee` where company = %s and employee_number IS NOT NULL and (first_name IN(NULL, "undefined", "None", "") or last_name IN(NULL, "unavailable", "None", "") or employee_gender IN(NULL, "undefined", "None", "") or contact_number IN(NULL, "undefined", "None", "") or employee_gender IN(NULL, "undefined", "None", "") or street_address IN(NULL, "undefined", "None", "") or email IN(NULL, "undefined", "None", "") or city IN(NULL, "undefined", "None", "") or state IN(NULL, "undefined", "None", "") or zip = 0 or lat IN(NULL, "undefined", "None", "") or lng IN(NULL, "undefined", "None", "")) """,company, as_dict=1)
        frappe.enqueue("tag_workflow.utils.jazz_integration.jazz_emp_update", queue='default', job_name=company, timeout=1200, api_key=api_key, company=company, emp_list=emp_list)
    except Exception as e:
        frappe.log_error(e, "JazzHR emp fetching")
        check_sent_notification(company,1)

def jazz_emp_update(api_key, company, emp_list):
    try:
        rng = int(len(emp_list)/JAZZHR_MAX_ITR) + 1
        start = 0
        end = JAZZHR_MAX_ITR
        for i in range(0, rng):
            print(i)
            frappe.enqueue("tag_workflow.utils.jazz_integration.jazz_make_emp_update_queue", queue='long', job_name=company, is_async=True, api_key=api_key, company=company, start=start, end=end, emp_list=emp_list)
            start += JAZZHR_MAX_ITR
            end += JAZZHR_MAX_ITR
    except Exception as e:
        frappe.log_error(e, "jazz_emp_update")
        check_sent_notification(company,1)

def jazz_make_emp_update_queue(api_key, company, start, end, emp_list):
    try:
        count, exce = 1, 1
        for e in emp_list[start:end]:
            try:
                if(count % JAZZHR_RATE_LIMIT_CALLS == 0):
                    time.sleep(120)
                frappe.enqueue(JAZZHR_APPLICANT_DETAIL, job_name=company, is_async=True, api_key=api_key, applicant_id=e['employee_number'], company=company, action=1)
                count += 1
                exce = 1
            except Exception as e:
                frappe.log_error(e, "JazzHR jazz_make_emp_update_queue")
                exce += 1
                count -= 1
                if(exce <= 3):
                    continue
        redis = frappe.cache()
        update = redis.get('Update'+str(company)) if redis.get('Update'+str(company)) is not None else None
        if update is not None and int(update)>0:
            frappe.enqueue(NOTIFY_METHOD,company=company,msg=f'Update Existing Records from JazzHR has completed with errors at {now_datetime().strftime(DATETIME_FORMAT)}. Please reach out to customer support for troubleshooting.',action=1)
        else:
            frappe.enqueue(NOTIFY_METHOD,company=company,msg=f'Update Existing Records from JazzHR has completed successfully at {now_datetime().strftime(DATETIME_FORMAT)}.',action=1)
    except Exception as e:
        frappe.log_error(e, "jazz_make_emp_update_queue")
        check_sent_notification(company,1)

def update_emp_to_db(applicant_id, company):
    try:
        applicant_key = f"{company}-{applicant_id}"
        redis = frappe.cache()
        emp = frappe.get_doc("Employee", {"employee_number": applicant_id, "company": company})
        for f in ["first_name", "last_name", "contact_number", "employee_gender", "street_address", "email", "city", "state", "zip", "lat", "lng"]:
            if(getattr(emp, f) in [None, "undefined", "None", "", 0]):
                frappe.db.set_value("Employee", emp.name, f, redis.hget(applicant_key, f))
        frappe.db.commit()
        redis.delete(applicant_id)
    except Exception as e:
        frappe.log_error(e, "JazzHR emp update")
        check_sent_notification(company,1)


#----------------------update single applicant---------------------#
@frappe.whitelist()
def update_single_employee(employee_number, company):
    try:
        api_key = frappe.db.get_value("Company", company, "jazzhr_api_key") or ""
        if(api_key):
            frappe.enqueue(JAZZHR_APPLICANT_DETAIL, job_name=company, is_async=True, api_key=api_key, applicant_id=employee_number, company=company, action=1)
        else:
            frappe.msgprint(_("JazzHR api key not found in company<b>({0})</b>.").format(company))
    except Exception as e:
        frappe.log_error(e, "JazzHR emp update single employee")





#-----------------------------------------#
@frappe.whitelist()
def button_disabled(company):
    try:
        from rq import Queue, Worker
        from frappe.utils.background_jobs import get_redis_conn
        conn = get_redis_conn()
        workers = Worker.all(conn)
        queues = Queue.all(conn)

        for worker in workers:
            job = worker.get_current_job()
            if job and job.kwargs.get('job_name') == company:
                    return 1

        for queue in queues:
            for job in queue.jobs:
                if job and job.kwargs.get('job_name') == company:
                    return 1
        return 0
    except Exception as e:
        return 0
        frappe.msgprint(e)

@frappe.whitelist()
def terminate_job(company):
    try:
        conn = get_redis_conn()
        workers = Worker.all(conn)
        queues = Queue.all(conn)

        for worker in workers:
            job = worker.get_current_job()
            if job and job.kwargs.get('job_name') == company:
                job.cancel()
                job.delete()

        for queue in queues:
            for job in queue.jobs:
                if job and job.kwargs.get('job_name') == company:
                    job.cancel()
                    job.delete()

        return 1
    except Exception as e:
        frappe.log_error(e, "JazzHR terminate_job")
        return 0

def notify_user(company,msg,action=None):
    sub = "Jazz Hr Notification"
    rds = frappe.cache()
    try:
        #----------allowed_user------------------#
        users = get_user_list(company)
        #-------------------Initial Notification------------------------------------------#
        if len(users)>0 and action is None:make_system_notification(users,msg,'Company',company,sub)
        #------------------Success Notification----------------------#
        elif len(users)>0 and  action is not None:
            update = rds.get('Update'+str(company)) if rds.get('Update'+str(company)) is not None else None
            insert = rds.get('Insert'+str(company)) if rds.get('Insert'+str(company)) is not None else None
            if (action == 1 and update is not None) or (action == 2 and insert is not None):
                make_system_notification(users,msg,'Company',company,sub)
                free_redis(company,action,rds)
    except Exception as e:
        frappe.log_error(e,'user notification error')

def check_sent_notification(company, action):
    try:
        rds = frappe.cache()
        if action == 2 and  int(rds.get('Insert'+str(company))) == 0:
            rds.set('Insert'+str(company),1)
        elif action ==1 and  int(rds.get('Update'+str(company))) == 0:
            rds.set('Update'+str(company),1)
    except Exception as e:
        frappe.log_error(e,'check_sent_notifiy_error')

def free_redis(company,action,redis):
    try:
        if action ==1: 
            redis.delete('Update'+str(company)) 
        else:
            redis.delete('Insert'+str(company))
    except Exception as e:
        frappe.log_error(e,'redis_error') 

def get_user_list(company):
    try:
        sql = None
        if 'Tag Admin' in frappe.get_roles(frappe.session.user): 
            sql = """ select parent from `tabHas Role`
            where role in ("Staffing Admin","Staffing User")
            and parent in(select name from `tabUser`
            where company = '{0}' and enabled= '1') 
            UNION
            select parent from `tabHas Role`
            where role ="Tag Admin"
            and parent in(select name from `tabUser`
            where company = 'TAG' and enabled= '1')  
            """.format(company)
        else:
            sql = """ select parent from `tabHas Role`
            where role in ("Staffing Admin","Staffing User")
            and parent in(select name from `tabUser`
            where company = '{0}' and enabled= '1' ) """.format(company)
        user_list = frappe.db.sql(sql, as_dict=1)
        if user_list is not None:
            users = [usr['parent'] for usr in user_list]
            return users
        return []
    except Exception as e:
        frappe.log_error(e,'sql_error')
        return []

def schedule_job():
    if int(frappe.db.get_value(SYS_SETTING,SYS_SETTING,'job_disable'))==1:
        return
    sql  ="""select name from `tabCompany` where jazzhr_api_key is not null and organization_type='Staffing' and make_organization_inactive='0'"""
    try:
        companies = frappe.db.sql(sql,as_dict=1)
        if len(companies)>0:
            for c in companies:
                doc = frappe.get_doc('Company',c['name'])
                api_key = doc.get_password('jazzhr_api_key')
                #----------------------------------Jazzhr_Grab_Record--------------------------------------------------------------------------#
                frappe.enqueue("tag_workflow.utils.jazz_integration.jazzhr_fetch_applicants",api_key=api_key,company=doc.name)
                #----------------------------------Jazzhr_Insert_Record-------------------------------------------------------------------------------------------#
                frappe.enqueue("tag_workflow.utils.jazz_integration.jazzhr_update_applicants",api_key=api_key,company=doc.name)
    except Exception as e:
        frappe.log_error(e,'cron_job_error')

@frappe.whitelist()
def enable_disable_job(enable):
    conn = get_redis_conn()
    workers = Worker.all(conn)
    sql  ="""select name from `tabCompany` where jazzhr_api_key is not null and organization_type='Staffing' and make_organization_inactive='0'"""
    try:
        if int(enable)==0:
            frappe.db.set_value(SYS_SETTING,SYS_SETTING,'job_disable',1,update_modified=False)
            data =frappe.db.sql(sql,as_dict=1)
            purge_pending_jobs()
            for c in data:
                for worker in workers:
                    job = worker.get_current_job()
                    if job and job.kwargs.get('job_name') == c['name']:
                        send_stop_job_command(conn,job.id)
        else:
            frappe.db.set_value(SYS_SETTING,SYS_SETTING,'job_disable',0,update_modified=False)
        frappe.publish_realtime(event='sync_doc',doctype= SYS_SETTING, docname = SYS_SETTING)
        return "OK"
    except Exception as e:
        frappe.log_error(e,"terminating_job")
        return "error"

@frappe.whitelist()
def check_status():
    try:
        return frappe.db.get_value(SYS_SETTING,SYS_SETTING,'job_disable')
    except Exception as e:
        print(e)
