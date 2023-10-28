frappe.flags.staff_home = null;
frappe.pages['staff_company_list'].on_page_load = function (wrapper) {
	let page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Staffing Companies',
		single_column: true
	});
	wrapper.face_recognition = new frappe.FaceRecognition(wrapper, page);

}
frappe.FaceRecognition = Class.extend({
	init: function (wrapper, page) {
		let me = this;
		this.parent = wrapper;
		this.page = this.parent.page;
		setTimeout(function () {
			me.setup(wrapper, page);
		}, 0);
		$('h3[title = "Staff Company List"]').html("Staffing Companies");
		frappe.flags.staff_home = me
	},
	setup: function (wrapper, page) {
		let me = this;
		this.start = 0
		this.end = 20
		this.filter_loc = localStorage.getItem(frappe.session.user + 'loc') ? JSON.parse(localStorage.getItem(frappe.session.user + 'loc')) : [];
		this.filters = {'radius':25}
		this.options = []
		this.data = null;
		this.accreditation = [];
		this.staff_comps = '';
		this.page_value = [20,100,500];
		this.body = $('<div></div>').appendTo(this.page.main);
		$(frappe.render_template('staff_company_list', "")).appendTo(this.body);
		me.show_profile(wrapper, page);
		this.$paging_area =$(`
		<div class="list-paging-area level">
			<div class="level-left">
				<div class="btn-group">
					<button type="button" class="btn btn-default btn-sm btn-paging btn-info" data-value="20">20
					</button>
					<button type="button" class="btn btn-default btn-sm btn-paging" data-value="100">100
					</button>
					<button type="button" class="btn btn-default btn-sm btn-paging" data-value="500">500
					</button>
				</div>
			</div>
		</div>`)
		$('.paging-area').append(this.$paging_area)
		this.$paging_area.on("click", ".btn-paging", (e) => {
			const $this = $(e.currentTarget);
			this.end = $this.data().value;
			this.$paging_area.find(".btn-paging").removeClass("btn-info");
            $this.addClass("btn-info");
			this.update_paging_value();
			this.refresh()
		})
		this.$paging_area.on("click", ".btn-location", (e) => {
			const $this = $(e.currentTarget);
			this.end = $this.data().value;
			this.refresh()
			me.display_modal();
		})
		if (frappe.boot.tag.tag_user_info.company_type == 'Hiring'|| frappe.boot.tag.tag_user_info.company_type == "Exclusive Hiring") {
			let str=' mi';
			document.getElementById('dropdownMenuLink').innerText = 25+str;
			me.get_industries()
			me.add_fields()
			let input = document.getElementById('citys');
			let autocomplete = new google.maps.places.Autocomplete(input);
			google.maps.event.addListener(autocomplete, 'place_changed', function () {
			let place = autocomplete.getPlace();							
			me.filters['city'] = place.name
			me.update_list()
			me.refresh()							
			})

		}



	},
	show_profile: function (_wrapper, _page) {
		let location_list = localStorage.getItem(frappe.session.user + 'loc') ? JSON.parse(localStorage.getItem(frappe.session.user + 'loc')) : [];
		if ((localStorage.getItem(frappe.session.user + 'location') == 1 && JSON.parse(localStorage.getItem(frappe.session.user + 'loc')).includes(location_list[0])) || localStorage.getItem(frappe.session.user + 'custom-address')) {
			$(".btn-location").css({background: 'var(--gray-600)',border: 'var(--gray-600)',color: 'var(--white)','font-weight':'var(--text-bold)',padding: '0.5rem 1rem'});
			$(".btn-location").hover(function() {
				$(this).css("background", "var(--gray-600)");
			  }
			)
		}
		else{
			$(".btn-location").css({background: 'var(--control-bg)',border: 'var(--gray-600)',color: 'var(--text-color)','font-weight':'unset',padding: '0.5rem 1rem'});
			$(".btn-location").hover(function() {
				$(this).css("background", "var(--gray-400)");
			  }, function() {
				$(this).css("background", "var(--control-bg)");
			  }
			)
		}
		
		custom_address_update_data(this);
		frappe.call({
			method: "tag_workflow.tag_workflow.page.staff_company_list.staff_company_list.comp",
			args: {
				company_name: frappe.boot.tag.tag_user_info.company,
				filters: this.filters,
				start:this.start,
				end:this.end
			},
			freeze: true,
			freeze_message:  __("<b>Loading") + "...</b>",
			callback: async function (r) {
				let data = r.message;
				
				let profile_html = ``;
				for (let p in data) {
					profile_html = await sorted_favourite_companies(data[p], profile_html, frappe.boot.tag.tag_user_info.company_type);
				}
				$("#myTable").html(profile_html);
				$(document).ready(function(){
					$('[data-toggle="tooltip"]').tooltip({
						container: 'body',
						placement: 'right',
						offset:'0,9'
					}); 
				});
				populate_filter();
			}
		})
	},
	add_fields: function () {
		const field = [
			{
				'parent': '#company', 'name': 'company', 'type': 'Data', 'class': 'input-xs', 'placeholder': 'Company Name','options':this.staff_comps,'filter':1, 'handler': () => {
					this.filters['company'] = document.getElementById('companys').value;
					this.update_list()
					this.refresh()
				}
			},
			{
				'parent': '#industry', 'name': 'industry', 'type': 'MultiSelectList', 'class': 'input-xs', 'placeholder': 'Industry', 'options': this.options, 'handler': () => {
					let  industry_list = document.getElementsByClassName('selectable-item industry selected');
					this.filters['industry'] = get_option_data(industry_list)
					this.update_list()
					this.refresh()
				}
			},
			{
				'parent': '#city', 'name': 'city', 'type': 'Data', 'class': 'input-xs ', 'placeholder': 'City', 'handler': () => {
					let self = this;
					get_city_filter_keyword(self);
				}
			},
			{
				'parent': '#rating', 'name': 'rating', 'type': 'Data', 'class': 'input-xs ', 'placeholder': 'Avg Rating', 'handler': () => {					
					this.filters['rating'] = document.getElementById('ratings').value;
					this.update_list()
					this.refresh()
				}
			},
			{
				'parent': '#accreditation', 'name': 'accreditation', 'type': 'MultiSelectList','class': 'input-xs ', 'placeholder': 'Accreditations', 
				'options':this.accreditation, 'handler': () => {
					let  accreditation_list = document.getElementsByClassName('selectable-item accreditation selected');
					this.filters['accreditation'] = get_option_data(accreditation_list)
					this.refresh()
				}
			},


		]
		for (let f in field) {
			let control = frappe.ui.form.make_control({
				parent: field[f]['parent'],
				df: {
					label: '',
					fieldname: field[f]['name'],
					fieldtype: field[f]['type'],
					input_class: field[f]['class'],
					placeholder: field[f]['placeholder'],
					options: field[f]['options'] ? field[f]['options'] : '',
					onchange: field[f]['handler']
				},
				render_input: true,
			})
			control.$wrapper.find(".input-with-feedback").attr("id", field[f]['name'] + "s")
		}
		document.getElementById('ratings').setAttribute('type', 'number')
		document.getElementById('companys').addEventListener('keyup',(e)=>{
			if(!e.target.value){
				this.filters['company'] = null;
				this.refresh()
			}
				
		})

		setTimeout(()=>{
			
			if (localStorage.getItem("city")) {
				this.filters['city']=localStorage.getItem("city")
		        document.getElementById('citys').value=localStorage.getItem("city")
		        this.refresh()
			}
			else if(localStorage.getItem("company_name")){
				this.filters['company']=localStorage.getItem("company_name")
		        document.getElementById('companys').value=localStorage.getItem("company_name")
		        this.refresh()
			}
			else{
				
				if(localStorage.getItem("industry")){
					document.querySelector('.input-xs > div').click();
				setTimeout(()=>{
					let li = document.querySelector('#industry > div > div > div.control-input-wrapper > div.control-input > div > ul > div ')
					select_industry_default_filter(li);
					this.filters['industry'] = localStorage.getItem("industry")
					document.querySelector('.input-xs > div').click();
				},300)
			}
		        this.refresh()
			}
			
	   }, 200);
	},
	refresh: function () {
		this.show_profile();
		this.update_list()
	},
	get_industries: function () {
		if (frappe.boot.tag.tag_user_info.company_type == "Hiring" ||frappe.boot.tag.tag_user_info.company_type == "Exclusive Hiring" ) {
			frappe.call({
				method: 'tag_workflow.tag_workflow.page.staff_company_list.staff_company_list.get_industries',
				args: { cur_user: frappe.session.user },
				async: 0,
				callback: (r) => {
					if (r.message) {
						for (let i in r.message[0])
							this.options.push(r.message[0][i]);
						for (let j in r.message[1])
							this.accreditation.push(r.message[1][j])
						this.staff_comps += r.message[2]
					}
				}
			})
		}
	},
	update_list: function(){
		this.start = 0
		this.end = 20
		this.update_paging_value();
		this.$paging_area.find(`.btn-paging[data-value="${this.end}"]`)

	},
	update_paging_value: function(){
		for (let p in this.page_value)
			this.$paging_area.find(`.btn-paging[data-value="${this.page_value[p]}"]`).removeClass('active')
 
	},

	display_modal:function (){
		this.order_location = get_job_site_location();
		this.create_table(this.order_location);
		this.add_fields = [{ label: 'Location', fieldname: 'rb1', fieldtype: 'Check', default: 1 }, { label: 'Custom', fieldname: 'rb2', fieldtype: 'Check' }, { label: '', fieldname: 'location', fieldtype: 'HTML', options: this.html }];
		let dialog = new frappe.ui.Dialog({
			title: 'Please select one or more addresses',
			fields: this.add_fields,
		});
			dialog.show();
		let me = this
		toggle_radio_button(dialog,me);
		me.filter_loc = []
		me.filter_loc = localStorage.getItem(frappe.session.user + 'loc') ? JSON.parse(localStorage.getItem(frappe.session.user + 'loc')) : [];
		dialog.set_primary_action(__('Submit'), function () {
			localStorage.setItem(frappe.session.user + 'location', 1);
			me.update_radius();
			me.start = 0;
			me.page_length = 20;
			dialog.hide();
			localStorage.setItem(frappe.session.user + 'loc', JSON.stringify(me.filter_loc));
			get_radius(me.filters['radius']?me.filters['radius']:25)			
			me.$paging_area.find(`.btn-info`).removeClass("btn-info");
			me.$paging_area.find(`.btn-paging[data-value="${me.page_length}"]`).addClass("btn-info");
			me.refresh();
		});
		setTimeout(() => { this.select_deselect_row1(me,dialog) }, 500)
	},
	update_radius: function() {
		if ([5, 10, 25, 50, 100].includes(parseInt(localStorage.getItem(frappe.session.user + 'radius'))))
			this.radius = parseInt(localStorage.getItem(frappe.session.user + 'radius'));
		else
			this.radius = 'All';
			
		/*------------------------------------------------------*/
		const ip_t = document.querySelectorAll('#custom-address');
		const val = ip_t[document.querySelectorAll('#custom-address').length - 1].value;
		if (!localStorage.getItem(frappe.session.user + 'custom-addres') && val != '') {
			this.custom_address = val;
			localStorage.setItem(frappe.session.user + 'custom-address', val)
		}
	},

	select_deselect_row1:function (me,dialog) {
		const items = document.querySelectorAll('.location');
		const input = document.querySelectorAll('#custom-address');
		this.single_row_event(items, input,me,dialog);
	},
	
	single_row_event:function(items, input,me,dialog){
		items.forEach(i => i.addEventListener(
			"change",
			e => {
				let e_ = dialog.fields_dict['location'].disp_area.querySelector('#main')
				e_.checked =false;
				if (i.checked && i.id != 'custom-location') {
					add_rows_(e.currentTarget.value,me);
				} else if (!i.checked && i.id != 'custom-location') {
					remove_rows_(e.currentTarget.value,me);
				}
			}));
		/*----------Input-Event--------------*/
	
		input[document.querySelectorAll('#custom-address').length - 1].addEventListener('keyup', (e) => {
			this.custom_address = e.currentTarget.value;
			localStorage.setItem(frappe.session.user + 'custom-address', e.currentTarget.value)
	
		})
	},
	create_table: function(location){
		location = location.map(l => l.split('#'))
		const middle = location.map((l) => `<tr>
				<td class="text-center"><input class="location" data-val="${l[0]}" value="${l[0]}" type="checkbox"></td>
				<td>${l[0]}</td>
				<td>${l[1]}</td>
				</tr>`).join("");
	
		this.html = `<div class="container-fluid">
	  
	  <div class="table-responsive" id="tab">
		  <table class="table table-bordered   table-hover">
			  <thead>
				  <tr>
					  <th class="text-center"><input id="main" data-val="parent" type="checkbox" ></th>
					  <th>Location</th>
					  <th>Company</th>
				  </tr>
			  </thead>
			  <tbody>`+ middle + `</tbody></table></div>
			  <div>
			  <div id ="input-custom"><input type="text" id="custom-address" placeholder="Custom" value="${localStorage.getItem(frappe.session.user + 'custom-address') ? localStorage.getItem(frappe.session.user + 'custom-address') : ''}" style="width: 100%;border: 1px solid #cccccc9e;border-radius: 10px; padding: 2px 8px;"></div>
			   
			  </div>
			  </div>`;
	
		let counter = 0;
		frappe.run_serially([
			() => {
				location.map((l) => {
					if (JSON.parse(localStorage.getItem(frappe.session.user + 'loc'))?.includes(l[0])) {
						counter++;
						setTimeout(() => {
							$(`.location[data-val="${l[0]}"]`).prop('checked', true);
						}, 400)
					}
				})
			},
			() => {
				if (location.length == counter && localStorage.getItem(frappe.session.user + 'location') == 1) {
					setTimeout(() => {
						$('#main[data-val="parent"]').prop('checked', true);
					}, 300)
				}
	
			}
		])
	
	
	}

})


