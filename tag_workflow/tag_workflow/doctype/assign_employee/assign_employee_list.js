frappe.listview_settings['Assign Employee'] = {
    onload: function(){
            $('[data-original-title="ID"]>input').attr('placeholder', 'Name');
            cur_list.columns[0].df.label = "Name";
            cur_list.render_header(cur_list.columns);
            $('.custom-actions.hidden-xs.hidden-md').hide();
			$('[data-original-title="Refresh"]').hide();
			$('.menu-btn-group').hide();
            $("button.btn.btn-primary.btn-sm.primary-action").hide()
            $("button.btn.btn-default.btn-sm.ellipsis").hide()
            if(!["Hiring","TAG"].includes(frappe.boot.tag.tag_user_info.company_type)){
                cur_list.columns.splice(6, 1);
                cur_list.render_header(cur_list.columns[5]);
              }
    },

    formatters: {
		hiring_organization(val,f){
            return `<span class="filterable ellipsis" title="" id="${val}-${f.name}" ><a class="filterable ellipsis" data-fieldname="${val}-${f.name}" onclick = "myfunction('${val}')">${val}</a></span>
            <script>
            function myfunction(name){
                var name1= name.replace(/%/g, ' ');
                localStorage.setItem('company', name1)
                window.location.href= "/app/dynamic_page"
        
            }
            </script>`;
		},
        company(val,f){
            return `<span class="filterable ellipsis" title="" id="${val}-${f.name}" ><a class="filterable ellipsis" data-fieldname="${val}-${f.name}" onclick = "myfunction1('${val}')">${val}</a></span>
            <script>
            function myfunction1(name){
                var name1= name.replace(/%/g, ' ');
                localStorage.setItem('company', name1)
                window.location.href= "/app/dynamic_page"
        
            }
            </script>`;
		},
        job_order(val,f){
            return `<span class="ellipsis" title="" id="${val}-${f.name}" ><a class="ellipsis" href="/app/job-order/${val}" data-fieldname="${val}-${f.name}" >${val}</a></span>`            
		},
        staffing_organization_ratings (val, d, f) {
            let a = 0
            frappe.call({
              async:false,
               method:"tag_workflow.tag_workflow.doctype.company.company.check_staffing_reviews",
               args:{
                 company_name: f.company
               },
               callback:(r)=>{
                 a = r
               }
           })
          return a.message ===0 ?'':`<span><span class='text-warning'>★</span> ${a.message}<span>`            
          },
	},
    refresh:function(){
        $("button.btn.btn-primary.btn-sm.primary-action").hide()
        $("button.btn.btn-default.btn-sm.ellipsis").hide()
        
    }
}