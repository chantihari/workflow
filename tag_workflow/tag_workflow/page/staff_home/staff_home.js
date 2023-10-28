let company1 = frappe.boot.tag.tag_user_info.company;
let company_type = frappe.boot.tag.tag_user_info.company_type;
frappe.breadcrumbs.clear();
frappe.flags.prev_val = [];
frappe.flags.wrapper = null;
function toggle_ele(point) {
  if (frappe.flags.prev_val.length > 0) {
    const pt = frappe.flags.prev_val[0];
    document.getElementById(pt).style.borderLeft = "transparent";
    frappe.flags.prev_val = [];
  }
  let container = $(".main-slider");
  let scrollTo = $("#" + point);
  let position =
    scrollTo.offset().top - container.offset().top + container.scrollTop();
  container.scrollTop(position);
  document.getElementById(point).style.borderLeft = "4px solid #7b68ef";
  document.getElementById(point).style.borderRadius = "5px";
  frappe.flags.prev_val.push(point);
}

frappe.pages["staff-home"].on_page_load = function (wrapper) {
  let page = frappe.ui.make_app_page({
    parent: wrapper,
    title: "Home",
    single_column: true,
  });
  wrapper.staff_home = new frappe.StaffHome(wrapper, page);
  frappe.flags.wrapper = wrapper.staff_home;
  localStorage.removeItem("category");
  localStorage.removeItem("order_by");
};

