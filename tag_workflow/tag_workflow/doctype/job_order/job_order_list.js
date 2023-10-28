frappe.listview_settings["Job Order"] = {
  add_fields: ["total_no_of_workers", "total_workers_filled", "category", "is_single_share", "claim"],
  onload: function () {
    $('h3[title = "Job Order"]').html("Job Orders");
    cur_list.columns[0].df.label = "Order ID";
    cur_list.render_header(cur_list.columns);
    $(".list-header-subject > div:nth-child(7) > span:nth-child(1)").html(
      "Industry"
    );
    $('[data-fieldname="name"]').attr("placeholder", "Order ID");
    $('[data-fieldname="order_status"]').hide();
    cur_list.render_header(cur_list.columns);
    if (
      frappe.boot.tag.tag_user_info.company_type == "Hiring" ||
      frappe.boot.tag.tag_user_info.company_type == "Exclusive Hiring"
    ) {
      [cur_list.columns[3], cur_list.columns[8]] = [cur_list.columns[8], cur_list.columns[3],];
      [cur_list.columns[4], cur_list.columns[8]] = [cur_list.columns[8], cur_list.columns[4],];
      [cur_list.columns[5], cur_list.columns[6]] = [cur_list.columns[6], cur_list.columns[5],];
      [cur_list.columns[6], cur_list.columns[8]] = [cur_list.columns[8], cur_list.columns[6],];
      [cur_list.columns[8], cur_list.columns[9]] = [cur_list.columns[9], cur_list.columns[8],];
      cur_list.columns[8].df.label = "Total Approved/Required";
      cur_list.columns.splice(9, 1);
      cur_list.render_header(cur_list.columns);
    }
    if (frappe.boot.tag.tag_user_info.company_type == "Staffing") {
      [cur_list.columns[3], cur_list.columns[8]] = [cur_list.columns[8], cur_list.columns[3],];
      [cur_list.columns[4], cur_list.columns[8]] = [cur_list.columns[8], cur_list.columns[4],];
      [cur_list.columns[5], cur_list.columns[8]] = [cur_list.columns[8], cur_list.columns[5],];
      [cur_list.columns[6], cur_list.columns[8]] = [cur_list.columns[8], cur_list.columns[6],];
      [cur_list.columns[7], cur_list.columns[9]] = [cur_list.columns[9], cur_list.columns[7],];
      [cur_list.columns[8], cur_list.columns[9]] = [cur_list.columns[9], cur_list.columns[8],];   
      cur_list.columns.splice(9, 1);
      cur_list.columns[7].df.label = "Industry";
      cur_list.columns[6].df.label = "Total Head Count Available";
      cur_list.render_header(cur_list.columns);
    }
    if (
      frappe.boot.tag.tag_user_info.company_type != "Staffing" &&
      frappe.boot.tag.tag_user_info.company_type != "Hiring" &&
      frappe.boot.tag.tag_user_info.company_type != "Exclusive Hiring"
    ) {
      [cur_list.columns[3], cur_list.columns[8]] = [cur_list.columns[8], cur_list.columns[3],];
      [cur_list.columns[4], cur_list.columns[8]] = [cur_list.columns[8], cur_list.columns[4],];
      [cur_list.columns[5], cur_list.columns[8]] = [cur_list.columns[8], cur_list.columns[5],];
      [cur_list.columns[6], cur_list.columns[9]] = [cur_list.columns[9], cur_list.columns[6],];
      cur_list.columns.splice(8, 2);
      cur_list.columns[6].df.label = "Industry";
      cur_list.render_header(cur_list.columns);
    }
    if (frappe.session.user != "Administrator") {
      $(".custom-actions.hidden-xs.hidden-md").hide();
      $('[data-original-title="Refresh"]').hide();
      $(".menu-btn-group").hide();
    }

    if (window.location.search) {
      $("button.btn.btn-sm.filter-button.btn-primary-light").hide();
      frappe.route_options = {
        order_status: "",
        staff_company:['like', frappe.boot.tag.tag_user_info.company]
      };
    } else {
      frappe.route_options = {
        order_status: "",
      };
    }

    if (frappe.boot.tag.tag_user_info.company_type == "Staffing") {
      frappe.db.get_value(
        "Company",
        { parent_staffing: frappe.boot.tag.tag_user_info.company },
        ["name"],
        function (r) {
          if (r.name === undefined) {
            $(".btn-primary").hide();
          }
        }
      );
    }
    if (
      frappe.session.user == "Administrator" ||
      frappe.boot.tag.tag_user_info.company_type == "TAG"
    ) {
      $(".btn-primary").hide();
    }
    document.body.addEventListener(
      "click",
      function () {
        $('[role = "tooltip"]').popover("dispose");
      },
      true
    );
  },
  refresh: function (listview) {
    $(".custom-actions.hidden-xs.hidden-md").hide();
    $("#navbar-breadcrumbs > li:nth-child(2) > a").html("Job Orders");
    $('[data-original-title="Menu"]').hide();
    $('[data-fieldname="order_status"]').hide();
    if (frappe.boot.tag.tag_user_info.company_type == "Staffing") {
      $(".unread_jo").closest(".list-row").addClass("unread_job");
      frappe.db.get_value(
        "Company",
        { parent_staffing: frappe.boot.tag.tag_user_info.company },
        ["name"],
        function (r) {
          if (r.name === undefined) {
            $("button.btn.btn-primary.btn-sm.btn-new-doc.hidden-xs").hide();
          }
        }
      );
    }

    $('[role = "tooltip"]').popover("dispose");
    const df = {
      condition: "=",
      default: null,
      fieldname: "company",
      fieldtype: "Select",
      input_class: "input-xs",
      is_filter: 1,
      onchange: function () {
        cur_list.refresh();
      },
      options: get_company_job_order(),
      placeholder: "Company",
    };
    if (cur_list.page.fields_dict.company === undefined) {
      listview.page.add_field(df, ".standard-filter-section");
    }
    if (
      frappe.boot.tag.tag_user_info.company_type != "Staffing" &&
      frappe.boot.tag.tag_user_info.company_type != "Hiring" &&
      frappe.boot.tag.tag_user_info.company_type != "Exclusive Hiring"
    ) {
      document
        .getElementsByClassName("frappe-list")[0]
        .classList.add("order-list-tag");
      document
        .getElementsByClassName("list-row-col")[7]
        .classList.remove("text-right");
        document.getElementsByClassName("list-row-col")[7].style.textAlign =
        "center";
      document
        .getElementsByClassName("list-row-col")[6]
        .classList.remove("text-right");


    }
    if (frappe.boot.tag.tag_user_info.company_type == "Staffing") {
      document
        .getElementsByClassName("frappe-list")[0]
        .classList.add("order-list-staffing");
      document
        .getElementsByClassName("list-row-col")[8]
        .classList.remove("text-right");
      document.getElementsByClassName("list-row-col")[8].style.textAlign =
        "center";
      document
        .getElementsByClassName("list-row-col")[7]
        .classList.remove("text-right");
      document.getElementsByClassName("list-row-col")[7].style.textAlign =
        "left";

        
    }
    if (
      frappe.boot.tag.tag_user_info.company_type == "Hiring" ||
      frappe.boot.tag.tag_user_info.company_type == "Exclusive Hiring"
    ) {
      document
        .getElementsByClassName("frappe-list")[0]
        .classList.add("order-list-hiring");
      document
        .getElementsByClassName("list-row-col")[8]
        .classList.remove("text-right");
    }
  },

  formatters: {
    select_job(val,d,f){
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
          } else if(r.message.length - 1){
              y=`<span class="ellipsis_title" id="Job-${f.name}-titles">
              <a class="ellipsis_title" data-job="${r.message[0]}" onmouseover="showJobPopover('${r.message}','Job-${f.name}-titles')" 
              onmouseout="hideJobPopover('Job-${f.name}-titles')">${r.message[0] + " + " + (r.message.length - 1)}</a>
              </span>
              <script>
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
            </script>`
            }
            else{
              y=`<span class="ellipsis_title" id="Job-${f.name}-titles">
              <a class="ellipsis_title" data-job="${r.message[0]}">${r.message[0]}</a>
              </span>`
            }
        },
      });
      return y
    },
    order_status(val, d, f) {
      if (
        frappe.boot.tag.tag_user_info.company_type == "Staffing" &&
        !["Completed", "Canceled"].includes(val) &&
        f.total_no_of_workers != f.total_workers_filled
      ) {
        let y;
        frappe.call({
          method: "tag_workflow.tag_data.vals",
          args: {
            name: f.name,
            comp: frappe.boot.tag.tag_user_info.company,
          },
          async: 0,
          callback: function (r) {
            if (r.message == "success") {
              y = val;
            } else {
              y = "Available";
            }
          },
        });
        if (y == "Available") {
          return `<span class=" ellipsis" title="" id="${val}-${f.name}" >
								<a class=" indicator-pill gray ellipsis" data-filter="${d.fieldname},=,${val}" data-fieldname="${val}-${f.name}" >Available</a>
							</span>`;
        } else {
          return `<span class=" ellipsis" title="" id="${val}-${f.name}" >
								<a class=" indicator-pill gray ellipsis" data-filter="${d.fieldname},=,${val}" data-fieldname="${val}-${f.name}" >${val}</a>
							</span>`;
        }
      } else if (val == "Completed") {
        return `<span class=" ellipsis" title="" id="${val}-${f.name}" >
						<a class=" indicator-pill green ellipsis" data-filter="${d.fieldname},=,${val}" data-fieldname="${val}-${f.name}" >${val}</a>
					</span>`;
      }else if (val == "Canceled") {
        return `<span class=" ellipsis" title="" id="${val}-${f.name}" >
						<a class=" indicator-pill red ellipsis" data-filter="${d.fieldname},=,${val}" data-fieldname="${val}-${f.name}" >${val}</a>
					</span>`;
      }else {
        return `<span class=" ellipsis" title="" id="${val}-${f.name}" >
						<a class=" indicator-pill gray ellipsis" data-filter="${d.fieldname},=,${val}" data-fieldname="${val}-${f.name}" >${val}</a>
					</span>`;
      }
    },
    company(val, d, f) {
      if (val) {
        return `<span class=" ellipsis" title="" id="Hiring-${f.name}" >
						<a class="ellipsis" data-filter="${d.fieldname},=,${val}" data-fieldname="${val}-${f.name}" onmouseover="showCasePopover('${val}','${f.name}')" onmouseout = "hideCasePopover('${val}','${f.name}')"  onclick = "myfunction('${val}')" data-company = "company" >${val}</a>
						
					</span>
					<script>
						function showCasePopover(cname,dname){
							$('.popover-body').hide();
							$("#Hiring-"+dname).popover({
								title: name,
								content: function(){
									let div_id =  "tmp-id-" + $.now();
									return details_in_popup($(this).attr('href'), div_id, cname)
								},
								html: true,
							}).popover('show');
						}

						function myfunction(name){
							$('.popover-body').hide();
							$('.arrow').hide();
							
							let name1= name.replace(/%/g, ' ');
							localStorage.setItem('company', name1)
							window.location.href= "/app/dynamic_page"
					
						}

						function details_in_popup(link, div_id, cname){
							frappe.call({
								method: "tag_workflow.tag_workflow.doctype.job_order.job_order.get_company_details",
								args: {"comp_name":cname},
								callback: function(res) {
									if (!res.exc) {
										$('#'+div_id).html(popup_content(res.message));
									}
								}
							});
							return '<div id="'+ div_id +'">Loading...</div>';
						}
						function popup_content(rawContent){
							let cont = "";
							for (const [key, value] of Object.entries(rawContent)) {
								const arr = key.replace(/_/g, " ").split(" ");
								for (let i = 0; i < arr.length; i++) {
									arr[i] = arr[i].charAt(0).toUpperCase() + arr[i].slice(1);
								}
                if (key=="organization_type"){
                  const final_key = "Company Type";
                  cont+= "<b>"+final_key+":</b> "+value+" <br />";
                }
                else{
                  const final_key = arr.join(" ");
                  cont+= "<b>"+final_key+":</b> "+value+" <br />";
                }
							}
							return cont;
						}
						function hideCasePopover(cname,dname){
							$("#Hiring-"+dname).popover('hide');
						}
					</script>`;
      } else {
        return `<span class="ellipsis" title=""><a class="ellipsis" data-filter="${d.fieldname},=,''"></a></span>`;
      }
    },
    name(val, d, f) {
      let unread_jo = f.is_single_share==1 && !f.claim && f.order_status != "Completed" ? "unread_jo":"";
      if (val) {
        return `<span class="level-item select-like ${unread_jo}">
						<input class="list-row-checkbox" type="checkbox" data-name="${f.name}">
						<span class="list-row-like hidden-xs style=" margin-bottom:="" 1px;"="">
							<span class="like-action not-liked" data-name="${f.name}" data-doctype="Job Order" data-liked-by="null" title="">
								<svg class="icon  icon-sm" style="">
									<use class="like-icon" href="#icon-heart"></use>
								</svg>
							</span>
							<span class="likes-count"></span>
						</span>
					</span>
					<span class=" ellipsis" title="" id="${f.name}">
						<a class="ellipsis" href="/app/job-order/${val}" data-doctype="Job Order" onmouseover="showCasePopover1('${val}','${f.name}')" onmouseout = "hideCasePopover1('${val}','${f.name}');"  data-jobname = "name" >${val}</a>
					</span>
					<script>
						function showCasePopover1(cname,dname){
							$("#"+dname).popover({
								title: name,
								content: function(){
									var div_id =  "tmp-id-" + $.now();
									return details_in_popup1($(this).attr('href'), div_id, cname);
								},
								html: true,
							}).popover('show');
						}
						function details_in_popup1(link, div_id, cname){
							frappe.call({
								method: "tag_workflow.tag_workflow.doctype.job_order.job_order.get_joborder_value",
								args: {"name": cname, "user": frappe.session.user, "company_type": frappe.boot.tag.tag_user_info.company_type},
								callback: function(res) {
									if(res.message=='error_occur'){
										console.log('some error occur')
									}
									else if (!res.exc) {
										$('#'+div_id).html(popup_content1(res.message));
									}		 
								}
							});
							return '<div id="'+ div_id +'">Loading...</div>';
						}

						function popup_content1(rawContent){
							var cont = "";
							for (const [key, value] of Object.entries(rawContent)) {
                let final_key = "";
                if(key=='category'){
                  final_key = 'Industry';
                }else{
								  const arr = key.replace(/_/g, " ").split(" ");
								  for (var i = 0; i < arr.length; i++) {
									  arr[i] = arr[i].charAt(0).toUpperCase() + arr[i].slice(1);
								  }
								  final_key = arr.join(" ");
                }  
								cont+= "<b>"+final_key+":</b> "+value+" <br />";
							}
							return cont;
						}
						function hideCasePopover1(cname,dname){
							$("#"+dname).popover('hide');
						}
					</script>`;
      } else {
        return `<span class="ellipsis" title=""><a class="ellipsis" data-filter="${d.fieldname},=,''"></a></span>`;
      }
    },
    job_start_time(val, d, f) {
        let time;
        frappe.call({
          method: "tag_workflow.tag_data.min_job_start_time",
          args: {
            job_order: f.name,
          },  
          async: 0,
          callback: function (r) {
            if(r.message[0]){
              let start_time = r.message[0][0]
              start_time = start_time.split(":")
              start_time.pop()
              start_time=start_time.join(":")
              time = `<span class="ellipsis_ind" id="Job-${f.name}-time">             
              ${start_time}
              </span>`
            }
          }
        })
        return time
    },
    head_count_available(val, d, f) {
      if (val == "success") {
        return `<span class=" ellipsis" title="" id="${val}-${f.name}" ><a  data-filter="${d.fieldname},=,${val}" data-fieldname="${val}-${f.name}">0</a></span>`;
      } else {
        return `<span class=" ellipsis" title="" id="${val}-${f.name}" ><a  data-filter="${d.fieldname},=,${val}" data-fieldname="${val}-${f.name}" >${f.total_no_of_workers-f.total_workers_filled}</a></span>`;
      }
    },
    no_of_workers(val, d, f) {
      if (
        frappe.boot.tag.tag_user_info.company_type == "Hiring" ||
        frappe.boot.tag.tag_user_info.company_type == "Exclusive Hiring"
      ) {
        let counts=return_counts(f);
        return counts
      } else if ((frappe.boot.tag.tag_user_info.company_type == "Staffing") || (frappe.boot.tag.tag_user_info.company_type != "Hiring" && frappe.boot.tag.tag_user_info.company_type != "Exclusive Hiring")) {
        
        let category;
        frappe.call({
          method: "tag_workflow.tag_data.industry_listing_page_vals",
          args: {
            job_order: f.name,
          },                                                            
          async: 0,
          callback: function (r) {
            if (r.message == "Single Industry") {
              category = f.category;
              return `<div class = "list-row-col ellipsis hidden-xs text-left" ><span class=" ellipsis" title="" id="${val}-${f.name}" >${category}</span></div>`;
            } else if(r.message.length - 1){
                category=`<span class="ellipsis_ind" id="Job-${f.name}-industry">
                <a class="ellipsis_ind" data-job="${r.message[0]}" onmouseover="showIndustryPopover('${r.message}','Job-${f.name}-industry')" 
                onmouseout="hideIndustryPopover('Job-${f.name}-industry')">${r.message[0] + " + " + (r.message.length - 1)}</a>
                </span>
                <script>
              function showIndustryPopover(job_list, job_industry) {
                job_list  = job_list.split(",") 
  
                $("#" +  job_industry).popover({
                content: function () {
                  var data = ""
                  for(var i=1;i<job_list.length;i++){
                    data+= "<li>"
                    data+= job_list[i]
                    data+= "</li>"
                  }
                  return data
                },
                html: true,
                }).popover('show');
              }
              function hideIndustryPopover( job_industry) {
                $("#" +  job_industry).popover('hide');
              }
              </script>`
              }
              else{
                category=`<span class="ellipsis_ind" id="Job-${f.name}-titles">
              <a class="ellipsis_ind" data-job="${r.message[0]}">${r.message[0]}</a>
              </span>`
              }
          },
        });
        return category
      }
    },
  },
};

