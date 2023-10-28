$(document).on("startup", function () {
  let url = window.location.href;
  let url_splits = url.split("home", 2);
  if (url_splits.length == 2) {
    if (url_splits[1] != "/" && url_splits[1] != "" && url_splits[1] != "#") {
      frappe.throw("Page " + decodeURI(url_splits[1]) + " not found");
    }
  }
  let url_splits2 = url.split("app");
  if (
    url_splits2.length == 1 ||
    (url_splits2.length == 2 &&
      ["", "crm", "accounting"].includes(url_splits2[1].replace(/\//g, "")))
  ) {
    if (
      ["Hiring", "Exclusive Hiring"].includes(
        frappe.boot.tag.tag_user_info.company_type
      )
    ) {
      window.location.replace("/app/hiring-home");
    } else if (frappe.boot.tag.tag_user_info.company_type == "Staffing") {
      window.location.replace("/app/staff-home");
    } else if (frappe.boot.tag.tag_user_info.company_type == "TAG") {
      window.location.replace("/app/tagadmin-page");
    } else {
      window.location.replace("/app/home");
    }
  }
});

$(window).on("popstate", ()=>{
	$('.datepicker.active').removeClass('active');
	$('[role = "tooltip"]').popover("dispose");
});

$(document).on("wheel", "input[type=number]", function (e) {
  $(this).blur();
});

$(window).on("popstate", ()=>{
	$('.datepicker.active').removeClass('active');
	$('[role = "tooltip"]').popover("dispose");
});