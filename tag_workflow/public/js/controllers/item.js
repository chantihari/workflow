frappe.ui.form.on("Item", {
  onload: function (frm) {
    frm.fields_dict["job_site_table"].grid.get_field("job_site").get_query =
      function (doc, cdt, cdn) {
        let jobsites = frm.doc.job_site_table,
          site_list = [];
        for (let t in jobsites) {
          if (jobsites[t]["job_site"]) {
            site_list.push(jobsites[t]["job_site"]);
          }
        }
        return {
          query:
            "tag_workflow.tag_workflow.doctype.job_site.job_site.get_sites_based_on_company",
          filters: {
            company: frm.doc.company,
            site_list: site_list,
          },
        };
      };
  },
  refresh: function (frm, cdt, cdn) {
    if (frm.doc.__islocal == 1) {
      Array.from($('[data-fieldtype="Currency"]')).forEach((_field) => {
        _field.id = "id_mvr_hour";
      });

      $(
        "div.row:nth-child(16) > div:nth-child(2) > div:nth-child(2) > form:nth-child(1) > div:nth-child(8) > div:nth-child(1) > div:nth-child(2) > div:nth-child(1)"
      ).attr("id", "id_mvr_hour");
      let len_history = frappe.route_history.length;
      if (
        frappe.route_history.length > 1 &&
        frappe.route_history[len_history - 2][1] == "Company"
      ) {
        frm.set_value("company", frappe.route_history[len_history - 2][2]);
        frm.set_df_property("company", "read_only", 1);
      } else if (
        frappe.route_history.length > 1 &&
        frappe.route_history[len_history - 2][1] == "Contract"
      ) {
        frm.set_df_property("company", "read_only", 1);
      }
      $('[data-fieldname="rate"]').attr("id", "title_rate");
      if (
        frappe.boot.tag.tag_user_info.company_type == "TAG" ||
        frappe.session.user == "Administrator"
      ) {
        frm.set_value("company", "");
      }
    }else{
      set_job_title_name(frm);
      Array.from($('[data-fieldtype="Currency"]')).forEach((_field) => {
        _field.id = "id_rate";
      });
      check_job_title_value();
    }
    set_descriptions_to_description(frappe, frm);
    readonly_fields(frm);
    cur_frm.clear_custom_buttons();
    hide_fields();
    read_only_company_field(frm);
    $('[data-fieldname="company"]').css("display", "block");
    $('[class="btn btn-primary btn-sm primary-action"]').show();
    $(".custom-actions.hidden-xs.hidden-md").show();
    set_job_site_disable_enable(cdt, cdn);
    if (
      frappe.boot.tag.tag_user_info.company_type != "TAG" &&
      frappe.session.user != "Administrator"
    ) {
      frm.set_df_property("company", "reqd", 1);
    }
    readonly_fields(frm);
    frm.fields_dict["pay_rate"].grid.wrapper
      .find(".grid-add-row")
      .click(function () {
        set_pay_rate(frm, cdt, cdn);
        set_staffing_data(frm);
        frm.refresh_field("pay_rate");
        set_job_site_disable_enable(cdt, cdn);
      });
    frm.fields_dict["pay_rate"].grid.wrapper
      .find(".grid-remove-rows")
      .unbind("click")
      .click(function () {
        delete_pay_rate_row(frm);
      });
    if (cur_frm.doc.company) {
      check_user_type(cur_frm);
    }
    make_description_editable(frm);
  },
  before_save: function (frm, cdt, cdn) {
    if ($(".help-box")[4].innerHTML.length > 0) {
      $(".control-value")[1].innerHTML = frm.doc.job_titless.split("-")[0];
      frappe.throw("Job Title already exists.");
    }
    set_fields(frm);
    frappe.call({
      method: "tag_workflow.controllers.master_controller.check_item_group",
    });
    let items = locals[cdt][cdn];
    $.each(frm.doc.pay_rate || [], function (i, v) {
      if (!v.staffing_company || v.staffing_company.length === 0 || v.staffing_company === "TAG") {
          v.job_pay_rate = 0.0;
          v.hiring_company = "";
          v.site = "";
          v.staffing_company = "";
      } else if (!v.hiring_company || v.hiring_company.length === 0) {
        if (!v.job_pay_rate) {
          v.job_pay_rate = items.rate;
        }
      }
  });
  
    frm.refresh_field("pay_rate");
  },
  validate: function (frm) {
    if (frm.doc.__islocal && frm.doc.job_titless) {
      if (frm.doc.job_titless.indexOf("-") > 0) {
        frm.set_value("job_titless", frm.doc.job_titless.split("-")[0]);
      } else {
        frm.set_value("job_titless", frm.doc.job_titless);
      }
      cur_frm.refresh_field("job_titless");
    }
    frm.set_value("item_code", frm.doc.job_titless);
    validate_form(frm);
  },
  company: function (frm) {
    if (frm.doc.company) {
      frappe.session["compamny_name"] = frm.doc.company;
      let datas = set_get_value_data(frm);
      frappe.db.get_value(
        "Item",
        { name: frm.doc.name, data: datas },
        "company",
        (r) => {
          if (r != frm.doc.company) {
            frm.doc.job_site_table = [];
            frm.refresh_field("job_site_table");
          }
          if (r.length != 0) {
            $(".help-box")[4].innerHTML =
              r.name.split("-")[0] + " already exists. Select another name";
          } else {
            $(".help-box")[4].innerHTML = "";
          }
        }
      );
      check_user_type(frm);
      set_staffing_data(frm);
    }
    if (frm.doc.__islocal && !cur_frm.doc.company) {
      $(".form-section:contains('Pay Rate')").hide();
      $(".form-section:contains('Job Sites')").hide();
    }
    if (!frm.doc.company) {
      frm.set_value("company", "");
      $('[data-fieldname = "company"]').attr("title", "");
      $('[data-fieldname = "company"]>input').attr("title", "");
    }
  },
  job_titless: function (frm) {
    frappe.session["industry"] = frm.doc.industry;
    if(frm.doc.job_titless){
      frm.set_value("job_titless", frm.doc.job_titless.replace(/-/g, ""));
    }
  },
  job_titless_name: function(frm){
    if(frm.doc.job_titless_name){
      frm.set_value("job_titless_name", frm.doc.job_titless_name.replace(/-/g, ""));
    }
  },
  after_save: function (frm) {
    if (frm.doc.name != frm.doc.job_titless) {
      frappe.call({
        method: "frappe.rename_doc",
        args: {
          doctype: frm.doctype,
          old: frm.docname,
          new: cur_frm.doc.job_titless,
          merge: 0,
        },
        callback: function (r) {
          if (!r.exc) {
            $(document).trigger("rename", [
              frm.doctype,
              frm.docname,
              r.message || cur_frm.doc.job_titless,
            ]);
            if (locals[frm.doctype]?.[frm.docname])
              delete locals[frm.doctype][frm.docname];
          }
        },
      });
      frappe.call({
        method: "tag_workflow.tag_data.new_activity",
        args: {
          activity: frm.doc.job_titless,
        },
      });
    }
    if (frm.doc.company) {
      frappe.call({
        method: "tag_workflow.tag_data.new_job_title_company",
        args: {
          job_name: frm.doc.name,
          company: frm.doc.company,
          industry: frm.doc.industry,
          rate: frm.doc.rate,
          description: frm.doc.descriptions,
        },
      });
    }
  },
  pay_rate_on_form_rendered: function (frm, cdt, cdn) {
    frm.fields_dict["pay_rate"].grid.wrapper
      .find(".grid-delete-row")
      .click(function () {
        check_and_delete_pay_rates(frm, frm);
      });
  },
  setup: function (frm) {
    frm.set_query("staffing_company", "pay_rate", function () {
      return {
        filters: [["Company", "organization_type", "in", ["Staffing"]]],
      };
    });
    set_hiring_company(frm);
  },
  industry: function(frm){
    if(frm.doc.industry && frm.doc.job_titless){
      frm.set_value("job_titless", "");
      frm.set_df_property("job_titles", "description", "");
    }
  }
});

