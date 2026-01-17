import {
  get_time,
  scroll_to_bottom,
  get_messages,
  get_date_from_now,
  is_date_change,
  send_message,
  set_typing,
  is_image,
  get_avatar_html,
  mark_message_read,
} from './chat_utils';

export default class ChatSpace {
  constructor(opts) {
    this.chat_list = opts.chat_list;
    this.$wrapper = opts.$wrapper;
    this.profile = opts.profile;
    this.file = null;
    this.setup();
  }

  setup() {
    this.$chat_space = $(document.createElement('div'));
    this.typing = false;
    this.$chat_space.addClass('chat-space');
    this.setup_header();
    this.fetch_and_setup_messages();
    this.setup_socketio();
  }

  setup_header() {
    this.avatar_html = get_avatar_html(
      this.profile.room_type,
      this.profile.opposite_person_email,
      this.profile.room_name
    );
    const header_html = `
			<div class='chat-header'>
				${
          this.profile.is_admin === true
            ? `<span class='chat-back-button' title='${__('Go Back')}' >
								${frappe.utils.icon('left')}
							</span>`
            : ``
        }
				${this.avatar_html}
				<div class='chat-profile-info'>
					<div class='chat-profile-name'>
					${__(this.profile.room_name)}
					<div class='online-circle'></div>
					</div>
					<div class='chat-profile-status'>${__('Typing...')}</div>
				</div>
                <div class="chat-header-actions" style="margin-left: auto; display: flex; gap: 10px;">
                    <div class="dropdown">
                        <button class="btn btn-secondary btn-sm dropdown-toggle" type="button" data-toggle="dropdown">
                            Actions
                        </button>
                        <div class="dropdown-menu dropdown-menu-right">
                            <a class="dropdown-item" href="#" onclick="cur_dialog.chat_space.send_template()">Send Template</a>
                            <a class="dropdown-item" href="#" onclick="cur_dialog.chat_space.show_message_builder('buttons')">Send Buttons</a>
                            <a class="dropdown-item" href="#" onclick="cur_dialog.chat_space.show_message_builder('list')">Send List</a>
                            <a class="dropdown-item" href="#" onclick="cur_dialog.chat_space.schedule_message()">Schedule Message</a>
                            <div class="dropdown-divider"></div>
                            <a class="dropdown-item" href="#" onclick="cur_dialog.chat_space.create_lead()">Create Lead</a>
                            <a class="dropdown-item" href="#" onclick="cur_dialog.chat_space.create_issue()">Create Issue (Ticket)</a>
                        </div>
                    </div>
                </div>
			</div>
		`;
    this.$chat_space.append(header_html);
  }

  create_lead() {
      const me = this;
      frappe.confirm('Create a CRM Lead from this chat?', () => {
          frappe.call({
              method: 'whatsapp_chat.api.integrations.create_lead_from_chat',
              args: {
                  mobile_no: me.profile.user_email, // In WA chat, user_email is the phone number
                  contact_name: me.profile.room_name
                  // chat_history: passed automatically if needed or fetch from current context
              },
              callback: function(r) {
                  if(!r.exc) {
                      frappe.show_alert({message: __('Lead Created: ' + r.message.name), indicator: 'green'});
                  }
              }
          });
      });
  }

  create_issue() {
      const me = this;
      frappe.prompt([
          {label: 'Issue Description', fieldname: 'description', fieldtype: 'Small Text', reqd: 1}
      ], (values) => {
          frappe.call({
              method: 'whatsapp_chat.api.integrations.create_issue_from_chat',
              args: {
                  mobile_no: me.profile.user_email,
                  description: values.description
              },
              callback: function(r) {
                  if(!r.exc) {
                    frappe.show_alert({message: __('Issue Created: ' + r.message.name), indicator: 'green'});
                  }
              }
          });
      }, 'Create Support Ticket', 'Create');
  }

