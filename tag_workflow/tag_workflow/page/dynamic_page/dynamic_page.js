let company = localStorage.getItem("company");
localStorage.setItem("set_limit", 20);
let org_arr = [];
let company_type = "";
window.rating = [];
frappe.pages["dynamic_page"].on_page_load = function (wrapper) {
  let page = frappe.ui.make_app_page({
    parent: wrapper,
    title: "Company",
    single_column: true,
  });
  wrapper.face_recognition = new frappe.FaceRecognition(wrapper, page);
};

function hide(r, page) {
  if (frappe.boot.tag.tag_user_info.company_type === "Staffing") {
    $("#place_order").hide();
    $("#work_order").css("color", "#fff");
    $("#work_order").css("background-color", "#21b9e4");
  }
  if (
    frappe.boot.tag.tag_user_info.company_type ===
    r.message[0].organization_type
  ) {
    $("#place_order").hide();
    $("#work_order").hide();
  }
  //--------hiding place order btn for tag and admin---------//
  if (
    frappe.boot.tag.tag_user_info.company_type === "TAG" ||
    frappe.session.user === "Administrator"
  ) {
    $("#place_order").hide();
  }

  if (r.message[0].organization_type != "Staffing") {
    $(".documents").hide();
    $("#coi").hide();
    $("#safety_manual").hide();
    $("#w_nine").hide();
  }
  get_blocked_list(page);
}