function return_counts(f) {
  let claimed_w = f.total_workers_filled;
  let total_required = f.total_no_of_workers;
  let counts = `<span class="ellipsis_ind" id="Job-${f.name}-counts">
                  <a class="ellipsis_ind" data-job="${f.name}" onmouseover="showCountsPopover('${f.name}', 'Job-${f.name}-counts')" 
                  onmouseout="hideCountsPopover('Job-${f.name}-counts')">${claimed_w}/${total_required}</a>
                </span>
                <script>
                  function showCountsPopover(job_order, job_industry) {
                    frappe.call({
                      method: "tag_workflow.tag_data.total_approved_or_required",
                      args: {
                        job_order: job_order
                      },
                      async: 0,
                      callback: function(r) {
                        let counts;
                        if (r.message == "Single Industry") {
                          counts = '<div class="list-row-col ellipsis hidden-xs text-left"><span class="ellipsis" title="" id="Job-' + job_order + '-counts">' + claimed_w + '/' + total_required + '</span></div>';
                        } else if (Array.isArray(r.message)) {
                          let job_list = r.message;
                          let data = "";
                          for (let i = 0; i < job_list.length; i++) {
                            data += "<li>";
                            data += job_list[i];
                            data += "</li>";
                          }
                          $("#" + job_industry).popover({
                            content: data,
                            html: true,
                          }).popover('show');
                        }
                        $("#" + job_industry).html(counts);
                      }
                    });
                  }
                  function hideCountsPopover(job_industry) {
                    $("#" + job_industry).popover('hide');
                  }
                </script>`;
  return counts;
}