function custom_address_update_data(a) {
	if(localStorage.getItem(frappe.session.user+'custom-address')) {
		let custom_add=localStorage.getItem(frappe.session.user+'custom-address');
		a.filters['custom_location']=[];
		a.filters['custom_location'].push(custom_add);
	} else {
		let loc=localStorage.getItem(frappe.session.user+'loc');
		a.filters['location']=JSON.parse(loc);
		a.filters['custom_location']=[];
	}
}

function get_city_filter_keyword(self) {
	if(document.getElementById('citys')) {
		let input=document.getElementById('citys');
		const boxes=document.querySelectorAll('.pac-container');
		if(!boxes.length) {
			let autocomplete=new google.maps.places.Autocomplete(input);
			google.maps.event.addListener(autocomplete,'place_changed',function() {
				let place=autocomplete.getPlace();
				self.filters['city']=place.name;
				self.update_list();
				self.refresh();
			});
		}
		self.filters['city']=document.getElementById('citys').value;
		self.update_list();
		self.refresh();
	}
	else {
		const boxes=document.querySelectorAll('.pac-container');
		boxes.forEach(box => {
			box.remove();
		});
		self.filters['city']=document.getElementById('citys').value;
		self.update_list();
		self.refresh();
	}
}

function select_industry_default_filter(li) {
	for(let child of li.children) {
		if(child.children[0].children[0].innerHTML==localStorage.getItem("industry")) {
			child.click();
		}
	}
}