frappe.FaceRecognition = Class.extend({
  init: function (wrapper, page) {
    let me = this;
    this.parent = wrapper;
    this.page = this.parent.page;
    setTimeout(function () {
      me.setup(wrapper, page);
    }, 100);
  },

  setup: function (wrapper, page) {
    let me = this;
    this.body = $("<div></div>").appendTo(this.page.main);
    $(frappe.render_template("dynamic_page", "")).appendTo(this.body);
    me.show_profile(wrapper, page);
  },

  show_profile: function (_wrapper, page) {
    frappe.call({
      method:
        "tag_workflow.tag_workflow.page.dynamic_page.dynamic_page.get_link1",
      args: {
        name: company || "",
        userid: frappe.user_info().email,
      },
      callback: function (r) {
        setTimeout(function () {
          hide(r, page);
        }, 10);
        let my_val = r.message[0];
        let txt = "";
        company_type = my_val.organization_type;
        let company_phone_no = check_phone_number(
          my_val.phone_no
        );
        let company_rating_list = [];
        let sum = 0;
        for (let i of r.message[1]) {
          company_rating_list.push(i[0]);
          sum += i[0];
        }
        let company_average_rating = company_rating_list.length
          ? (sum / company_rating_list.length).toFixed(1)
          : "0.0";
        let text = r.message[2];
        for (let i in text) {
          txt += text[i].full_name + "<br>";
        }

        let company_logo = r.message[3];

        let industry = "";
        let industry_vals = [];
        for (let j in my_val.industry_type) {
          industry_vals.push(my_val.industry_type[j].industry_type);
        }
        industry_vals.sort((a, b) => a.localeCompare(b));
        let industry_list = Array.from(new Set(industry_vals));
        for (let p in industry_list) {
          industry += industry_list[p] + "<br>";
        }
        window.rating = r.message[1];
        let count = r.message[1].length;
        let rev = get_reviews(r);

        let arr1 = add_ress(my_val);
        let jobsite_address = arr1.join(", ");
        let count_val = count;
        count = count > 1 ? count + " Reviews" : count + " Review";
        let description = my_val.about_organization
          ? my_val.about_organization
          : "No description added.";
          let {acc_rec_name,acc_rec_phone_number,acc_rec_email}=get_receivable_details(my_val);
        let link_coi = "";
        let link_sm = "";
        let w_nine = "";
        if (
          r.message[0].cert_of_insurance ||
          r.message[0].safety_manual ||
          r.message[0].w9
        ) {
          link_coi = r.message[0].cert_of_insurance.split(" ").join("%");
          link_sm = r.message[0].safety_manual.split(" ").join("%");
          w_nine = r.message[0].w9.split(" ").join("%");
        }
        let template = `
					<div class="container form-section m-auto card-section visible-section" style="max-width: 97%;width: 100%;padding: 0;animation: animatop 1.7s cubic-bezier(0.425, 1.14, 0.47, 1.125) forwards;background: transparent;"> 
					<div id="listdata">
					 <div class="user_list border rounded pt-4">
						<div class="w-100 px-3 d-flex flex-wrap">
							<div class="col-md-6 col-sm-12 company_list d-flex">
								<div class="company_logo">
									<img src="${company_logo}" class="img-fluid">
								</div>
								<div style="margin-left:2vw; padding-top:2vh;">
								<h5 class="col-md-4 px-0" id="comp_name">${my_val.name}</h5> 
								<div id="jobsite">
									<div id="address"> ${jobsite_address}</div>
								</div>
								<p class="my-3 rating">${company_phone_no}</p>
								${
                  count_val >= 10
                    ? ` <p class="my-3 rating"> <span class="text-warning"> ★ </span> <span> ${
                        company_average_rating || 0
                      } </span> <span> <a href="#" onclick="return theReviewsFunction();"> <u> ${count} </u> </a> </span> </p>`
                    : "<div></div>"
                }</div>
							</div>
							<div class="col-md-6 col-sm-12 order text-left text-md-right ">
                                <div>
								<div>
                                    <a href=javascript:new_order()>
                                        <button  type="button" id="place_order" style="width:140px;margin-right:0px !important; background-color: #21b9e4 !important; font-size: 12px; box-shadow: var(--btn-shadow); !important;color:#fff; border:1px solid transparent !important; text-align: center !important; padding:8px" class="demo btn-xs mb-1 mt-1 mr-2 ">Place Order</button>
                                    </a></div>
                                    <div><a href=javascript:work_order_history()>
									<button type="button"  id="work_order" style="width:140px; padding:8px; background:white; font-size: 12px; box-shadow: var(--btn-shadow); !important;color:#333C44;border:1px solid transparent !important; text-align: center !important" class="demo btn-xs mb-1 mt-1">Work Order History</button>
									</a></div>

									<div class="documents">
									<button class="demo demo1 btn-xs mb-1 mt-1 dropdown-toggle" style="width:140px; background:white; font-size: 12px; box-shadow: var(--btn-shadow); !important;color:#333C44;border:1px solid transparent !important; padding:8px; text-align: center !important " type="button" data-toggle="dropdown">Documents
									<span class="caret"></span></button>
									<ul class="dropdown-menu" style="min-width: 120px;">
									<a style="text-decoration: none;" href=javascript:my_function("${link_coi}","COI")><div class="menuitem" style="width:130px"><div><li style=" padding: 5px; color: #333C44; display:flex; justify-content:space-between;">COI <span style = "padding-right:5px"><i class="fa fa-angle-right rotate" aria-hidden="true"></i></span></li></div></div></a>
									<a style="text-decoration: none;" href=javascript:my_function("${link_sm}","Safety&nbsp;Manual")><div class="menuitem" style="width:130px"><li style=" padding: 5px; color: #333C44; display:flex; justify-content:space-between;">Safety Manual <span style = "padding-right:5px"><i class="fa fa-angle-right rotate" aria-hidden="true"></i></li></div></a>
									<a style="text-decoration: none;" href=javascript:my_function("${w_nine}","W9")><div class="menuitem" style="width:130px"><li style=" padding: 5px; color: #333C44; display:flex; justify-content:space-between; ">W9 <span style = "padding-right:5px"><i class="fa fa-angle-right rotate" aria-hidden="true"></i></li></div></a>
									</ul>
								  </div>	
                                </div>
                               
								
                            </div>
						</div>
						<div class = "container mt-5" id ="accreditations_container">
								
						</div>
								   
						<div class="accordion mt-1 custom_collapse" id="accordionExample">
						
							<div class="card">
								<div class="card-body">
									<div class="card-header">
										<button class="card-title btn-block text-left " data-toggle="collapse" data-target="#collapse" aria-expanded="false" aria-controls="collapse">
										About &nbsp; <span class="rotate-icon "> &#x2304; </span>
										</button>
									</div>
									<div class="card-text collapse pb-2 show" id="collapse">
										${description}
									</div>
								</div>
							</div>

              <div class="card">
								<div class="card-body">
									<div class="card-header">
										<button class="card-title btn-block text-left " data-toggle="collapse" data-target="#collapse3" aria-expanded="false" aria-controls="collapse">
										Accounts Receivables &nbsp; <span class="rotate-icon "> &#x2304; </span>
										</button>
									</div>
									<div class="card-text collapse pb-2 show" id="collapse3">
										${acc_rec_name || ""}<br>
                    ${acc_rec_phone_number || ""}<br>
                    ${acc_rec_email || ""}
									</div>
								</div>
							</div>

							<div class="card">
								<div class="card-body">
									<div class="card-header">
										<button class="card-title btn-block text-left " data-toggle="collapse" data-target="#collapse1" aria-expanded="false" aria-controls="collapse">
										Industries &nbsp; <span class="rotate-icon "> &#x2304; </span>
										</button>
									</div>
									<div class="card-text collapse pb-2 show" id="collapse1">
										<div id="industry"> 
										${industry}
										</div>
								</div>
								</div>
							</div>

							<div class="card">
								<div class="card-body">
									<div class="card-header">
										<button class="card-title btn-block text-left " data-toggle="collapse" data-target="#collapse2" aria-expanded="false" aria-controls="collapse">
										Team Members &nbsp; <span class="rotate-icon "> &#x2304; </span>
										</button>
									</div>
									<div class="card-text collapse pb-2 show" id="collapse2">
										<div id="employee"> 
										${txt}
										</div>
									</div>
								</div>
							</div>

							${
                count_val >= 10
                  ? `<div class="card">
								<div class="card-body">
									<div class="card-header">
										<button class="card-title btn-block text-left " data-toggle="collapse" data-target="#collapse3" aria-expanded="false" aria-controls="collapse">
										Ratings & Reviews &nbsp; <span class="rotate-icon "> &#x2304; </span>
										</button>
									</div>
									<div class="card-text collapse pb-2 show" id="collapse3">
										<div id="employee" class="d-block"> 
										${rev} 
										</div>
									</div>
								</div>
							</div>`
                  : "<div></div>"
              }
							
						</div>
					</div>`;
        $("#dynamic_company_data1").html(template);
        setHover();
      },
    });
    setTimeout(() => {
      create_accreditations(company, company_type);
    }, 1000);
  },
});