function get_company_job_order() {
  let text = "\n";

  frappe.call({
    method: "tag_workflow.utils.whitelisted.get_company_job_order",
    args: {
      user_type: frappe.boot.tag.tag_user_info.company_type,
    },
    async: 0,
    callback: function (r) {
      if (r.message) {
        text += r.message;
      }
    },
  });
  return text;
}

setTimeout(function () {
  const btn = document.getElementById("staff_filter_button1");
  btn.addEventListener("click", function () {
    cur_list.order_status = "Available";
    cur_list.start = 0;
    cur_list.refresh();
  });

  const btn2 = document.getElementById("staff_filter_button2");
  btn2.addEventListener("click", function () {
    cur_list.order_status = "Ongoing";
    cur_list.start = 0;
    cur_list.refresh();
  });

  const btn3 = document.getElementById("staff_filter_button3");
  btn3.addEventListener("click", function () {
    cur_list.order_status = "Upcoming";
    cur_list.start = 0;
    cur_list.refresh();
  });

  const btn4 = document.getElementById("staff_filter_button4");
  btn4.addEventListener("click", function () {
    cur_list.order_status = "Completed";
    cur_list.start = 0;
    cur_list.refresh();
  });

  const btn5 = document.getElementById("staff_filter_button5");
  btn5.addEventListener("click", function () {
    cur_list.order_status = "All";
    cur_list.start = 0;
    cur_list.refresh();
  });

  const btn6 = document.getElementById("staff_filter_button6");
  btn6.addEventListener("click", function () {
    cur_list.order_status = "Canceled";
    cur_list.start = 0;
    cur_list.refresh();
  });
}, 2000);
