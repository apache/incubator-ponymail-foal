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

function search(query, date) {
    let list = current_list;
    let global = false;
    let domain = current_domain;
    if (ponymail_search_list == 'global') {
        list = '*';
        domain = '*';
        global = true;
    }
    if (ponymail_search_list == 'domain') {
        list = '*';
        global = true;
    }
    let sURL = '%sapi/stats.lua?d=%s&list=%s&domain=%s&q=%s'.format(apiURL, date, list, domain, query);
    GET(sURL, renderListView, {
        search: true,
        global: global
    });
    let listid = '%s@%s'.format(list, domain);
    let newhref = "list?%s:%s:%s".format(listid, date, query);
    if (location.href !== newhref) {
        window.history.pushState({}, null, newhref);
    }

    listview_list_lists({
        url: sURL,
        search: true,
        query: query
    });
    hideWindows(true);
    document.getElementById('q').value = query;
    return false;
}

// set the list(s) to search, update links
function search_set_list(what) {
    ponymail_search_list = what;
    let links = document.getElementsByClassName('searchlistoption');
    let whatxt = "this list"
    for (var i = 0; i < links.length; i++) {
        let el = links[i];
        if (el.getAttribute("id").match(what)) {
            el.setAttribute("class", "searchlistoption checked");
            whatxt = el.innerText.toLowerCase();
        } else {
            el.setAttribute("class", "searchlistoption");
        }
    }
    document.getElementById('q').setAttribute("placeholder", "Search %s...".format(whatxt));
}