frappe.StaffHome = Class.extend({
  init: function (wrapper, page) {
    let me = this;
    this.parent = wrapper;
    this.page = this.parent.page;
    setTimeout(function () {
      frappe.breadcrumbs.clear();
      me.setup(wrapper, page);
    }, 900);
  },
  setup: function (wrapper, page) {
    let me = this;
    this.body = $("<div></div>").appendTo(this.page.main);
    $(frappe.render_template("staff_home", "")).appendTo(this.body);
    me.make_data(wrapper, page);
    me.init_map(wrapper, page);
  },
  init_map: function (_wrapper, _page) {
    let me = this;
    let center = { lat: 38.889248, lng: -77.050636 };
    me.map = new google.maps.Map(document.getElementById("maps"), {
      zoom: 3.3,
      center: center,
    });
  },
  make_data: function (wrapper, page) {
    let me = this;
    me.update_job_order(wrapper, page);
  },

  update_job_order: function (wrapper, page) {
    let me = this;
    frappe.call({
      method:
        "tag_workflow.tag_workflow.page.staff_home.staff_home.get_order_info",
      args: {
        company1: company1,
        com : frappe.boot.tag.tag_user_info.company_type
      },
      callback: function (r) {
        let location = r.message.location;
        let order = r.message.order;
        let org_type = r.message.org_type;
        let category = r.message.category;
        me.update_dropdown_item(wrapper, page);
        for (let c in category) {
          let a = document.createElement("a");
          a.setAttribute("href", "#");
          a.classList.add("dropdown-item");
          a.addEventListener("click", filter_category);
          a.innerHTML = category[c];
          document.getElementById("category").appendChild(a);
        }
        me.update_map(wrapper, page, location);
        me.update_order(wrapper, page, order, org_type);
      },
    });
  },
  update_map: function (_wrapper, _page, location) {
    let me = this;
    let locations = location;
    let latlngbounds = new google.maps.LatLngBounds();
    let ht = {};
    unique_location_hashing(locations, ht);
    for (let p in ht) {
      let data = ht[p].slice(2);
      let content_list = `<div style="padding: 0px 9px 0px 10px ; max-height:120px"><br>`;
      if (data.length == 1) {
        content_list += `<span style="font-weight:bold;cursor:pointer;" onclick=toggle_ele("${data[0]}")>${data[0]}</span>`;
      } else {
        for (let li in data) {
          content_list += `<li class="select-order" style="font-weight:bold;cursor:pointer;" onclick=toggle_ele("${data[li]}")>${data[li]}</li>`;
        }
      }
      content_list += "</div>";
      let marker = new google.maps.Marker({
        position: new google.maps.LatLng(ht[p][0], ht[p][1]),
        map: me.map,
        title: p.concat(
          " ",
          ht[p].length - 2 == 1
            ? ht[p][2]
            : " x" + JSON.stringify(ht[p].length - 2)
        ),
        label: {
          text:
            ht[p].length - 2 == 1
              ? null
              : " x" + JSON.stringify(ht[p].length - 2),
          color: "#fff",
          fontWeight: "bold",
        },
      });
      latlngbounds.extend(marker.position);
      marker.info = new google.maps.InfoWindow({
        content: content_list,
      });

      google.maps.event.addListener(marker, "click", function () {
        marker.info.open(me.map, marker);
      });
    }
    let check_if_same_loc = new Set(location.map((item) => item[0]));
    if (check_if_same_loc.size == 1) {
      me.map.setZoom(11);
      const geocoder = new google.maps.Geocoder();
      let request = { address: locations[0][0] };
      geocoder
        .geocode(request)
        .then((result) => {
          const { results } = result;
          me.map.setCenter(results[0].geometry.location);
        })
        .catch((e) => {
          alert("Geocode was not successful for the following reason: " + e);
        });
    } else if (location.length == 0) {
      me.map.setZoom(3.3);
    } else {
      me.map.setCenter(latlngbounds.getCenter());
      me.map.fitBounds(latlngbounds);
    }
  },
  update_order: function (_wrapper, _page, order, org_type) {
    let html = `<div class="main-slider" style="max-height: 385px; overflow: auto;">`;
    for (let o in order) {
      this.o = o;
      let from = moment(order[o].from_date)._d.toDateString();
      let to = moment(order[o].to_date)._d.toDateString();
      let job_title = order[o].select_job.split("~");
      let select_job = job_title.length>1 ? job_title[0]+" +"+(job_title.length-1) : job_title[0];
      job_title.shift();
      let tooltip_values = [];
      job_title.forEach((ele) => {
        tooltip_values.push("&#x2022 " + ele);
      });
      tooltip_values = tooltip_values.join("<br>");
      html += `
				
				<div class="row bg-white mx-2 my-3 rounded border job" data-job="${
          order[o].select_job
        }" style="margin-top: 0px !important;">
					<div id="${order[o].name}">
						<div class="d-flex flex-wrap p-3 ">
							<div class="d-flex justify-content-between w-100 ">
								<div id="staffhome_${o}" data-toggle="popover" data-placement="right" onmouseover="showcasepopover(this.id, '${tooltip_values}')" onmouseout="hideCasePopover(this.id)" style="cursor: pointer;"><h6>${select_job}</h6></div>
							</div>
							<div class="d-flex w-100">
								<span class="badge badge-pill exclusive">${order[o].name}</span>
								<span class="badge badge-pill ml-2 exclusive">${org_type}</span>
							</div>
							<div class="d-flex flex-wrap w-100 pt-3 ">
								<div class="col-xl-7 col-lg-12">
									<div class="row flex-nowrap">
										<div class="pt-2 pr-2 mr-0">
										<img src="/assets/tag_workflow/images/ico-calendar.svg">
									</div>
									<div>
										<small class="text-secondary"> Start-End Date </small>
										<p> ${from}, ${to} </p>
									</div>
								</div>
							</div>
							<div class="col-xl-5 col-lg-12">
								<div class="row flex-nowrap">
									<div class="pt-2 pr-2 mr-0">
                  <img src="/assets/tag_workflow/images/ico-worker.svg">
									</div>
									<div>
                    <small class="text-secondary">No. of Employees </small>
                    <p> ${order[o].approved_workers} </p>
									</div>
								</div>
							</div>
						</div>
					</div>
					<div class="d-flex flex-wrap w-100 py-3 border-top">
						<div class="col-lg-4">
							<!--<a href="#" class="text-secondary pt-2">See on map</a> -->
						</div>
						<div class="col-lg-8 px-2"> 
							<div class="d-flex flex-wrap">
								<button type="button" class="btn btn-light btn-sm ml-3 border order-btn text-center" onclick=redirect_order('${
                  order[o].name
                }')>Order Details</button>
								<button type="button" id='quick_info' class="btn btn-primary btn-sm ml-3 rounded  text-center" onclick="show_info_order('${
                  order[o].name
                }', '${o}')">Quick Info</button>
							</div>
						</div>
					</div>
				</div>
			</div>`;
    }
    html += `</div>`;
    let total_order = `<div class="row bg-white mx-2 my-md-4 my-2 rounded border" style="margin-top: 0px !important;"><div class="d-flex flex-wrap p-3" style="width: 100%;"><div class="d-flex justify-content-between w-100 "><h6 class="mb-0">Total Number Of Today's Order: </h6><h6 class="mb-0" id="counter">${order.length}</h6></div></div></div>`;
    $("#order").html(total_order + html);
  },
  update_dropdown_item: function (_wrapper, _page) {
    // Default Value
    document.getElementById("category").innerHTML = "";
    let a = document.createElement("a");
    a.setAttribute("href", "#");
    a.setAttribute("class", "dropdown-item");
    a.addEventListener("click", filter_category);
    a.innerHTML = "All";
    document.getElementById("category").appendChild(a);
    //Order BY
    document.getElementById("order-by").innerHTML = "";
    const ord = ["All", "Non Exclusive", "Exclusive"];
    for (let i of ord) {
      let b = document.createElement("a");
      b.setAttribute("href", "#");
      b.setAttribute("class", "dropdown-item");
      b.addEventListener("click", order_by);
      b.innerHTML = i;
      document.getElementById("order-by").appendChild(b);
    }
  },
  render_map: function (r, wrapper, page) {
    let me = this;
    let location = r.message.location;
    let order = r.message.order;
    let org_type = r.message.org_type;
    me.init_map();
    frappe.flags.wrapper.update_map(wrapper, page, location);
    frappe.flags.wrapper.update_order(wrapper, page, order, org_type);
  },
});