function set_job_title_name(frm) {
  $("[data-fieldname='job_titless_name']>div>.control-input-wrapper>.like-disabled-input").html(frm.doc.name.split("-")[0]);
  $("#navbar-breadcrumbs > li.disabled > a").html(frm.doc.name.split("-")[0]);
  $(".admin-title[title='"+frm.doc.name+"']").html(frm.doc.name.split("-")[0]);
}

function set_get_value_data(frm) {
  return {
    filedname: frm.doc.job_titless ? frm.doc.job_titless : "None",
    Company_name: frm.doc.company ? frm.doc.company : "None",
    industry: frm.doc.industry ? frm.doc.industry : "None",
  };
}

function check_job_title_value() {
  $("#awesomplete_list_5").click(function (e) {
    if (e.target.outerText) {
      frappe.session["industry"] = e.target.outerText;
      get_company_and_industry_name();
    }
  });
  $("#awesomplete_list_3").click(function (e) {
    if (e.target.outerText) {
      frappe.session["industry"] = e.target.outerText;
      if ($('[data-fieldname="job_titless"]')[0].fieldobj.value != undefined) {
        frappe.call({
          method: "frappe.client.get_value",
          type: "GET",
          args: {
            doctype: "Item",
            fieldname: "name",
            filters: $('[data-fieldname="job_titless"]')[0].fieldobj.value,
            industry: frappe.session["industry"],
            company_name: frappe.session["compamny_name"],
          },
          callback: function (r) {
            if (r.message.length != 0) {
              $(".help-box")[4].innerHTML =
                $('[data-fieldname="job_titless"]')[0].fieldobj.value.split(
                  "-"
                )[0] + " already exists. Select another name";
            } else {
              $(".help-box")[4].innerHTML = "";
            }
          },
        });
      }
    }
  });
  $("#awesomplete_list_7").click(function (e) {
    if (e.target.innerText) {
      frappe.session["compamny_name"] = e.target.innerText;
      get_company_and_industry_name();
    }
  });
}

