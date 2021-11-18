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

function calc_email_width() {
    // Figure out how many emails per page
    let body = document.body;
    let html = document.documentElement;
    let width = Math.max(body.scrollWidth, body.offsetWidth,
        html.clientWidth, html.scrollWidth, html.offsetWidth);
    return width;
}

function listview_threaded(json, start) {
    let list = document.getElementById('emails');
    list.innerHTML = "";

    let s = start || 0;
    if (json.thread_struct && json.thread_struct.length) {
        for (let n = s; n < (s + current_per_page); n++) {
            let z = json.thread_struct.length - n - 1; // reverse order by default
            if (json.thread_struct[z]) {
                let item = listview_threaded_element(json.thread_struct[z], z);
                list.inject(item);
                // Hidden placeholder for expanding email(s)
                let placeholder = new HTML('div', {
                    class: chatty_layout ? 'email_placeholder_chatty' : 'email_placeholder',
                    id: 'email_%u'.format(z)
                });
                list.inject(placeholder);
            }
        }
    } else {
        list.inject(txt("No emails found..."));
    }
}

function find_email(id) {
    let json = current_json;
    for (let i = 0; i < json.emails.length; i++) {
        if (json.emails[i].id == id) return json.emails[i];
    }
    return null;
}

function count_replies(thread) {
    let reps = 0;
    if (isArray(thread.children)) {
        for (let i = 0; i < thread.children.length; i++) {
            if (thread.children[i].tid == thread.tid) reps--;
            if (true) {
                reps++;
                reps += count_replies(thread.children[i]);
            }
        }
    }
    return reps;
}

function count_people(thread, hash) {
    let ppl = hash || {};
    let eml = find_email(thread.tid);
    if (eml) ppl[eml.from] = true;
    if (isArray(thread.children)) {
        for (let i = 0; i < thread.children.length; i++) {
            if (true) {
                count_people(thread.children[i], ppl);
            }
        }
    }
    let n = 0;
    for (let _ in ppl) n++;
    return n;
}


function last_email(thread) {
    let newest = thread.epoch;
    if (isArray(thread.children)) {
        for (let i = 0; i < thread.children.length; i++) {
            newest = Math.max(newest, last_email(thread.children[i]));
        }
    }
    return newest;
}



function listview_threaded_element(thread, idx) {
    let eml = find_email(thread.tid);
    if (!eml) {
        return;
    }

    let link_wrapper = new HTML('a', {
        href: 'thread/%s'.format(eml.id),
        onclick: 'return(expand_email_threaded(%u));'.format(idx)
    });

    let element = new HTML('div', {
        class: "listview_email_flat"
    }, " ");
    let date = new Date(eml.epoch * 1000.0);
    let now = new Date();

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

    // If needed, inject ML name
    if (current_domain == 'inbox' || current_list == '*') {
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
    if (current_json.list.match(/\*/) || current_json.domain == '*') {
        let kbd = new HTML('kbd', {
            class: 'listview_kbd'
        }, eml.list_raw.replace(/[<>]/g, '').replace('.', '@', 1))
        suba = [kbd, suba];
    }
    let subject = new HTML('div', {
        class: 'listview_email_subject email_unread'
    }, suba);
    as.inject(subject);

    let body = new HTML('div', {
        class: 'listview_email_body'
    }, eml.body);
    as.inject(body);

    element.inject(as);

    // Labels
    let labels = new HTML('div', {
        class: 'listview_email_labels'
    });


    // Participants
    let ppl = count_people(thread);
    let ptitle = (ppl == 1) ? "one participant" : "%u participants".format(ppl);
    let people = new HTML('span', {
        class: 'label label-default',
        title: ptitle
    }, [
        new HTML('span', {
            class: 'glyphicon glyphicon-user'
        }, ' '),
        " %u".format(ppl)
    ]);
    labels.inject(people);

    // Replies
    let reps = count_replies(thread);
    let rtitle = (reps == 1) ? "one reply" : "%u replies".format(reps);
    let repl = new HTML('span', {
        class: 'label label-default',
        title: rtitle
    }, [
        new HTML('span', {
            class: 'glyphicon glyphicon-envelope'
        }, ' '),
        " %u".format(reps)
    ]);
    labels.inject(repl);

    // Date
    date = new Date(last_email(thread) * 1000.0);
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