function unique_location_hashing(locations, ht) {
  for (let a in locations) {
    if (ht[locations[a][0]] != undefined) {
      ht[locations[a][0]].push(locations[a][3]);
    } else {
      ht[locations[a][0]] = [locations[a][1], locations[a][2], locations[a][3]];
    }
  }
}

function show_info_order(order, row) {
  frappe.call({
    method: "tag_workflow.tag_workflow.page.staff_home.staff_home.order_info",
    args: { name: order },
    callback: function (r) {
      let data = r.message || [];
      let html = ``;
      let from = moment(data[0].from_date)._d.toDateString();
      let to = moment(data[0].to_date)._d.toDateString();
      let job_title = data[0].select_job.split("~");
      let select_job = job_title.length>1 ? job_title[0]+" +"+(job_title.length-1) : job_title[0];
      job_title.shift();
      let tooltip_values = [];
      job_title.forEach((ele) => {
        tooltip_values.push("&#x2022 " + ele);
      });
      tooltip_values = tooltip_values.join("<br>");
      html += `
      <div class="row bg-white quick-info-detail border-bottom py-3">
          <div class="col-lg-3">
            <p>Title</p>
            <span id="quick_${row}" data-toggle="popover" data-placement="right" onmouseover="showcasepopover(this.id, '${tooltip_values}')" onmouseout="hideCasePopover(this.id)" style="cursor: pointer;">${select_job}</span>
          </div>
          <div class="col-lg-3">
            <p>Start/End Date</p>
            <p>${from} ${to}</p>
          </div>
        </div>

        <div class="row bg-white quick-info-detail border-bottom py-3">
          <div class="col-lg-3">
            <p>Job Site</p>
            <p>${data[0].job_site}</p>
          </div>
          <div class="col-lg-3">
            <p>Job Site Contact</p>
            <p class="text-primary">${data[0].contact_email||""}</p>
          </div>
          <div class="col-lg-3">
            <p>No. Of Workers</p>
            <p>${data[0].total_no_of_workers}</p>
          </div>
          <div class="col-lg-3">
            <p>Notes</p>
            <p>${data[0].extra_notes||""}</p>
          </div>
        </div>

        <div class="row bg-white py-3">
          <div class="col-lg-3" style="padding: 10px 10px;">
            <div class="form-group frappe-control input-max-width" data-fieldtype="Check" data-fieldname="resume" title="Resume Required">
              <div class="checkbox">
                <label>
                  <span class="input-area"><input type="checkbox" autocomplete="off" class="input-with-feedback" data-fieldtype="Check" data-fieldname="resume" placeholder="" disabled check=${data[0].resumes_required}></span>
                  <span class="label-area">Resumes Required</span>
                </label>
              </div>
            </div>
          </div>

          <div class="col-lg-3" style="padding: 10px 10px;">
            <div class="form-group frappe-control input-max-width" data-fieldtype="Check" data-fieldname="mask" title="Require Staff To Wear Face Mask">
              <div class="checkbox">
                <label>
                  <span class="input-area"><input type="checkbox" autocomplete="off" class="input-with-feedback" data-fieldtype="Check" data-fieldname="mask" placeholder="" disabled check=${data[0].require_staff_to_wear_face_mask}></span>
                  <span class="label-area">Require Staff To Wear Face Mask</span>
                </label>
              </div>
            </div>
          </div>
        </div>
      `;

      let fields = [{ fieldname: "html", fieldtype: "HTML", options: html }];
      let dialog = new frappe.ui.Dialog({
        title: "Quick Info",
        fields: fields,
      });
      if(!$('#quick_info').hasClass('active')){
        dialog.show();
        $('#quick_info').addClass('active');
      }
      dialog.$wrapper.on("hidden.bs.modal", function() {
        $('#quick_info').removeClass("active");
      });
      dialog.$wrapper.find(".modal-dialog").css("max-width", "980px");
    },
  });
}

function redirect_order(name) {
  frappe.set_route("app", "job-order", name);
}