  send_template() {
      const me = this;
      // Fetch available templates
      frappe.call({
          method: 'frappe.client.get_list',
          args: {
              doctype: 'WhatsApp Templates',
              filters: { status: 'APPROVED' },
              fields: ['name', 'template', 'header_type', 'footer'],
              limit_page_length: 50
          },
          callback: function(r) {
              if (!r.message || r.message.length === 0) {
                  frappe.msgprint(__('No approved templates available'));
                  return;
              }

              const templates = r.message;
              const template_options = templates.map(t => t.name);

              const d = new frappe.ui.Dialog({
                  title: __('Send Template Message'),
                  fields: [
                      {
                          label: 'Template',
                          fieldname: 'template_name',
                          fieldtype: 'Select',
                          options: template_options.join('\n'),
                          reqd: 1,
                          onchange: function() {
                              const selected = templates.find(t => t.name === d.get_value('template_name'));
                              if (selected) {
                                  d.set_value('preview', selected.template || '');
                              }
                          }
                      },
                      {
                          label: 'Preview',
                          fieldname: 'preview',
                          fieldtype: 'Small Text',
                          read_only: 1
                      },
                      {
                          label: 'Variables (comma separated)',
                          fieldname: 'variables',
                          fieldtype: 'Data',
                          description: 'Replace {{1}}, {{2}}, etc.'
                      }
                  ],
                  primary_action_label: __('Send'),
                  primary_action(values) {
                      frappe.call({
                          method: 'frappe_whatsapp.utils.send_template_message',
                          args: {
                              to: me.profile.user_email,
                              template_name: values.template_name,
                              params: values.variables ? values.variables.split(',').map(v => v.trim()) : []
                          },
                          callback: function(res) {
                              if (!res.exc) {
                                  frappe.show_alert({message: __('Template sent successfully'), indicator: 'green'});
                                  d.hide();
                              }
                          }
                      });
                  }
              });
              d.show();
          }
      });
  }

  show_message_builder(type) {
      const me = this;
      frappe.require('/assets/whatsapp_chat/js/components/message_builder.js', () => {
          const builder = new window.MessageBuilder((payload) => {
              // Call send_interactive endpoint
               frappe.call({
                  method: 'whatsapp_chat.api.message.send_interactive',
                  args: {
                      room: me.profile.room,
                      user_no: me.profile.user_email,
                      message_payload: payload
                  },
                  callback: function(r) {
                      if (!r.exc) {
                          frappe.show_alert({message: __('Message Sent'), indicator: 'green'});
                          me.fetch_and_setup_messages();
                      }
                  }
              });
          });
          builder.show_builder_dialog(type);
      });
  }

  schedule_message() {
      const me = this;
      const d = new frappe.ui.Dialog({
          title: __('Schedule Message'),
          fields: [
              {
                  label: 'Message',
                  fieldname: 'message',
                  fieldtype: 'Small Text',
                  reqd: 1
              },
              {
                  label: 'Scheduled Time',
                  fieldname: 'scheduled_time',
                  fieldtype: 'Datetime',
                  reqd: 1,
                  default: frappe.datetime.add_hours(frappe.datetime.now_datetime(), 1)
              }
          ],
          primary_action_label: __('Schedule'),
          primary_action(values) {
              frappe.call({
                  method: 'frappe_whatsapp.utils.scheduler.schedule_message',
                  args: {
                      to: me.profile.user_email,
                      message: values.message,
                      scheduled_time: values.scheduled_time,
                      whatsapp_account: null // Will use default account
                  },
                  callback: function(r) {
                      if (!r.exc) {
                          frappe.show_alert({message: __('Message scheduled for ') + values.scheduled_time, indicator: 'green'});
                          d.hide();
                      }
                  }
              });
          }
      });
      d.show();
  }

  async fetch_and_setup_messages() {
    try {
      const res = await get_messages(
        this.profile.room,
        this.profile.user_email
      );
      this.setup_messages(res);
      this.setup_actions();
      this.render();

      // Mark messages as read when viewing the chat
      // This will also send read receipts to WhatsApp if enabled in settings
      mark_message_read(this.profile.room);
    } catch (error) {
      frappe.msgprint({
        title: __('Error'),
        message: __('Something went wrong. Please refresh and try again.'),
      });
    }
  }

