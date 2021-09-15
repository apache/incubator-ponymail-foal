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
let prev_listview_json = {};
let prev_listview_state = {};
let current_index_pos = 0;
let current_per_page = 0;

function listview_header(state, json) {
    let list_title = json.list;
    prev_listview_json = json;
    prev_listview_state = state;
    if (current_list == 'virtual' && current_domain == 'inbox') {
        list_title = "Virtual inbox, past 30 days";
    }
    let blobs = json.emails;
    if (current_listmode == 'threaded') blobs = json.thread_struct;

    if (current_year && current_month) {
        list_title += ", %s %u".format(months[current_month - 1], current_year);
    } else {
        list_title += ", past month";
    }

    if (json.searchParams.q && json.searchParams.q.length || (json.searchParams.d || "").match(/=/)) {
        list_title = "Custom search";
    }

    document.getElementById('listview_title').innerText = list_title + ":";
    let download = new HTML('button', {
        title: 'Download as mbox archive',
        download: 'true'
    }, new HTML('span', {
        class: 'glyphicon glyphicon-save'
    }, " "));
    document.getElementById('listview_title').inject(download);
    download.addEventListener('click', () => {
        dl_url = pm_config.apiURL + 'api/mbox.lua?';
        for (let key in json.searchParams || {}) {
            dl_url += key + "=" + encodeURIComponent(json.searchParams[key]) + "&";
        }
        location.href = dl_url;
    });

    let chevrons = document.getElementById('listview_chevrons');
    let per_page = calc_per_page();
    current_per_page = per_page;
    current_index_pos = state.pos || 0;
    let first = 1;
    if (state && state.pos) {
        first = 1 + state.pos;
    }
    if (blobs.length == 0) {
        chevrons.innerHTML = "No topics to show";
    } else {
        chevrons.innerHTML = "Showing <b>%u through %u</b> of <b>%u</b> topics&nbsp;".format(first, Math.min(first + per_page - 1, blobs.length), blobs.length || 0);
    }

    let pprev = Math.max(0, first - per_page - 1);
    let cback = new HTML('button', {
        onclick: 'listview_header({pos: %u}, current_json);'.format(pprev),
        disabled: (first == 1) ? 'true' : null
    }, new HTML('span', {
        class: 'glyphicon glyphicon-chevron-left'
    }, " "));
    chevrons.inject(cback);

    let pnext = first + per_page - 1;
    let cforward = new HTML('button', {
        onclick: 'listview_header({pos: %u}, current_json);'.format(pnext),
        disabled: (first + per_page - 1 >= blobs.length) ? 'true' : null
    }, new HTML('span', {
        class: 'glyphicon glyphicon-chevron-right'
    }, " "));
    chevrons.inject(cforward);

    let crefresh = new HTML('button', {
        onclick: 'parseURL({noprefs: true});',
        title: 'Refresh results',
        style: {
            marginLeft: '8px'
        }
    }, new HTML('span', {
        class: 'glyphicon glyphicon-refresh'
    }, " "));
    chevrons.inject(crefresh);

    if (state && state.pos != undefined) {
        if (current_listmode == 'threaded') {
            listview_threaded(json, state.pos);
        } else {
            listview_flat(json, state.pos);
        }
    }

    let tm = document.getElementById('threaded_mobile_img');
    if (tm) {
        if (current_listmode == 'threaded') tm.setAttribute("src", "images/threading_enabled.png");
        else tm.setAttribute("src", "images/threading_disabled.png");
    }
}