async function sorted_favourite_companies(data, profile_html, company_type) {
	let count = data.count>1?'<span class="pl-1">&#x2B;</span>' + parseInt(data.count-1):"";
	let block_count = data.blocked_count>1?'<span class="pl-1">&#x2B;</span>' + parseInt(data.blocked_count-1):"";
	let link = data.name.split(' ').join('%');
	let Likebtnexclusice = `<td></td>`
	let Likebtnnonexclusice = `<td>
		<svg ${data.LikeStatus ? "class='icon icon-sm liked'" : "class='icon icon-sm not-liked'"}cursor:pointer" onClick = setLike(this,"${link}")>
		<use class="like-icon" href="#icon-heart"></use>
		</svg>
		</td>`
	profile_html += `<tr data-name="${data.name}" class="comps">
					${company_type === "Exclusive Hiring" ? Likebtnexclusice : Likebtnnonexclusice}
					<td ><a onclick=dynamic_route("${link}")>${data.name}</a></td>
					${data.industry_type?`<td><div class="staff_tooltip" data-toggle="tooltip" data-placement="right" data-html="true" style="position: relative;" title="${data.all_industries}"><span>`+ data.industry_type+block_count +`</span></div></td>`: '<td></td>'}
					<td>${data.address || data.complete_address || ''}</td>	
					<td ${data.rating ?'<span class="rating pr-2"><svg class="icon icon-sm star-click" data-rating="1"><use href="#icon-star"></use></svg></span>' + data.rating 
					:""}</td>
					 ${data.accreditation ? `<td><div class="staff_tooltip" data-toggle="tooltip" data-placement="right" data-html="true" title="${data.title}"><span class="staff-certificate-btn px-3 py-1"  id="${data.name}">` + data.accreditation + '</span><span class="text-primary">' + count + `</span></div></td>`
					:"<td></td>"}
					<td>${data.is_blocked ? "<td></td>" : '<td><button class="btn-primary" onclick=trigger_direct_order("' + link + '")>Place Direct Order</button></td>'}</td>
					</tr>`;
	return profile_html;
}