function get_receivable_details(my_val) {
  let acc_rec_name;
  let acc_rec_email;
  let acc_rec_phone_number;
  if(my_val.organization_type=="Hiring"||my_val.organization_type=="Exclusive Hiring") {
    acc_rec_name=my_val.accounts_payable_contact_name? my_val.accounts_payable_contact_name:my_val.contact_name;
    acc_rec_email=my_val.accounts_payable_email? my_val.accounts_payable_email:my_val.email;
    acc_rec_phone_number=my_val.accounts_payable_phone_number? check_phone_number(
      my_val.accounts_payable_phone_number
    ):check_phone_number(
      my_val.phone_no
    );
  }
  else {
    acc_rec_name=my_val.accounts_receivable_name? my_val.accounts_receivable_name:my_val.contact_name;
    acc_rec_email=my_val.accounts_receivable_rep_email? my_val.accounts_receivable_rep_email:my_val.email;
    acc_rec_phone_number=my_val.accounts_receivable_phone_number? check_phone_number(
      my_val.accounts_receivable_phone_number
    ):check_phone_number(
      my_val.phone_no
    );
  }
  return {acc_rec_name,acc_rec_phone_number,acc_rec_email};
}

function setHover() {
  $(".dropdown-menu")
    .find(".menuitem")
    .hover(
      function (e) {
        $(this).css("background", "#e8f8fc");
        $(this).css("border-radius", "5px");
        $(this).css("cursor", "pointer");
      },
      function (e) {
        $(this).css("background", "white");
        $(this).css("border-radius", "5px");
        $(this).css("cursor", "default");
      }
    );
  $(".demo").hover(
    function () {
      $(this).css("border", " 1px solid #21B9E4");
    },
    function () {
      $(this).css("border", "1px solid transparent");
    }
  );
  $("head").append("<style>.demo1::after{ margin-left:3.3em }</style>");
}