function get_company_and_industry_name() {
  if ($('[data-fieldname="job_titless"]')[2].fieldobj.value) {
    frappe.call({
      method: "frappe.client.get_value",
      type: "GET",
      args: {
        doctype: "Item",
        fieldname: "name",
        filters: $('[data-fieldname="job_titless"]')[2].fieldobj.value,
        industry: frappe.session["industry"],
        company_name: frappe.session["compamny_name"],
      },
      callback: function (r) {
        if (r.message.length != 0) {
          $(".help-box")[6].innerHTML =
            r.message["name"] + " already exists. Select another name";
        } else {
          $(".help-box")[6].innerHTML = "";
        }
      },
    });
  }
}

function set_pay_rate(frm, cdt, cdn) {
  let items = locals[cdt][cdn];
  $.each(frm.doc.pay_rate || [], function (i, v) {
    if (v.staffing_company.length !== 0 && (!v.hiring_company || v.hiring_company.length === 0)) {
      if (!v.job_pay_rate) {
        v.job_pay_rate = items.rate;
      }
    }
  });
  frm.refresh_field("pay_rate");
}

let hiring_company_data_list = "";

function set_index(datass, data_idx, list_data) {
  if (data_idx != 0) {
    datass.innerHTML = list_data;
    datass["options"]["selectedIndex"] = data_idx;
  }
}

function set_hiring_company_options(e, data_idx, list_data) {
  for (let hco of $("[data-fieldname=" + "hiring_company" + "]")) {
    if (hco["options"]) {
      hiring_company_data_list.forEach((value, idx) => {
        if (value == e.target.textContent) {
          data_idx = idx;
        }
        list_data.push(`<option value='${value}'>${value}</option>`);
      });
      set_index(hco, data_idx, list_data);
    }
  }
}

function set_data_idex(e, value, data_idx, idx) {
  if (value == e.target.textContent.trim()) {
    e.target.title = e.target.textContent.trim();
    data_idx = idx;
  }
  if (e.target.title == value) {
    data_idx = idx;
  }
  if (e.target.offsetParent.title == value) {
    data_idx = idx;
  }
  if (e.currentTarget.lastChild.innerHTML == value) {
    data_idx = idx;
  }
  return data_idx;
}