function get_option_data(data_list){
	let data_lists = []
	for(let data of data_list){
		data_lists.push(decodeURIComponent(data.dataset.value))
	}
	return data_lists.toString().replace("[]","") ?  data_lists.toString().replace("[]","") + "," : ''
}
function dynamic_route(name) {
	let name1 = name.replace(/%/g, ' ');
	localStorage.setItem("company", name1);
	window.location.href = "/app/dynamic_page";
}

function setLike(event, company) {
	if (event.classList.contains('not-liked')) {
		event.style.fill = 'red'
		event.style.stroke = 'white'
		event.classList.remove('not-liked')
		event.classList.add('liked')
		favourite_company(company)
	} else {
		event.classList.remove('liked')
		event.classList.add('not-liked')
		event.style.fill = 'white'
		event.style.stroke = 'var(--gray-500)'
		unfavourite_company(company)
	}
}

function trigger_direct_order(staff_name) {
	staff_name = staff_name.split('%').join(' ')
	let doc = frappe.model.get_new_doc("Job Order");
	doc.company = frappe.boot.tag.tag_user_info.company;
	doc.staff_company = staff_name;
	doc.staff_company2 = staff_name;
	doc.posting_date_time = frappe.datetime.now_date();
	frappe.set_route("Form", doc.doctype, doc.name);
}
function favourite_company(company) {
	let company_name = company.replaceAll("%", " ")
	frappe.call({
		method: 'tag_workflow.tag_workflow.page.staff_company_list.staff_company_list.favourite_company',
		"freeze": true,
		"freeze_message": "<p><b>Adding Company to favorites</b></p>",
		args: {
			'company_to_favourite': company_name,
			'user_company': frappe.boot.tag.tag_user_info.company,
			'user': frappe.session.user
		},
		callback: function (r) {
			if (r.message == "True") {
				frappe.msgprint(company_name + " has been added to favorites.")
			}
		}
	})
	return "True"
}

