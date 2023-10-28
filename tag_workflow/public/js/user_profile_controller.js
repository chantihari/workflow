frappe.provide('frappe.energy_points');

class UserProfile {
	constructor(wrapper) {
		this.wrapper = $(wrapper);
		this.page = frappe.ui.make_app_page({
			parent: wrapper,
		});
		this.sidebar = this.wrapper.find('.layout-side-section');
		this.main_section = this.wrapper.find('.layout-main-section');
		this.wrapper.bind('show', () => {
			this.show();
		});
	}

	show() {
		
		let route = frappe.get_route();
		this.user_id = route[1] || frappe.session.user;
		if(this.user_id!=frappe.session.user){
			frappe.validated = false;
			frappe.msgprint(__('Invalid User'));
		}
		//validate if user
		if (route.length > 1) {
			frappe.dom.freeze(__('Loading user profile') + '...');
			frappe.db.exists('User', this.user_id).then(exists => {
				frappe.dom.unfreeze();
				if (exists) {
					this.make_user_profile();
				} else {
					frappe.msgprint(__('User does not exist'));
				}
			});
		} else {
			frappe.set_route('user-profile', frappe.session.user);
		}
	}

}

frappe.provide('frappe.ui');
frappe.ui.UserProfile = UserProfile;
