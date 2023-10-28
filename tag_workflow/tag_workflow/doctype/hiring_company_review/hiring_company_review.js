// Copyright (c) 2021, SourceFuse and contributors
// For license information, please see license.txt

frappe.ui.form.on("Hiring Company Review", {
  refresh: (frm) => {
    if (
      frappe.session.user == "Administrator" ||
      frappe.boot.tag.tag_user_info.company_type == "TAG"
    ) {
      $("#navbar-breadcrumbs > li:nth-child(1) > a").html(
        "Hiring Ratings & Reviews"
      );
    }
    for (let i = 0; i <= 5; i++) {
      $("[data-rating=" + i + "]").off("click");
    }
    hiring_review();
    frm.disable_save();
    $('[data-original-title="Menu"]').hide();
  },
});

function hiring_review() {
  if (frappe.boot.tag.tag_user_info.company_type == "Staffing") {
    frappe.msgprint("You don't have enough permissions.");
    frappe.set_route("app");
  }
}