function listview_list_lists(state, json) {
    let lists = document.getElementById('list_picker_ul');
    let searching = (state && state.search === true) ? true : false;
    if (state && state.to) {
        let tab = undefined;
        let tabs = lists.childNodes;
        for (var i = 0; i < tabs.length; i++) {
            let xtab = tabs[i];
            if ((state.to == 'search' && xtab.getAttribute('id') == 'tab_search') || (xtab.innerText == state.to || xtab.getAttribute('data-list') == state.to)) {
                tab = xtab;
                tab.setAttribute("class", state.to == 'search' ? 'search' : 'active');
            } else if (xtab.getAttribute("class") != 'list_all_narrow' && xtab.getAttribute("class") != 'others') {
                xtab.setAttribute("class", "");
            }

        }
        return;
    }
    if (!json) {
        json = ponymail_preferences;
    }
    if (lists) {
        lists.innerHTML = "";

        if (isHash(json.lists) && json.lists[current_domain]) {
            lists_sorted = [];
            for (var list in json.lists[current_domain]) {
                lists_sorted.push([list, json.lists[current_domain][list]]);
            }
            lists_sorted.sort((a, b) => b[1] - a[1]);
            let alists = [];
            for (var i = 0; i < lists_sorted.length; i++) alists.push(lists_sorted[i][0]);
            if (current_list != '*' && current_domain != '*') {
                alists.remove(current_list);
                alists.unshift(current_list);
            }
            let maxlists = (searching && 3 || 4);
            if (alists.length == maxlists + 1) maxlists++; // skip drop-down if only one additional list (#54)
            for (var i = 0; i < alists.length; i++) {
                if (i >= maxlists) break;
                let listname = alists[i];
                let listnametxt = listname;
                if (long_tabs) {
                    listnametxt = '%s@%s'.format(listname, current_domain);
                }
                let li = new HTML('li', {
                    onclick: 'switch_list(this, "tab");',
                    class: (listname == current_list && !searching) ? 'active' : null
                }, listnametxt);
                li.setAttribute("data-list", '%s@%s'.format(listname, current_domain));
                lists.inject(li);
            }

            if (alists.length > maxlists) {
                let other_lists_sorted = [];
                for (var i = maxlists; i < alists.length; i++) {
                    other_lists_sorted.push(alists[i]);
                }
                other_lists_sorted.sort();
                let li = new HTML('li', {
                    class: 'others'
                });
                let otherlists = new HTML('select', {
                    class: 'listview_others',
                    onchange: 'switch_list(this.value);'
                });
                otherlists.inject(new HTML('option', {
                    disabled: 'disabled',
                    selected: 'selected'
                }, 'Other lists (%u):'.format(other_lists_sorted.length)));
                li.inject(otherlists);
                for (var i = 0; i < other_lists_sorted.length; i++) {
                    let listname = other_lists_sorted[i];
                    let opt = new HTML('option', {
                        value: "%s@%s".format(listname, current_domain)
                    }, listname);
                    otherlists.inject(opt);
                }
                lists.inject(li);
            }
            // All lists, for narrow UI
            let all_lists_narrow = [];
            for (var i = 0; i < alists.length; i++) {
                all_lists_narrow.push(alists[i]);
            }
            all_lists_narrow.sort();
            let li = new HTML('li', {
                class: 'list_all_narrow'
            });
            let otherlists = new HTML('select', {
                class: 'listview_others',
                onchange: 'switch_list(this.value);'
            });
            otherlists.inject(new HTML('option', {
                disabled: 'disabled',
                selected: 'selected'
            }, "%s@%s".format(current_list, current_domain)));
            li.inject(otherlists);
            for (var i = 0; i < all_lists_narrow.length; i++) {
                let listname = all_lists_narrow[i];
                let opt = new HTML('option', {
                    value: "%s@%s".format(listname, current_domain)
                }, listname);
                otherlists.inject(opt);
            }
            lists.inject(li);
        }
    }
    if (searching) {
        let li = new HTML('li', {
            onclick: 'switch_list(this, "tab");',
            id: 'tab_search',
            class: 'search'
        }, "Search: %s".format(state.query));
        li.setAttribute("data-url", state.url);
        li.setAttribute("data-href", location.href);
        lists.inject(li);
    }

    // Populate the project selector
    if (isHash(json.lists)) {
        let no_projects = 0;
        let select = document.getElementById('project_select');
        if (!select || select_primed) return;
        let opts = {}
        let doms = [];
        for (var domain in json.lists) {
            let option = new HTML('option', {
                value: domain
            }, domain);
            opts[domain] = option;
            doms.push(domain);
            no_projects++;
        }
        if (no_projects > 1 || current_domain == '*') {
            select.innerHTML = "";
            let title = new HTML('option', {
                disabled: 'disabled',
                selected: 'true',
                value: ''
            }, "Available projects (%u):".format(no_projects));
            select.inject(title);
            doms.sort();
            for (var i = 0; i < doms.length; i++) {
                select.inject(opts[doms[i]]);
            }
            select.style.display = "inline-block";
            select_primed = true; // mark it primed so we don't generate it again later
        }
    }
}


function switch_project(domain) {
    // TODO: improve this
    if (ponymail_preferences && ponymail_preferences.lists[domain]) {
        // Switch to the most populous, but not commits/cvs
        let lists_sorted = [];
        for (var list in ponymail_preferences.lists[domain]) {
            lists_sorted.push([list, ponymail_preferences.lists[domain][list]]);
        }
        lists_sorted.sort((a, b) => b[1] - a[1]);
        let lists = [];
        for (var i = 0; i < lists_sorted.length; i++) lists.push(lists_sorted[i][0]);
        let listname = lists[0];
        let n = 1;
        if (lists.length > n) {
            while (boring_lists.has(listname) && lists.length > n) {
                listname = lists[n];
                n++;
            }
            if (lists.has(favorite_list)) {
                listname = favorite_list;
            }
        }
        switch_list('%s@%s'.format(listname, domain));
    } else {
        switch_list('dev@%s'.format(domain));
    }
}

function switch_list(list, from) {
    let listid = list;
    if (typeof list == 'object') {
        let dataURL = list.getAttribute('data-url');
        if (dataURL) {
            GET(dataURL, renderListView, {
                search: true,
                cached: true
            });
            let newhref = list.getAttribute('data-href');
            if (location.href !== newhref) {
                window.history.pushState({}, null, newhref);
            }
            listview_list_lists({
                to: 'search'
            });
            return;
        }
        listid = list.getAttribute("data-list") || list.innerText;
    }
    let bits = listid.split("@");
    current_list = bits[0];
    current_domain = bits[1];
    current_year = 0;
    current_month = 0;

    let newhref = "list.html?%s".format(listid);
    if (location.href !== newhref) {
        window.history.pushState({}, null, newhref);
    }

    console.log("Switching list to %s...".format(listid));
    listview_list_lists({
        to: from ? listid : undefined
    });
    post_prime({
        cached: true,
        from: from
    });
}

window.addEventListener('orientationchange', function() {
    window.setTimeout(function() {
        if (anyOpen() == false) {
            listview_header(prev_listview_state, prev_listview_json);
        }
    }, 100);
}, false);
