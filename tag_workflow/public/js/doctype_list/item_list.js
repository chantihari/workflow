frappe.listview_settings["Item"] = {
  hide_name_column: true,
  onload: function (listview) {
    $('[data-fieldname="is_company"]').hide();
    $('[data-fieldname="name"]').attr("placeholder", "Job Title");
    frappe.route_options = {
      company: "",
    };
    const df = {
      condition: "=",
      default: null,
      fieldname: "rate",
      fieldtype: "Autocomplete",
      input_class: "input-xs",
      label: "Rate",
      is_filter: 1,
      onchange: function () {
        listview.refresh();
      },
      placeholder: "Rate",
    };
    listview.page.add_field(df, ".standard-filter-section");
  },
  refresh: function () {
    $('[data-fieldname="is_company"]').hide();
    if(frappe.boot.tag.tag_user_info.company_type == "Hiring" || frappe.boot.tag.tag_user_info.company_type == "Exclusive Hiring"){
      $(".list-row-col>span:contains('Status')").hide()
      $("[title='Document is in draft state']").hide()
      $(".list-row-col>span:contains('Rate')")[0].innerHTML = "Bill Rate"
      $(".list-row-col>span:contains('Descriptions')")[0].innerHTML = "Description"
    }
    $('div[data-fieldname="name"]').hide();
    let btn = document.getElementById("filter_selected_data");
    btn.addEventListener("click", function () {
      btn.style.backgroundColor = "#21B9E4";
      btn.style.color = "#fff";
      let btn3 = document.getElementById("filter_all_data");
      btn3.style.backgroundColor = "White";
      btn3.style.color = "black";
    });
    let btn1 = document.getElementById("filter_all_data");
    btn1.addEventListener("click", function () {
      btn1.style.backgroundColor = "#21B9E4";
      btn1.style.color = "#fff";
      let btn2 = document.getElementById("filter_selected_data");
      btn2.style.backgroundColor = "White";
      btn2.style.color = "black";
    });
  },
};