async function sorted_favourite_company() {
	let a = '';
	a = frappe.call({
		method: 'tag_workflow.tag_workflow.page.staff_company_list.staff_company_list.sorted_favourite_companies',
		"freeze": true,
		"freeze_message": "<p><b>Adding Company to Favorites</b></p>",
		args: {
			'user_name': frappe.boot.tag.tag_user_info.company
		},
	})
	return a
}

function unfavourite_company(company) {
	let company_name = company.replaceAll("%", " ")
	frappe.call({
		method: 'tag_workflow.tag_workflow.page.staff_company_list.staff_company_list.unfavourite_company',
		"freeze": true,
		"freeze_message": "<p><b>Removing Company from Favorites</b></p>",
		args: {
			'company_to_favourite': company_name,
			'user_company': frappe.boot.tag.tag_user_info.company,
			'user': frappe.session.user
		},
		callback: async function (r) {
			if (r.message == "False") {
				frappe.msgprint(company_name + " has been removed from favorites.")
				return "False"
			}
		}
	})
	return "True"
}


async function get_favourites_list(company) {
	let a = '';
	if (frappe.boot.tag.tag_user_info.company_type == 'Hiring') {
		a = frappe.call({
			method: 'tag_workflow.tag_workflow.page.staff_company_list.staff_company_list.checking_favourites_list',
			args: {
				'company_to_favourite': company,
				'user_name': frappe.boot.tag.tag_user_info.company
			}
		})
	}
	return a
}

