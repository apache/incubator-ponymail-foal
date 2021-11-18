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

// logout: log out a user
// call the logout URL, then refresh this page - much simple!
function logout() {
    GET("%sapi/preferences.lua?logout=true".format(G_apiURL), () => location.href = document.location);
}

function init_preferences(state, json) {
    G_ponymail_preferences = json || {};
    // First, load session local settings, if possible
    if (G_can_store) {
        let local_preferences = window.localStorage.getItem('G_ponymail_preferences');
        if (local_preferences) {
            let ljson = JSON.parse(local_preferences);
            if (ljson.G_chatty_layout !== undefined) {
                G_chatty_layout = ljson.G_chatty_layout;
            }
        }
    }

    // color some links
    let cl = document.getElementById('chatty_link');
    if (cl) {
        cl.setAttribute("class", G_chatty_layout ? "enabled" : "disabled");
    }

    if (G_ponymail_preferences.login && G_ponymail_preferences.login.credentials) {
        let prefsmenu = document.getElementById('prefs_dropdown');
        let uimg = document.getElementById('uimg');
        uimg.setAttribute("src", "images/user.png");
        uimg.setAttribute("title", "Logged in as %s".format(G_ponymail_preferences.login.credentials.fullname));

        // Generate user menu
        prefsmenu.innerHTML = "";


        let logout = new HTML('a', {
            href: "javascript:void(logout());"
        }, "Log out");
        let li = new HTML('li', {}, logout)
        prefsmenu.inject(li);

    } else {
        let prefsmenu = document.getElementById('prefs_dropdown');
        if (prefsmenu) {
            prefsmenu.innerHTML = "";
            let login = new HTML('a', {
                href: "javascript:location.href='oauth.html';"
            }, "Log In");
            let li = new HTML('li', {}, login)
            prefsmenu.inject(li);
        }
    }

    if (json) {
        listview_list_lists(state, json);
        if (state && state.prime) {
            // If lists is accessible, show it
            if (json.lists[G_current_domain] && (G_current_list == '*' || json.lists[G_current_domain][G_current_list] != undefined)) {
                post_prime(state);
            } else if  (G_current_domain == '*') { // assume a match
                post_prime(state);
            } else { // otherwise, bork
                if (G_current_list.length > 0 && (!json.lists[G_current_domain] || Object.keys(json.lists[G_current_domain]).length > 0)) {
                    let eml = document.getElementById('emails');
                    eml.innerText = "We couldn't find this list. It may not exist or require you to be logged in with specific credentials.";
                    eml.inject(new HTML('br'));
                    eml.inject(new HTML('a', {
                        href: 'oauth.html',
                        onclick: 'location.href="oauth.html";'
                    }, "Click here to log in via OAuth"));
                } else {
                    switch_project(G_current_domain);
                }
            }
        }
    }
}

function save_preferences() {
    if (G_can_store) {
        let ljson = {
            G_chatty_layout: G_chatty_layout
        };
        let lstring = JSON.stringify(ljson);
        window.localStorage.setItem('G_ponymail_preferences', lstring);
        console.log("Saved local preferences");
    }
}


function set_theme(theme) {
    G_current_listmode = theme;
    renderListView(G_current_state, G_current_json);
    save_preferences();
}

function set_skin(skin) {
    G_chatty_layout = !G_chatty_layout;
    let cl = document.getElementById('chatty_link');
    if (cl) {
        cl.setAttribute("class", G_chatty_layout ? "enabled" : "disabled");
    }
    hideWindows(true);
    renderListView(G_current_state, G_current_json);
    save_preferences();
}

// set_skin, but for permalinks
function set_skin_permalink(skin) {
    G_chatty_layout = !G_chatty_layout;
    let cl = document.getElementById('chatty_link');
    if (cl) {
        cl.setAttribute("class", G_chatty_layout ? "enabled" : "disabled");
    }
    hideWindows(true);
    save_preferences();
    parse_permalink();
}