function my_function(title, heading) {
  let is_docs = title.includes(".docx");
  let data = viewFile(title);
  if (is_docs) {
    return document_download(title);
  }
  if (data == undefined) {
    return;
  }
  data = data + "#toolbar=0";
  let html_content = `<div id="bodycontent" style= "overflow:auto; max-height:580px;padding-right:35px;padding-left:25px;padding:8px 10px 8px 10px;margin:15px 25px 10px 25px;background:rgb(215,218,222,.2);border-radius:5px; ">
	<object width="100%" height="550px" style="max-height:480px" data="${data}"></object>
	</div><div style="text-align:center"><a href=javascript:document_download("${title}")>
	<button type="button" id="coi" class="attached-file-link btn btn-primary mr-2 btn-xs mt-2" style="padding:5px 19.5px;">
	<i class="fa fa-download mx-2" aria-hidden="true"></i>
	<span style="margin-left:5px;margin-top:5px">Download </span>
	</button></a></div>`;

  let fields = [{ fieldname: "", fieldtype: "HTML", options: html_content }];
  let dialog = new frappe.ui.Dialog({ title: heading, fields: fields });
  dialog.$wrapper.find(".modal-dialog").css("max-width", "1000px");
  dialog.$wrapper.find("h4").css("font-size", "20px");

  dialog.show();
}

function viewFile(file1) {
  let file2 = file1.replace(/%/g, " ");
  let file = "";
  if (file2.includes("/private")) {
    file = file2.replace("/private/", "/");
  } else {
    file = file2;
  }
  if (file == "" || undefined) {
    frappe.msgprint("No File Attached");
  }
  let link = "";
  if (file.includes(".")) {
    if (file.length > 1) {
      if (file.includes("/files/")) {
        link = window.location.origin + file;
      } else {
        link = window.location.origin + "/files/" + file;
      }
      console.log(link);
      return link;
    }
  }
}

function get_reviews(r) {
  let rev = "";
  for (let k in r.message[1].slice(0, 10)) {
    let stars = get_stars(r.message[1][k][0]);
    if (r.message[1][k][1]) {
      rev +=
        "<div class= 'my-3'>" +
        stars +
        "<br>" +
        r.message[1][k][1] +
        "<br>" +
        r.message[1][k][2] +
        "<br>" +
        "</div>";
    } else {
      rev +=
        "<div class= 'my-3'>" +
        stars +
        "<br>" +
        r.message[1][k][2] +
        "<br>" +
        "</div>";
    }
  }
  return rev;
}

function new_order() {
  let b = document.getElementById("comp_name").innerHTML;
  let doc = frappe.model.get_new_doc("Job Order");
  doc.company = frappe.boot.tag.tag_user_info.company;
  doc.staff_company = b;
  doc.staff_company2 = b;
  doc.posting_date_time = frappe.datetime.now_date();
  frappe.set_route("Form", doc.doctype, doc.name);
}

//--------tg-5154 changes---------//
function work_order_history() {
  localStorage.setItem("limiter", 20);
  frappe.call({
    method:
      "tag_workflow.tag_workflow.page.dynamic_page.dynamic_page.get_link2",
    args: {
      name: company || "",
      comp: frappe.boot.tag.tag_user_info.company,
      comp_type: frappe.boot.tag.tag_user_info.company_type,
      user_id: frappe.user_info().email,
    },
    callback: function (r) {
      let body;
      let title1;
      if (r.message[1] === "exceed") {
        let opt = ``;
        title1 = "Select Your Company";
        for (let companies in r.message[0]) {
          let link = r.message[0][companies].company.split(" ").join("%@");
          opt += `<a href=javascript:work_order_history_for_multi_companies("${link}")><button type="button" class="btn btn-primary btn-sm mt-1" style="margin-right:10px">${r.message[0][companies].company}</button></a>`;
        }
        body = opt;
        let fields = [{ fieldname: "", fieldtype: "HTML", options: body }];
        let dialog = new frappe.ui.Dialog({ title: title1, fields: fields });
        dialog.show();
        dialog.$wrapper.find(".modal-dialog").css("max-width", "680px");
      } else {
        my_pop_up(r.message);
      }
    },
  });
}

