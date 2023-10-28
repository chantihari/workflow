frappe.listview_settings["Hiring Company Review"] = {
  refresh() {
    if (
      frappe.session.user == "Administrator" ||
      frappe.boot.tag.tag_user_info.company_type == "TAG"
    ) {
      $("#navbar-breadcrumbs > li > a").html("Hiring Ratings & Reviews");
      $('h3[title = "Ratings & Reviews"]').html("Hiring Ratings & Reviews");
      $(".add-btn").hide();
    }
  },
  onload: (listview) => {
    $('[data-fieldname="name"]').attr("placeholder", "Name");
    listview.columns[0].df.label = "Name";
    listview.render_header(listview);
    hiring_review();
    $('[data-original-title="Hiring Company"]>div>div>input').val("");
    $(".list-row-col.ellipsis.hidden-xs.text-right").removeClass("text-right");
    let rating_filter = {
      condition: "=",
      default: null,
      fieldname: "rating_hiring",
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
  formatters: {
    rating_hiring(val, _d, f) {
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
};

function hiring_review() {
  if (frappe.boot.tag.tag_user_info.company_type == "Staffing") {
    frappe.msgprint("You don't have enough permissions.");
    frappe.set_route("app");
  }
}
