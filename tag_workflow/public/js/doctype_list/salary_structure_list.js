frappe.listview_settings["Salary Structure"] = {
    filters: [["company", "=", frappe.boot.tag.tag_user_info.company]],
    formatters:{
        name(val , _d, f){
            let name = val.split("_")
            return `
            <span class="level-item select-like">
				<input class="list-row-checkbox" type="checkbox" data-name="${f.name}">
				<span class="list-row-like hidden-xs style=" margin-bottom:="" 1px;"="">
					<span class="like-action not-liked" data-name="${f.name}" data-doctype="Salary Structure" data-liked-by="null" title="">
			<svg class="icon  icon-sm" style="">
			<use class="like-icon" href="#icon-heart"></use>
		    </svg>
		    </span>
		    <span class="likes-count">
			
		    </span>
			</span>
            <span class="level-item bold ellipsis ml-2" title="${f.name}">
				<a class="ellipsis" href="/app/salary-structure/${val}" title="${val}" data-doctype="Salary Structure" data-name="${val}">
                    ${name[0]}
                </a>
            </span>`
           }
    },
    refresh:()=>{
        check_payroll_perm()
    }
}
