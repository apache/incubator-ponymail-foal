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

 /* jshint -W097 */
'use strict';

const PONYMAIL_VERSION = "1.0.1"; // Current version of Pony Mail Foal

let apiURL = ''; // external API URL. Usually left blank.

// Stuff regarding what we're doing right now
let current_json = {};
let current_state = {};
let current_list = '';
let current_domain = '';
let current_year = 0;
let current_month = 0;
let current_quick_search = '';
let current_query = '';
let select_primed = false;
let ponymail_preferences = {};
let ponymail_search_list = 'this';

let current_listmode = 'threaded';
let ponymail_max_nesting = 10; // max nesting level before unthreading to save space

// thread state
let current_email_idx;
let chatty_layout = true;
let ponymail_date_format = {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric'
};
let collated_json = {};

if (pm_config.apiURL) {
    apiURL = pm_config.apiURL;
    console.log("Setting API URL to " + apiURL);
}

// check local storage for settings
console.log("Checking localStorage availability");
let can_store = false;
if (window.localStorage && window.localStorage.setItem) {
    try {
        window.localStorage.setItem("ponymail_test", "foo");
        can_store = true;
        console.log("localStorage available!");
    } catch (e) {
        console.log("no localStorage available!");
    }
}
