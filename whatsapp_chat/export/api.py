# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

"""
API endpoints for chat export functionality.
"""

import frappe
from frappe import _
from frappe.utils import nowdatetime
from whatsapp_chat.export.handler import ChatExporter


@frappe.whitelist()
def export_chat(
	contact_name: str,
	format: str = "pdf",
	date_from: str = None,
	date_to: str = None
):
	"""
	Export chat conversation to specified format.
	
	Args:
		contact_name: Name of the WhatsApp Contact document
		format: Export format (pdf, csv, json)
		date_from: Start date (YYYY-MM-DD)
		date_to: End date (YYYY-MM-DD)
		
	Returns:
		File download response
	"""
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required"))
	
	if not frappe.has_permission("WhatsApp Contact", "read", contact_name):
		frappe.throw(_("Permission denied"))
	
	# Validate format
	format = format.lower()
	if format not in ["pdf", "csv", "json"]:
		frappe.throw(_("Invalid export format. Use pdf, csv, or json."))
	
	# Create exporter
	exporter = ChatExporter(contact_name, date_from, date_to)
	
	# Get contact info for filename
	contact = frappe.get_doc("WhatsApp Contact", contact_name)
	contact_identifier = contact.contact_name or contact.mobile_no
	safe_name = "".join(c for c in contact_identifier if c.isalnum() or c in " -_")[:30]
	timestamp = nowdatetime().strftime("%Y%m%d_%H%M")
	
	# Generate export
	if format == "pdf":
		content = exporter.to_pdf()
		filename = f"chat_transcript_{safe_name}_{timestamp}.pdf"
		content_type = "application/pdf"
	elif format == "csv":
		content = exporter.to_csv()
		filename = f"chat_transcript_{safe_name}_{timestamp}.csv"
		content_type = "text/csv"
	else:  # json
		content = exporter.to_json()
		filename = f"chat_transcript_{safe_name}_{timestamp}.json"
		content_type = "application/json"
	
	# Set response headers for file download
	frappe.local.response.filename = filename
	frappe.local.response.filecontent = content
	frappe.local.response.type = "download"
	
	# Log export
	frappe.logger().info(
		f"Chat exported: {contact_name} to {format} by {frappe.session.user}"
	)


@frappe.whitelist()
def export_multiple_chats(
	contact_names: str,
	format: str = "pdf"
):
	"""
	Bulk export multiple chat conversations.
	
	Args:
		contact_names: JSON array of contact names
		format: Export format (pdf, csv, json)
		
	Returns:
		ZIP file with all exports
	"""
	import json
	import zipfile
	from io import BytesIO
	
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required"))
	
	try:
		contacts = json.loads(contact_names)
	except json.JSONDecodeError:
		frappe.throw(_("Invalid contact names format"))
	
	if not contacts:
		frappe.throw(_("No contacts specified"))
	
	if len(contacts) > 50:
		frappe.throw(_("Maximum 50 contacts can be exported at once"))
	
	format = format.lower()
	if format not in ["pdf", "csv", "json"]:
		frappe.throw(_("Invalid export format"))
	
	# Create ZIP file
	zip_buffer = BytesIO()
	
	with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
		for contact_name in contacts:
			try:
				if not frappe.has_permission("WhatsApp Contact", "read", contact_name):
					continue
				
				exporter = ChatExporter(contact_name)
				contact = frappe.get_doc("WhatsApp Contact", contact_name)
				
				safe_name = "".join(
					c for c in (contact.contact_name or contact.mobile_no) 
					if c.isalnum() or c in " -_"
				)[:30]
				
				if format == "pdf":
					content = exporter.to_pdf()
					ext = "pdf"
				elif format == "csv":
					content = exporter.to_csv().encode("utf-8")
					ext = "csv"
				else:
					content = exporter.to_json().encode("utf-8")
					ext = "json"
				
				zip_file.writestr(f"{safe_name}.{ext}", content)
				
			except Exception as e:
				frappe.log_error(
					f"Error exporting chat {contact_name}: {str(e)}",
					"Bulk Chat Export Error"
				)
	
	zip_buffer.seek(0)
	
	timestamp = nowdatetime().strftime("%Y%m%d_%H%M")
	filename = f"chat_transcripts_{timestamp}.zip"
	
	frappe.local.response.filename = filename
	frappe.local.response.filecontent = zip_buffer.getvalue()
	frappe.local.response.type = "download"


