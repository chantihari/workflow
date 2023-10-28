# Copyright (c) 2021, SourceFuse and Contributors
# See license.txt

import frappe
import unittest
from tag_workflow.tag_workflow.doctype.assign_employee.assign_employee import  worker_data,approved_workers,get_dest,my_emp_work,get_souce,check_distance,get_employee,payrate_change,update_workers_filled ,check_old_value,check_emp_available, check_pay_rate
jobOrder='Job Order'
STREET = '101 A'
class TestAssignEmployee(unittest.TestCase):
							
	def test_worker_data(self):
	#Pass test case
		data = worker_data('JO-00005')
		self.assertEqual([{'no_of_workers': 3,'worker_filled': 2}],data)

	#Fail test case

		data_1 = worker_data('JO-00005')
		self.assertEqual([{'no_of_workers': 'a','worker_filled': 2}],data_1)

		data_2 = worker_data('JO-00005')
		self.assertEqual([{'no_of_workers': 3,'worker_filled': 3}],data_2)

		data_3 = worker_data('JO-00005')
		self.assertEqual([{'no_of_workers': 3,'worker_filled': 0}],data_3)

		data_4 = worker_data('JO-00005')
		self.assertEqual([{'no_of_workers': 3,'worker_filled': 5}],data_4)

		data_5 = worker_data('JO-00005')
		self.assertEqual([{'no_of_workers': 0 ,'worker_filled': 9}], data_5)

		

	def test_get_dest(self):
		name_in_upper = "New York"
		name_in_lower = "new york"
	#Pass test case
		loc_1 = get_dest({'street_address':STREET,'city':name_in_upper,'state':name_in_upper,'zip':'10010'})
		self.assertEqual('101 A,New York,New York,10010', loc_1)

		loc_2 = get_dest({'street_address':STREET,'state':name_in_upper,'zip':'10010'})
		self.assertEqual('', loc_2)

		loc_3 = get_dest({'street_address':STREET,'city':'','state':name_in_upper,'zip':'10010'})
		self.assertEqual('101 A,,New York,10010', loc_3)

		loc_4 = get_dest({'street_address':STREET,'city':name_in_lower,'state':name_in_lower,'zip':'10010'})
		self.assertEqual('101 A,new york,new york,10010', loc_4)

	# Fail Test Case
		loc_5 = get_dest({'street_address':STREET,'city':name_in_upper,'state':name_in_upper,'zip':'10010'})
		self.assertEqual('10010,New York,New York,101 A', loc_5)

		loc_6 = get_dest({'street_address':STREET,'state':name_in_upper,'zip':'10010'})
		self.assertEqual('101 A,New York,10010', loc_6)

		loc_7 = get_dest({'street_address':STREET,'city':name_in_lower,'state':name_in_lower,'zip':'10010'})
		self.assertEqual('101 A,new york,NEW york,10010', loc_7)		



	def test_get_souce(self):
	#Pass Case
		source_1 = get_souce('New York, NY 10116, USA')
		self.assertEqual('New York, NY 10116, USA,New York,New York,10116',source_1)
	
		source_2 = get_souce('new york, ny 10116, usa')
		self.assertEqual('New York, NY 10116, USA,New York,New York,10116',source_2)

	# Fail Case

		source_3 = get_souce('new york, ny 10116, usa')
		self.assertEqual('new nork, ny 10116, usa,new york,new york,10116',source_3)

		source_4 = get_souce('New York, NY 10010, USA')
		self.assertEqual('New York, NY 10010, USA,New York,New York,10011',source_4)

		source_5 = get_souce('New York, NY 10116, USA')
		self.assertEqual('New York, NY 10116, USA,New York,New York',source_5)

		source_6 = get_souce('Washington,D.C, USA')
		self.assertEqual('Washington,D.C, USA',source_6)

		source_7 = get_souce('10010')
		self.assertEqual('New York, NY 10010, USA,New York,New York,10011',source_7)


	def test_old_value(self):
	# Pass case
		val_1 = check_old_value('1862010294')
		self.assertEqual('HR-EMP-00003',val_1)

	#Fail Case
		val_2 = check_old_value('c3806845f9')
		self.assertEqual('HR-EMP-00003',val_2)

		val_3 = check_old_value('HR-EMP-00003')
		self.assertEqual('HR-EMP-00003',val_3)

		val_4 = check_old_value('00003')
		self.assertEqual('HR-EMP-00003',val_4)		

		val_5 = check_old_value('HREMP00003')
		self.assertEqual('HR-EMP-00003',val_5)


	def test_payrate_change(self):

	#Pass Case

		pay_1 = payrate_change('Genpact Hiring')
		self.assertEqual('failure',pay_1)

	#Fail Case

		pay_2 = payrate_change('Garvit Hiring')
		self.assertEqual('failure',pay_2)


	


	


	






