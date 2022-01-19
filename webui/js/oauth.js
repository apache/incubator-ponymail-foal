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

// Sometimes we don't need ponymail.js, so let's redefine GetAsync here
function GetAsync(theUrl, xstate, callback) {
    let xmlHttp = null;
    if (window.XMLHttpRequest) {
        xmlHttp = new XMLHttpRequest();
    } else {
        xmlHttp = new ActiveXObject("Microsoft.XMLHTTP");
    }
    if (pm_config.URLBase && pm_config.URLBase.length > 0) {
        theUrl = pm_config.URLBase + theUrl
        theUrl = theUrl.replace(/\/+/g, "/")
    }
    xmlHttp.open("GET", theUrl, true);
    xmlHttp.send(null);
    xmlHttp.onreadystatechange = function(state) {
        if (xmlHttp.readyState == 4 && xmlHttp.status == 200) {
            if (callback) {
                try {
                    callback(JSON.parse(xmlHttp.responseText), xstate);
                } catch (e) {
                    callback(JSON.parse(xmlHttp.responseText), xstate)
                }
            }

        }
        if (xmlHttp.readyState == 4 && xmlHttp.status == 404) {
            alert("404'ed: " + theUrl)
        }
    }
}

// redirect to the oauth provider
function oauthPortal(key) {
    let ot = pm_config.oauth[key]
    let state = parseInt(Math.random()*1000000000) + '' + parseInt(Math.random()*1000000000)
    // google is different (as usual)
    if (key == 'google') {
        location.href = ot.oauth_portal + 
            "?state=" + state + 
            "&client_id=" + encodeURIComponent(ot.client_id ? ot.client_id : "") + 
            "&response_type=id_token&scope=email&redirect_uri=" + encodeURIComponent(window.location)
    } else {
        let cid = ""
        if (ot.construct) {
            for (let k in ot) {
                cid += "&" + k + "=" + encodeURIComponent(ot[k])
            }
        }
        location.href = ot.oauth_portal + 
            "?state=" + state + 
            "&redirect_uri=" + encodeURIComponent(window.location + "?key=" + key + "&state=" + state) + 
            cid
    }
}

// Callback for oauth response from backend. if okay, send user back to front
// page.
function parseOauthResponse(json) {
    if (json.okay) {
        console.log('Checking for origin URL');
        if (window.sessionStorage) {
            let url = window.sessionStorage.getItem('ponymail_oauth_origin');
            console.log('Origin is ', url);
            if (url && url.length > 0) {
                location.href = url;
                return
            }
        }
        console.log("No origin found, defaulting to ./");
        location.href = "./" // TODO: Return to whence we came...
    } else {
        popup("Oauth failed", "Authentication failed: " + json.msg)
    }
}


// Func for rendering all available oauth options
function oauthOptions() {
    // get the oauth div
    let oobj = document.getElementById('oauthtypes') 
    oobj.innerHTML = ""
    // For each enabled oauth plugin, list it.
    for (let key in pm_config.oauth) {
        let ot = pm_config.oauth[key]
        if (true) { // dunno why this is here, but whatever.
            let img = document.createElement('img')
            img.setAttribute("src", "images/oauth_" + key + ".png")
            img.setAttribute("title", "Log on with " + ot.name)
            img.setAttribute("onclick", "oauthPortal('" + key + "');")
            img.style.cursor = "pointer"
            img.style.width = "250px"
            oobj.appendChild(img)
            oobj.appendChild(document.createElement('br'))
            oobj.appendChild(document.createTextNode(' '))
            oobj.appendChild(document.createElement('br'))
        }
    }

}

// onLoad function for oauth. If args (query string or bookmark) are supplied,
// we pass that on to the backend, otherwise show which oauth options are
// enabled.
function oauthWelcome(args) {
    // google auth sometimes uses bookmarks instead of passing the code as a
    // query string arg.
    if (!args || args.length == 0) {
        args = window.location.hash.substring(1)
    } else {
        // Disable title and back button while logging in...
        document.getElementById('oauth_title').style.display = "none";
        document.getElementById('oauth_regrets').style.display = "none";
    }
    // Is this a callback from an oauth provider? If so, run the oauth stuff
    if (args && args.length >= 40) {
        let key = args.match(/key=([a-z]+)/i)
        if (key) {
            key = key[1]
        }
        if (args.match(/id_token=/)) {
            key = 'google'
            args += "&key=google";
        }
        if (key && key.length > 0 && pm_config.oauth[key]) {
            document.getElementById('oauthtypes').innerHTML = "Logging you in, hang on..!"
            GetAsync(G_apiURL + "api/oauth.lua?" + args + "&oauth_token=" + pm_config.oauth[key].oauth_url, {}, parseOauthResponse)
        } else {
            alert("Key missing or invalid! " + key)
        }
    // Not a callback, let's just show which oauth/persona options are enabled.
    } else {
        oauthOptions();
        window.sessionStorage.setItem('ponymail_oauth_origin', document.referrer);
    }
}