frappe.realtime.on('refresh_data', () => {
	if (localStorage.getItem('search')) {
		document.getElementById('companys').value = '';
		populate_filter();
		$('#companys').change()


	}

})


function populate_filter() {
	localStorage.removeItem("city");
	localStorage.removeItem("industry");
	localStorage.removeItem("company_name")
	
	
	if (localStorage.getItem('search')) {
		const val = localStorage.getItem('search');
		document.getElementById('companys').value = val;
		Array.from(document.querySelectorAll('.comps')).filter((el) => {
			if (!el.attributes['data-name'].value.toLowerCase().startsWith(val)) {
				document.querySelector(`#myTable tr[data-name="${el.attributes['data-name'].value}"]`).style.display = 'none'
			}
		})
		localStorage.removeItem('search')
	}
}

function get_radius(val) {
	if (!['', undefined].includes(val)) {

		let str=' mi';
		document.getElementById('dropdownMenuLink').innerText = val+str
		frappe.flags.staff_home.filters['radius'] = val
		frappe.flags.staff_home.refresh()
	}
	else {

		document.getElementById('dropdownMenuLink').innerText = 'Distance'
		frappe.flags.staff_home.filters['radius'] = ''
		this.filter_loc = []
		localStorage.setItem(frappe.session.user + 'location', 0);
		localStorage.setItem(frappe.session.user + 'loc', JSON.stringify(this.filter_loc));
		localStorage.removeItem(frappe.session.user + 'custom-address')
		frappe.flags.staff_home.refresh()
	}
	frappe.flags.staff_home.$paging_area.find(".btn-paging").removeClass("btn-info");
	frappe.flags.staff_home.$paging_area.find(`.btn-paging[data-value="${frappe.flags.staff_home.end}"]`).addClass("btn-info");


}

function uncheck_cells_(items,me) {
    for (let i in items) {
        if (items[i].type == 'checkbox') {
            items[i].checked = false;
            remove_rows_(items[i].value,me)
        }
    }

}

function remove_rows_(val,me) {
    const index = me.filter_loc.indexOf(val)
    index !== -1 ? me.filter_loc.splice(index, 1) : console.log(index);
    if (parseInt(localStorage.getItem(frappe.session.user + 'location')) === 1) {
        localStorage.setItem(frappe.session.user + 'loc', JSON.stringify(me.filter_loc))
    }
}

function add_rows_(val,me) {
    if (!me.filter_loc.includes(val)){
		me.filter_loc.push(val);
	}
}

function check_cells_(e,me) {
    const items = document.querySelectorAll('.location');
    if (e.currentTarget.checked) {
        for (let i in items) {
            if (items[i].type == 'checkbox') {
                items[i].checked = true;
                add_rows_(items[i].value,me)
            }
        }
    } else {
		for (let i in items) {
            if (items[i].type == 'checkbox') {
                items[i].checked = false;
            }
        }
        uncheck_cells_(items,me);
    }
}
function radio_button_location_(e) {
    if (cur_dialog.fields_dict['rb1'].get_value() == 1) {
        cur_dialog.fields_dict['location'].disp_area.querySelector('#tab').hidden = false;
        cur_dialog.fields_dict['location'].disp_area.querySelector('#custom-address').hidden = true;
        cur_dialog.fields_dict['rb2'].set_value(0)
        localStorage.removeItem(frappe.session.user + 'custom-address')
		localStorage.setItem('is_loc',true)
        cur_dialog.fields_dict['location'].disp_area.querySelector('#custom-address').value = null;
    }

    else {
        cur_dialog.fields_dict['location'].disp_area.querySelector('#custom-address').hidden = false;
        cur_dialog.fields_dict['rb2'].set_value(1);
		localStorage.setItem('is_loc',false)
        cur_dialog.fields_dict['location'].disp_area.querySelector('#tab').hidden = true;

    }

}

