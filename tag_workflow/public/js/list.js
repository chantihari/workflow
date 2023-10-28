/*------------ override baselist view -------------*/
frappe.provide("views");

/*------------------preparing data---------------*/
frappe.views.BaseList.prototype.prepare_data = function (r) {
    let data = r.message || {};
    // extract user_info for assignments
    Object.assign(frappe.boot.user_info, data.user_info);
    delete data.user_info;
    if (data){
        let me = this;
        if(this.doctype == "Job Order" && frappe.boot.tag.tag_user_info.company_type == "Staffing"){
            this.order_length = data.order_length;
            this.job_order_data(me, data);
        }else{
            data = !Array.isArray(data) ? frappe.utils.dict(data.keys, data.values) : data;
            if (this.start === 0) {
                this.data = data;
            } else {
                this.data = this.data.concat(data);
            }
        }
        this.data = this.data.uniqBy((d) => d.name);
    }
}

frappe.views.BaseList.prototype.job_order_data=(me,data)=>{
    if ([5, 10, 25, 50, 100].includes(parseInt(cur_list.radius))) {
        localStorage.setItem(frappe.session.user + 'radius', cur_list.radius);
        document.querySelector(`.btn-loc-rad[data-value="${cur_list.radius}"]`).classList.add('active');
        localStorage.getItem(frappe.session.user + 'location') == 1 ? $('.btn-location').addClass('active') : $('.btn-location').removeClass('active');
    }
    data = !Array.isArray(data) ? frappe.utils.dict(data.keys, data.values) : data;
    if (me.start === 0) {
        me.data = data;
    } else if (me.radius === "All" && me.len === 0) {
            me.data = me.data.concat(data);
        } else {
            me.data = data;
            me.len = me.start;
        }
}

/*--------------updating args----------------*/
frappe.views.BaseList.prototype.get_call_args = function () {
    this.method = "tag_workflow.utils.reportview.get";
    let args = this.get_args();
    args.radius = this.radius;
    args.filter_loc = this.filter_loc;
    args.order_status = this.order_status;
    args.custom_address = this.custom_address;

    return {
        method: this.method,
        args: args,
        freeze: true,
        freeze_message: __("<b>Loading") + "...</b>",
    };
}

/*-------------------added buttons--------------------*/
frappe.views.BaseList.prototype.setup_paging_area = function () {
    const paging_values = [20, 100, 500];
    const radius = [5, 10, 25, 50, 100];
    this.order_location = [];
    this.radius = frappe.boot.tag.tag_user_info.company_type == "Staffing" ? get_cache_radius() : 'All';
    this.len = 0;
    this.order_status = 'All'
    this.selected_page_count = 20;
    this.order_length = 0;
    this.filter_loc = localStorage.getItem(frappe.session.user + 'loc') ? JSON.parse(localStorage.getItem(frappe.session.user + 'loc')) : [];
    this.custom_address = frappe.boot.tag.tag_user_info.company_type == "Staffing" && localStorage.getItem(frappe.session.user + 'custom-address') ? localStorage.getItem(frappe.session.user + 'custom-address') : '';

    this.update_paging_area(paging_values, radius);
    this.$frappe_list.append(this.$paging_area);

    // set default paging btn active
    this.$paging_area.find(`.btn-paging[data-value="${this.page_length}"]`).addClass("btn-info");

    // order location(s)

    this.$paging_area.on("click", ".btn-paging, .btn-more, .btn-radius", (e) => {
        const $this = $(e.currentTarget);
        if ($this.is(".btn-paging")) {
            // set active button
            this.$paging_area.find(".btn-paging").removeClass("btn-info");
            $this.addClass("btn-info");
            this.start = 0;
            this.page_length = this.selected_page_count = $this.data().value;
            this.refresh();
        } else if ($this.is(".btn-more")) {
            this.remove_data();
            this.start = this.start + this.page_length;
            this.page_length = this.selected_page_count;

            $(".btn.btn-default.btn-radius.btn-sm.active").removeClass("active");
            $this.addClass("active");
            this.refresh();
            if (this.doctype == "Job Order" && frappe.boot.tag.tag_user_info.company_type == "Staffing")
                this.update_button();

        } else if ($this.is(".btn-radius")) {
            let val = $this.data().value;
            $(".btn.btn-default.btn-radius.btn-sm.active").removeClass("active");
            $(".btn.btn-default.btn-more.btn-sm.active").removeClass("active");
            $this.addClass("active");
            /*----------------Display-Modal----------------------------------------------------*/
            this.display_modal(val);
        }
    });
}