function redirect_doc(name) {
  location.href = "/app/" + name;
}
function filterOrder() {
  let input, filter, o, j, a, i;
  input = document.getElementById("my-input");
  filter = input.value.toUpperCase();
  o = document.getElementById("order");
  j = o.getElementsByClassName("job");
  for (i = 0; i < j.length; i++) {
    a = j[i].getAttribute("data-job");
    if (a.toUpperCase().indexOf(filter) > -1) {
      j[i].style.display = "";
    } else {
      j[i].style.display = "none";
    }
  }
  document.getElementById("counter").innerHTML = document.querySelectorAll(
    '.job:not([style*="display: none"])'
  ).length;
}

function ajaxCallOrderBy(category, wrapper, page) {
  frappe.call({
    method:
      "tag_workflow.tag_workflow.page.staff_home.staff_home.filter_category",
    args: {
      company: company1,
      com: frappe.boot.tag.tag_user_info.company_type,
      category: category
    },
    callback: function (r) {
      let location = r.message.location;
      let order = r.message.order;
      let org_type = r.message.org_type;
      frappe.flags.wrapper.update_map(wrapper, page, location);
      frappe.flags.wrapper.update_order(wrapper, page, order, org_type);
      localStorage.removeItem("order_by");
    },
  });
}
function ajaxCallCategory(ob, wrapper, page) {
  frappe.call({
    method:
      "tag_workflow.tag_workflow.page.staff_home.staff_home.filter_category",
    args: {
      company: company1,
      com: frappe.boot.tag.tag_user_info.company_type,
      order_by: ob
    },
    callback: function (r) {
      let location = r.message.location;
      let order = r.message.order;
      let org_type = r.message.org_type;
      frappe.flags.wrapper.update_map(wrapper, page, location);
      frappe.flags.wrapper.update_order(wrapper, page, order, org_type);
      localStorage.removeItem("category");
    },
  });
}
function order_by() {
  if (this.tagName.toLowerCase() == "a" && this.text != "All") {
    localStorage.setItem("order_by", this.text);
    let args = null;
    document.querySelector('.btn-link[data-ord="btn-ord"]').innerHTML =
      this.text;
    if (localStorage.getItem("category"))
      args = {
        company: company1,
        category: localStorage.getItem("category"),
        order_by: this.text,
      };
    else args = {
      company: company1,
      com: frappe.boot.tag.tag_user_info.company_type,
      order_by: this.text
    };
    frappe.call({
      method:
        "tag_workflow.tag_workflow.page.staff_home.staff_home.filter_category",
      args: args,
      callback: function (r) {
        frappe.flags.wrapper.render_map(r, cur_page.page, cur_page.page.page);
      },
    });
  } else if (this.tagName.toLowerCase() == "a" && this.text == "All") {
    document.querySelector('.btn-link[data-ord="btn-ord"]').innerHTML =
      this.text;
    if (localStorage.getItem("category"))
      ajaxCallOrderBy(
        localStorage.getItem("category"),
        cur_page.page,
        cur_page.page.page
      );
    else {
      frappe.flags.wrapper.update_job_order(cur_page.page, cur_page.page.page);
      localStorage.removeItem("order_by");
    }
  }
}

function filter_category() {
  if (this.tagName.toLowerCase() == "a" && this.text != "All") {
    localStorage.setItem("category", this.text);
    let args = null;
    document.querySelector('.btn-link[data-cat="btn-cat"]').innerHTML =
      this.text;
    if (localStorage.getItem("order_by"))
      args = {
        company: company1,
        com: frappe.boot.tag.tag_user_info.company_type,
        category: this.text,
        order_by: localStorage.getItem("order_by"),
      };
    else args = {
      company: company1,
      com: frappe.boot.tag.tag_user_info.company_type,
      category: this.text
    };
    frappe.call({
      method:
        "tag_workflow.tag_workflow.page.staff_home.staff_home.filter_category",
      args: args,
      callback: function (r) {
        frappe.flags.wrapper.render_map(r, cur_page.page, cur_page.page.page);
      },
    });
  } else if (this.tagName.toLowerCase() == "a" && this.text == "All") {
    document.querySelector('.btn-link[data-cat="btn-cat"]').innerHTML =
      this.text;
    if (localStorage.getItem("order_by"))
      ajaxCallCategory(
        localStorage.getItem("order_by"),
        cur_page.page,
        cur_page.page.page
      );
    else {
      frappe.flags.wrapper.update_job_order(cur_page.page, cur_page.page.page);
      localStorage.removeItem("category");
    }
  }
}

function showcasepopover(id, content) {
  if(content){
    $("#"+id).popover({
      placement: "right",
      content: function () {
        return content;
      },
      html: true,
    }).popover("show");
  }
}

function hideCasePopover(id) {
  $("#"+id).popover("hide");
}
