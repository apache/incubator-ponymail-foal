let admin_current_email = null;
let admin_email_meta = {};
let audit_page = 0;
let audit_size = 30;
let mgmt_prefs = {}

async function POST(url, formdata, state) {
    const resp = await fetch(url, {
        credentials: "same-origin",
        mode: "same-origin",
        method: "post",
        headers: {
            "Content-Type": "application/json"
        },
        body: formdata
    });
    return resp
}

// Removes an attachment from the archives
async function admin_del_attachment(hash) {
    if (!confirm("Are you sure you wish remove this attachment from the archives?")) {
        return
    }
    // rewrite attachments for email
    let new_attach = [];
    for (let el of admin_email_meta.attachments) {
        if (el.hash != hash) {
            new_attach.push(el);
        }
    }
    admin_email_meta.attachments = new_attach;
    let formdata = JSON.stringify({
        action: "delatt",
        document: hash
    });
    // remove attachment
    let rv = await POST('%sapi/mgmt.json'.format(G_apiURL), formdata, {});
    let response = await rv.text();

    // Edit email in place
    admin_save_email(true);

    if (rv.status == 200) {
        modal("Attachment removed", "Server responded with: " + response, "help");
    } else {
        modal("Something went wrong!", "Server responded with: " + response, "error");
    }
}

// Hides an email from the archives
async function admin_hide_email() {
    if (!confirm("Are you sure you wish to hide this email from the archives?")) {
        return
    }
    let formdata = JSON.stringify({
        action: "hide",
        document: admin_current_email
    });
    let rv = await POST('%sapi/mgmt.json'.format(G_apiURL), formdata, {});
    let response = await rv.text();
    if (rv.status == 200) {
        modal("Email hidden", "Server responded with: " + response, "help");
    } else {
        modal("Something went wrong!", "Server responded with: " + response, "error");
    }
}

async function admin_unhide_email() {
    if (!confirm("Are you sure you wish to unhide this email?")) {
        return
    }
    let formdata = JSON.stringify({
        action: "unhide",
        document: admin_current_email
    });
    let rv = await POST('%sapi/mgmt.json'.format(G_apiURL), formdata, {});
    let response = await rv.text();
    if (rv.status == 200) {
        modal("Email unhidden", "Server responded with: " + response, "help");
    } else {
        modal("Something went wrong!", "Server responded with: " + response, "error");
    }
}


// Fully deletes an email from the archives
async function admin_delete_email() {
    if (!confirm("Are you sure you wish to remove this email from the archives?")) {
        return
    }
    let formdata = JSON.stringify({
        action: "delete",
        document: admin_current_email
    });
    let rv = await POST('%sapi/mgmt.json'.format(G_apiURL), formdata, {});
    let response = await rv.text();
    if (rv.status == 200) {
        modal("Email removed", "Server responded with: " + response, "help");
    } else {
        modal("Something went wrong!", "Server responded with: " + response, "error");
    }
}

// Saves an email with edits
async function admin_save_email(edit_attachment = false) {
    let from = document.getElementById('email_from').value;
    let subject = document.getElementById('email_subject').value;
    let listname = document.getElementById('email_listname').value;
    let is_private = document.getElementById('email_private').value;
    let body = document.getElementById('email_body').value;
    let attach = null;
    if (edit_attachment) {
        attach = admin_email_meta.attachments;
    }
    let formdata = JSON.stringify({
        action: "edit",
        document: admin_current_email,
        from: from,
        subject: subject,
        list: listname,
        private: is_private,
        body: body,
        attachments: attach
    })
    let rv = await POST('%sapi/mgmt.json'.format(G_apiURL), formdata, {});
    let response = await rv.text();
    if (edit_attachment && rv.status == 200) return
    if (rv.status == 200) {
        modal("Email changed", "Server responded with: " + response, "help");
    } else {
        modal("Something went wrong!", "Server responded with: " + response, "error");
    }
}