frappe.views.BaseList.prototype.remove_data = function () {
    if (this.doctype == "Job Order" && frappe.boot.tag.tag_user_info.company_type == "Staffing") {
        this.data = [];
    }
}


/*-----------------------order location(s)-------------------------*/
function get_order_location() {
    let order_location = null;
    frappe.call({
        "method": "tag_workflow.utils.reportview.get_location",
        "args": {
            organization_type: frappe.boot.tag.tag_user_info.company_type,
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

/*----------------------list view count update--------------------*/
frappe.views.ListView.prototype.get_count_str = function () {
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

        if (this.doctype == "Job Order" && frappe.boot.tag.tag_user_info.company_type == "Staffing") {
            this.total_count = this.data.length;
            str = __('{0} of {1}', [current_count, this.order_length]);
            return str;
        } else {
            return str;
        }
    });
}
/*----------------------------------------------------------------*/
frappe.views.ListView.prototype.display_modal = function (val) {
    if (!["Custom Address", "Clear"].includes(val)) {
        localStorage.setItem(frappe.session.user + 'radius', parseInt(val));
        this.filter_loc.length > 0 || localStorage.getItem(frappe.session.user + 'location') == 1 ? $('.btn-location').addClass('active') : $('.btn-location').removeClass('active');
        this.radius = val;
        this.start = 0;
        this.page_length = 20;
        if (localStorage.getItem(frappe.session.user + 'custom-address'))
            this.custom_address = localStorage.getItem(frappe.session.user + 'custom-address');
        this.$paging_area.find(`.btn-info`).removeClass("btn-info");
        this.$paging_area.find(`.btn-paging[data-value="${this.page_length}"]`).addClass("btn-info");
        this.refresh();
    } else if (val == "Custom Address") {
        if ([5, 10, 25, 50, 100].includes(parseInt(this.radius))){
            localStorage.setItem(frappe.session.user + 'radius', parseInt(this.radius));
            document.querySelector(`.btn-loc-rad[data-value="${this.radius}"]`).classList.add('active');}
        this.order_location = get_order_location();
        this.create_table(this.order_location);

        this.add_fields = [{ label: 'Location', fieldname: 'rb1', fieldtype: 'Check', default: 1 }, { label: 'Custom', fieldname: 'rb2', fieldtype: 'Check' }, { label: '', fieldname: 'location', fieldtype: 'HTML', options: this.html }];
        let dialog = new frappe.ui.Dialog({
            title: 'Please select one or more addresses',
            fields: this.add_fields,
        });
        dialog.show();
        toggle_radio_button(dialog);
        dialog.set_primary_action(__('Submit'), function () {
            localStorage.setItem(frappe.session.user + 'location', 1);
            update_radius();
            cur_list.start = 0;
            cur_list.page_length = 20;
            cur_list.$paging_area.find(`.btn-info`).removeClass("btn-info");
            cur_list.$paging_area.find(`.btn-paging[data-value="${cur_list.page_length}"]`).addClass("btn-info");
            cur_list.refresh();
            dialog.hide();
            localStorage.setItem(frappe.session.user + 'loc', JSON.stringify(cur_list.filter_loc));
        });
        setTimeout(() => { select_deselect_row() }, 500)
    } else if (val == "Clear") {
            clear_cache();
            this.len = 0;
            this.start = 0;
            this.page_length = 20;
            this.$paging_area.find(`.btn-info`).removeClass("btn-info");
            this.$paging_area.find(`.btn-paging[data-value="${this.page_length}"]`).addClass("btn-info");
            this.radius = "All";
            this.filter_loc = [];
            this.custom_address = '';
            document.querySelector(`.btn-radius[data-value="Clear"]`).classList.remove('active');
            this.refresh();
        }
}
/*----------------------Generate table in Modal--------------------*/
frappe.views.ListView.prototype.create_table = function (location) {
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
/*----------------------add_remove_row--------------------*/
frappe.views.ListView.prototype.single_row_event = function (items, input) {
    items.forEach(i => i.addEventListener(
        "change",
        e => {
            if (i.checked && i.id != 'custom-location') {
                add_rows(e.currentTarget.value);
            } else if (!i.checked && i.id != 'custom-location') {
                remove_rows(e.currentTarget.value);
            }
        }));
    /*----------Input-Event--------------*/

    input[document.querySelectorAll('#custom-address').length - 1].addEventListener('keyup', (e) => {
        cur_list.custom_address = e.currentTarget.value;
        localStorage.setItem(frappe.session.user + 'custom-address', e.currentTarget.value)

    })
}
/*----------------------create paging area--------------------*/
frappe.views.ListView.prototype.update_paging_area = function (paging_values, radius) {
    this.$paging_area = $(`
        <div class="list-paging-area level">
            <div class="level-left">
                <div class="btn-group">${paging_values.map((value) => `<button type="button" class="btn btn-default btn-sm btn-paging" data-value="${value}">${value}</button>`).join("")}</div>
            </div>
            <div class="level-right"><button class="btn btn-default btn-more btn-sm">${__("Load More")}</button></div>
        </div>`).hide();

    if (this.doctype == "Job Order" && frappe.boot.tag.tag_user_info.company_type == "Staffing") {
        this.$paging_area = $(`
            <div class="list-paging-area level flex-wrap">
                <div class="level-left">
                    <div class="btn-group">${paging_values.map((value) => `<button type="button" class="btn btn-default btn-sm btn-paging" data-value="${value}">${value}</button>`).join("")}</div>
                </div>
                <div class="level-right custom-location">${radius.map((value) => `
                    <button class="btn btn-default btn-radius btn-sm btn-loc-rad" data-value="${value}" style="margin-right: 5px;">${value} Miles</button>`).join("")}
                    <button class="btn btn-default btn-radius btn-location btn-sm" data-value="Custom Address" style="margin-right: 5px;">Locations</button>
                    <button class="btn btn-default btn-radius btn-sm" data-value="Clear" style="margin-right: 5px;">Clear</button>
                    <button class="btn btn-default btn-more btn-sm">${__("Load More")}</button>
                </div>
            </div>`).hide();
    }
}
/*---------------------------Updating button-----------------------------------------------------------*/
frappe.views.ListView.prototype.update_button = function () {
    this.filter_loc.length > 0 || localStorage.getItem(frappe.session.user + 'location') == 1 ? $('.btn-location').addClass('active') : $('.btn-location').removeClass('active');
    if ([5, 10, 25, 50, 100].includes(parseInt(this.radius)))
        document.querySelector(`.btn-loc-rad[data-value="${this.radius}"]`).classList.add('active');
}
const select_deselect_row = function (e) {
    const items = document.querySelectorAll('.location');
    const input = document.querySelectorAll('#custom-address');
    frappe.views.ListView.prototype.single_row_event(items, input);
}
/*----------------------------------check-cells----------------------------------------------------------------*/
const check_cells = function (e) {
    const items = document.querySelectorAll('.location');
    if (e.currentTarget.checked) {
        for (let i in items) {
            if (items[i].type == 'checkbox') {
                items[i].checked = true;
                add_rows(items[i].value)
            }
        }
    } else {
        uncheck_cells(items);
    }
}
function remove_rows(val) {
    const index = cur_list.filter_loc.indexOf(val)
    index !== -1 ? cur_list.filter_loc.splice(index, 1) : console.log(index);
    if (parseInt(localStorage.getItem(frappe.session.user + 'location')) === 1) {
        localStorage.setItem(frappe.session.user + 'loc', JSON.stringify(cur_list.filter_loc))
    }
}
function add_rows(val) {
    if (!cur_list.filter_loc.includes(val))
        cur_list.filter_loc.push(val);
}
function update_radius() {
    if ([5, 10, 25, 50, 100].includes(parseInt(localStorage.getItem(frappe.session.user + 'radius'))))
        cur_list.radius = parseInt(localStorage.getItem(frappe.session.user + 'radius'));
    else
        cur_list.radius = 'All';
    /*------------------------------------------------------*/
    const ip_t = document.querySelectorAll('#custom-address');
    const val = ip_t[document.querySelectorAll('#custom-address').length - 1].value;
    if (!localStorage.getItem(frappe.session.user + 'custom-addres') && val != '') {
        cur_list.custom_address = val;
        localStorage.setItem(frappe.session.user + 'radius', parseInt(localStorage.getItem(frappe.session.user + 'radius'))?parseInt(localStorage.getItem(frappe.session.user + 'radius')):10);
        cur_list.radius = localStorage.getItem(frappe.session.user + 'radius')
        document.querySelector(`.btn-loc-rad[data-value="${cur_list.radius}"]`).classList.add('active');
        localStorage.setItem(frappe.session.user + 'custom-address', val)
    }




}
function remove_cells() {
    const items = document.querySelectorAll('.location');
    for (let i in items) {
        if (items[i].type == 'checkbox')
            items[i].checked = false;

    }
}
/*---------Uncheck-Cells---------------*/
function uncheck_cells(items) {
    for (let i in items) {
        if (items[i].type == 'checkbox') {
            items[i].checked = false;
            remove_rows(items[i].value)
        }
    }

}

function update_data() {
    if (cur_list && cur_list.doctype == "Job Order" && frappe.boot.tag.tag_user_info.company_type == "Staffing") {
        if (localStorage.getItem(frappe.session.user + 'location') == 1 || localStorage.getItem(frappe.session.user + 'radius')) {
            cur_list.start = 0;
            cur_list.page_length = 20;
            /***************location button************/
            localStorage.getItem(frappe.session.user + 'location') == 1 ? $('.btn-location').addClass('active') : $('.btn-location').removeClass('active');
            /******************radius button*********/
            if (localStorage.getItem(frappe.session.user + 'radius') && [5, 10, 25, 50, 100].includes(parseInt(localStorage.getItem(frappe.session.user + 'radius'))))
                document.querySelector(`.btn-loc-rad[data-value="${cur_list.radius}"]`).classList.add('active');


        }
    }

}

function clear_cache() {
    const cache_keys = [frappe.session.user + 'location', frappe.session.user + 'radius', frappe.session.user + 'loc', frappe.session.user + 'custom-address', 'radius']
    for (let k in cache_keys) {
        if (localStorage.getItem(cache_keys[k]))
            localStorage.removeItem(cache_keys[k]);
    }

}

function get_cache_radius() {
    if (localStorage.getItem(frappe.session.user + 'radius'))
        return localStorage.getItem(frappe.session.user + 'radius');
    else if (localStorage.getItem('radius'))
        return '25';
    else
        return 'All';
}

function radio_button_location() {
    if (cur_dialog.fields_dict['rb1'].get_value() == 1) {
        cur_dialog.fields_dict['location'].disp_area.querySelector('#tab').hidden = false;
        cur_dialog.fields_dict['location'].disp_area.querySelector('#custom-address').hidden = true;
        cur_dialog.fields_dict['rb2'].set_value(0)
        cur_list.custom_address = '';
        localStorage.removeItem(frappe.session.user + 'custom-address')
        cur_dialog.fields_dict['location'].disp_area.querySelector('#custom-address').value = null;
    }

    else {
        cur_dialog.fields_dict['location'].disp_area.querySelector('#custom-address').hidden = false;
        cur_dialog.fields_dict['rb2'].set_value(1);
        cur_dialog.fields_dict['location'].disp_area.querySelector('#tab').hidden = true;

    }

}

function radio_button_custom() {
    if (cur_dialog.fields_dict['rb2'].get_value() == 1) {
        cur_dialog.fields_dict['rb1'].set_value(0)
        cur_dialog.fields_dict['location'].disp_area.querySelector('#tab').hidden = true;
        cur_dialog.fields_dict['location'].disp_area.querySelector('#custom-address').hidden = false;
        cur_list.filter_loc = [];
        localStorage.removeItem(frappe.session.user + 'loc');
        cur_dialog.fields_dict['location'].disp_area.querySelector('#main').checked = false
        remove_cells()
    }

    else {
        cur_dialog.fields_dict['location'].disp_area.querySelector('#custom-address').hidden = true;
        cur_dialog.fields_dict['location'].disp_area.querySelector('#tab').hidden = false;
        cur_dialog.fields_dict['rb1'].set_value(1)
    }

}

function toggle_radio_button(dialog) {
    const autocomplete = new google.maps.places.Autocomplete(
        dialog.fields_dict['location'].disp_area.querySelector('#custom-address'), {
        types: ["geocode"]
    }
    );
    console.log(autocomplete)
    dialog.fields_dict['location'].disp_area.querySelector('#main').addEventListener('change', (e) => check_cells(e))
    dialog.fields_dict['rb1'].input.addEventListener('change', e => radio_button_location())
    dialog.fields_dict['rb2'].input.addEventListener('change', e => radio_button_custom())
    if (dialog.fields_dict['rb1'].get_value() == 1)
        dialog.fields_dict['location'].disp_area.querySelector('#custom-address').hidden = true;

    if (localStorage.getItem(frappe.session.user + 'custom-address')) {
        dialog.fields_dict['rb2'].set_value(1)
        dialog.fields_dict['location'].disp_area.querySelector('#tab').hidden = true;
        dialog.fields_dict['location'].disp_area.querySelector('#custom-address').hidden = false;
        dialog.fields_dict['rb1'].set_value(0);
    }
}

window.onload = function () {
    setTimeout(() => update_data(), 3000)
}