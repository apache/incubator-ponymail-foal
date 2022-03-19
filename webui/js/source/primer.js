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


/* List View Rendering main func */
function renderListView(state, json) {
    if (json) {
        G_current_json = json;
    }
    G_current_state = state;
    async_escrow['rendering'] = new Date();
    if (!state || state.update_calendar !== false) {
        renderCalendar({
            FY: json.firstYear,
            FM: json.firstMonth,
            LY: json.lastYear,
            LM: json.lastMonth,
            activity: json.active_months
        });
    }
    // sort threads by date
    if (isArray(json.thread_struct)) {
        G_current_json.thread_struct.sort((a, b) => last_email(a) - last_email(b));
    }
    listview_header(state, json);
    if (G_current_listmode == 'threaded') {
        listview_threaded(json, 0);
    } else if (G_current_listmode == 'treeview') {
        listview_treeview(json, 0);
    } else {
        listview_flat(json, 0);
    }

    sidebar_stats(json); // This comes last, takes the longest with WC enabled.
    delete async_escrow['rendering'];

    if (state && state.to) {
        listview_list_lists(state);
    }
}

/* Primer function for List View
 * Fetches the following:
 * - user preferences (api/preferences.lua)
 * When done, we create the scaffolding and list view
 */
function primeListView(state) {
    console.log("Priming user interface for List View..");
    state = state || {};
    state.prime = true;
    GET('%sapi/preferences.lua'.format(G_apiURL), init_preferences, state);
}

// callback from when prefs have loaded
function post_prime(state) {
    let sURL = '%sapi/stats.lua?list=%s&domain=%s'.format(G_apiURL, encodeURIComponent(G_current_list), encodeURIComponent(G_current_domain));
    if (G_current_year && G_current_month) {
        sURL += "&d=%u-%u".format(G_current_year, G_current_month);
    }
    if (!(state && state.search)) {
        if (state && state.array) {
            G_collated_json = {};
            for (let entry of state.array) {
                let list = entry.split('@');
                sURL = '%sapi/stats.lua?list=%s&domain=%s'.format(G_apiURL, encodeURIComponent(list[0]), encodeURIComponent(list[1]));
                GET(sURL, render_virtual_inbox, state);
            }
        } else {
            GET(sURL, renderListView, state);
        }
    } else {
        search(state.query, state.date);
    }
}

// onload function for list.html
function parseURL(state) {
    console.log("Running ParseURL");
    console.log(state);
    let bits = window.location.search.substring(1).split(":", 3);
    let list = bits[0];
    let month = bits[1];
    let query = bits[2];
    state = state || {};
    G_current_query = query || "";
    G_current_month = 0;
    G_current_year = 0;

    // If "month" (year-month) is specified,
    // we should set the current vars
    if (month) {
        try {
            let dbits = month.split("-");
            G_current_year = dbits[0];
            G_current_month = dbits[1];
        } catch (e) {}
    }
    // Is this a valid list?
    if (list !== '') {
        // multi-list??
        if (list.match(/,/)) {
            state.array = list.split(',');
            G_current_domain = 'inbox';
            G_current_list = 'virtual';
        } else {
            let lbits = list.split("@");
            if (lbits.length > 1) {
                G_current_list = lbits[0];
                G_current_domain = lbits[1];
            } else {
                G_current_domain = lbits;
                G_current_list = '';
            }
        }
    }
    // Are we initiating a search?
    if (query || (month && !month.match(/^\d\d\d\d-\d+$/))) { // single-month isn't a search, but any other date marker is
        state.search = true;
        state.query = decodeURIComponent(query||"");
        state.date = month;
    }
    // If hitting the refresh button, don't refresh preferences, just do the search.
    if (state.noprefs) {
        post_prime(state);
    } else {
        primeListView(state);
    }
}