function work_order_history_for_multi_companies(name2) {
  let name3 = name2.replace(/%@/g, " ");
  frappe.call({
    method:
      "tag_workflow.tag_workflow.page.dynamic_page.dynamic_page.get_link3",
    args: {
      name: company || "",
      comp: name3,
      comp_type: frappe.boot.tag.tag_user_info.company_type,
    },
    callback: function (r) {
      my_pop_up(r.message);
    },
  });
}
function my_pop_up(message) {
  org_arr = message;
  let arr1 = message[0].slice(0, 20);
  let arr2 = message[1].slice(0, 20);
  let arr3 = message[2].slice(0, 20);
  let initial_list = [arr1, arr2, arr3];
  let job_order = "";
  let created = "";
  let job_category = "";
  let rate1 = "";
  let total = "";
  let title1 = "Work Order History";
  for (let l in arr1) {
    let jobb = arr1[l].name;
    for (let s in arr3) {
      let invoice = arr3[s][1];
      if (invoice == jobb) {
        total += invoice + "<br>" + "<br>";
      }
    }

    job_order += arr1[l].name + "<br>" + "<br>";
  }

  for (let m in arr1) {
    let from_date = arr1[m].from_date + "<br>" + "<br>";

    created += from_date;
  }

  for (let n in arr2) {
    let job_cat = arr2[n].multiple_titles+" "+(arr2[n].multiple_titles.length - 1).toString() + "<br>" + "<br>";

    job_category += job_cat;
  }

  for (let p in arr1) {
    let rate = arr1[p].rate + "<br>" + "<br>";

    rate1 += rate;
  }

  let head = `<div class="table-responsive"><table class="col-md-12 mt-0 basic-table table-headers table table-hover id="dynamic_table"><thead><tr><th class="border-0">Job Order</th><th class="border-0">Start Date</th><th class="border-0">Job Title</th><th class="border-0">Invoiced Amount</th><th class="border-0"></th></tr></thead><tbody></div>`;
  let html = ``;
  let footer = `<div class="row mx-2 pt-1"> <div class="col-xl-6 col-xs-6 paging-area"> <div class="level-left">
  <div class="btn-group">
    <button type="button" class="btn btn-default btn-xs btn-paging " data-value="20" onclick="load_data(20)">20
    </button>
    <button type="button" id = "load-100" class="btn btn-default btn-xs btn-paging" data-value="100" onclick="load_data(100)">100
    </button>
    <button type="button" class="btn btn-default btn-xs btn-paging" data-value="500" onclick="load_data(500)">500
    </button>
  </div>
</div></div> <div class="col-xl-6 col-xs-6"> <button type="button" class="btn border btn-xs float-right btn-light" onclick="load_more()">Load More</button> </div> </div> </div>`;
if (message[0].length < 20) {
  setTimeout(function () {
  $(".btn-light").hide();
}, 200);
}
  html = html_data(html, initial_list);
  console.log(html);
  let body;
  if (html) {
    body = head + html + "</tbody></table>" + footer;
  } else {
    body =
      head +
      `<tr><td></td><td></td><td>No Data Found</td><td></td><td></td><td></td></tbody></table>`;
  }

  let fields = [{ fieldname: "", fieldtype: "HTML", options: body }];
  let dialog = new frappe.ui.Dialog({ title: title1, fields: fields });
  if(!$('#work_order').hasClass('active')){
    dialog.show();
    $('#work_order').addClass('active');
  }
  dialog.$wrapper.on("hidden.bs.modal", function() {
    $('#work_order').removeClass("active");
  });
  dialog.$wrapper.find(".modal-body").addClass("overflow-auto");
  dialog.$wrapper.find(".modal-dialog").css("max-width", "980px");
  dialog.$wrapper.find(".modal-body").css("max-height", "650px");
}

