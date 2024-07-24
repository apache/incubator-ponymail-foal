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

const pm_config = {
    URLBase: '',
    apiURL: '/',
    boring_lists: ['commits', 'cvs', 'site-cvs', 'security', 'notifications'], // we'd rather not default to these, noisy!
    favorite_list: 'dev', // if we have this, default to it
    long_tabs: false, // tab name format (long or short)
    LOTS_OF_LISTS: 25, // Beyond this number of list domains we start using the old phonebook.
    perm_error_postface: "" // Optional text to append to potential permission error messages
}

// Gravatar support. Defaults to using the gravatar proxy.
const GRAVATAR_URL = "/api/gravatar?md5=%s"; // This must agree with apiURL above
// TODO generate the correct URL if apiURL changes

// For performance or other reasons, this can be set to the origin by uncommenting the below:
// const GRAVATAR_URL = "https://secure.gravatar.com/avatar/%s.png?s=96&r=g&d=mm";


// Localized preferences (defaults)
const prefs = {
    subscribeLinks: false,          // Add subscribe button in stats pane?
    displayMode: 'threaded',        // threaded or flat
    groupBy: 'thread',              // thread or date
    sortOrder: 'forward',           // forward or reverse sort
    compactQuotes: true,            // Show quotes from original email as compacted blocks?
    notifications: 'direct',        // Notify on direct or indirect replies to your posts?
    hideStats: 'yes',               // Hide the email statistics window?
    theme: 'default',               // Set to 'social' to default to the social theme
    loggedIn: false,
    UTC: true,                     // Use UTC for timestamps in UI. If false, use browser local time.
    title: "Apache Pony Mail"       // Default browser window title
}
