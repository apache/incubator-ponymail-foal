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

var ponymail_version = "1.0.1-Foal" // Current version of Pony Mail
var ponymail_name = "Pony Mail" // name of archive (set to "Foo's mail archive" or whatever)

var hits_per_page = 10;
var apiURL = ''; // external API URL. Usually left blank.

// Stuff regarding what we're doing right now
var current_json = {};
var current_state = {};
var current_list = '';
var current_domain = '';
var current_year = 0;
var current_month = 0;
var current_quick_search = '';
var select_primed = false;
var ponymail_preferences = {};
var ponymail_search_list = 'this';

var current_listmode = 'threaded';
var ponymail_max_nesting = 10; // max nesting level before unthreading to save space

// thread state
var current_email_idx = undefined;
var chatty_layout = true;
var ponymail_date_format = {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric'
};
var virtual_inbox_loading = false;
var collated_json = {};

// List auto-picker criteria
var boring_lists = ['commits', 'cvs', 'site-cvs', 'security', 'notifications']; // we'd rather not default to these, noisy!
var favorite_list = 'dev'; // if we have this, default to it
var long_tabs = false; // tab name format (long or short)

console.log("/******* Apache Pony Mail (Foal v/%s) Initializing ********/".format(ponymail_version))
// Adjust titles:
document.title = ponymail_name;
let titles = document.getElementsByClassName("title");
for (var i in titles) {
    titles[i].innerText = ponymail_name;
}

// check local storage for settings
console.log("Checking localStorage availability");
var can_store = false;
if (window.localStorage && window.localStorage.setItem) {
    try {
        window.localStorage.setItem("ponymail_test", "foo");
        can_store = true;
        console.log("localStorage available!");
    } catch (e) {
        console.log("no localStorage available!");
    }
}


console.log("Initializing escrow checks");
window.setInterval(escrow_check, 250);

console.log("Initializing key command logger");
window.addEventListener('keyup', keyCommands);

if (pm_config && pm_config.apiURL) {
    apiURL = pm_config.apiURL;
    console.log("Setting API URL to %s".format(apiURL));
}

window.addEventListener('load', function() {
    document.body.appendChild(new HTML('footer', {
        class: 'footer'
    }, [
        new HTML('div', {
            class: 'container'
        }, [
            new HTML('p', {
                class: 'muted'
            }, "Powered by Apache Pony Mail (Foal v/%s)".format(ponymail_version))
        ])
    ]));
});
console.log("initializing pop state checker");
window.onpopstate = function(event) {
    console.log("Popping state");
    return parseURL({
        cached: true
    });
};