function admin_email_preview(stats, json) {
    admin_current_email = json.mid;
    admin_email_meta = json;
    let cp = document.getElementById("panel");
    let div = new HTML('div', {
        style: {
            margin: '5px'
        }
    });
    cp.inject(div);

    div.inject(new HTML('h1', {}, "Editing email " + json.mid + ":"));

    // Author
    let author_field = new HTML('div', {
        class: 'email_kv_edit'
    });
    let author_key = new HTML('div', {
        class: 'email_key'
    }, "From: ");
    let author_value = new HTML('input', {
        id: 'email_from',
        style: {
            width: "480px"
        },
        value: json.from
    });
    author_field.inject([author_key, author_value]);
    div.inject(author_field);

    // Subject
    let subject_field = new HTML('div', {
        class: 'email_kv_edit'
    });
    let subject_key = new HTML('div', {
        class: 'email_key'
    }, "Subject: ");
    let subject_value = new HTML('input', {
        id: 'email_subject',
        style: {
            width: "480px"
        },
        value: json.subject
    });
    subject_field.inject([subject_key, subject_value]);
    div.inject(subject_field);

    // Date
    let date_field = new HTML('div', {
        class: 'email_kv_edit'
    });
    let date_key = new HTML('div', {
        class: 'email_key'
    }, "Date: ");
    let date_value = new HTML('div', {
        class: 'email_value'
    }, new Date(json.epoch * 1000.0).ISOBare());
    date_field.inject([date_key, date_value]);
    div.inject(date_field);

    // List
    let listname = json.list_raw.replace(".", "@", 1).replace(/[<>]/g, "");
    let list_field = new HTML('div', {
        class: 'email_kv_edit'
    });
    let list_key = new HTML('div', {
        class: 'email_key'
    }, "List: ");
    let list_value = new HTML('input', {
        id: 'email_listname',
        style: {
            width: "480px"
        },
        value: listname
    });
    list_field.inject([list_key, list_value]);
    div.inject(list_field);

    // Private email?
    let priv_field = new HTML('div', {
        class: 'email_kv_edit'
    });
    let priv_key = new HTML('div', {
        class: 'email_key'
    }, "Visibility: ");
    let priv_value = new HTML('select', {
        id: 'email_private'
    });
    priv_value.inject(new HTML('option', {
        value: 'no',
        style: {
            color: 'green'
        },
        selected: json.private ? null : "selected"
    }, "Public"));
    priv_value.inject(new HTML('option', {
        value: 'yes',
        style: {
            color: 'red'
        },
        selected: json.private ? "selected" : null
    }, "Private"));
    priv_field.inject([priv_key, priv_value]);
    div.inject(priv_field);

    // Attachments?
    if (json.attachments && json.attachments.length > 0) {
        let attach_field = new HTML('div', {
            class: 'email_kv'
        });
        let attach_key = new HTML('div', {
            class: 'email_key'
        }, "Attachment(s): ");
        let alinks = [];
        for (let attachment of json.attachments) {
            let link = `${G_apiURL}api/email.lua?attachment=true&id=${encodeURIComponent(json.mid)}&file=${encodeURIComponent(attachment.hash)}`;
            let a = new HTML('a', {
                href: link,
                target: '_blank'
            }, attachment.filename);
            alinks.push(a);
            let fs = ` ${attachment.size} bytes`;
            if (attachment.size >= 1024) fs = ` ${Math.floor(attachment.size/1024)} KB`;
            if (attachment.size >= 1024 * 1024) fs = ` ${Math.floor(attachment.size/(1024*10.24))/100} MB`;
            alinks.push(fs);
            let adel = new HTML('a', {
                onclick: `admin_del_attachment('${attachment.hash}');`,
                href: "javascript:void(0);"
            }, "Delete attachment");
            alinks.push(adel);
            alinks.push(new HTML('br'));
        }
        let attach_value = new HTML('div', {
            class: 'email_value'
        }, alinks);
        attach_field.inject([attach_key, attach_value]);
        div.inject(attach_field);
    }

    let text = new HTML('textarea', {
        id: 'email_body',
        style: {
            width: "100%",
            height: "480px"
        }
    }, json.body);
    div.inject(text);

    let btn_edit = new HTML('button', {
        onclick: "admin_save_email();"
    }, "Save changes to archive");
    let btn_del = new HTML('button', {
        onclick: "admin_delete_email();",
        style: {
            marginLeft: "36px",
            color: 'red'
        }
    }, "Delete email from archives");

    let btn_hide = new HTML('button', {
        onclick: "admin_hide_email();",
        style: {
            marginLeft: "36px",
            color: 'purple'
        }
    }, "Hide email from archives");
    if (admin_email_meta.deleted) {
        btn_hide = new HTML('button', {
            onclick: "admin_unhide_email();",
            style: {
                marginLeft: "36px",
                color: 'purple'
            }
        }, "Unhide email from archives");
    }

    div.inject(new HTML('br'));
    div.inject(btn_edit);
    div.inject(btn_hide);
    div.inject(btn_del);
    div.inject(new HTML('br'));
    div.inject(new HTML('small', {}, "Modifying emails will remove the option to view their sources via the web interface, as the source may contain traces that reveal the edit."))
    div.inject(new HTML('br'));
    if (!mgmt_prefs.login.credentials.fully_delete) {
        div.inject(new HTML('small', {}, "Emails that are deleted may still be recovered by the base system administrator. For complete expungement, please contact the system administrator."))
    } else {
        div.inject(new HTML('small', {style:{color: 'red'}}, "As full delete enforcement is enabled on this server, emails are removed forever from the archive when deleted, and cannot be recovered."))
    }
}

