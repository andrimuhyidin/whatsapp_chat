# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

"""
Chat export handler for WhatsApp Chat.
"""

import frappe
from frappe import _
from frappe.utils import getdate, get_datetime, format_datetime, now_datetime
from typing import List, Dict, Any, Optional
import json
import csv
from io import StringIO


class ChatExporter:
	"""
	Export WhatsApp chat conversations to various formats.
	
	Supports PDF, CSV, and JSON export formats.
	"""
	
	def __init__(
		self,
		contact_name: str,
		date_from: Optional[str] = None,
		date_to: Optional[str] = None
	):
		"""
		Initialize chat exporter.
		
		Args:
			contact_name: Name of the WhatsApp Contact document
			date_from: Start date for filtering (YYYY-MM-DD)
			date_to: End date for filtering (YYYY-MM-DD)
		"""
		self.contact = frappe.get_doc("WhatsApp Contact", contact_name)
		self.date_from = get_datetime(date_from) if date_from else None
		self.date_to = get_datetime(date_to) if date_to else None
		self._messages = None
	
	def get_messages(self) -> List[Dict[str, Any]]:
		"""
		Fetch all messages for the contact.
		
		Returns:
			List of message dictionaries
		"""
		if self._messages is not None:
			return self._messages
		
		filters = [
			["to", "=", self.contact.mobile_no],
		]
		
		or_filters = [
			["to", "=", self.contact.mobile_no],
			["from", "=", self.contact.mobile_no]
		]
		
		# Build query
		messages = frappe.db.sql("""
			SELECT 
				name,
				type,
				`from`,
				`to`,
				message,
				content_type,
				attach,
				status,
				creation,
				modified
			FROM `tabWhatsApp Message`
			WHERE (`to` = %(mobile_no)s OR `from` = %(mobile_no)s)
			{date_filter}
			ORDER BY creation ASC
		""".format(
			date_filter=self._get_date_filter()
		), {
			"mobile_no": self.contact.mobile_no,
			"date_from": self.date_from,
			"date_to": self.date_to
		}, as_dict=True)
		
		# Process messages
		self._messages = []
		for msg in messages:
			self._messages.append({
				"name": msg.name,
				"type": msg.type,
				"direction": "incoming" if msg.type == "Incoming" else "outgoing",
				"sender": msg.get("from") or "System",
				"recipient": msg.to,
				"content": msg.message or "",
				"content_type": msg.content_type or "text",
				"attachment": msg.attach,
				"status": msg.status,
				"timestamp": msg.creation,
				"formatted_time": format_datetime(msg.creation, "dd MMM yyyy HH:mm")
			})
		
		return self._messages
	
	def _get_date_filter(self) -> str:
		"""Get SQL date filter clause."""
		filters = []
		
		if self.date_from:
			filters.append("AND creation >= %(date_from)s")
		
		if self.date_to:
			filters.append("AND creation <= %(date_to)s")
		
		return " ".join(filters)
	
	def to_pdf(self) -> bytes:
		"""
		Export chat to PDF format.
		
		Returns:
			PDF file content as bytes
		"""
		messages = self.get_messages()
		
		# Generate HTML content
		html_content = self._generate_html(messages)
		
		# Convert to PDF using Frappe's PDF generation
		from frappe.utils.pdf import get_pdf
		
		pdf_options = {
			"page-size": "A4",
			"margin-top": "15mm",
			"margin-bottom": "15mm",
			"margin-left": "15mm",
			"margin-right": "15mm",
			"encoding": "UTF-8"
		}
		
		return get_pdf(html_content, options=pdf_options)
	
	def to_csv(self) -> str:
		"""
		Export chat to CSV format.
		
		Returns:
			CSV content as string
		"""
		messages = self.get_messages()
		
		output = StringIO()
		writer = csv.writer(output)
		
		# Write header
		writer.writerow([
			"Timestamp",
			"Direction",
			"Sender",
			"Recipient",
			"Content Type",
			"Message",
			"Attachment",
			"Status"
		])
		
		# Write messages
		for msg in messages:
			writer.writerow([
				msg["formatted_time"],
				msg["direction"],
				msg["sender"],
				msg["recipient"],
				msg["content_type"],
				msg["content"],
				msg["attachment"] or "",
				msg["status"] or ""
			])
		
		return output.getvalue()
	
	def to_json(self) -> str:
		"""
		Export chat to JSON format.
		
		Returns:
			JSON content as string
		"""
		messages = self.get_messages()
		
		export_data = {
			"contact": {
				"name": self.contact.name,
				"mobile_no": self.contact.mobile_no,
				"contact_name": self.contact.contact_name,
				"email": self.contact.email
			},
			"export_info": {
				"exported_at": str(now_datetime()),
				"exported_by": frappe.session.user,
				"date_from": str(self.date_from) if self.date_from else None,
				"date_to": str(self.date_to) if self.date_to else None,
				"total_messages": len(messages)
			},
			"messages": messages
		}
		
		return json.dumps(export_data, indent=2, default=str)
	
	def _generate_html(self, messages: List[Dict]) -> str:
		"""
		Generate HTML content for PDF export.
		
		Args:
			messages: List of message dictionaries
			
		Returns:
			HTML string
		"""
		# Count messages by direction
		incoming_count = sum(1 for m in messages if m["direction"] == "incoming")
		outgoing_count = sum(1 for m in messages if m["direction"] == "outgoing")
		
		# Generate message HTML
		messages_html = ""
		current_date = None
		
		for msg in messages:
			msg_date = getdate(msg["timestamp"])
			
			# Add date separator
			if msg_date != current_date:
				current_date = msg_date
				messages_html += f"""
				<div class="date-separator">
					<span>{format_datetime(msg["timestamp"], "dd MMMM yyyy")}</span>
				</div>
				"""
			
			# Message bubble
			direction_class = msg["direction"]
			content = frappe.utils.escape_html(msg["content"]) if msg["content"] else ""
			
			# Handle attachments
			attachment_html = ""
			if msg["attachment"]:
				attachment_html = f'<div class="attachment">📎 {msg["attachment"]}</div>'
			
			messages_html += f"""
			<div class="message {direction_class}">
				<div class="content">{content}</div>
				{attachment_html}
				<div class="meta">
					<span class="time">{format_datetime(msg["timestamp"], "HH:mm")}</span>
					{f'<span class="status">{msg["status"]}</span>' if msg["status"] else ''}
				</div>
			</div>
			"""
		
		# Full HTML template
		html = f"""
		<!DOCTYPE html>
		<html>
		<head>
			<meta charset="UTF-8">
			<title>Chat Transcript - {self.contact.contact_name or self.contact.mobile_no}</title>
			<style>
				body {{
					font-family: Arial, sans-serif;
					max-width: 800px;
					margin: 0 auto;
					padding: 20px;
					background: #f5f5f5;
				}}
				.header {{
					background: #075e54;
					color: white;
					padding: 20px;
					border-radius: 8px;
					margin-bottom: 20px;
				}}
				.header h1 {{
					margin: 0 0 10px 0;
					font-size: 24px;
				}}
				.header .meta {{
					font-size: 14px;
					opacity: 0.9;
				}}
				.stats {{
					display: flex;
					gap: 20px;
					margin-top: 15px;
				}}
				.stat {{
					background: rgba(255,255,255,0.2);
					padding: 10px 15px;
					border-radius: 5px;
				}}
				.chat-container {{
					background: #e5ddd5;
					padding: 20px;
					border-radius: 8px;
				}}
				.date-separator {{
					text-align: center;
					margin: 15px 0;
				}}
				.date-separator span {{
					background: #d1f4cc;
					padding: 5px 12px;
					border-radius: 8px;
					font-size: 12px;
					color: #555;
				}}
				.message {{
					max-width: 65%;
					padding: 8px 12px;
					border-radius: 8px;
					margin: 5px 0;
					clear: both;
				}}
				.message.incoming {{
					background: white;
					float: left;
					border-bottom-left-radius: 0;
				}}
				.message.outgoing {{
					background: #dcf8c6;
					float: right;
					border-bottom-right-radius: 0;
				}}
				.message .content {{
					word-wrap: break-word;
					white-space: pre-wrap;
				}}
				.message .attachment {{
					font-size: 12px;
					color: #666;
					margin-top: 5px;
				}}
				.message .meta {{
					font-size: 11px;
					color: #888;
					text-align: right;
					margin-top: 5px;
				}}
				.clearfix {{
					clear: both;
				}}
				.footer {{
					margin-top: 20px;
					padding: 15px;
					background: #fff;
					border-radius: 8px;
					font-size: 12px;
					color: #666;
				}}
			</style>
		</head>
		<body>
			<div class="header">
				<h1>Chat Transcript</h1>
				<div class="meta">
					<strong>Contact:</strong> {self.contact.contact_name or 'Unknown'}<br>
					<strong>Phone:</strong> {self.contact.mobile_no}
				</div>
				<div class="stats">
					<div class="stat">
						<strong>{len(messages)}</strong> Total Messages
					</div>
					<div class="stat">
						<strong>{incoming_count}</strong> Incoming
					</div>
					<div class="stat">
						<strong>{outgoing_count}</strong> Outgoing
					</div>
				</div>
			</div>
			
			<div class="chat-container">
				{messages_html}
				<div class="clearfix"></div>
			</div>
			
			<div class="footer">
				<strong>Export Information</strong><br>
				Exported on: {format_datetime(now_datetime(), "dd MMMM yyyy HH:mm")}<br>
				Exported by: {frappe.session.user}<br>
				Period: {format_datetime(self.date_from, "dd MMM yyyy") if self.date_from else 'All time'} 
				- {format_datetime(self.date_to, "dd MMM yyyy") if self.date_to else 'Present'}
			</div>
		</body>
		</html>
		"""
		
		return html
