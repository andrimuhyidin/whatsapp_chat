# Copyright (c) 2024, BizOps and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class WhatsAppQuickReply(Document):
	"""
	WhatsApp Quick Reply for agent productivity.
	
	Stores predefined message templates with shortcuts for
	fast responses in the agent chat interface.
	"""

	def validate(self):
		if not self.shortcut.startswith("/"):
			self.shortcut = "/" + self.shortcut
