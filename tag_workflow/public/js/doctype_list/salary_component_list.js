frappe.listview_settings["Salary Component"] = {
  filters: [["company", "=", frappe.boot.tag.tag_user_info.company]],
  onload: function () {

      [cur_list.columns[2], cur_list.columns[3]] = [
        cur_list.columns[3],
        cur_list.columns[2],
      ];
      [cur_list.columns[3], cur_list.columns[5]] = [
        cur_list.columns[5],
        cur_list.columns[3],
      ];

      cur_list.render_header(cur_list);
    },
    formatters:{
      salary_component_abbr(val , _d, f){
        let abbr = val.split("_")
        return `<div class="list-row-col ellipsis   text-left "><span class="filterable ellipsis " title="" id="${val}-${f.name}" >${abbr[0]}</span></div>`;
      },
      name(val , _d, f){
          let name = val.split("_")
          return `
          <span class="level-item select-like">
      <input class="list-row-checkbox" type="checkbox" data-name="${f.name}">
      <span class="list-row-like hidden-xs style=" margin-bottom:="" 1px;"="">
        <span class="like-action not-liked" data-name="${f.name}" data-doctype="Salary Component" data-liked-by="null" title="">
    <svg class="icon  icon-sm" style="">
    <use class="like-icon" href="#icon-heart"></use>
      </svg>
      </span>
      <span class="likes-count">
    
      </span>
    </span>
          <span class="level-item bold ellipsis ml-2" title="${f.name}">
      <a class="ellipsis" href="/app/salary-component/${val}" title="${val}" data-doctype="Salary Component" data-name="${val}">
                  ${name[0]}
              </a>
          </span>`
         }
    },
    refresh:()=>{
      check_payroll_perm()
    }
}