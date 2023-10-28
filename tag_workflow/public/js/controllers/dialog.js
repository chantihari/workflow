frappe.utils.icon = function(icon_name, size="sm", icon_class="", icon_style="", svg_class=""){
	let size_class = "";
		if (typeof size == "object") {
			icon_style += ` width: ${size ? size.width:""}; height: ${size?size.height:""}`;
		} else {
			size_class = `icon-${size}`;
		}
		return `<svg class="icon ${svg_class} ${size_class}" style="${icon_style}">
			<use class="${icon_class}"  id="Claim Order-close-icon" href="#icon-${icon_name}"></use>
		</svg>`;
	
	
}

frappe.msgprint = function(msg, title, is_minimizable) {
	if(!msg) return;
	let data;
	if($.isPlainObject(msg)) {
		data = msg;
	} else if(typeof msg==='string' && msg.startsWith('{')) {
		// passed as JSON
			data = JSON.parse(msg);
		} else {
			data = {'message': msg, 'title': title};
		}
	

	if(!data.indicator) {
		data.indicator = 'blue';
	}

	if (data.as_list) {
		const list_rows = data.message.map(m => `<li>${m}</li>`).join('');
		data.message = `<ul style="padding-left: 20px">${list_rows}</ul>`;
	}

	if (data.as_table) {
		const rows = data.message.map(row => {
			const cols = row.map(col => `<td>${col}</td>`).join('');
			return `<tr>${cols}</tr>`;
		}).join('');
		data.message = `<table class="table table-bordered" style="margin: 0;">${rows}</table>`;
	}

	if(data.message instanceof Array) {
		data.message.forEach(function(m) {
			frappe.msgprint(m);
		});
		return;
	}

	if(data.alert) {
		frappe.show_alert(data);
		return;
	}

	custom_dialog(data,is_minimizable)
	setup_action(data)
	return frappe.msg_dialog;
}

function primary_action(data){
	if (data.primary_action.server_action && typeof data.primary_action.server_action === 'string') {
		data.primary_action.action = () => {
			frappe.call({
				method: data.primary_action.server_action,
				args: {
					args: data.primary_action.args
				},
				callback() {
					if (data.primary_action.hide_on_success) {
						frappe.hide_msgprint();
					}
				}
			});
		}
	}

	if (data.primary_action.client_action && typeof data.primary_action.client_action === 'string') {
		let parts = data.primary_action.client_action.split('.');
		let obj = window;
		for (let part of parts) {
			obj = obj[part];
		}
		data.primary_action.action = () => {
			if (typeof obj === 'function') {
				obj(data.primary_action.args);
			}
		}
	}

	frappe.msg_dialog.set_primary_action(
		__(data.primary_action.label || data.primary_action_label || "Done"),
		data.primary_action.action
	);
}

function custom_dialog(data,is_minimizable){
	if(!frappe.msg_dialog) {
		frappe.msg_dialog = new frappe.ui.Dialog({
			title: __("Message"),
			onhide: function() {
				if(frappe.msg_dialog.custom_onhide) {
					frappe.msg_dialog.custom_onhide();
				}
				frappe.msg_dialog.msg_area.empty();
			},
			minimizable: data.is_minimizable || is_minimizable
		});

		// class "msgprint" is used in tests
		frappe.msg_dialog.msg_area = $(`<div class="msgprint" id="${cur_frm.doctype}-msgprint">`)
			.appendTo(frappe.msg_dialog.body);

		frappe.msg_dialog.clear = function() {
			frappe.msg_dialog.msg_area.empty();
		}

		frappe.msg_dialog.indicator = frappe.msg_dialog.header.find('.indicator');
	}

}
function setup_action(data){
	// setup and bind an action to the primary button
	if (data.primary_action) {
		primary_action(data)
	} else if (frappe.msg_dialog.has_primary_action) {
			frappe.msg_dialog.get_primary_btn().addClass('hide');
			frappe.msg_dialog.has_primary_action = false;
		}
	

	if (data.secondary_action) {
		frappe.msg_dialog.set_secondary_action(data.secondary_action.action);
		frappe.msg_dialog.set_secondary_action_label(__(data.secondary_action.label || "Close"));
	}

	if(data.message==null) {
		data.message = '';
	}

	if(data.message.search(/<br>|<p>|<li>/)==-1) {
		frappe.utils.replace_newlines(data.message);
	}

	let msg_exists = false;
	if(data.clear) {
		frappe.msg_dialog.msg_area.empty();
	} else {
		msg_exists = frappe.msg_dialog.msg_area.html();
	}

	if(data.title || !msg_exists) {
		// set title only if it is explicitly given
		// and no existing title exists
		frappe.msg_dialog.set_title(data.title || __('Message', null, 'Default title of the message dialog'));
	}

	show_indicator(data,msg_exists)
	frappe.msg_dialog.show();
}
function show_indicator(data,msg_exists){
	// show / hide indicator
	if(data.indicator) {
		frappe.msg_dialog.indicator.removeClass().addClass('indicator ' + data.indicator);
	} else {
		frappe.msg_dialog.indicator.removeClass().addClass('hidden');
	}

	// width
	if (data.wide) {
		// msgprint should be narrower than the usual dialog
		if (frappe.msg_dialog.wrapper.classList.contains('msgprint-dialog')) {
			frappe.msg_dialog.wrapper.classList.remove('msgprint-dialog');
		}
	} else {
		// msgprint should be narrower than the usual dialog
		frappe.msg_dialog.wrapper.classList.add('msgprint-dialog');
	}

	if(msg_exists) {
		frappe.msg_dialog.msg_area.append("<hr>");
	// append a <hr> if another msg already exists
	}

	frappe.msg_dialog.msg_area.append(data.message);

	// make msgprint always appear on top
	frappe.msg_dialog.$wrapper.css("z-index", 2000);
}