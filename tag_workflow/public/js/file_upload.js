import FileUploader from './frappe/new_file_uploader';

frappe.provide("frappe.ui");
frappe.provide("tag_workflow");

// override file uploader
frappe.ui.FileUploader = FileUploader;
