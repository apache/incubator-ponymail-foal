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


console.log("/******* Apache Pony Mail (Foal v/%s) Initializing ********/".format(PONYMAIL_VERSION))

// Adjust titles:
document.title = prefs.title;
for (let title of document.getElementsByClassName("title")) {
    title.innerText = prefs.title;
}

console.log("Initializing escrow checks");
window.setInterval(escrow_check, 250);

console.log("Initializing key command logger");
window.addEventListener('keyup', keyCommands);

window.addEventListener('load', function() {
    let powered_by = "Powered by Apache Pony Mail (Foal v/%s ~%s)".format(PONYMAIL_VERSION, PONYMAIL_REVISION);
    let pb = document.getElementById("powered_by");
    if (pb) {
        pb.innerHTML = powered_by
    }
    document.body.appendChild(new HTML('footer', {
        class: 'footer hidden-xs'
    }, [
        new HTML('div', {
            class: 'container'
        }, [
            new HTML('p', {
                class: 'muted'
            }, powered_by)
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
