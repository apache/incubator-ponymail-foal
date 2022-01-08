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

let G_apiURL = ''; // external API URL. Usually left blank.

// Stuff regarding what we're doing right now
let G_current_json = {};
let G_current_state = {};
let G_current_list = '';
let G_current_domain = '';
let G_current_year = 0;
let G_current_month = 0;
let G_current_query = '';
let G_current_open_email = null;
let G_select_primed = false;
let G_ponymail_preferences = {};
let G_ponymail_search_list = 'this';

let G_current_listmode = 'threaded';
let G_current_listmode_compact = false;
const PONYMAIL_MAX_NESTING = 10; // max nesting level before unthreading to save space

// thread state
let G_current_email_idx;
let G_chatty_layout = true;

// emails (composer, key-commands, render-email)
let G_full_emails = {};

// listview-*.js, key-commands
let G_current_index_pos = 0;
let G_current_per_page = 0;

// sidebar calendar
const MONTHS_SHORTENED = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const CALENDAR_YEARS_SHOWN = 4; // TODO: should this be configurable?
let G_show_stats_sidebar = true; // Whether to show author stats or not

// datepicker
const DAYS_SHORTENED = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

// render_email_chatty
const PONYMAIL_DATE_FORMAT = {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric'
};
const PONYMAIL_TIME_FORMAT = { timeStyle: 'long'}; // ensure TZ is shown

let G_collated_json = {};

if (pm_config.apiURL) {
    G_apiURL = pm_config.apiURL;
    console.log("Setting API URL to " + G_apiURL);
}

// check local storage for settings
console.log("Checking localStorage availability");
let G_can_store = false;
if (window.localStorage && window.localStorage.setItem) {
    try {
        window.localStorage.setItem("ponymail_test", "foo");
        G_can_store = true;
        console.log("localStorage available!");
    } catch (e) {
        console.log("no localStorage available!");
    }
}
