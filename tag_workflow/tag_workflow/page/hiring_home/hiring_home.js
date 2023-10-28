frappe.pages["hiring-home"].on_page_load = function(wrapper) {
  let page = frappe.ui.make_app_page({
    parent: wrapper,
    title: "",
    single_column: true,
  });
  wrapper.HireHome = new frappe.HireHome(wrapper, page);
  wrapper.HireHome.get_order_data();
}
frappe.pages['hiring-home'].refresh = function(wrapper) {
	reload_page()
}
frappe.HireHome = Class.extend({
  init: function(wrapper, page) {
    let me = this;
    this.parent = wrapper;
    this.page = this.parent.page;
    me.setup(wrapper, page);
  },
  setup: function(wrapper, page) {
    this.body = $(`<style>
		.home-tab .inner-search {
			max-width: 470px;
			width: 100%;
			transition: .8s ease-in-out;
			display: none;
			position: absolute;
			background: #fff;
		}
	
		<style>
		.home-tab .inner-search {
		max-width: 470px;
		width: 100%;
		transition: .8s ease-in-out;
		display: none;
		position: absolute;
		background: #fff;
		}
	</style>
	<div class="row hiring-home">
		<div class="col-xs-12 tittle">
			<div class="widget-group-title">
				<h3>Discover Top-Rated Professionals</h3>
				<p>We are here to help you with any project</p>
			</div>
			<div class="widget-group-control"></div>
		</div>
		<div style="display:inline-flex">
			<div class="container" style="display:inline-flex; align-items: center;">
				<div style="color:pink"><select name="search_choice" id="search_choice" class="demo demo1 btn-xs mb-1 mt-1 search_dropdown" onchange=toogle_search_icon()>
					<option value="company_name" style=" padding: 5px; color: #333C44;">Company Name</option>
					<option value="industry" style=" padding: 5px; color: #333C44;">Industry</option>
					<option value="city" style=" padding: 5px; color: #333C44;">City</option>
				</select></div>
				<div class="frappe-control input-max-width search_field" style="margin-left:0px">
					<div class="form-group" style="margin-bottom: 0px">
						<div class="control-input-wrapper">
							<div class="control-input" style="display: block;">
								<input class="form-control my-0 py-2 search-area" type="text" placeholder="Search" aria-label="Search" oninput="update_list()" id="staff">
								<span class="search_icon">
									<i class="fa fa-search" aria-hidden="true" onclick=toogle_search_icon()></i>
								</span>
								<div class="inner-search border shadow rounded mt-2 py-3" style="display: none;">
									<div class="d-flex flex-wrap border-bottom">
										<div class="col-md-6">
											<label class="text-secondary placeholder_change"> Top search company </label>
										</div>
										<div class="col-md-6 text-right">
											<a style="color: #21b9e4 !important;" onclick=redirect_see_all()> See All</a>
										</div>
									</div>
									<div id="staffing_list"></div>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
	<div class="row widget-group">
		<div class="col-md-10 widget-group-head col-xs-6 col-sm-6">
			<div class="widget-group-title mt-2">Today's Orders</div>
			<div class="widget-group-control"></div>
		</div>
		<div class="col-md-2 col-xs-6 col-sm-6 ">
			<button class="btn btn-xs btn-primary px-2 float-right restricted-button flex align-center" onclick="frappe.set_route('form', 'Job Order')">
				View All
			</button>
		</div>
		<div class="col-xs-12">
			<div class="widget widget-shadow hiring_dashboard_table p-0 shortcut-widget-box" id="data"></div>
		</div>
	</div>
	<div class="col-xs-12">
	<div class="widget widget-shadow hiring_dashboard_table p-0 shortcut-widget-box" id="data">
	</div>
	</div>
		<div class="widget-group ">
		<div class="widget-group-head">
			<div class="widget-group-title">Shortcuts</div>
			<div class="widget-group-control"></div>
		</div>
		<div class="widget-group-body grid-col-3">
			<div class="widget widget-shadow shortcut-widget-box" data-widget-name="a85252dcd0"
				onclick=redirect_doc("job-order")>
				<div class="widget-head">
					<div>
						<div class="widget-title ellipsis" name="home-job-order">Job Orders</div>
						<div class="widget-subtitle"></div>
					</div>
					<div class="widget-control"></div>
				</div>
				<div class="widget-body"></div>
				<div class="widget-footer"></div>
			</div>
			<div class="widget widget-shadow shortcut-widget-box" data-widget-name="a98f4b28cd"
				onclick=redirect_doc("job-site")>
				<div class="widget-head">
					<div>
						<div class="widget-title ellipsis">Job Sites</div>
						<div class="widget-subtitle"></div>
					</div>
					<div class="widget-control"></div>
				</div>
				<div class="widget-body"></div>
				<div class="widget-footer"></div>
			</div>
		</div>
	</div>
	<div class="widget-group">
		<div class="widget-group-head">
			<div class="widget-group-title">My Activities</div>
			<div class="widget-group-control"></div>
		</div>
		<div class="widget-group-body grid-col-3">
			<div class="widget links-widget-box" data-widget-name="6ff65e433e">
				<div class="widget-head">
					<div>
						<div class="widget-title ellipsis">
							<svg class="icon icon-sm">
								<use class="" href="#icon-file"></use>
							</svg>
							<span>Operations (Settings)</span>
						</div>
						<div class="widget-subtitle"></div>
					</div>
					<div class="widget-control"></div>
				</div>
				<div class="widget-body">
					<a href="/app/user" class="link-item ellipsis" type="Link">
						<span class="indicator-pill no-margin gray"></span>
						<span class="link-content ellipsis">Company Users</span>
					</a>
					<a href="#" class="link-item ellipsis" type="Link" onclick=redirect_doc("company")>
						<span class="indicator-pill no-margin gray"></span>
						<span class="link-content ellipsis">Affiliate Companies</span>
					</a>
					<a href="/app/contract" class="link-item ellipsis" type="Link">
						<span class="indicator-pill no-margin gray"></span>
						<span class="link-content ellipsis">Contract</span>
					</a>
				</div>
				<div class="widget-footer"></div>
			</div>
			<div class="widget links-widget-box" data-widget-name="c8b579fdd9">
				<div class="widget-head">
					<div>
						<div class="widget-title ellipsis">
							<svg class="icon icon-sm">
								<use class="" href="#icon-file"></use>
							</svg>
							<span>Job Order Resources</span>
						</div>
						<div class="widget-subtitle"></div>
					</div>
					<div class="widget-control"></div>
				</div>
				<div class="widget-body">
					<a href="#" onclick=redirect_doc("job-site") class="link-item ellipsis" type="Link">
						<span class="indicator-pill no-margin gray"></span>
						<span class="link-content ellipsis">Job Sites</span>
					</a>
					<a href="/app/job-order" class="link-item ellipsis" type="Link">
						<span class="indicator-pill no-margin gray"></span>
						<span class="link-content ellipsis">Job Orders</span>
					</a>
					<a href="/app/timesheet" class="link-item ellipsis" type="Link">
						<span class="indicator-pill no-margin gray"></span>
						<span class="link-content ellipsis">Timesheets</span>
					</a>
					<a href="/app/sales-invoice" class="link-item ellipsis" type="Link">
						<span class="indicator-pill no-margin gray"></span>
						<span class="link-content ellipsis">Invoices</span>
					</a>
				</div>
				<div class="widget-footer"></div>
			</div>
		</div>
	</div>
	
	<script>
		 function redirect_see_all(){
			let data = document.getElementById("staff").value;
			if((document.getElementById('search_choice').selectedOptions[0].value=="city") || (document.getElementById('search_choice').selectedOptions[0].value=="company_name")){localStorage.setItem(document.getElementById('search_choice').selectedOptions[0].value, document.getElementById('staff').value);window.location.href = "/app/staff_company_list";}
			else{
				window.location.href = "/app/staff_company_list"
			}		 
		 }
		function toogle_search_icon(){
			$(".fa-remove").removeClass("fa-remove")
			$(".fa").addClass("fa-search")
			}
		function update_list(){
			$(".inner-search").css("display", "none");
			let data = document.getElementById("staff").value;
			if (data.length == 0)
			{
			$(".fa-remove").removeClass("fa-remove")
			$(".fa").addClass("fa-search")
			}
			let search_choice_val = document.getElementById('search_choice').selectedOptions[0].value;
			if(search_choice_val=="industry")
			{
			$(".placeholder_change").html("Top Search Industry")
			}
			if(search_choice_val=="city")
			{
			$(".placeholder_change").html("Top Search City")
			}
			if(search_choice_val=="company_name")
			{
			$(".placeholder_change").html("Top Search Company")
			}
			var ignoreClickOnMeElement = document.getElementById('staff');
			    document.addEventListener('click', function(event) {
				var isClickInsideElement = ignoreClickOnMeElement.contains(event.target);
				if (!isClickInsideElement) {
					$(".inner-search").css("display", "none");
					document.getElementById("staff").value=""
				}
			    });
			  frappe.call({
					method: "tag_workflow.utils.whitelisted.search_staffing_by_hiring",
					args: {"data": data,"search_choice_val":search_choice_val},
					callback: function(r){
					if(r && r.message.length){
					let result = r.message || [];
					let html="";
					$(".fa-search").removeClass("fa-search")
					$(".fa").addClass("fa-remove")
					var input = document.getElementById("staff");
					$( "#staff" ).keyup(function() {
					$( "#staff" ).keyup();
					alert( "Handler for .keyup() called." );
					});
						input.addEventListener("keyup", function(event) {
							if (event.keyCode === 13) {
								if (result.length > 0 && data.length>0)
								{	
									if((document.getElementById('search_choice').selectedOptions[0].value=="city") || (document.getElementById('search_choice').selectedOptions[0].value=="company_name")){localStorage.setItem(document.getElementById('search_choice').selectedOptions[0].value, document.getElementById('staff').value);window.location.href = "/app/staff_company_list";}
									 else{
										localStorage.setItem(document.getElementById('search_choice').selectedOptions[0].value, result[0]);
										window.location.href = "/app/staff_company_list"
									 }

								}
							}
						});
					for(let d in result){
					if(result[d] != "undefined"){
					document.getElementsByClassName("search_icon").innerHTML = "";
					document.getElementsByClassName("search_icon").innerHTML = "<i class='fa fa-remove' aria-hidden='true'></i>";
					let link = result[d].split(' ').join('%');
					html += "<div class='d-flex flex-wrap border-bottom' style='margin-top: 0.5rem;'><div class='col-md-12' onclick=dynamic_route('"+link+"')><label class='text-secondary'><a onclick=dynamic_route('"+link+"')>"+result[d]+"</a></label></div></div>"
					}
					}
					$("#staffing_list").html(html);
					$(".inner-search").css("display", "block");
					}
					}
			  });
		}

			function dynamic_route(name){
			if(document. getElementById('search_choice'). selectedOptions[0]. value == "company_name"){
			name1= name.replace(/%/g, ' ');
			localStorage.setItem("company", name1);
			window.location.href = "/app/dynamic_page"; }
			
			else{
				if(document. getElementById('search_choice'). selectedOptions[0].value=="industry"){
					localStorage.setItem("industry", name.replace(/%/g, ' '));
				}
			    else{localStorage.setItem("city", name.replace(/%/g, ' '));}
			window.location.href = "/app/staff_company_list"; 
			} 
			}
			</script>`).appendTo(this.page.main);
    $(frappe.render_template("hiring_home", "")).appendTo(this.body);
  },
  get_order_data() {
    let data;
    frappe.call({
      method: "tag_workflow.utils.whitelisted.get_order_data",
      async: false,
      callback: function(r) {
        data = r.message;
      },
    });
    let body;
    let head = `<table class="col-md-12 basic-table table-headers table table-hover"><thead id="Hiring_home_head"><tr><th>Job Order</th><th>Job Titles</th><th>Date</th><th>Job Site</th><th>Company</th><th style="text-align:center">Total Assigned/Required</th><th></th></tr></thead><tbody>`;
    let html = `<script>
	function show_count_popover(val){
		frappe.call({
			method: "tag_workflow.tag_data.total_approved_or_required",
			args: {
			  job_order: val,
			},
			async: 0,
			callback: function(r) {
				if(r.message!="Single Industry"){
				console.log("#" +  val+'-total_workers')
				$("#" +  val+'-total_workers').popover({
				content: function () {
					let data = ""
					for(let i=0;i<r.message.length;i++){
					data+= "<li>"
					data+= r.message[i]
					data+= "</li>"
					}
					return data
				},
				html: true,
				}).popover('show');
			}
		}})
		
	}
	function hide_count_popover(val) {
		$("#" +  val+'-total_workers').popover('hide');
	  }
	</script>`;
    for (let d in data) {
		let jobTitle = this.select_job(data[d].select_job, data[d], data[d]);
      	html += `<tr><td>${data[d].name}</td><td>${jobTitle}</td><td>${data[d].date}</td><td>${
        data[d].job_site
      }</td><td>${data[d].company}</td><td style="text-align:center"><span class="ellipsis_title" id="${data[d].name}-total_workers"  onmouseover="show_count_popover('${data[d].name}')" onmouseout="hide_count_popover('${data[d].name}')">${data[d].total_workers_filled}/${
        data[d].total_no_of_workers
      }</span></td><td><button class="btn btn-primary btn-xs primary-action" data-label="Order Details" onclick="frappe.set_route('form', 'Job Order', '${
        data[d].name
      }')">Order<span class="alt-underline"> Det</span>ails</button></td></tr>`;
    }
    if (html) {
      body = head + html + "</tbody></table>";
    } else {
      body =
        head +
        `<tr><td></td><td></td><td>No Data Found</td><td></td><td></td><td></td></tbody></table>`;
    }
    $("#data").html(body);
  },
  select_job(val, d, f) {
	let y;
	frappe.call({
	  method: "tag_workflow.tag_data.job_titles_listing_page_vals",
	  args: {
		job_order: f.name,
	  },
	  async: 0,
	  callback: function (r) {
		if (r.message == "Single Title") {
		  y = `${val}`
		} else if (r.message.length > 1) {
			y = `<span class="ellipsis_title" id="Job-${f.name}-titles">
				<a class="ellipsis_title" data-job="${r.message[0]}" onmouseover="showJobPopover('${r.message}','Job-${f.name}-titles')" 
				onmouseout="hideJobPopover('Job-${f.name}-titles')">${r.message[0] + " + " + (r.message.length - 1)}</a>
				</span>
				<script>
				  function showJobPopover(job_list_title, job_title) {
					job_list_title = job_list_title.split(",");
					$("#" + job_title).popover({
					  content: function () {
						let data = "";
						for (let i = 1; i < job_list_title.length; i++) {
						  data += "<li>";
						  data += job_list_title[i];
						  data += "</li>";
						}
						return data;
					  },
					  html: true,
					}).popover('show');
				  }
				  function hideJobPopover(job_title) {
					$("#" + job_title).popover('hide');
				  }
				</script>`;
		  } else {
			y = `<span class="ellipsis_title" id="Job-${f.name}-titles">
				<a class="ellipsis_title" data-job="${r.message[0]}">${r.message[0]}</a>
				</span>`;
		  }
	  },
	});
	return y;
  }
});

function reload_page(){
	let val = parseInt(localStorage.getItem("refresh"))
	if(val == 1){
		window.location.reload()
	}
	localStorage.setItem("refresh",0)
}
function redirect_doc(name) {
  location.href = "/app/" + name;
}