function admin_audit_view(state, json) {
    let headers = ['Date', 'Author', 'Remote', 'Action', 'Target', 'Log'];
    let cp = document.getElementById("panel");
    let div = document.getElementById('auditlog_entries');
    if (!div) {
        div = new HTML('div', {
            id: "auditlog",
            style: {
                margin: '5px'
            }
        });
        cp.inject(div);
        div.inject(new HTML('h1', {}, "Audit log:"));
    }
    let table = document.getElementById('auditlog_entries');
    if (json.entries && json.entries.length > 0 || table) {
        if (!table) {
            table = new HTML('table', {
                border: "1",
                id: "auditlog_entries",
                class: "auditlog_entries"
            });
            let trh = new HTML('tr');
            for (let header of headers) {
                let th = new HTML('th', {}, header + ":");
                trh.inject(th);
            }
            table.inject(trh)
            div.inject(table);
            let btn = new HTML('button', {
                onclick: "admin_audit_next();"
            }, "Load more entries");
            div.inject(btn);
        }
        for (let entry of json.entries) {
            let tr = new HTML('tr', {
                class: "auditlog_entry"
            });
            for (let header of headers) {
                let key = header.toLowerCase();
                let value = entry[key];
                if (key == 'target') {
                    value = new HTML('a', {
                        href: "/admin/" + value
                    }, value);
                }
                if (key == 'action') {
                    let action_colors = {
                        edit: 'blue',
                        delete: 'red',
                        default: 'black'
                    };
                    value = new HTML('spam', {
                        style: {
                            color: action_colors[value] ? action_colors[value] : action_colors['default']
                        }
                    }, value);
                }
                let th = new HTML('td', {}, value);
                tr.inject(th);
            }
            table.inject(tr);
        }
    } else {
        div.inject("Audit log is empty");
    }
}

function admin_audit_next() {
    audit_page++;
    GET('%sapi/mgmt.json?action=log&page=%u&size=%u'.format(G_apiURL, audit_page, audit_size), admin_audit_view, null);
}

// Onload function for admin.html
function admin_init() {
    init_preferences(); // blank call to load defaults like social rendering
    GET('%sapi/preferences.lua'.format(G_apiURL), (state, json) => {
        mgmt_prefs = json
        init_preferences(state, json);
    }, null);
    let mid = decodeURIComponent(location.href.split('/').pop());
    // Specific email/list handling?
    if (mid.length > 0) {
        // List handling?
        if (mid.match(/^<.+>$/)) {

        }
        // Email handling?
        else {
            GET('%sapi/email.json?id=%s'.format(G_apiURL, encodeURIComponent(mid)), admin_email_preview, null);
        }
    } else { // View audit log
        GET('%sapi/mgmt.json?action=log&page=%s&size=%u'.format(G_apiURL, audit_page, audit_size), admin_audit_view, null);
    }
}
