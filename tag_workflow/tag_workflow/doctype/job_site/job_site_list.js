frappe.listview_settings["Job Site"] = {
  onload: function () {
    $('h3[title = "Job Site"]').html("Job Sites");
    if (frappe.session.user != "Administrator") {
      $(".custom-actions.hidden-xs.hidden-md").hide();
      $('[data-original-title="Refresh"]').hide();
      $(".menu-btn-group").hide();
    }
  },
  formatters: {
    name(val, f) {
      let value = val.split(",");
      let value2 = val.split(",");
      value2.shift();
      let val2 = value2.join(", ");
      return ` <div class="level-left ellipsis">
						
			<div class="list-row-col ellipsis list-subject level ">
				
			<span class="level-item select-like">
				<input class="list-row-checkbox" type="checkbox" data-name="${val}">
				<span class="list-row-like hidden-xs style=" margin-bottom:="" 1px;"="">
					<span class="like-action not-liked" data-name="${val}" data-doctype="Job Site" data-liked-by="null" title="">
			<svg class="icon  icon-sm" style="">
			<use class="like-icon" href="#icon-heart"></use>
		</svg>
		</span>
		<span class="likes-count">
			
		</span>
				</span>
			</span>
			<span class="level-item bold ellipsis" title="${val}">
				<a class="ellipsis" href="/app/job-site/${val}" title="${val}" data-doctype="Job Site" data-name="${val}">
					${value[0]} </br> ${val2}
				</a>
			</span>
		
			</div>
		
				<div class="list-row-col tag-col hide hidden-xs ellipsis">
					<div class="tags-empty">-</div>
				</div>
			
					</div>
            `;
    },
  },
  refresh: function (listview) {
    $("#navbar-breadcrumbs > li:nth-child(2) > a").html("Job Sites");
    $('[data-original-title="ID"]>input').attr("placeholder", "Name");
    listview.columns[0].df.label = "Name";
    $(".dropdown-text").html("Name");
    setTimeout(() => {
      let option = $(".dropdown-item")[15];
      option.innerHTML = "Name";
    }, 100);
    listview.render_header(listview.columns);
  },
};
