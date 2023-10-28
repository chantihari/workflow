frappe.pages['tagadmin-page'].on_page_load = function(wrapper) {
	let page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "Home",
		single_column: true
	});
	wrapper.TagHome = new frappe.TagHome(wrapper, page);

}
frappe.TagHome = Class.extend({
	init: function (wrapper, page) {
		let me = this;
		this.parent = wrapper;
		this.page = this.parent.page;
		me.setup(wrapper, page);
		me.remove(wrapper,page)


	},
	setup: function (wrapper, page) {
		this.body = $(`
		<div class="home">
			<div class="widget-group ">
				<div class="widget-group-head">
					<div class="widget-group-title">Shortcuts</div>
					<div class="widget-group-control"></div>
				</div>
				<div class="widget-group-body grid-col-3">
					<div class="widget widget-shadow shortcut-widget-box" data-widget-name="a85252dcd0"
						onclick=redirect_doc("job-order")>
						<div class="widget-head">
							<div>
								<div class="widget-title ellipsis" name="home-job-order">Job Orders</div>
								<div class="widget-subtitle"></div>
							</div>
							<div class="widget-control"></div>
						</div>
						<div class="widget-body"></div>
						<div class="widget-footer"></div>
					</div>
					<div class="widget widget-shadow shortcut-widget-box" data-widget-name="a98f4b28cd"
						onclick=redirect_doc("sales-invoice")>
						<div class="widget-head">
							<div>
								<div class="widget-title ellipsis">Invoice</div>
								<div class="widget-subtitle"></div>
							</div>
							<div class="widget-control"></div>
						</div>
						<div class="widget-body"></div>
						<div class="widget-footer"></div>
					</div>
				</div>
			</div>
					<div class="widget-group ">
						<div class="widget-group-head">
							<div class="widget-group-title">Reports &amp; Masters</div>
							<div class="widget-group-control"></div>
						</div>
						<div class="widget-group-body grid-col-3">
							<div class="widget              links-widget-box" data-widget-name="0d6099fd89">
								<div class="widget-head">
									<div>
										<div class="widget-title ellipsis"><svg class="icon  icon-sm" style="">
												<use class="" href="#icon-file"></use>
											</svg> <span>Accounting</span></div>
										<div class="widget-subtitle"></div>
									</div>
									<div class="widget-control"></div>
								</div>
								<div class="widget-body">
									<a href="/app/company" class="link-item ellipsis onboard-spotlight " type="Link">
										<span class="indicator-pill no-margin yellow"></span>
										<span class="link-content ellipsis">Company</span>
									</a><a href="/app/user" class="link-item ellipsis onboard-spotlight " type="Link">
										<span class="indicator-pill no-margin yellow"></span>
										<span class="link-content ellipsis">User</span>
									</a>
								</div>
								<div class="widget-footer">
								</div>
							</div>
							<div class="widget              links-widget-box" data-widget-name="2bdf9597c0">
								<div class="widget-head">
									<div>
										<div class="widget-title ellipsis"><svg class="icon  icon-sm" style="">
												<use class="" href="#icon-file"></use>
											</svg> <span>Services</span></div>
										<div class="widget-subtitle"></div>
									</div>
									<div class="widget-control"></div>
								</div>
								<div class="widget-body">
									<a href="/app/item" class="link-item ellipsis onboard-spotlight " type="Link">
										<span class="indicator-pill no-margin yellow"></span>
										<span class="link-content ellipsis">Job Title</span>
									</a><a href="/app/timesheet" class="link-item ellipsis  " type="Link">
										<span class="indicator-pill no-margin gray"></span>
										<span class="link-content ellipsis">Timesheet</span>
									</a>
								</div>
								<div class="widget-footer">
								</div>
							</div>
							<div class="widget              links-widget-box" data-widget-name="a2e9ef37ec">
								<div class="widget-head">
									<div>
										<div class="widget-title ellipsis"><svg class="icon  icon-sm" style="">
												<use class="" href="#icon-file"></use>
											</svg> <span>CRM</span></div>
										<div class="widget-subtitle"></div>
									</div>
									<div class="widget-control"></div>
								</div>
								<div class="widget-body">
									<a href="/app/lead" class="link-item ellipsis onboard-spotlight " type="Link">
										<span class="indicator-pill no-margin yellow"></span>
										<span class="link-content ellipsis">Lead</span>
									</a>
								</div>
								<div class="widget-footer">
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
			<script>
				function dynamic_route(name){
					name1= name.replace(/%/g, ' ');
					localStorage.setItem("company", name1);
					window.location.href = "/app/dynamic_page";						
				}
			</script>`).appendTo(this.page.main);
		$(frappe.render_template("tagadmin_page", "")).appendTo(this.body);
 	},
	remove:function(wrapper,page){
		$(".ellipsis.title-text.admin-title").remove();
	}
});
function redirect_doc(name) {
	location.href = '/app/' + name
}





