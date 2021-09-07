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

function calc_per_page() {
    // Figure out how many emails per page
    let body = document.body;
    let html = document.documentElement;
    let height = Math.max( body.scrollHeight, 
                       html.clientHeight, html.scrollHeight);
    let width = Math.max( body.scrollWidth, 
                       html.clientWidth, html.scrollWidth);
    let email_h = 40;
    console.log("window area: %ux%u".format(width, height));
    if (width < 600) { console.log("Using narrow view, halving emails per page..."); email_h = 80;}
    height -= 180;
    let per_page = Math.max(5, Math.floor(height / email_h));
    per_page -= per_page % 5;
    return per_page;
}

function listview_flat(json, start) {
    let list = document.getElementById('emails');
    list.innerHTML = "";
    let per_page = calc_per_page();
    
    let s = start || 0;
    if (json.emails && json.emails.length) {
        for (n = s; n < (s+per_page); n++ ) {
            let z = json.emails.length - n - 1; // reverse order by default
            if (json.emails[z]) {
                let item = listview_flat_element(json.emails[z], z);
                list.inject(item);
                
                // Hidden placeholder for expanding email(s)
                let placeholder = new HTML('div', {class: chatty_layout ? 'email_placeholder_chatty' : 'email_placeholder', id: 'email_%u'.format(z)});
                list.inject(placeholder);
            }
        }
    } else {
        list.inject(txt("No emails found..."));
    }
}

function listview_flat_element(eml, idx) {
    
    let link_wrapper = new HTML('a', {href:'thread/%s'.format(eml.id), onclick:'return(expand_email_threaded(%u, true));'.format(idx)});
    
    let element = new HTML('div', { class: "listview_email_flat"}, " ");
    let date = new Date(eml.epoch*1000.0);
    let now = new Date();
    
    // Add gravatar
    let gravatar = new HTML('img', { class:"gravatar", src: "https://secure.gravatar.com/avatar/%s.png?s=96&r=g&d=mm".format(eml.gravatar)});
    element.inject(gravatar);
    
    
    // Add author
    let authorName = eml.from.replace(/\s*<.+>/, "").replace(/"/g, '');
    let authorEmail = eml.from.match(/\s*<(.+@.+)>\s*/);
    if (authorName.length == 0) authorName = authorEmail ? authorEmail[1] : "(No author?)";
    let author = new HTML('span', { class: "listview_email_author"}, authorName);
    element.inject(author);
    
    
    // Combined space for subject + body teaser
    let as = new HTML('div', {class: 'listview_email_as'});
    
    let suba = new HTML('a', {}, eml.subject === '' ? '(No subject)' : eml.subject);
    let subject = new HTML('div', {class: 'listview_email_subject email_unread'}, suba);
    as.inject(subject);
    
    let body = new HTML('div', {class: 'listview_email_body'}, eml.body);
    as.inject(body);
    
    element.inject(as);
    
    // Labels
    let labels = new HTML('div', {class: 'listview_email_labels'});
    let dl = new HTML('span', { class: 'label label-default'}, date.ISOBare());
    if (now - date < 86400000) {
        dl.setAttribute("class", "label label-primary");
    }
    labels.inject(dl);
    
    element.inject(labels);
    link_wrapper.inject(element);
    
    return link_wrapper;
}
