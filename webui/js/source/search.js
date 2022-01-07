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
    let list = G_current_list;
    let global = false;
    let domain = G_current_domain;
    if (G_ponymail_search_list == 'global') {
        list = '*';
        domain = '*';
        global = true;
    }
    if (G_ponymail_search_list == 'domain') {
        list = '*';
        global = true;
    }

    let listid = '%s@%s'.format(list, domain);
    G_current_list = list;
    G_current_domain = domain;
    let newhref = "list?%s:%s:%s".format(listid, date, query);

    let header_from = document.getElementById('header_from');
    let header_subject = document.getElementById('header_subject');
    let header_to = document.getElementById('header_to');
    let header_body = document.getElementById('header_body');
    let sURL = '%sapi/stats.lua?d=%s&list=%s&domain=%s&q=%s'.format(
        G_apiURL, encodeURIComponent(date), encodeURIComponent(list), encodeURIComponent(domain), encodeURIComponent(query)
        );
    if (header_from.value.length > 0) {
        sURL += "&header_from=%s".format(encodeURIComponent(header_from.value));
        newhref += "&header_from=%s".format(header_from.value);
        header_from.value = "";
    }
    if (header_subject.value.length > 0) {
        sURL += "&header_subject=%s".format(encodeURIComponent(header_subject.value));
        newhref += "&header_subject=%s".format(header_subject.value);
        header_subject.value = "";
    }
    if (header_to.value.length > 0) {
        sURL += "&header_to=%s".format(encodeURIComponent(header_to.value));
        newhref += "&header_to=%s".format(header_to.value);
        header_to.value = "";
    }
    if (header_body.value.length > 0) {
        sURL += "&header_body=%s".format(encodeURIComponent(header_body.value));
        newhref += "&header_body=%s".format(header_body.value);
        header_body.value = "";
    }
    GET(sURL, renderListView, {
        search: true,
        global: global
    });
    if (location.href !== newhref) {
        window.history.pushState({}, null, newhref);
    }

    listview_list_lists({
        url: sURL,
        search: true,
        query: query,
        list: list,
        domain: domain
    });
    hideWindows(true);
    document.getElementById('q').value = query;
    return false;
}

// set the list(s) to search, update links
function search_set_list(what) {
    G_ponymail_search_list = what;
    let links = document.getElementsByClassName('searchlistoption');
    let whatxt = "this list"
    for (let el of links) {
        if (el.getAttribute("id").match(what)) {
            el.setAttribute("class", "searchlistoption checked");
            whatxt = el.innerText.toLowerCase();
        } else {
            el.setAttribute("class", "searchlistoption");
        }
    }
    document.getElementById('q').setAttribute("placeholder", "Search %s...".format(whatxt));
}