  setup_messages(messages_list) {
    this.$chat_space_container = $(document.createElement('div'));
    this.$chat_space_container.addClass('chat-space-container');

    this.make_messages_html(messages_list);

    this.$chat_space_container.html(this.message_html);
    this.$chat_space.append(this.$chat_space_container);
  }

  make_messages_html(messages_list) {
    this.prevMessage = {};
    this.message_html = ``;
    if (this.profile.message) {
      messages_list.push(this.profile.message);
      send_message(
        this.profile.message.content,
        this.profile.user,
        this.profile.room,
        this.profile.user_email
      );
    }
    messages_list.forEach((element) => {
      const date_line_html = this.make_date_line_html(element.creation);
      this.message_html += date_line_html;

      let message_type = 'sender';

      if (element.sender_user_no === this.profile.user_email) {
        message_type = 'recipient';
      } else if (this.profile.room_type === 'Guest') {
        if (this.profile.is_admin === true && element.sender !== 'Guest') {
          message_type = 'recipient';
        }
      }
      this.message_html += this.make_message(
        element.content,
        get_time(element.creation),
        message_type,
        element.sender,
        element.caption
      ).prop('outerHTML');

      this.prevMessage = element;
    });
  }

  make_date_line_html(dateObj) {
    let result = `
			<div class='date-line'>
				<span>
					${__(get_date_from_now(dateObj, 'space'))}
				</span>
			</div>
		`;
    if ($.isEmptyObject(this.prevMessage)) {
      return result;
    } else if (is_date_change(dateObj, this.prevMessage.creation)) {
      return result;
    } else {
      return '';
    }
  }

  setup_actions() {
    this.$chat_actions = $(document.createElement('div'));
    this.$chat_actions.addClass('chat-space-actions');
    const chat_actions_html = `
			<span class='open-attach-items'>
				${frappe.utils.icon('attachment', 'lg')}
			</span>
			<input type='file' id='chat-file-uploader'
				accept='image/*, application/pdf, .doc, .docx'
				style='display: none;'
			>
			<input class='form-control type-message'
				type='search'
				placeholder='${__('Type message')}'
			>
			<div>
				<span class='message-send-button'>
					<svg xmlns="http://www.w3.org/2000/svg" width="1.1rem" height="1.1rem" viewBox="0 0 24 24">
						<path d="M24 0l-6 22-8.129-7.239 7.802-8.234-10.458 7.227-7.215-1.754 24-12zm-15 16.668v7.332l3.258-4.431-3.258-2.901z"/>
					</svg>
				</span>
			</div>
		`;
    this.$chat_actions.html(chat_actions_html);
    this.$chat_space.append(this.$chat_actions);
  }

  async handle_upload_file(file) {
    const dataurl = await frappe.dom.file_to_base64(file.file_obj);
    file.dataurl = dataurl;
    file.name = file.file_obj.name;
    return this.upload_file(file);
  }

  upload_file(file) {
    const me = this;
    return new Promise((resolve, reject) => {
      let xhr = new XMLHttpRequest();

      xhr.upload.addEventListener('load', () => {
        resolve();
      });

      xhr.addEventListener('error', () => {
        reject(frappe.throw(__('Internal Server Error')));
      });
      xhr.onreadystatechange = () => {
        if (xhr.readyState == XMLHttpRequest.DONE) {
          if (xhr.status === 200) {
            let r = null;
            let file_doc = null;
            try {
              r = JSON.parse(xhr.responseText);
              if (r.message.doctype === 'File') {
                file_doc = r.message;
              }
            } catch (e) {
              r = xhr.responseText;
            }
            try {
              if (file_doc === null) {
                reject(frappe.throw(__('File upload failed!')));
              }
              me.handle_send_message(file_doc.file_url);
            } catch (error) {
              //pass
            }
          } else {
            try {
              const error = JSON.parse(xhr.responseText);
              const messages = JSON.parse(error._server_messages);
              const errorObj = JSON.parse(messages[0]);
              reject(frappe.throw(__(errorObj.message)));
            } catch (e) {
              // pass
            }
          }
        }
      };

      xhr.open('POST', '/api/method/upload_file', true);
      xhr.setRequestHeader('Accept', 'application/json');
      xhr.setRequestHeader('X-Frappe-CSRF-Token', frappe.csrf_token);

      let form_data = new FormData();

      form_data.append('file', file.file_obj, file.name);
      form_data.append('is_private', +false);

      form_data.append('doctype', 'WhatsApp Contact');
      form_data.append('docname', this.profile.room);
      form_data.append('optimize', +true);
      xhr.send(form_data);
    });
  }

