frappe.provide("frappe.data_import");
frappe.data_import.DataExporter = class DataExporter {
  constructor(doctype, exporting_for) {
    this.doctype = doctype;
    this.exporting_for = exporting_for;
    frappe.model.with_doctype(doctype, () => {
      this.make_dialog();
    });
  }

  make_dialog() {
    this.dialog = new frappe.ui.Dialog({
      title: __("Export Data"),
      fields: [
        {
          fieldtype: "Select",
          fieldname: "export_records",
          label: __("Export Type"),
          options: [
            {
              label: __("All Records"),
              value: "all",
            },
            {
              label: __("Filtered Records"),
              value: "by_filter",
            },
            {
              label: __("5 Records"),
              value: "5_records",
            },
            {
              label: __("Blank Template"),
              value: "blank_template",
            },
          ],
          default:
            this.exporting_for === "Insert New Records"
              ? "blank_template"
              : "all",
          change: () => {
            this.update_record_count_message();
          },
          hidden: 1,
        },
        {
          fieldtype: "HTML",
          fieldname: "filter_area",
          depends_on: (doc) => doc.export_records === "by_filter",
        },
        {
          fieldtype: "Select",
          fieldname: "file_type",
          label: __("File Type"),
          options: ["Excel", "CSV"],
          default: "CSV",
        },
        {
          fieldtype: "Section Break",
        },
        {
          fieldtype: "HTML",
          fieldname: "military_veteran",
          options: ["Contact", "Employee"].includes(this.doctype)
            ? ""
            : "** Please type only 0 and 1 are Military Veteran<br> ** For Gender,Options are: Male, Female,Decline to answer<br> ** For Status,Options Available are: Active,Inactive,Suspended,Left",
        },
        {
          fieldtype: "Section Break",
        },
        {
          fieldtype: "HTML",
          fieldname: "select_all_buttons",
        },
        {
          label: __(this.doctype),
          fieldname: this.doctype,
          fieldtype: "MultiCheck",
          columns: 2,
          hidden: 1,
          on_change: () => this.update_primary_action(),
          options: this.get_multicheck_options(this.doctype),
        },
        ...frappe.meta.get_table_fields(this.doctype).map((df) => {
          let doctype = df.options;
          let label = df.reqd
            ? // prettier-ignore
              __('{0} ({1}) (1 row mandatory)', [__(df.label || df.fieldname), __(doctype)])
            : __("{0} ({1})", [__(df.label || df.fieldname), __(doctype)]);
          console.log(label);
          return {
            // label,
            // fieldname: child_fieldname,
            fieldtype: "MultiCheck",
            columns: 2,
            on_change: () => this.update_primary_action(),
            // options: this.get_multicheck_options(doctype, child_fieldname)
          };
        }),
      ],
      primary_action_label: __("Export"),
      primary_action: (values) => this.export_records(values),
      on_page_show: () => this.select_mandatory(),
    });

    this.make_filter_area();
    this.update_record_count_message();

    this.dialog.show();

    if (["Contact", "Employee"].includes(this.doctype)) {
      this.hide_fields();
    }
  }

  hide_fields() {
    let a = this.dialog.$wrapper
      .find(".modal-content>.modal-body>div>.form-layout>.form-page")
      .children();
    a[1].style.display = "none";
    a[2].style.display = "none";
  }

  export_records() {
    this.select_all();
    let method =
      "/api/method/frappe.core.doctype.data_import.data_import.download_template";

    let multicheck_fields = this.dialog.fields
      .filter((df) => df.fieldtype === "MultiCheck")
      .map((df) => df.fieldname);

    let values = this.dialog.get_values();

    let doctype_field_map = {...values};
    for (let key in doctype_field_map) {
      if (!multicheck_fields.includes(key)) {
        delete doctype_field_map[key];
      }
    }

    let filters = null;
    if (values.export_records === "by_filter") {
      filters = this.get_filters(this.doctype);
    }

    open_url_post(method, {
      doctype: this.doctype,
      file_type: values.file_type,
      export_records: values.export_records,
      export_fields: doctype_field_map,
      export_filters: filters,
    });
  }

  make_filter_area() {
    this.filter_group = new frappe.ui.FilterGroup({
      parent: this.dialog.get_field("filter_area").$wrapper,
      doctype: this.doctype,
      on_change: () => {
        this.update_record_count_message();
      },
    });
  }

  make_select_all_buttons() {
    let for_insert = this.exporting_for === "Insert New Records";
    let section_title = for_insert
      ? __("Select Fields To Insert")
      : __("Select Fields To Update");
    let $select_all_buttons = $(`
			<div>
				<h6 class="form-section-heading uppercase">${section_title}</h6>
				<button class="btn btn-default btn-xs" data-action="select_all">
					${__("Select All")}
				</button>
				${
          for_insert
            ? `<button class="btn btn-default btn-xs" data-action="select_mandatory">
					${__("Select Mandatory")}
				</button>`
            : ""
        }
				<button class="btn btn-default btn-xs" data-action="unselect_all">
					${__("Unselect All")}
				</button>
			</div>
		`);
    frappe.utils.bind_actions_with_object($select_all_buttons, this);
    this.dialog
      .get_field("select_all_buttons")
      .$wrapper.html($select_all_buttons);
  }

  select_all() {
    this.dialog.$wrapper
      .find(":checkbox")
      .prop("checked", true)
      .trigger("change");
  }

  select_mandatory() {
    let mandatory_table_fields = frappe.meta
      .get_table_fields(this.doctype)
      .filter((df) => df.reqd)
      .map((df) => df.fieldname);
    mandatory_table_fields.push(this.doctype);

    let multicheck_fields = this.dialog.fields
      .filter((df) => df.fieldtype === "MultiCheck")
      .map((df) => df.fieldname)
      .filter((doctype) => mandatory_table_fields.includes(doctype));

    let checkboxes = [].concat(
      ...multicheck_fields.map((fieldname) => {
        let field = this.dialog.get_field(fieldname);
        return field.options
          .filter((option) => option.danger)
          .map((option) => option.$checkbox.find("input").get(0));
      })
    );

    this.unselect_all();
    $(checkboxes).prop("checked", true).trigger("change");
  }

  unselect_all() {
    let update_existing_records =
      this.dialog.get_value("exporting_for") == "Update Existing Records";
    this.dialog.$wrapper
      .find(
        `:checkbox${update_existing_records ? ":not([data-unit=name])" : ""}`
      )
      .prop("checked", false)
      .trigger("change");
  }

  update_record_count_message() {
    let export_records = this.dialog.get_value("export_records");
    let count_method = {
      all: () => frappe.db.count(this.doctype),
      by_filter: () =>
        frappe.db.count(this.doctype, {
          filters: this.get_filters(),
        }),
      blank_template: () => Promise.resolve(0),
      "5_records": () => Promise.resolve(5),
    };

    count_method[export_records]().then((value) => {
      let message = "";
      value = parseInt(value, 10);
      if (value === 0) {
        message = __("No records will be exported");
      } else if (value === 1) {
        message = __("1 record will be exported");
      } else {
        message = __("{0} records will be exported", [value]);
      }
      this.dialog.set_df_property("export_records", "description", message);

      this.update_primary_action(value);
    });
  }

  update_primary_action(no_of_records) {
    let $primary_action = this.dialog.get_primary_btn();
    if (no_of_records != null) {
      let label = "";
      if (no_of_records === 0) {
        label = __("Export");
      } else if (no_of_records === 1) {
        label = __("Export 1 record");
      } else {
        label = __("Export {0} records", [no_of_records]);
      }
      $primary_action.html(label);
    } else {
      let parent_fields = this.dialog.get_value(this.doctype);
      $primary_action.prop("disabled", parent_fields.length === 0);
    }
  }

  get_filters() {
    return this.filter_group.get_filters().map((filter) => {
      return filter.slice(0, 4);
    });
  }

  get_multicheck_options(doctype, child_fieldname = null) {
    if (!this.column_map) {
      this.column_map = get_columns_for_picker(
        this.doctype,
        this.exporting_for
      );
    }

    let autoname_field = null;
    let meta = frappe.get_meta(doctype);
    autoname_field = auto_name_vals(meta, autoname_field);

    let fields = child_fieldname
      ? this.column_map[child_fieldname]
      : this.column_map[doctype];

    let is_field_mandatory = (df) => {
      if (df.reqd && this.exporting_for == "Insert New Records") {
        return true;
      }
      if (autoname_field && df.fieldname == autoname_field.fieldname) {
        return true;
      }
      return df.fieldname === "name";
    };

    return fields
      .filter((df) => {
        console.log(df);
        return true;
      })
      .map((df) => {
        return {
          label: __(df.label),
          value: df.fieldname,
          danger: is_field_mandatory(df),
          checked: false,
          description: `${df.fieldname} ${df.reqd ? __("(Mandatory)") : ""}`,
        };
      });
  }
};