function html_data(html, message) {
  for (let d in message[0]) {
    if (message[2][d].total_billing_amount == null) {
      message[2][d].total_billing_amount = (0).toFixed(2);
    } else {
      console.log(
        message[2][d].total_billing_amount,
        typeof message[2][d].total_billing_amount
      );
      message[2][d].total_billing_amount = parseFloat(
        message[2][d].total_billing_amount
      ).toFixed(2);
    }
    html += `<tr><td>${message[0][d].name}</td><td>${
      message[0][d].from_date
    }</td>`
    if(message[1][d].multiple_titles.length - 1){
      html+= `<td>
                <span id="${message[0][d].name}-order-history" onmouseout="hideJobPopover('${message[0][d].name}-order-history')" onmouseover="showJobPopover('${message[1][d].multiple_titles}','${message[0][d].name}-order-history')">
                  ${message[1][d].multiple_titles[0]+" +"+(message[1][d].multiple_titles.length - 1).toString()}
                </span>
              </td>`
    }
    else{
      html += `<td><span>${message[1][d].multiple_titles[0]}</span></td>`
    }
    html += `<td>$ ${message[2][d].total_billing_amount}${
      message[0][d].order_status != "Completed" ? "*" : ""
    }</td><td><button class="btn btn-primary btn-xs primary-action" data-label="Order Details" onclick="frappe.set_route('form', 'Job Order', '${
      message[0][d].name
    }')">Order <span class="alt-underline">Det</span>ails</button></td></tr>`;
  }
  return html;
}
function load_data(limit) {
  $("tbody").html("");
  let html = ``;
  let arr1 = org_arr[0].slice(0, limit);
  let arr2 = org_arr[1].slice(0, limit);
  let arr3 = org_arr[2].slice(0, limit);
  let message = [arr1, arr2, arr3];
  html = html_data(html, message);
  $("tbody").html(html);
}
function load_more() {
  $("tbody").html("");
  let limit = parseInt(localStorage.getItem("limiter")) + 20;
  localStorage.setItem("limiter", limit);
  let html = ``;
  let arr1 = org_arr[0].slice(0, limit);
  let arr2 = org_arr[1].slice(0, limit);
  let arr3 = org_arr[2].slice(0, limit);
  let message = [arr1, arr2, arr3];
  html = html_data(html, message);
  $("tbody").html(html);
}
function document_download(file1) {
  let file2 = file1.replace(/%/g, " ");
  let file = "";
  if (file2.includes("/private")) {
    file = file2.replace("/private/", "/");
  } else {
    file = file2;
  }
  if (file == "" || undefined) {
    frappe.msgprint("No File Attached");
  }
  let link = "";
  if (file.includes(".")) {
    if (file.length > 1) {
      if (file.includes("/files/")) {
        link = window.location.origin + file;
      } else {
        link = window.location.origin + "/files/" + file;
      }
      let data = file.split("/");
      const anchor = document.createElement("a");
      anchor.href = link;
      anchor.download = data[data.length - 1];
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
    }
  }
}

function add_ress(my_val) {
  let arr = [];
  if (my_val.suite_or_apartment_no) {
    arr.push(my_val.suite_or_apartment_no);
  }

  if (my_val.address) {
    arr.push(my_val.address);
  }

  if (my_val.city) {
    arr.push(my_val.city);
  }

  if (my_val.state) {
    arr.push(my_val.state);
  }

  if (my_val.zip) {
    arr.push(my_val.zip);
  }
  return arr;
}

function block_company() {
  frappe.call({
    method:
      "tag_workflow.tag_workflow.page.dynamic_page.dynamic_page.block_company",
    freeze: true,
    freeze_message: "<p><b>Blocking Staffing Company</b></p>",
    args: {
      company_blocked: company,
      blocked_by: frappe.boot.tag.tag_user_info.company,
      user: frappe.session.user
    },
    callback: function (r) {
      if (r.message == 1) {
        frappe.msgprint("The " + company + " is blocked successfully.");
        setTimeout(function () {
          window.location.reload();
        }, 5000);
      }
    },
  });
}

function theReviewsFunction() {
  let rate = "";
  for (let k in window.rating) {
    let stars = get_stars(window.rating[k][0]);
    if (window.rating[k][1]) {
      rate +=
        stars +
        "<br>" +
        window.rating[k][1] +
        "<br>" +
        window.rating[k][2] +
        "<br>" +
        "<br>";
    } else {
      rate += stars + "<br>" + window.rating[k][2] + "<br>" + "<br>";
    }
  }
  let pop_up = new frappe.ui.Dialog({
    title: __("Ratings & Reviews"),
    fields: [
      {
        fieldname: "rate",
        fieldtype: "HTML",
        options: `<div style = "overflow: auto;max-height:500px">${rate}</div>`,
      },
    ],
  });
  pop_up.show();
}
function unblock_company() {
  frappe.call({
    method:
      "tag_workflow.tag_workflow.page.dynamic_page.dynamic_page.unblock_company",
    freeze: true,
    freeze_message: "<p><b>Unblocking Staffing Company</b></p>",
    args: {
      company_blocked: company,
      blocked_by: frappe.boot.tag.tag_user_info.company,
      user:frappe.session.user
    },
    callback: function (r) {
      if (r.message == 1) {
        frappe.msgprint("The " + company + " is unblocked successfully.");
        setTimeout(function () {
          window.location.reload();
        }, 5000);
      }
    },
  });
}