  setup_events() {
    const me = this;

    //Timeout function
    me.typing_timeout = () => {
      me.typing = false;
    };

    $('.chat-back-button').on('click', function () {
      me.chat_list.render_messages();
      me.chat_list.render();
    });

    $('.open-attach-items').on('click', function () {
      $('#chat-file-uploader').click();
    });

    $('#chat-file-uploader').on('change', function () {
      if (this.files.length > 0) {
        me.file = {};
        me.file.file_obj = this.files[0];
        me.handle_upload_file(me.file);
        me.file = null;
      }
    });

    $('.message-send-button').on('click', function () {
      me.handle_send_message();
    });

    $('.type-message').keydown(function (e) {
      if (e.which === 13) {
        me.handle_send_message();
      }
    });

    // Quick Reply Listener
    $('.type-message').on('keyup', (e) => {
        const val = e.target.value;
        if (val === '/') {
            me.show_quick_reply_dialog(e.target);
        }
    });

    // Internal Note Toggle
    const $actions = this.$chat_actions;
    const internal_note_btn = $(`<span class="internal-note-toggle" title="${__('Internal Note')}">${frappe.utils.icon('locked', 'md')}</span>`);
    internal_note_btn.insertBefore($actions.find('.open-attach-items'));
    
    internal_note_btn.on('click', function() {
        me.is_internal_note = !me.is_internal_note;
        $(this).toggleClass('active');
        const input = $actions.find('.type-message');
        if (me.is_internal_note) {
            input.addClass('internal-note-mode');
            input.attr('placeholder', __('Type internal note...'));
            $(this).css('color', 'var(--yellow-500)');
        } else {
            input.removeClass('internal-note-mode');
            input.attr('placeholder', __('Type message'));
            $(this).css('color', 'inherit');
        }
    });
  }

  show_quick_reply_dialog(input_element) {
    const me = this;
    const d = new frappe.ui.Dialog({
        title: __('Select Quick Reply'),
        fields: [
            {
                label: 'Search Reply',
                fieldname: 'reply',
                fieldtype: 'Link',
                options: 'WhatsApp Quick Reply',
                reqd: 1,
                get_query: () => { return { filters: {} }; },
                onchange: () => {
                    if (d.get_value('reply')) {
                        frappe.db.get_value('WhatsApp Quick Reply', d.get_value('reply'), 'message')
                            .then(r => {
                                if (r && r.message) {
                                    $(input_element).val(r.message);
                                    d.hide();
                                    $(input_element).focus();
                                }
                            });
                    }
                }
            }
        ],
        primary_action_label: __('Insert'),
        primary_action: (values) => { d.hide(); }
    });
    d.show();
  }

