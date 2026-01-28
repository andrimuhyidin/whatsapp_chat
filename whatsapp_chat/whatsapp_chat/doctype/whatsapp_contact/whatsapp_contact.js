// Copyright (c) 2024, shridhar patil and contributors
// For license information, please see license.txt

frappe.ui.form.on("WhatsApp Contact", {
	refresh(frm) {
        if (!frm.is_new()) {
            // --- Chat History Tab ---
            frm.add_custom_button(__("Open Chat"), () => {
                if ($('.chat-app').length > 0) {
                     $('.chat-navbar-icon').click();
                     frappe.msgprint("Please select the contact in the chat list.");
                } else {
                    frappe.msgprint("Chat Widget not loaded. Please check integration settings.");
                }
            });

            // --- Export Actions ---
            frm.add_custom_button(__("Export PDF"), () => {
                window.open(`/api/method/whatsapp_chat.export.api.export_chat?contact_name=${frm.doc.name}&format=pdf`);
            }, __("Export"));

            frm.add_custom_button(__("Export CSV"), () => {
                window.open(`/api/method/whatsapp_chat.export.api.export_chat?contact_name=${frm.doc.name}&format=csv`);
            }, __("Export"));

            frm.add_custom_button(__("Export JSON"), () => {
                window.open(`/api/method/whatsapp_chat.export.api.export_chat?contact_name=${frm.doc.name}&format=json`);
            }, __("Export"));

            frm.add_custom_button(__("Email Transcript"), () => {
                frappe.prompt([
                    {
                        label: __("Recipients"),
                        fieldname: "recipients",
                        fieldtype: "Data",
                        reqd: 1,
                        description: __("Comma-separated email addresses")
                    },
                    {
                        label: __("Subject"),
                        fieldname: "subject",
                        fieldtype: "Data"
                    },
                    {
                        label: __("Format"),
                        fieldname: "format",
                        fieldtype: "Select",
                        options: "PDF\nCSV",
                        default: "PDF"
                    }
                ], (values) => {
                    frappe.call({
                        method: "whatsapp_chat.export.api.email_chat_transcript",
                        args: {
                            contact_name: frm.doc.name,
                            recipients: values.recipients,
                            subject: values.subject,
                            format: values.format.toLowerCase()
                        },
                        freeze: true,
                        freeze_message: __("Sending..."),
                        callback: function(r) {
                            if (!r.exc) {
                                frappe.show_alert({message: __("Email sent successfully"), indicator: "green"});
                            }
                        }
                    });
                }, __("Email Chat Transcript"), __("Send"));
            }, __("Export"));

            // --- Agent Assignment Actions ---
            if (!frm.doc.assigned_agent) {
                frm.add_custom_button(__("Assign to Me"), () => {
                    frappe.call({
                        method: 'whatsapp_chat.utils.agent_assignment.assign_chat_to_me',
                        args: { contact_name: frm.doc.name },
                        callback: function(r) {
                            if (!r.exc) {
                                frappe.show_alert({message: __('Chat assigned to you'), indicator: 'green'});
                                frm.reload_doc();
                            }
                        }
                    });
                }, __("Actions"));
            } else if (frm.doc.assigned_agent === frappe.session.user) {
                frm.add_custom_button(__("Release Chat"), () => {
                    frappe.call({
                        method: 'whatsapp_chat.utils.agent_assignment.release_chat',
                        args: { contact_name: frm.doc.name },
                        callback: function(r) {
                            if (!r.exc) {
                                frappe.show_alert({message: __('Chat released to queue'), indicator: 'blue'});
                                frm.reload_doc();
                            }
                        }
                    });
                }, __("Actions"));

                frm.add_custom_button(__("Resolve"), () => {
                    frappe.call({
                        method: 'whatsapp_chat.utils.agent_assignment.resolve_chat',
                        args: { contact_name: frm.doc.name },
                        freeze: true,
                        callback: function(r) {
                            if (!r.exc) {
                                frappe.show_alert({message: __('Chat resolved'), indicator: 'green'});
                                frm.reload_doc();
                            }
                        }
                    });
                }, __("Actions"));
            }

            // --- Chat History Section ---
            if (!frm.chat_history_rendered) {
                frm.chat_history_rendered = true;
                // Create a custom section for chat history
                const section = $(`
                    <div class="form-section">
                        <div class="section-head" data-toggle="collapse" data-target="#chat-history-section">
                            <span>Chat History</span>
                            <i class="fa fa-chevron-down float-right"></i>
                        </div>
                        <div id="chat-history-section" class="section-body collapse show">
                            <div class="chat-history-placeholder text-center text-muted" style="padding: 20px;">
                                <button class="btn btn-sm btn-default load-history-btn">
                                    <i class="fa fa-history"></i> Load Chat History
                                </button>
                            </div>
                        </div>
                    </div>
                `);
                
                $(frm.fields_dict.last_message.wrapper).closest('.form-section').after(section);

                section.find('.load-history-btn').on('click', function() {
                    const container = section.find('#chat-history-section');
                    container.html('<div class="text-center"><i class="fa fa-spinner fa-spin"></i> Loading...</div>');
                    
                    frappe.call({
                        method: 'whatsapp_chat.api.message.get_all',
                        args: { room: frm.doc.name, limit: 20 },
                        callback: function(r) {
                            const messages = r.message || [];
                            if (messages.length === 0) {
                                container.html('<div class="text-center text-muted" style="padding: 20px;">No messages yet</div>');
                                return;
                            }
                            
                            let html = '<div class="chat-history-list" style="max-height: 400px; overflow-y: auto; padding: 10px;">';
                            messages.forEach(msg => {
                                const is_out = msg.type === 'Outgoing';
                                const time = frappe.datetime.prettyDate(msg.creation);
                                html += `
                                    <div style="display: flex; flex-direction: column; margin-bottom: 10px; align-items: ${is_out ? 'flex-end' : 'flex-start'};">
                                        <div style="max-width: 80%; padding: 8px 12px; border-radius: 12px; background: ${is_out ? 'var(--primary)' : 'var(--bg-light-gray)'}; color: ${is_out ? 'white' : 'inherit'};">
                                            ${frappe.utils.escape_html(msg.message || '[Media]')}
                                        </div>
                                        <div class="text-muted" style="font-size: 11px; margin-top: 2px;">${time}</div>
                                    </div>
                                `;
                            });
                            html += '</div>';
                            container.html(html);
                        }
                    });
                });
            }
        }
	},
});
