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

let compact_email_height = 24;  // a normal email element is 24 pixels high
let preview_email_height = 40;

let narrow_width = 600;  // <= 600 pixels and we're in narrow view

function calc_per_page() {
    // Figure out how many emails per page
    let body = document.body;
    let html = document.documentElement;
    let height = Math.max(body.scrollHeight,
        html.clientHeight, html.scrollHeight);
    let width = Math.max(body.scrollWidth,
        html.clientWidth, html.scrollWidth);
    let email_h = G_current_listmode_compact ? compact_email_height : preview_email_height;
    if (width < narrow_width) {
        console.log("Using narrow view, reducing emails per page...");
        email_h = G_current_listmode_compact ? compact_email_height * 1.5 : preview_email_height * 2;
    }
    height -= document.getElementById("emails").getBoundingClientRect().y + 16; // top area height plus footer
    email_h += 2;
    let per_page = Math.max(5, Math.floor(height / email_h));
    per_page -= per_page % 5;
    console.log("Viewport is %ux%u. We can show %u emails per page".format(width, height, per_page));
    return per_page;
}

function listview_flat(json, start) {
    let list = document.getElementById('emails');
    list.innerHTML = "";

    let s = start || 0;
    let n;
    if (json.emails && json.emails.length) {
        for (n = s; n < (s + G_current_per_page); n++) {
            let z = json.emails.length - n - 1; // reverse order by default
            if (json.emails[z]) {
                let item = listview_flat_element(json.emails[z], z);
                list.inject(item);

                // Hidden placeholder for expanding email(s)
                let placeholder = new HTML('div', {
                    class: G_chatty_layout ? 'email_placeholder_chatty' : 'email_placeholder',
                    id: 'email_%u'.format(z)
                });
                list.inject(placeholder);
            }
        }
    } else {
        list.inject(txt("No emails found..."));
    }
}

function listview_flat_element(eml, idx) {

    let link_wrapper = new HTML('a', {
        href: 'thread/%s'.format(eml.id),
        onclick: 'return(expand_email_threaded(%u, true));'.format(idx)
    });

    let element = new HTML('div', {
        class: G_current_listmode_compact ? "listview_email_compact" : "listview_email_flat"
    }, " ");

    // Add gravatar
    let gravatar = new HTML('img', {
        class: "gravatar",
        src: GRAVATAR_URL.format(eml.gravatar)
    });
    element.inject(gravatar);


    // Add author
    let authorName = eml.from.replace(/\s*<.+>/, "").replace(/"/g, '');
    let authorEmail = eml.from.match(/\s*<(.+@.+)>\s*/);
    if (authorName.length == 0) authorName = authorEmail ? authorEmail[1] : "(No author?)";
    let author = new HTML('span', {
        class: "listview_email_author"
    }, authorName);
    element.inject(author);

    // reasons to show the list name
    let showList = G_current_domain == 'inbox' || G_current_list == '*' || G_current_domain == '*';

    // If space and needed, inject ML name
    if (!G_current_listmode_compact && showList) {
        author.style.lineHeight = '16px';
        author.inject(new HTML('br'));
        author.inject(new HTML('span', {
            class: "label label-primary",
            style: "font-style: italic; font-size: 1rem;"
        }, eml.list_raw.replace(/[<>]/g, '').replace('.', '@', 1)));
    }

    // Combined space for subject + body teaser
    let as = new HTML('div', {
        class: 'listview_email_as'
    });

    let suba = new HTML('a', {}, eml.subject === '' ? '(No subject)' : eml.subject);
    if (G_current_listmode_compact && showList) {
        let kbd = new HTML('kbd', {
            class: 'listview_kbd'
        }, eml.list_raw.replace(/[<>]/g, '').replace('.', '@', 1))
        suba = [kbd, suba];
    }
    let subject = new HTML('div', {
        class: 'listview_email_subject email_unread'
    }, suba);
    as.inject(subject);
    if (!G_current_listmode_compact) { // No body in compact mode
        let body = new HTML('div', {
            class: 'listview_email_body'
        }, eml.body);
        as.inject(body);
    }

    element.inject(as);

    // Labels
    let labels = new HTML('div', {
        class: 'listview_email_labels'
    });

    let date = new Date(eml.epoch * 1000.0);
    let now = new Date();

    let dl = new HTML('span', {
        class: 'label label-default'
    }, date.ISOBare());
    if (now - date < 86400000) {
        dl.setAttribute("class", "label label-primary");
    }
    labels.inject(dl);

    element.inject(labels);
    link_wrapper.inject(element);

    return link_wrapper;
}