@frappe.whitelist()
def email_chat_transcript(
	contact_name: str,
	recipients: str,
	subject: str = None,
	message: str = None,
	format: str = "pdf"
):
	"""
	Email chat transcript to specified recipients.
	
	Args:
		contact_name: Name of the WhatsApp Contact document
		recipients: Comma-separated email addresses
		subject: Email subject (optional)
		message: Email message body (optional)
		format: Export format (pdf, csv)
	"""
	import json
	
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required"))
	
	if not frappe.has_permission("WhatsApp Contact", "read", contact_name):
		frappe.throw(_("Permission denied"))
	
	# Parse recipients
	if isinstance(recipients, str):
		try:
			recipient_list = json.loads(recipients)
		except json.JSONDecodeError:
			recipient_list = [r.strip() for r in recipients.split(",")]
	else:
		recipient_list = recipients
	
	if not recipient_list:
		frappe.throw(_("No recipients specified"))
	
	# Validate email addresses
	from frappe.utils import validate_email_address
	for email in recipient_list:
		if not validate_email_address(email):
			frappe.throw(_("Invalid email address: {0}").format(email))
	
	# Generate export
	format = format.lower()
	if format not in ["pdf", "csv"]:
		format = "pdf"
	
	exporter = ChatExporter(contact_name)
	contact = frappe.get_doc("WhatsApp Contact", contact_name)
	
	if format == "pdf":
		content = exporter.to_pdf()
		filename = f"chat_transcript_{contact.mobile_no}.pdf"
	else:
		content = exporter.to_csv().encode("utf-8")
		filename = f"chat_transcript_{contact.mobile_no}.csv"
	
	# Prepare email
	if not subject:
		subject = _("Chat Transcript - {0}").format(
			contact.contact_name or contact.mobile_no
		)
	
	if not message:
		message = _("""
		<p>Please find attached the chat transcript for {0}.</p>
		<p>This transcript was exported on {1} by {2}.</p>
		""").format(
			contact.contact_name or contact.mobile_no,
			nowdatetime().strftime("%d %B %Y %H:%M"),
			frappe.session.user
		)
	
	# Send email with attachment
	frappe.sendmail(
		recipients=recipient_list,
		subject=subject,
		message=message,
		attachments=[{
			"fname": filename,
			"fcontent": content
		}],
		reference_doctype="WhatsApp Contact",
		reference_name=contact_name
	)
	
	frappe.msgprint(
		_("Chat transcript sent to {0}").format(", ".join(recipient_list)),
		indicator="green"
	)
	
	return {"success": True, "message": _("Email sent successfully")}


@frappe.whitelist()
def get_export_preview(contact_name: str, limit: int = 20):
	"""
	Get preview of messages for export confirmation.
	
	Args:
		contact_name: Name of the WhatsApp Contact document
		limit: Number of recent messages to preview
		
	Returns:
		Dictionary with preview data
	"""
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required"))
	
	if not frappe.has_permission("WhatsApp Contact", "read", contact_name):
		frappe.throw(_("Permission denied"))
	
	exporter = ChatExporter(contact_name)
	messages = exporter.get_messages()
	
	contact = frappe.get_doc("WhatsApp Contact", contact_name)
	
	return {
		"contact": {
			"name": contact.name,
			"contact_name": contact.contact_name,
			"mobile_no": contact.mobile_no
		},
		"total_messages": len(messages),
		"preview_messages": messages[-limit:] if limit else messages,
		"date_range": {
			"first": messages[0]["timestamp"] if messages else None,
			"last": messages[-1]["timestamp"] if messages else None
		}
	}