function check_phone_number(phone_no) {
  if(!phone_no) return ""
  if(phone_no.startsWith("+1")){
    let phone = phone_no.slice(2).replace(/\D/g, '');
    return "("+phone.slice(0,3)+") "+phone.slice(3,6)+"-"+phone.slice(6);
  }
  return phone_no;
}

function get_blocked_list(page) {
  if (
    frappe.boot.tag.tag_user_info.company_type == "Hiring" &&
    frappe.boot.tag.tag_user_info.company != company
  ) {
    frappe.call({
      method:
        "tag_workflow.tag_workflow.page.dynamic_page.dynamic_page.checking_blocked_list",
      args: {
        company_blocked: company,
        blocked_by: frappe.boot.tag.tag_user_info.company,
      },
      callback: function (r) {
        if (frappe.boot.tag.tag_user_info.user_type == "Hiring Admin") {
          if (r.message == 1) {
            page
              .set_secondary_action("Block Staffing Company ", () =>
                block_company()
              )
              .addClass("btn-primary block-company-btn");
          } else {
            page
              .set_secondary_action("Unblock Staffing Company ", () =>
                unblock_company()
              )
              .addClass("btn-primary block-company-btn");
            $("#place_order").hide();
          }
        } else if (r.message != 1) {
            $("#place_order").hide();
          }
      },
    });
  }
}
function create_accreditations(company_name, company_type) {
  let intitator_html = `<label><h5>Accreditations:</h5></label>
						<div class = "container-fluid" id = "accreditations_btn_section" style= " display: inline; ">	
						</div>`;
  frappe.call({
    method:
      "tag_workflow.tag_workflow.page.dynamic_page.dynamic_page.get_accreditations",
    args: { company: company_name },
    callback: function (r) {
      if (!r.message.length == 0 && company_type == "Staffing") {
        document.getElementById("accreditations_container").innerHTML =
          intitator_html;
        for (let val of r.message) {
          let btn = `<button type="button" class="Accreditations-btn btn" title="${val.attached_certificate}" onclick=create_popup(this.title)>${val.certificate_type}</button> `;
          document.getElementById("accreditations_btn_section").innerHTML =
            document.getElementById("accreditations_btn_section").innerHTML +
            btn;
        }
      }
    },
  });
}
function create_popup(link) {
  let certificate = `<div id="bodycontent" style= "overflow:auto; max-height:580px;padding-right:35px;padding-left:25px;padding:8px 10px 8px 10px;margin:15px 25px 10px 25px;background:rgb(215,218,222,.2);border-radius:5px; ">
	<object width="100%" height="550px" style="max-height:480px" data="${link}"></object>
	</div>`;
  let certificate_pop = new frappe.ui.Dialog({
    title: "Certificate Details",
    fields: [{ fieldname: "html_37", fieldtype: "HTML", options: certificate }],
  });
  certificate_pop.show();
}

function get_stars(rating) {
  let stars = "";
  let total_rating = rating;
  let full_stars = total_rating % 1;
  if (full_stars == 0) {
    stars += '<i class="fa fa-star" style="color: #f3da35"></i>'.repeat(
      total_rating
    );
  } else {
    let half_stars = full_stars;
    full_stars = total_rating - half_stars;
    stars += '<i class="fa fa-star" style="color: #f3da35"></i>'.repeat(
      full_stars
    );
    stars +=
      '<i class="fa fa-star-half-full" style="color: #f3da35"></i>'.repeat(
        half_stars * 2
      );
  }
  return stars;
}

function showJobPopover(job_list_title, job_title) {
  job_list_title  = job_list_title.split(",") 
  $("#" +  job_title).popover({
  content: function () {
    let data = ""
    for(let i=1;i<job_list_title.length;i++){
      data+= "<li>"
      data+= job_list_title[i]
      data+= "</li>"
    }
    return data
  },
  html: true,
  }).popover('show');
}

function hideJobPopover( job_title) {
  $("#" +  job_title).popover('hide');
}