function hiring_company_set_innerText(e, data_idx, list_data) {
  for (let hco of $("[data-fieldname=" + "hiring_company" + "]")) {
    if (hco["options"]) {
      hiring_company_data_list.forEach((value, idx) => {
        data_idx = set_data_idex(e, value, data_idx, idx);
        list_data.push(`<option value='${value}'>${value}</option>`);
      });
      if (data_idx > 0) {
        set_index(hco, data_idx, list_data);
      } else {
        hco.innerHTML = list_data;
      }
    }
  }
}

function set_hiring_company_data_idx(e, value, data_idx, idx) {
  if (value == e.target.previousSibling.textContent.trim()) {
    e.target.title = e.target.previousSibling.textContent.trim();
    data_idx = idx;
  }
  if (e.target.title == value) {
    data_idx = idx;
  }
  if (e.delegateTarget.previousSibling.lastChild.textContent == value) {
    data_idx = idx;
  }
  return data_idx;
}

function job_site_set_hiring_company_innerText(e, data_idx, list_data) {
  for (let datass of $("[data-fieldname=" + "hiring_company" + "]")) {
    if (datass["options"]) {
      hiring_company_data_list.forEach((value, idx) => {
        if (e.target.previousSibling) {
          data_idx = set_hiring_company_data_idx(e, value, data_idx, idx);
          list_data.push(`<option value='${value}'>${value}</option>`);
        }
      });
      set_index(datass, data_idx, list_data);
    }
  }
}

function hiring_company_set_options(e, datass, data_idx, list_data) {
  if (datass["options"]) {
    hiring_company_data_list.forEach((value, idx) => {
      if (e.delegateTarget.previousSibling) {
        if (value == e.delegateTarget.previousSibling.textContent.trim()) {
          e.target.title = e.delegateTarget.previousSibling.textContent.trim();
          data_idx = idx;
        }
        if (e.target.title == value) {
          data_idx = idx;
        }

        list_data.push(`<option value='${value}'>${value}</option>`);
      }
    });
    set_index(datass, data_idx, list_data);
  }
}
function job_site_set_hiring_company_options(e, data_idx, list_data) {
  for (let datass of $("[data-fieldname=" + "hiring_company" + "]")) {
    hiring_company_set_options(e, datass, data_idx, list_data);
  }
}
function job_site_set_hiring_company_data(e, data_idx, list_data) {
  if (!e.target.innerText) {
    job_site_set_hiring_company_innerText(e, data_idx, list_data);
  } else {
    job_site_set_hiring_company_options(e, data_idx, list_data);
  }
}

frappe.ui.form.on("Job Sites", {
  job_site_table_add: function (frm, cdt, cdn) {
    let child = locals[cdt][cdn];
    child.bill_rate = frm.doc.rate;
    frm.refresh_field("job_site_table");
  },
  comp_code: function (frm, cdt, cdn) {
    let child1 = locals[cdt][cdn];
    if (child1["comp_code"].length > 10) {
      frappe.msgprint({
        message: __("Maximum Characters allowed for Class Code are 10."),
        title: __("Error"),
        indicator: "orange",
      });
      frappe.model.set_value(cdt, cdn, "comp_code", "");
      frappe.validated = false;
    }
  }
});

function set_descriptions_to_description(frappe, frm) {
  if (
    frappe.boot.tag.tag_user_info.company_type == "Hiring" ||
    frappe.boot.tag.tag_user_info.company_type == "Exclusive Hiring"
  ) {
    frm.set_df_property("descriptions", "label", "Description");
  }
}

function set_staffing_company_data(v) {
  if((frappe.boot.tag.tag_user_info.company_type=="TAG" && v.staffing_company=="TAG") || (frappe.boot.tag.tag_user_info.company_type !== "TAG" && v.staffing_company)){
    v.staffing_company = "";
  }
}

