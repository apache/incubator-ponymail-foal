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

function listview_treeview(json, start) {
    let list = document.getElementById('emails');
    list.innerHTML = "";
    let s = start || 0;
    let email_ordered = [];
    for (let thread of json.thread_struct) {
        let eml = find_email(thread.tid);
        if (eml) email_ordered.push(eml);
        for (let child of thread.children) {
            let eml = find_email(child.tid);
            if (eml) email_ordered.push(eml);
        }
    }
    if (email_ordered.length) {
        for (let n = s; n < (s + G_current_per_page); n++) {
            let z = email_ordered.length - n - 1; // reverse order by default
            if (email_ordered[z]) {
                let item = listview_flat_element(email_ordered[z], z);
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
