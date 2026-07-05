/*
 Licensed to the Apache Software Foundation (ASF) under one or more
 contributor license agreements.  See the NOTICE file distributed with
 this work for additional information regarding copyright ownership.
 The ASF licenses this file to You under the Apache License, Version 2.0
 (the "License"); you may not use this file except in compliance with
 the License.  You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
*/

// Long-term API token management UI.
// Talks to /api/token; see server/endpoints/token.py.

// POST a JSON action to the token endpoint and return {status, json}.
async function tokens_api(payload) {
    let rv = await POST('%sapi/token.json'.format(G_apiURL), JSON.stringify(payload), {});
    let js = {};
    try {
        js = await rv.json();
    } catch (e) {
        js = { okay: false, message: "Malformed server response." };
    }
    return { status: rv.status, json: js };
}

// Format an epoch (seconds) as a compact UTC date, or "never" when 0/empty.
// The " UTC" suffix is dropped here and shown once in the column header instead.
function tokens_fmt_date(epoch) {
    if (!epoch) {
        return "never";
    }
    return new Date(epoch * 1000.0).ISOBare().replace(' UTC', '');
}

// Entry point (wired into the user dropdown menu). Opens the modal and draws
// the token management UI.
function manage_tokens() {
    modal("API Tokens", "", "help", true);
    let body = document.getElementById('modal_text');
    if (!body) {
        return;
    }
    body.innerHTML = "";

    body.inject(new HTML('p', {}, "API tokens let you authenticate to the API from scripts by sending an " +
        "'Authorization: Bearer <token>' header. Scopes limit what a token can do; a token can never exceed " +
        "your own account's access. Treat tokens like passwords."));

    // Creation form
    let form = new HTML('div', { class: 'token_create' });
    let desc = new HTML('input', {
        type: 'text',
        id: 'token_desc',
        placeholder: 'Description (e.g. "laptop backup script")',
        style: { width: '260px' }
    });
    form.inject(desc);

    // Scope selection (read is the least-privilege default). The admin scope is
    // only offered to admin accounts - it would be inert for anyone else.
    let scope_defs = [
        ['read', 'Read archives (search, fetch, download mbox)', true],
        ['write', 'Send email (compose)', false]
    ];
    let creds = (G_ponymail_preferences.login && G_ponymail_preferences.login.credentials) || {};
    if (creds.admin) {
        scope_defs.push(['admin', 'Administrative actions (hide / delete / edit)', false]);
    }
    let scopes = new HTML('div', { class: 'token_scopes', style: { margin: '6px 0' } });
    for (let s of scope_defs) {
        let cb = new HTML('input', { type: 'checkbox', id: 'token_scope_' + s[0], value: s[0] });
        if (s[2]) {
            cb.checked = true;
        }
        scopes.inject(new HTML('div', {}, new HTML('label', {}, [cb, " " + s[0] + " — " + s[1]])));
    }
    form.inject(scopes);

    form.inject(new HTML('button', { onclick: 'create_token();' }, "Create token"));
    body.inject(form);
    body.inject(new HTML('hr'));

    // List placeholder, filled asynchronously
    body.inject(new HTML('div', { id: 'token_list' }, "Loading…"));
    load_tokens();
}