  handle_send_message(attachment) {
    const $type_message = $('.type-message');
    let content = null;

    if (attachment) {
      content = attachment;
    } else {
      content = $type_message.val();
    }

    if (content.length === 0) {
      return;
    }
    this.typing = false;
    if (this.timeout) {
      clearTimeout(this.timeout);
    }

    if (
      this.profile.is_admin === true &&
      frappe.Chat.settings.user.enable_message_tone === 1
    ) {
      frappe.utils.play_sound('chat-message-send');
    }

    // Pass is_internal_note flag if set
    const is_internal = this.is_internal_note || false;

    // Optimistic UI update - styling for internal note
    const msg_element = this.make_message(content, get_time(), 'recipient', this.profile.user);
    if (is_internal) {
        msg_element.find('.message-bubble').css({'background': 'var(--yellow-100)', 'color': 'var(--text-color)'});
        msg_element.find('.message-bubble').prepend(`<strong>[Internal]</strong> `);
    }
    this.$chat_space_container.append(msg_element);
    
    $type_message.val('');
    // Reset internal note mode after send? optional. Let's keep it until toggled off or reset it.
    // Usually convenient to reset.
    if (is_internal) {
        $('.internal-note-toggle').click(); // toggle back
    }

    scroll_to_bottom(this.$chat_space_container);
    send_message(
      content,
      this.profile.user,
      this.profile.room,
      this.profile.user_email,
      attachment,
      is_internal
    );
  }

  setup_socketio() {
    const me = this;
    // Track received message IDs to prevent duplicates
    this.received_message_ids = new Set();

    // Listen for room-specific messages
    frappe.realtime.on(this.profile.room, function (res) {
      me.handle_incoming_message(res);
    });

    // Also listen for latest_chat_updates and filter by room
    frappe.realtime.on('latest_chat_updates', function (res) {
      if (res.room === me.profile.room) {
        me.handle_incoming_message(res);
      }
    });
  }

  handle_incoming_message(res) {
    // Create a unique ID for the message to prevent duplicates
    const msg_id = res.name || `${res.content}-${res.creation}-${res.sender_user_no}`;

    // Skip if we've already processed this message
    if (this.received_message_ids.has(msg_id)) {
      return;
    }
    this.received_message_ids.add(msg_id);

    // Display the message
    this.receive_message(res, get_time(res.creation));

    // Mark as read since chat is open and user is viewing it
    mark_message_read(this.profile.room);
  }

  destroy_socket_events() {
    frappe.realtime.off(this.profile.room);
    frappe.realtime.off('latest_chat_updates');
  }

  get_typing_changes(res) {
    if (res.user != this.profile.user_email) {
      if (
        (this.profile.is_admin === true && res.is_guest === 'true') ||
        this.profile.is_admin === false ||
        this.profile.room_type === 'Group' ||
        this.profile.room_type === 'Direct'
      ) {
        if (res.is_typing === 'false') {
          $('.chat-profile-status').css('visibility', 'hidden');
        } else {
          $('.chat-profile-status').css('visibility', 'visible');
          const timeout = setTimeout(() => {
            $('.chat-profile-status').css('visibility', 'hidden');
          }, 3000);
        }
      }
    }
  }

  make_message(content, time, type, name, caption) {
    const message_class =
      type === 'recipient' ? 'recipient-message' : 'sender-message';
    const $recipient_element = $(document.createElement('div')).addClass(
      message_class
    );
    const $message_element = $(document.createElement('div')).addClass(
      'message-bubble'
    );

    const $name_element = $(document.createElement('div'))
      .addClass('message-name')
      .text(name);

    const n = content.lastIndexOf('/');
    const file_name = content.substring(n + 1) || '';
    let $sanitized_content;

    if (content.startsWith('/files/') && file_name !== '') {
      let $url;
      if (is_image(file_name)) {
        $url = $(document.createElement('img'));
        $url.attr({ src: content }).addClass('img-responsive chat-image');
        $message_element.css({ padding: '0px', background: 'inherit' });
        $name_element.css({
          color: 'var(--text-muted)',
          'padding-bottom': 'var(--padding-xs)',
        });
      } else {
        $url = $(document.createElement('a'));
        $url.attr({ href: content, target: '_blank' }).text(__(file_name));

        if (type === 'sender') {
          $url.css('color', 'var(--cyan-100)');
        }
      }
      $sanitized_content = $url;
    } else {
      $sanitized_content = __($('<div>').text(content).html());
    }

    if (type === 'sender' && this.profile.room_type === 'Group') {
      $message_element.append($name_element);
    }
    $message_element.append($sanitized_content);

    // Add caption below image/media if present
    if (caption) {
      const $caption_element = $(document.createElement('div'))
        .addClass('message-caption')
        .css({
          'padding': 'var(--padding-sm)',
          'font-size': 'var(--text-sm)',
          'color': type === 'sender' ? 'var(--white)' : 'var(--text-color)',
          'background': type === 'sender' ? 'var(--primary-color)' : 'var(--control-bg)',
          'border-radius': '0 0 13px 13px',
        })
        .text(caption);
      $message_element.append($caption_element);
    }

    $recipient_element.append($message_element);
    $recipient_element.append(`<div class='message-time'>${__(time)}</div>`);

    return $recipient_element;
  }