function set_staffing_data(cur_frm) {
  if (frappe.boot.tag.tag_user_info.company_type === "Staffing" && cur_frm.doc.company) {
    $.each(cur_frm.doc.pay_rate || [], function (i, v) {
      v.staffing_company = cur_frm.doc.company;
      cur_frm.refresh_field("pay_rate");
    });
  } else {
    $.each(cur_frm.doc.pay_rate || [], function (i, v) {
      set_staffing_company_data(v);
    });
  }
}

function check_user_type(cur_frm) {
  frappe.call({
    method: "tag_workflow.utils.doctype_method.check_company_type",
    args: { company: cur_frm.doc.company },
    callback: function (r) {
      if (
        r.message[0]["organization_type"] === "Hiring" ||
        r.message[0]["organization_type"] == "Exclusive Hiring"
      ) {
        $(".form-section:contains('Job Sites')").show();
        $(".form-section:contains('Pay Rate')").hide();
      } else if (r.message[0]["organization_type"] === "Staffing") {
        $(".form-section:contains('Job Sites')").hide();
        $(".form-section:contains('Pay Rate')").show();
      }
    },
  });
}

function set_job_site_disable_enable(cdt, cdn) {
  $("[data-fieldname=" + "hiring_company" + "]").on("click", function (e) {
    let list_data = [];
    let data_idx = 0;
    let hiring_company_data = e.target.value;
    if (!e.target.innerText) {
      hiring_company_set_innerText(e, data_idx, list_data);
    }
    if (!e.target.innerHTML && e.target.options.length == 0) {
      hiring_company_data_list.forEach((value, idx) => {
        list_data.push(`<option value='${value}'>${value}</option>`);
      });
      e.target.innerHTML = list_data;
    }
    set_hiring_company_options(e, data_idx, list_data);
    if (!hiring_company_data || hiring_company_data.length == 1) {
      $("[data-fieldname=" + "job_site" + "]").prop("disabled", true);
    } else if (hiring_company_data.length != 0) {
      $("[data-fieldname=" + "job_site" + "]").prop("disabled", false);
    }
  });

  $("[data-fieldname=" + "job_site" + "]").on("click", function (e) {
    let items = locals[cdt][cdn];
    let list_data = [];
    let data_idx = 0;
    job_site_set_hiring_company_data(e, data_idx, list_data);
    for (const data of items.pay_rate) {
      if (
        data["hiring_company"] == undefined ||
        data["hiring_company"].length == 0 ||
        data["job_order"]
      ) {
        $(
          "[data-name=" +
            data["name"] +
            "]  [data-fieldname=" +
            "job_site" +
            "]"
        ).prop("disabled", true);
      } else if (data["hiring_company"].length != 0) {
        $(
          "[data-name=" +
            data["name"] +
            "]  [data-fieldname=" +
            "job_site" +
            "]"
        ).prop("disabled", false);
      }
    }
  });
}

function check_and_delete_pay_rates(data, frm) {
  frappe.call({
    method: "tag_workflow.utils.doctype_method.check_payrates_data",
    args: {
      name: data.fields_dict
        ? data.fields_dict["pay_rate"].grid.open_grid_row.row.doc.name
        : data,
    },
    callback: function (response) {
      if (response.message) {
        frappe.msgprint({
          title: __("Error"),
          indicator: "red",
          message: __("Already linked with job order"),
        });
        frm.reload_doc();
      }
    },
  });
}

function delete_pay_rate_row(frm) {
  for (let data of frm.doc.pay_rate) {
    if (data["__checked"]) {
      check_and_delete_pay_rates(data["name"], frm);
    }
  }
}

function set_hiring_company(frm) {
  frappe.call({
    method: "tag_workflow.utils.doctype_method.get_hiring_company_data",
    callback: function (response) {
      hiring_company_data_list = response.message;
      frappe.meta.get_docfield(
        "Pay Rates",
        "hiring_company",
        cur_frm.doc.name
      ).options = response.message;
      frm.refresh_field("pay_rate");
    },
  });
}