// Fetch and render the current user's tokens into #token_list.
async function load_tokens() {
    let list = document.getElementById('token_list');
    if (!list) {
        return;
    }
    let res = await tokens_api({ action: 'list' });
    list.innerHTML = "";
    if (!res.json.okay) {
        list.inject(new HTML('p', { style: { color: 'red' } }, res.json.message || "Could not load tokens."));
        return;
    }
    let tokens = res.json.tokens || [];
    if (tokens.length === 0) {
        list.inject(new HTML('p', {}, "You have no API tokens yet."));
        return;
    }

    // Theme-neutral colours so the table reads well in both light and dark skins.
    let hairline = '1px solid rgba(128, 128, 128, 0.25)';
    let table = new HTML('table', {
        class: 'token_table',
        style: { borderCollapse: 'collapse', width: '100%', marginTop: '8px', fontSize: '13px' }
    });

    let hrow = new HTML('tr');
    for (let h of ['Description', 'Scopes', 'Created (UTC)', 'Expires (UTC)', 'Last used (UTC)', '']) {
        hrow.inject(new HTML('th', {
            style: {
                textAlign: 'left',
                padding: '6px 10px',
                borderBottom: '2px solid rgba(128, 128, 128, 0.45)',
                whiteSpace: 'nowrap'
            }
        }, h));
    }
    table.inject(hrow);

    let cell = { padding: '6px 10px', borderBottom: hairline, verticalAlign: 'top' };
    let nowrap = { padding: '6px 10px', borderBottom: hairline, verticalAlign: 'top', whiteSpace: 'nowrap' };
    let idx = 0;
    for (let t of tokens) {
        let revoke = new HTML('button', {
            onclick: "revoke_token('%s');".format(t.id),
            style: { color: 'red', cursor: 'pointer' }
        }, "Revoke");
        let row = new HTML('tr', {
            class: 'token_row',
            style: (idx++ % 2) ? { background: 'rgba(128, 128, 128, 0.06)' } : {}
        }, [
            new HTML('td', { style: cell }, t.description || ""),
            new HTML('td', { style: nowrap }, (t.scopes || []).join(', ') || "read"),
            new HTML('td', { style: nowrap }, tokens_fmt_date(t.created)),
            new HTML('td', { style: nowrap }, tokens_fmt_date(t.expires)),
            new HTML('td', { style: nowrap }, tokens_fmt_date(t.last_used)),
            new HTML('td', { style: { padding: '6px 10px', borderBottom: hairline, textAlign: 'right', whiteSpace: 'nowrap' } }, revoke)
        ]);
        table.inject(row);
    }

    // Wrap in a horizontal scroller so the modal never overflows the viewport.
    let scroller = new HTML('div', { style: { overflowX: 'auto' } });
    scroller.inject(table);
    list.inject(scroller);
}

// Create a new token and show the raw secret exactly once.
async function create_token() {
    let descEl = document.getElementById('token_desc');
    let description = descEl ? descEl.value : "";
    let scopes = [];
    for (let s of ['read', 'write', 'admin']) {
        let cb = document.getElementById('token_scope_' + s);
        if (cb && cb.checked) {
            scopes.push(s);
        }
    }
    let res = await tokens_api({ action: 'create', description: description, scopes: scopes.join(' ') });
    if (!res.json.okay) {
        modal("Could not create token", res.json.message || "Unknown error.", "error");
        return;
    }

    let body = document.getElementById('modal_text');
    if (!body) {
        return;
    }
    body.innerHTML = "";
    body.inject(new HTML('p', {}, "Your new token is shown below. Copy it now — for security it will never be shown again:"));
    let tokenBox = new HTML('textarea', {
        readonly: 'readonly',
        rows: "2",
        style: { width: '100%' }
    }, res.json.token);
    body.inject(tokenBox);
    body.inject(new HTML('p', {}, "Scopes: " + ((res.json.scopes || []).join(', ') || "read")));
    if (res.json.expires) {
        body.inject(new HTML('p', {}, "Expires: " + tokens_fmt_date(res.json.expires)));
    } else {
        body.inject(new HTML('p', {}, "This token does not expire."));
    }
    body.inject(new HTML('button', { onclick: 'manage_tokens();' }, "Back to token list"));

    // Pre-select the secret for easy copying.
    if (tokenBox.select) {
        tokenBox.focus();
        tokenBox.select();
    }
}

// Revoke a token by id, after confirmation.
async function revoke_token(id) {
    if (!confirm("Revoke this token? Any scripts using it will immediately stop working.")) {
        return;
    }
    let res = await tokens_api({ action: 'revoke', id: id });
    if (!res.json.okay) {
        modal("Could not revoke token", res.json.message || "Unknown error.", "error");
        return;
    }
    await load_tokens();
}