  handle_send_message(attachment) {
    const $type_message = $('.type-message');
    let content = null;

    if (attachment) {
      content = attachment;
    } else {
      content = $type_message.val();
    }

    if (content.length === 0) {
      return;
    }
    this.typing = false;
    if (this.timeout) {
      clearTimeout(this.timeout);
    }

    if (
      this.profile.is_admin === true &&
      frappe.Chat.settings.user.enable_message_tone === 1
    ) {
      frappe.utils.play_sound('chat-message-send');
    }

    // Pass is_internal_note flag if set
    const is_internal = this.is_internal_note || false;

    // Optimistic UI update - styling for internal note
    const msg_element = this.make_message(content, get_time(), 'recipient', this.profile.user);
    if (is_internal) {
        msg_element.find('.message-bubble').css({'background': 'var(--yellow-100)', 'color': 'var(--text-color)'});
        msg_element.find('.message-bubble').prepend(`<strong>[Internal]</strong> `);
    }
    this.$chat_space_container.append(msg_element);
    
    $type_message.val('');
    // Reset internal note mode after send? optional. Let's keep it until toggled off or reset it.
    // Usually convenient to reset.
    if (is_internal) {
        $('.internal-note-toggle').click(); // toggle back
    }

    scroll_to_bottom(this.$chat_space_container);
    send_message(
      content,
      this.profile.user,
      this.profile.room,
      this.profile.user_email,
      attachment,
      is_internal
    );
  }

  receive_message(res, time) {
    let chat_type = 'sender';
    // Skip if this is our own outgoing message (sender_user_no would be empty or 'Administrator' for outgoing)
    if (res.sender_user_no === 'Administrator' || res.sender_user_no === this.profile.user) {
      return;
    }

    if (
      this.profile.is_admin === true &&
      $('.chat-element').is(':visible') &&
      frappe.Chat.settings.user.enable_message_tone === 1
    ) {
      frappe.utils.play_sound('chat-message-receive');
    }

    if (this.profile.room_type === 'Guest') {
      if (this.profile.is_admin === true && res.user !== 'Guest') {
        chat_type = 'recipient';
      }
    }

    this.$chat_space_container.append(
      this.make_message(res.content, time, chat_type, res.user)
    );
    scroll_to_bottom(this.$chat_space_container);
  }

  show_quick_reply_dialog(input_element) {
    const me = this;
    const d = new frappe.ui.Dialog({
        title: __('Select Quick Reply'),
        fields: [
            {
                label: 'Search Reply',
                fieldname: 'reply',
                fieldtype: 'Link',
                options: 'WhatsApp Quick Reply',
                reqd: 1,
                get_query: () => { return { filters: {} }; },
                onchange: () => {
                    if (d.get_value('reply')) {
                        frappe.db.get_value('WhatsApp Quick Reply', d.get_value('reply'), 'message')
                            .then(r => {
                                if (r && r.message) {
                                    $(input_element).val(r.message);
                                    d.hide();
                                    $(input_element).focus();
                                }
                            });
                    }
                }
            }
        ],
        primary_action_label: __('Insert'),
        primary_action: (values) => { d.hide(); }
    });
    d.show();
  }

  render() {
    this.$wrapper.html(this.$chat_space);
    this.setup_events();

    scroll_to_bottom(this.$chat_space_container);
  }
}