// Parse a permalink and fetch the thread
// URL is expected to be of the form /thread[.html]/<msgid>?<list.id>|find_parent=true
// onload function for thread.html
function parse_permalink() {
    // message id is the bit after the last /
    // TODO: could look for thread[.html]/ instead
    let mid = decodeURIComponent(location.pathname.split('/').pop());
    // List-ID specified?
    // query needs decodeURIComponent with '+' conversion
    const query = decodeURIComponent(location.search.substring(1).replace(/\+/g, ' '));
    let list_id = null;
    let find_parent = false;
    if (query.length) {
        if (query.match(/^<.+>$/)) {
            list_id = query;
        }
        find_parent = query == 'find_parent=true';
    }

    mid = unshortenID(mid);  // In case of old school shortened links
    init_preferences(); // blank call to load defaults like social rendering
    GET('%sapi/preferences.lua'.format(G_apiURL), init_preferences, null);
    // Fetch the thread data and pass to build_single_thread
    if (list_id) {
        GET('%sapi/thread.lua?id=%s&listid=%s'.format(G_apiURL, encodeURIComponent(mid), encodeURIComponent(list_id)), construct_single_thread, {
            cached: true
        });
    }
    else {
        let encoded_mid = encodeURIComponent(mid);
        if (find_parent) {
            GET('%sapi/thread.lua?id=%s&find_parent=true'.format(G_apiURL, encoded_mid), construct_single_thread, {
                cached: true
            });
        } else {
            GET('%sapi/thread.lua?id=%s'.format(G_apiURL, encoded_mid), construct_single_thread, {
                cached: true
            });
        }
    }
}


// Virtual inbox ŕendering
function render_virtual_inbox(state, json) {
    if (json) {
        G_collated_json.emails = G_collated_json.emails || [];
        G_collated_json.thread_struct = G_collated_json.thread_struct || [];
        for (let email of json.emails) {
            G_collated_json.emails.push(email);
        }
        for (let thread_struct of json.thread_struct) {
            G_collated_json.thread_struct.push(thread_struct);
        }
    }

    for (let _ in async_escrow) {
        return;
    }

    if (true) {
        console.log("Rendering multi-list")
        G_current_json = G_collated_json;
        G_current_json.participants = [];

        async_escrow['rendering'] = new Date();
        if (!state || state.update_calendar !== false) {
            renderCalendar({
                FY: json.firstYear,
                FM: json.firstMonth,
                LY: json.lastYear,
                LM: json.lastMonth,
                activity: json.active_months
            });
        }
        // sort threads by date
        if (isArray(json.thread_struct)) {
            G_current_json.thread_struct.sort((a, b) => last_email(a) - last_email(b));
        }
        listview_header(state, G_current_json);
        if (G_current_listmode == 'threaded') {
            listview_threaded(G_current_json, 0);
        } else if (G_current_listmode == 'treeview') {
            listview_treeview(G_current_json, 0);
        } else {
            listview_flat(G_current_json, 0);
        }

        sidebar_stats(G_current_json); // This comes last, takes the longest with WC enabled.
        delete async_escrow['rendering'];
    }
}


// hex <- base 36 conversion, reverses short links
function unshortenID(mid) {
    // all short links begin with 'Z'. If not, it's not a short link
    // so let's just pass it through unaltered if so.
    // Some old shortlinks begin with 'B', so let's be backwards compatible for now.
    // Shortlinks are also 15 chars (including prefix)
    // They should also consist of base 36 chars or '-'
    if ((mid[0] == 'Z' || mid[0] == 'B') && mid.length == 15){
        // remove padding
        let id1 = parseInt(mid.substr(1, 7).replace(/-/g, ""), 36)
        let id2 = parseInt(mid.substr(8, 7).replace(/-/g, ""), 36)
        id1 = id1.toString(16)
        id2 = id2.toString(16)

        // add 0-padding
        while (id1.length < 9) id1 = '0' + id1
        while (id2.length < 9) id2 = '0' + id2
        return id1+id2
    }
    return mid
}