function radio_button_custom_(me) {
    if (cur_dialog.fields_dict['rb2'].get_value() == 1) {
        cur_dialog.fields_dict['rb1'].set_value(0)
        cur_dialog.fields_dict['location'].disp_area.querySelector('#tab').hidden = true;
        cur_dialog.fields_dict['location'].disp_area.querySelector('#custom-address').hidden = false;
        me.filter_loc = [];
		me.filters.location = []
		localStorage.setItem('is_loc',false)
        localStorage.removeItem(frappe.session.user + 'loc');
        cur_dialog.fields_dict['location'].disp_area.querySelector('#main').checked = false
        remove_cells()
    }

    else {
		localStorage.setItem('is_loc',true)
        cur_dialog.fields_dict['location'].disp_area.querySelector('#custom-address').hidden = true;
        cur_dialog.fields_dict['location'].disp_area.querySelector('#tab').hidden = false;
        cur_dialog.fields_dict['rb1'].set_value(1)
    }

}

function toggle_radio_button(dialog,me) {
	let autocomplete=new google.maps.places.Autocomplete(
		dialog.fields_dict['location'].disp_area.querySelector('#custom-address'), {
		types: ["geocode"]
	}
	);
	console.log(autocomplete)
	dialog.fields_dict['location'].disp_area.querySelector('#main').addEventListener('change', (e) => check_cells_(e,me))
	dialog.fields_dict['rb1'].input.addEventListener('change', e => radio_button_location_(e))
	dialog.fields_dict['rb2'].input.addEventListener('change', e => radio_button_custom_(me))
	if (dialog.fields_dict['rb1'].get_value() == 1)
		dialog.fields_dict['location'].disp_area.querySelector('#custom-address').hidden = true;

	if (localStorage.getItem(frappe.session.user + 'custom-address')) {
		dialog.fields_dict['rb2'].set_value(1)
		dialog.fields_dict['location'].disp_area.querySelector('#tab').hidden = true;
		dialog.fields_dict['location'].disp_area.querySelector('#custom-address').hidden = false;
		dialog.fields_dict['rb1'].set_value(0);
	}
}

/*-----------------------order location(s)-------------------------*/
function get_job_site_location() {
    let order_location = null;
    frappe.call({
        "method": "tag_workflow.utils.reportview.get_location_staff_company_list",
		"args":{
			"comps":frappe.boot.tag.tag_user_info.comps
		},
        "async": 0,
        "freeze": true,
        "freeze_message": __("<b>Loading Job Site(s)") + "...</b>",
        "callback": function (r) {
            order_location = r.message;
        }
    });
    return order_location;
}

function get_count_str(){
	let current_count = this.data.length;
	let count_without_children = this.data.uniqBy((d) => d.name).length;

	return frappe.db.count(this.doctype, {
		filters: this.get_filters_for_args()
	}).then(total_count => {
		this.total_count = total_count || current_count;
		this.count_without_children = count_without_children !== current_count ? count_without_children : undefined;
		let str = __('{0} of {1}', [current_count, this.total_count]);
		if (this.count_without_children) {
			str = __('{0} of {1} ({2} rows with children)', [count_without_children, this.total_count, current_count]);
		}

		if (this.doctype == "Job Order" && frappe.boot.tag.tag_user_info.company_type == "Hiring") {
			this.total_count = this.data.length;
			str = __('{0} of {1}', [current_count, this.order_length]);
			return str;
		} else {
			return str;
		}
	});
}

function locationpopup(){
	frappe.flags.staff_home.display_modal();
}