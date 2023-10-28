frappe.listview_settings["Company Review"] = {
  refresh: () => {
    if (
      frappe.session.user == "Administrator" ||
      frappe.boot.tag.tag_user_info.company_type == "TAG"
    ) {
      $("#navbar-breadcrumbs > li > a").html("Staffing Ratings & Reviews");
      $('h3[title = "Ratings & Reviews"]').html("Staffing Ratings & Reviews");
      $(".add-btn").hide();
    }
    $('[data-original-title="ID"]').hide();
    cur_list.render_header(cur_list.columns);
    staffing_review();
    $(".list-row-col.ellipsis.hidden-xs.text-right").removeClass("text-right");
  },
  hide_name_column: true,
  formatters: {
    staffing_ratings(val, _d, f) {
      return `<div class="list-row-col ellipsis hidden-xs ">
				<span class="ellipsis" title="${f.name}: ${val}">
				<a class="filterable ellipsis">
					<span class="rating pr-2"><svg class="icon icon-sm star-click" data-rating="1"><use href="#icon-star"></use></svg>(${val})</span>
				</a>
			</span>
			</div>`;
    },
    job_order(val, d, f) {
      return `<span class=" ellipsis2" title="" id="${val}-${f.name}">
                        <a class="ellipsis" href="/app/job-order/${val}" data-filter="${d.fieldname},=,${val}" data-fieldname="${val}-${f.name}">${val}</a>
                    </span>`;
    },
  },
  onload: function (listview) {
    let rating_filter = {
      condition: "=",
      default: null,
      fieldname: "staffing_ratings",
      fieldtype: "Data",
      input_class: "input-xs",
      label: "Ratings",
      is_filter: 1,
      onchange: function () {
        listview.refresh();
      },
      placeholder: "Ratings",
    };
    let standard_filters_wrapper = listview.page.page_form.find(
      ".standard-filter-section"
    );
    listview.page.add_field(rating_filter, standard_filters_wrapper);
  },
};

function staffing_review() {
  if (
    ["Hiring", "Exclusive Hiring"].includes(
      frappe.boot.tag.tag_user_info.company_type
    )
  ) {
    frappe.msgprint("You don't have enough permissions.");
    frappe.set_route("app");
  }
}
