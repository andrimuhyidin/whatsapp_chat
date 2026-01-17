# Copyright (c) 2024, BizOps and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class WhatsAppQuickReply(Document):
	def validate(self):
		if not self.shortcut.startswith("/"):
			self.shortcut = "/" + self.shortcut
