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
        current_json = json;
    }
    current_state = state;
    async_escrow['rendering'] = new Date();
    if (!state || state.update_calendar !== false) {
        renderCalendar(json.firstYear, json.firstMonth, json.lastYear, json.lastMonth, json.active_months);
    }
    // sort threads by date
    if (isArray(json.thread_struct)) {
        current_json.thread_struct.sort((a, b) => last_email(a) - last_email(b));
    }
    listview_header(state, json);
    if (current_listmode == 'threaded') {
        listview_threaded(json, 0);
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
 * - pony mail list DB (api/pminfo.lua)
 * - emails from this list (api/stats.lua)
 * When done, we create the scaffolding and list view
 */
function primeListView(state) {
    console.log("Priming user interface for List View..");
    state = state || {};
    state.prime = true;
    GET('%sapi/preferences.lua'.format(apiURL), init_preferences, state);
}

// callback from when prefs have loaded
function post_prime(state) {
    let sURL = '%sapi/stats.lua?list=%s&domain=%s'.format(apiURL, current_list, current_domain);
    if (current_year && current_month) {
        sURL += "&d=%u-%u".format(current_year, current_month);
    }
    if (!(state && state.search)) {
        if (state && state.array) {
            collated_json = {};
            virtual_inbox_loading = true;
            for (var i = 0; i < state.array.length; i++) {
                let list = state.array[i].split('@');
                sURL = '%sapi/stats.lua?list=%s&domain=%s'.format(apiURL, list[0], list[1]);
                GET(sURL, render_virtual_inbox, state);
            }
        } else {
            GET(sURL, renderListView, state);
        }
    } else {
        search(state.query, state.date);
    }
}


function parseURL(state) {
    let bits = window.location.search.substr(1).split(":", 3);
    let list = bits[0];
    let month = bits[1];
    let query = bits[2];
    let list_array = null;
    state = state || {};
    current_query = query || "";
    current_month = 0;
    current_year = 0;

    // If "month" (year-month) is specified,
    // we should set the current vars
    if (month) {
        try {
            let dbits = month.split("-");
            current_year = dbits[0];
            current_month = dbits[1];
        } catch (e) {}
    }
    // Is this a valid list?
    if (list !== '') {
        // multi-list??
        if (list.match(/,/)) {
            state.array = list.split(',');
            current_domain = 'inbox';
            current_list = 'virtual';
        } else {
            let lbits = list.split("@");
            if (lbits.length > 1) {
                current_list = lbits[0];
                current_domain = lbits[1];
            } else {
                current_domain = lbits;
                current_list = '';
            }
        }
    }
    // Are we initiating a search?
    if (query) {
        state.search = true;
        state.query = query;
        state.date = month;
    }
    // If hitting the refresh button, don't refresh preferences, just do the search.
    if (state.noprefs) {
        post_prime(state);
    } else {
        primeListView(state);
    }
};



// Parse a permalink and fetch the thread
function parse_permalink() {
    // message id is the bit after the last /
    let mid = location.href.split('/').pop();
    init_preferences(); // blank call to load defaults like social rendering
    GET('%sapi/preferences.lua'.format(apiURL), init_preferences, null);
    // Fetch the thread data and pass to build_single_thread
    GET('%sapi/thread.lua?id=%s'.format(apiURL, mid), construct_single_thread, {
        cached: true
    });
}


// Virtual inbox ŕendering
function render_virtual_inbox(state, json) {
    if (json) {
        collated_json.emails = collated_json.emails || [];
        collated_json.thread_struct = collated_json.thread_struct || [];
        for (var i = 0; i < json.emails.length; i++) {
            collated_json.emails.push(json.emails[i]);
        }
        for (var i = 0; i < json.thread_struct.length; i++) {
            collated_json.thread_struct.push(json.thread_struct[i]);
        }
    }

    for (var k in async_escrow) {
        return;
    }

    if (true) {
        console.log("Rendering multi-list")
        current_json = collated_json;
        current_json.participants = [];

        async_escrow['rendering'] = new Date();
        if (!state || state.update_calendar !== false) {
            renderCalendar(json.firstYear, json.firstMonth, json.lastYear, json.lastMonth, json.active_months);
        }
        // sort threads by date
        if (isArray(json.thread_struct)) {
            current_json.thread_struct.sort((a, b) => last_email(a) - last_email(b));
        }
        listview_header(state, current_json);
        if (current_listmode == 'threaded') {
            listview_threaded(current_json, 0);
        } else {
            listview_flat(current_json, 0);
        }

        sidebar_stats(current_json); // This comes last, takes the longest with WC enabled.
        delete async_escrow['rendering'];
    }
}
