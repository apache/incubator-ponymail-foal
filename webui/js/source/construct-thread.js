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

function expand_email_threaded(idx, flat) {
    let placeholder = document.getElementById('email_%u'.format(idx));
    if (placeholder) {
        // Check if email is already visible - if so, hide it!
        if (placeholder.style.display == 'block') {
            console.log("Collapsing thread at index %u".format(idx));
            placeholder.style.display = 'none';
            G_current_email_idx = undefined;
            return false;
        }
        G_current_email_idx = idx;
        console.log("Expanding thread at index %u".format(idx));
        placeholder.style.display = 'block';

        // Check if we've already filled out the structure here
        if (placeholder.getAttribute('data-filled') == 'yes') {
            console.log("Already constructed this thread, bailing!");
        } else {
            // Construct the base scaffolding for all emails
            let eml = flat ? G_current_json.emails[idx] : G_current_json.thread_struct[idx];
            if (eml) {
                G_current_open_email = eml.tid || eml.mid;
            }
            let thread = construct_thread(eml);
            placeholder.inject(thread);
            placeholder.setAttribute("data-filled", 'yes');
        }
    }
    return false;
}

function construct_thread(thread, cid, nestlevel, included) {
    // First call on a thread/email, this is indef.
    // Use this to plop a scroll call when loaded
    // to prevent weird cache-scrolling
    let doScroll = false;
    if (cid === undefined) {
        doScroll = true;
    }
    included = included || [];
    cid = (cid || 0) + 1;
    nestlevel = (nestlevel || 0) + 1;
    let mw = calc_email_width();
    let max_nesting = PONYMAIL_MAX_NESTING;
    if (mw < 700) {
        max_nesting = Math.floor(mw / 250);
    }
    cid %= 5;
    let color = ['286090', 'ccab0a', 'c04331', '169e4e', '6d4ca5'][cid];
    let email;
    if (nestlevel < max_nesting) {
        email = new HTML('div', {
            class: 'email_wrapper',
            id: 'email_%s'.format(thread.tid || thread.id)
        });
        if (G_chatty_layout) {
            email.style.border = "none !important";
        } else {
            email.style.borderLeft = '3px solid #%s'.format(color);
        }
    } else {
        email = new HTML('div', {
            class: 'email_wrapper_nonest',
            id: 'email_%s'.format(thread.tid || thread.id)
        });
    }
    let wrapper = new HTML('div', {
        class: 'email_inner_wrapper',
        id: 'email_contents_%s'.format(thread.tid || thread.id)
    });
    email.inject(wrapper);
    if (isArray(thread.children)) {
        thread.children.sort((a, b) => a.epoch - b.epoch);
        for (let child of thread.children) {
            let reply = construct_thread(child, cid, nestlevel, included);
            cid++;
            if (reply) {
                email.inject(reply);
            }
        }
    }
    let tid = thread.tid || thread.id;
    if (!included.includes(tid)) {
        included.push(tid);
        console.log("Loading email %s".format(tid));
        GET("%sapi/email.lua?id=%s".format(G_apiURL, encodeURIComponent(tid)), render_email, {
            cached: true,
            scroll: doScroll,
            id: tid,
            div: wrapper
        });
    }
    return email;
}

// Singular thread construction via permalinks
function construct_single_thread(state, json) {
    G_current_json = json;
    if (json) {
        // Old schema has json.error filled on error, simplified schema has json.message filled and json.okay set to false
        let error_message = json.okay === false ? json.message : json.error;
        if (error_message) {
            modal("An error occured", "Sorry, we hit a snag while trying to load the email(s): \n\n%s".format(error_message), "error");
            return;
        }
    }
    let div = document.getElementById('emails');
    div.innerHTML = "";

    // Fix URLs if they point to an deprecated permalink
    if (json.thread) {
        let url_to_push = location.href.replace(/[^/]+$/, "") + json.thread.id;
        if (location.href != url_to_push) {
            console.log("URL differs from default permalink, pushing correct ID to history.");
            window.history.pushState({}, json.thread.subject, url_to_push)
        }
    }

    // Not top level thread?
    let looked_for_parent = location.query == 'find_parent=true';
    if (!looked_for_parent && json.thread['in-reply-to'] && json.thread['in-reply-to'].length > 0) {
        let isign = new HTML('span', {class: 'glyphicon glyphicon-eye-close'}, " ");
        let btitle = new HTML("b", {}, "This may not be the start of the conversation...");
        let a = new HTML("a", {href: "javascript:void(location.href += '?find_parent=true');"}, "Find parent email");
        let notice = new HTML("div", {class: "infobox"}, [
            isign,
            btitle,
            new HTML("br"),
            "This email appears to be a reply to another email, as it contains an in-reply-to reference.",
            new HTML("br"),
            "If you wish to attempt finding the root thread, click here: ",
            a
        ]);
        div.inject(notice);
        notice.inject(a);
    }

    if (G_chatty_layout) {
        let listname = json.thread.list_raw.replace(/[<>]/g, '').replace('.', '@', 1);
        div.setAttribute("class", "email_placeholder_chatty");
        div.inject(new HTML('h4', {
            class: 'chatty_title'
        }, json.emails[0].subject));
        div.inject(new HTML('a', {
            href: 'list.html?%s'.format(listname),
            class: 'chatty_title'
        }, 'Posted to %s'.format(listname)));
    } else {
        div.setAttribute("class", "email_placeholder");
    }
    document.title = json.emails[0].subject + "-" + prefs.title
    div.style.display = "block";
    let thread = json.thread;
    let email = construct_thread(thread);
    div.inject(email);
}
