let script = document.createElement('script');
script.src = `https://maps.googleapis.com/maps/api/js?key=${frappe.boot.tag.tag_user_info.api_key}&libraries=places`;
script.defer = true;
// script.async = true;
// Attach your callback function to the `window` object
window.initMap = function() {
	// JS API is loaded and available
};
// Append the 'script' element to 'head'
document.head.appendChild(script);