export function get_columns_for_picker(doctype, exporting_for) {
  let out = {};

  const exportable_fields = (df) => {
    let keep = true;
    if (frappe.model.no_value_type.includes(df.fieldtype)) {
      keep = false;
    }
    if (["lft", "rgt"].includes(df.fieldname)) {
      keep = false;
    }
    return keep;
  };

  // parent
  let doctype_fields = frappe.meta
    .get_docfields(doctype)
    .filter(exportable_fields);
  if (doctype == "Contact") {
    console.log("sliced", doctype_fields.slice(31, 35));
    out[doctype] = [
      {
        label: __("ID"),
        fieldname: "name",
        fieldtype: "Data",
        reqd: 1,
      },
      {
        label: __("Contact Name"),
        fieldname: doctype_fields[0].fieldname,
        fieldtype: "Data",
        reqd: 1,
      },
      {
        label: __("phone number"),
        fieldname: doctype_fields[5].fieldname,
        fieldtype: "Int",
        reqd: 1,
      },
      {
        label: __("Email Address"),
        fieldname: doctype_fields[11].fieldname,
        fieldtype: "Data",
        reqd: 1,
      },
      {
        label: __("Company"),
        fieldname: doctype_fields[18].fieldname,
        fieldtype: "Data",
        reqd: 1,
      },
    ].concat(doctype_fields.slice(31, 36));
  } else if (doctype == "Employee") {
    if (exporting_for == "Update Existing Records") {
      out[doctype] = [
        {
          label: __("ID"),
          fieldname: "name",
          fieldtype: "Data",
          reqd: 1,
        },
        {
          label: __("First Name"),
          fieldname: "first_name",
          fieldtype: "Data",
          reqd: 1,
        },
        {
          label: __("Last Name"),
          fieldname: "last_name",
          fieldtype: "Data",
          reqd: 1,
        },
        {
          label: __("Email"),
          fieldname: "email",
          fieldtype: "Data",
          reqd: 1,
        },
        {
          label: __("Company"),
          fieldname: "company",
          fieldtype: "Link",
          reqd: 1,
        },
        {
          label: __("Status"),
          fieldname: "status",
          fieldtype: "Select",
          reqd: 1,
        },
        {
          label: __("Date of Birth"),
          fieldname: "date_of_birth",
          fieldtype: "Date",
          reqd: 1,
        },
        {
          label: __("Contact Number"),
          fieldname: "contact_number",
          fieldtype: "Data",
          reqd: 0,
        },
        {
          label: __("Gender"),
          fieldname: "employee_gender",
          fieldtype: "Select",
          reqd: 0,
        },
        {
          label: __("SSN"),
          fieldname: "sssn",
          fieldtype: "Data",
          reqd: 0,
        },
        {
          label: __("Military Veteran"),
          fieldname: "military_veteran",
          fieldtype: "Check",
          reqd: 0,
        },
        {
          label: __("Street Address"),
          fieldname: "street_address",
          fieldtype: "Data",
          reqd: 0,
        },
        {
          label: __("Suite or Apartment No"),
          fieldname: "suite_or_apartment_no",
          fieldtype: "Data",
          reqd: 0,
        },
        {
          label: __("City"),
          fieldname: "city",
          fieldtype: "Data",
          reqd: 0,
        },
        {
          label: __("State"),
          fieldname: "state",
          fieldtype: "Data",
          reqd: 0,
        },
        {
          label: __("Zip"),
          fieldname: "zip",
          fieldtype: "Data",
          reqd: 0,
        },
      ];
    } else {
      out[doctype] = [
        {
          label: __("First Name"),
          fieldname: "first_name",
          fieldtype: "Data",
          reqd: 1,
        },
        {
          label: __("Last Name"),
          fieldname: "last_name",
          fieldtype: "Data",
          reqd: 1,
        },
        {
          label: __("Email"),
          fieldname: "email",
          fieldtype: "Data",
          reqd: 1,
        },
        {
          label: __("Company"),
          fieldname: "company",
          fieldtype: "Link",
          reqd: 1,
        },
        {
          label: __("Status"),
          fieldname: "status",
          fieldtype: "Select",
          reqd: 1,
        },
        {
          label: __("Date of Birth"),
          fieldname: "date_of_birth",
          fieldtype: "Date",
          reqd: 1,
        },
        {
          label: __("Contact Number"),
          fieldname: "contact_number",
          fieldtype: "Data",
          reqd: 0,
        },
        {
          label: __("Gender"),
          fieldname: "employee_gender",
          fieldtype: "Select",
          reqd: 0,
        },
        {
          label: __("SSN"),
          fieldname: "sssn",
          fieldtype: "Data",
          reqd: 0,
        },
        {
          label: __("Military Veteran"),
          fieldname: "military_veteran",
          fieldtype: "Check",
          reqd: 0,
        },
        {
          label: __("Street Address"),
          fieldname: "street_address",
          fieldtype: "Data",
          reqd: 0,
        },
        {
          label: __("Suite or Apartment No"),
          fieldname: "suite_or_apartment_no",
          fieldtype: "Data",
          reqd: 0,
        },
        {
          label: __("City"),
          fieldname: "city",
          fieldtype: "Data",
          reqd: 0,
        },
        {
          label: __("State"),
          fieldname: "state",
          fieldtype: "Data",
          reqd: 0,
        },
        {
          label: __("Zip"),
          fieldname: "zip",
          fieldtype: "Data",
          reqd: 0,
        },
      ];
    }
  } else {
    out[doctype] = [
      {
        label: __("ID"),
        fieldname: "name",
        fieldtype: "Data",
        reqd: 1,
      },
    ].concat(doctype_fields);
  }
  // children
  const table_fields = frappe.meta.get_table_fields(doctype);
  table_fields.forEach((df) => {
    const cdt = df.options;
    const child_table_fields = frappe.meta
      .get_docfields(cdt)
      .filter(exportable_fields);

    out[df.fieldname] = [
      {
        label: __("ID"),
        fieldname: "name",
        fieldtype: "Data",
        reqd: 1,
      },
    ].concat(child_table_fields);
  });

  return out;
}
function auto_name_vals(meta, autoname_field) {
  if (meta.autoname?.startsWith("field:")) {
    let fieldname = meta.autoname.slice("field:".length);
    autoname_field = frappe.meta.get_field(doctype, fieldname);
  }
  return autoname_field;
}
