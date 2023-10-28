// Copyright (c) 2021, SourceFuse and contributors
// For license information, please see license.txt

frappe.ui.form.on("Company Review", {
  refresh: function (frm) {
    if (
      frappe.session.user == "Administrator" ||
      frappe.boot.tag.tag_user_info.company_type == "TAG"
    ) {
      $("#navbar-breadcrumbs > li:nth-child(1) > a").html(
        "Staffing Ratings & Reviews"
      );
    }
    staffing_review();
    $(".form-footer").hide();
    for (let i = 0; i <= 5; i++) {
      $("[data-rating=" + i + "]").off("click");
    }
    frm.disable_save();
  },
});

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
