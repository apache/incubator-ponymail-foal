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


// Generic modal function
function modal(title, msg, type, isHTML) {
    let modalId = document.getElementById('modal');
    let text = document.getElementById('modal_text');
    if (modalId == undefined) {
        text = new HTML('p', {
            id: 'modal_text'
        }, "");
        modalId = new HTML('div', {
            id: 'modal'
        }, [
            new HTML('div', {
                id: 'modal_content'
            }, [
                new HTML('span', {
                    id: 'modal_close',
                    onclick: 'document.getElementById("modal").style.display = "none";'
                }, 'X'),
                new HTML('h2', {
                    id: 'modal_title'
                }, title),
                new HTML('div', {}, text)
            ])
        ]);
        document.body.appendChild(modalId);

    }
    if (type) {
        modalId.setAttribute("class", "modal_" + type);
    } else {
        modalId.setAttribute("class", undefined);
    }
    modalId.style.display = 'block';
    document.getElementById('modal_title').innerText = title;
    // If we trust HTML, use it. Otherwise only show as textNode.
    if (isHTML) {
        text.innerHTML = msg;
    } else {
        msg = msg.replace(/<.*?>/g, ""); // strip HTML tags
        text.innerText = msg;
    }
}

// Helper for determining if an email is open or not...
function anyOpen() {
    let open = (G_current_email_idx !== undefined) ? true : false;
    console.log("Emails open? " + open);
    return open;
}

// Helper function for hiding windows and open tabs
// Hide previous action on first escape, hide everything on second escape
function hideWindows(force_all) {

    // First, check if we want to hide a modal
    let modalId = document.getElementById('modal');
    if (modalId && modalId.style.display == 'block') {
        modalId.style.display = 'none';
        if (force_all !== true) return;
    }

    // RThen, check if we want to hide a composer modal
    let cmodal = document.getElementById('composer_modal');
    if (cmodal && cmodal.style.display == 'block') {
        cmodal.style.display = 'none';
        if (force_all !== true) return;
    }

    // Check Advanced Search
    let as = document.getElementById('advanced_search');
    if (as && as.style.display == 'block') {
        as.style.display = 'none';
        if (force_all !== true) return;
    }

    // Check for individually opened email
    if (G_current_email_idx !== undefined) {
        console.log("Hiding placeholder at index %u".format(G_current_email_idx));
        let placeholder = document.getElementById('email_%u'.format(G_current_email_idx));
        if (placeholder) {
            placeholder.style.display = 'none';
        }
        G_current_email_idx = undefined; // undef this even if we can't find the email
        if (force_all !== true) return;
    }

    // if viewing a single thread, disregard the collapses below - the won't make sense!
    if (location.href.match(/thread(?:\.html)?/)) return;

    // Finally, check for other opened emails, close 'em all
    let placeholders = document.getElementsByClassName('email_placeholder');
    for (let placeholder of placeholders) {
        if (placeholder.style.display == 'block') {
            console.log("Hiding placeholder %s".format(placeholder.getAttribute('id')));
            placeholder.style.display = 'none';
            // Reset scroll cache
            try {
                window.scrollTo(0, 0);
            } catch (e) {}
        }
    }

    placeholders = document.getElementsByClassName('email_placeholder_chatty');
    for (let placeholder of placeholders) {
        if (placeholder.style.display == 'block') {
            console.log("Hiding placeholder %s".format(placeholder.getAttribute('id')));
            placeholder.style.display = 'none';
            // Reset scroll cache
            try {
                window.scrollTo(0, 0);
            } catch (e) {}
        }
    }

}

// Show keyboard commands
function showHelp() {
    modal("Keyboard shortcuts:", "<pre><kbd>H</kbd>: Show this help window.\n<kbd>C</kbd>: Compose a new email to this list.\n<kbd>R</kbd>: Reply to the currently active thread.\n<kbd>S</kbd>: Go to the search bar.\n<kbd>Escape</kbd>: Hide modals or collapse threads.\n<kbd>RightArrow</kbd>: Go to next bunch of emails in list view.\n<kbd>LeftArrow</kbd>: Go to previous bunch of emails in list view.</pre>", "help", true);
}

// Function for capturing and evaluating key strokes
// If it matches a known shortcut, execute that then..
function keyCommands(e) {
    if (!e.ctrlKey) {
        // Get calling element and its type
        let target = e.target || e.srcElement;
        let type = target.tagName;
        // We won't jump out of an input field!
        if (['INPUT', 'TEXTAREA', 'SELECT'].has(type)) {
            return;
        }
        switch (e.key) {
            case 's':
                document.getElementById('q').focus();
                return;
            case 'h':
                showHelp();
                return;
            case 'c':
                compose_email(null, `${G_current_list}@${G_current_domain}`);
                return;
            case 'r':
                console.log(G_current_open_email);
                if (G_current_open_email && G_full_emails[G_current_open_email]) {
                    compose_email(G_current_open_email);
                }
                return;
            case 'Escape':
                hideWindows();
                return;
            case 'ArrowRight': // quick-next
                if (G_current_json) { // IF list view...
                    let blobs = G_current_json.emails;
                    if (G_current_listmode == 'threaded') blobs = G_current_json.thread_struct;
                    let no_emails = blobs.length;
                    if (G_current_email_idx == undefined && G_current_json && (G_current_index_pos + G_current_per_page) < no_emails) {
                        listview_header({
                            pos: G_current_index_pos + G_current_per_page
                        }, G_current_json);
                    }
                }
                return;
            case 'ArrowLeft': // quick previous
                if (G_current_json) { // IF list view...
                    if (G_current_email_idx == undefined && G_current_json && (G_current_index_pos - G_current_per_page) >= 0) {
                        listview_header({
                            pos: G_current_index_pos - G_current_per_page
                        }, G_current_json);
                    }
                }
                return;
        }

    }
}

// swipe left/right for next/previous page on mobile
function ponymail_swipe(event) {
    // Only accept "big" swipes
    let len = Math.abs(event.detail.swipestart.coords[0] - event.detail.swipestop.coords[0]);
    let direction = event.detail.swipestart.coords[0] > event.detail.swipestop.coords[0] ? 'left' : 'right';
    console.log("swipe %s of %u pixels detected".format(direction, len));
    if (len < 20) return false;
    if (direction == 'right') {
        if (G_current_json) { // IF list view...
            if (G_current_email_idx == undefined && G_current_json && (G_current_index_pos - G_current_per_page) >= 0) {
                listview_header({
                    pos: G_current_index_pos - G_current_per_page
                }, G_current_json);
            }
        }
    } else if (direction == 'left') {
        if (G_current_json) { // IF list view...
            let blobs = G_current_json.emails;
            if (G_current_listmode == 'threaded') blobs = G_current_json.thread_struct;
            let no_emails = blobs.length;
            if (G_current_email_idx == undefined && G_current_json && (G_current_index_pos + G_current_per_page) < no_emails) {
                listview_header({
                    pos: G_current_index_pos + G_current_per_page
                }, G_current_json);
            }
        }
    }
    return false;
}