/*-------hide fields------------*/
function hide_fields() {
  let fields = [
    "gst_hsn_code",
    "is_nil_exempt",
    "is_non_gst",
    "is_item_from_hub",
    "allow_alternative_item",
    "is_stock_item",
    "include_item_in_manufacturing",
    "opening_stock",
    "valuation_rate",
    "standard_rate",
    "is_fixed_asset",
    "auto_create_assets",
    "asset_category",
    "asset_naming_series",
    "over_delivery_receipt_allowance",
    "over_billing_allowance",
    "image",
    "brand",
    "sb_barcodes",
    "inventory_section",
    "reorder_section",
    "unit_of_measure_conversion",
    "serial_nos_and_batches",
    "variants_section",
    "defaults",
    "purchase_details",
    "supplier_details",
    "foreign_trade_details",
    "sales_details",
    "deferred_revenue",
    "deferred_expense_section",
    "customer_details",
    "item_tax_section_break",
    "inspection_criteria",
    "manufacturing",
    "hub_publishing_sb",
    "more_information_section",
    "stock_uom",
    "item_group",
    "item_code",
    "disabled",
    "item_name",
    "description",
  ];
  for (let field in fields) {
    cur_frm.toggle_display(fields[field], 0);
  }
}

function validate_form(frm) {
  let error_fields = [],
    mandatory_fields = [];
  if (
    frappe.boot.tag.tag_user_info.company_type != "TAG" &&
    frappe.session.user != "Administrator"
  ) {
    mandatory_fields = [
      "industry",
      "job_titless",
      "rate",
      "company",
      "descriptions",
    ];
  } else {
    mandatory_fields = ["industry", "job_titless", "rate", "descriptions"];
  }
  let message = __("<b>Please Fill Mandatory Fields to create a {0}:</b>", [
    __(frm.doc.doctype),
  ]);
  mandatory_fields.forEach((field) => {
    if (!frm.doc[field]) {
      if (field == "job_titless") {
        error_fields.push("Job Title");
      } else {
        error_fields.push(frappe.unscrub(field));
      }
    }
  });
  if (error_fields?.length) {
    message =
      message + "<br><br><ul><li>" + error_fields.join("</li><li>") + "</ul>";
    frappe.msgprint({
      message: message,
      indicator: "orange",
      title: __("Missing Fields"),
    });
    frappe.validated = false;
  }
}

function readonly_fields(frm) {
  if (
    frm.doc.__islocal != 1 &&
    frappe.boot.tag.tag_user_info.company_type == "TAG"
  ) {
    $('[data-fieldname="rate"]').attr("id", "title_rate");
  }
  if (
    frm.doc.__islocal != 1 &&
    !(
      frappe.boot.tag.tag_user_info.company_type == "TAG" ||
      frappe.session.user == "Administrator"
    )
  ) {
    let fields = [
      "industry",
      "rate",
      "company",
      "job_titless",
      "descriptions",
      "job_titless_name",
    ];
    for (let i in fields) {
      frm.set_df_property(fields[i], "read_only", 1);
    }
  }
}


function read_only_company_field(frm) {
  if (
    frm.doc.__islocal != 1 &&
    (frappe.boot.tag.tag_user_info.company_type == "TAG" ||
      frappe.session.user == "Administrator")
  ) {
    if (frm.doc.company) {
      frm.set_df_property("industry", "read_only", 1);
      frm.set_df_property("company", "read_only", 1);
    }
  }
}
function make_description_editable(frm) {
  setTimeout(() => {
    if (
      frappe.boot.tag.tag_user_info.user_type == "Hiring Admin" ||
      frappe.boot.tag.tag_user_info.user_type == "Staffing Admin"
    ) {
      if (frm.doc.company && frm.doc.company != null) {
        frm.set_df_property("descriptions", "read_only", 0);
      }
    } else if (frappe.boot.tag.tag_user_info.company_type == "TAG") {
      frm.set_df_property("descriptions", "read_only", 0);
    }
  }, 100);
}

function set_fields(frm){
  if(frm.doc.__islocal){
    frm.set_value("job_titless_name", frm.doc.job_titless);
    frm.set_value("item_code", frm.doc.job_titless);
    frm.set_value("item_group", "All Item Groups");
    frm.set_value("stock_uom", "Nos");
    frm.set_value("is_company", +(frm.doc.company.length!=0));
  }
}