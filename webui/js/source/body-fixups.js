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

const PONYMAIL_URL_RE = new RegExp("(" + "(?:(?:[a-z]+)://)" + "(?:\\S+(?::\\S*)?@)?" + "(?:" + "([01][0-9][0-9]|2[0-4][0-9]|25[0-5])" + "|" + "(?:(?:[a-z\\u00a1-\\uffff0-9]-*)*[a-z\\u00a1-\\uffff0-9]+)" + "(?:\\.(?:[a-z\\u00a1-\\uffff0-9]-*)*[a-z\\u00a1-\\uffff0-9]+)*" + "(?:\\.(?:[a-z\\u00a1-\\uffff]{2,}))" + "\\.?" + ")" + "(?::\\d{2,5})?" + "\\/?" + "(?:[/?#]?([^,<>()\\[\\] \\t\\r\\n]|(<[^:\\s]*?>|\\([^:\\s]*?\\)|\\[[^:\\s]*?\\]))*)?" + ")\\.?" + "\\b", "mi");

// Regex for things to potentially put inside quote objects:
// - quotes
// - forwarded emails
// - inline quoting
// - top posting with original email following
const PONYMAIL_QUOTE_RE = new RegExp("(" +
    // Typical encapsulation of context by ticketing systems and/or bug trackers
    "(---\\r?\\n([^\\r\\n]*?\\r?\\n)*?---$)|" +
    "(" +
    "(?:\\r?\\n|^)" + // start of line or after a colon
    // Classic method; a signal line and the quote with '>' starting each line quoted
    "(" +
    "(" + // Initial line signalling a quote
    "((\\d+-\\d+-\\d+)\\s+.+<\\S+@\\S+>:[ \t\r\n]+)|" + // "01-02-1982 Foo Bar <foo@bar.baz>:" OR
    "(on\\s+(.+|.+\\n.+)\\s+wrote:[\r?\n]+)|" + // "On $somedate, $someone wrote:", OR...
    "(le\\s+(.+|.+\\n.+)\\s+écrit:[\r?\n]+)|" + // French version of the above, OR...
    "(.?am .+? schrieb\\s+.+:[\r?\n]+)|" + // German version of the above, OR...
    "(envoy[ée] de mon .+|sent from my .+|von meinem .+ gesendet)[ \t\r\n]+" + // "sent from my iphone/ipad/android phone/whatever", usually means the next part is a quote.
    ")" + // End initial signal line
    "(^$)*" + // Accept blank newlines following it...
    "(((^(?!>)[\\s\\S]+$)*)|(^\\s*>[\\s\\S]+$)*)" + // Either text that follows immediately after with no '>' first, OR text with '>' first, but NOT both...
    ")|" +
    "(" +
    // Lines after the signal line; comes in one shape, generally speaking...
    "(^\\s*>+[ \\t]*[^\r\n]*\r*\n+)+" + // Lines beginning with one or more '>' after the initial signal line
    ")" +
    ")+|" + //OR...
    "(" +
    "^(-{5,10}) .+? \\1[\r\n]+" + // ----- Forwarded Message -----
    "(^\\w+:\\s+.+[\r\n]+){3,10}[\r\n]+" + // Between three and ten header fields (we ask for at least 3, so as to not quote PGP blocks)
    "[\\S\\s]+" + // Whatever comes next...
    ")+" +
    ")", "mi");

// Somewhat simplified method for catching email footers/trailers that we don't need
const PONYMAIL_TRAILER_RE = new RegExp("^--[\r\n]+.*", "mi"); //(--\r?\n([^\r\n]*?\r?\n){1,6}$)|[\r\n.]+^((--+ \r?\n|--+\r?\n|__+\r?\n|--+\\s*[^\r\n]+\\s*--+\r?\n)(.*\r?\n)+)+$", "m");

// This is a regex for capturing code diff blocks in an email
const PONYMAIL_DIFF_RE = new RegExp(
    "(" +
    "^-{3} .+?[\r\n]+" + // Starts with a "--- /foo/bar/baz"
    "^\\+{3} .+?[\r\n]+" + // Then a "+++ /foo/bar/baz"
    "(" + // Then one or more of...
    "^@@@? .+[\r\n]+" + // positioning
    "(^ .*[\r\n]*$){0,3}" + // diff header
    "(^[-+ ].*[\r\n]*)+" + // actual diff
    "(^ .*[\r\n]*$){0,3}" + // diff trailer
    ")+" +
    ")", "mi");

// Function for turning URLs into <a> tags
function fixup_urls(splicer) {

    if (typeof splicer == 'object') {
        return splicer;
        //splicer = splicer.innerText;
    }
    /* Array holding text and links */
    let i, m, t, textbits, url, urls;
    textbits = [];

    /* Find the first link, if any */
    i = splicer.search(PONYMAIL_URL_RE);
    urls = 0;

    /* While we have more links, ... */
    while (i !== -1) {
        urls++;

        /* Only parse the first 250 URLs... srsly */
        if (urls > 250) {
            break;
        }

        /* Text preceding the link? add it to textbits frst */
        if (i > 0) {
            t = splicer.substr(0, i);
            textbits.push(t);
            splicer = splicer.substr(i);
        }

        /* Find the URL and cut it out as a link */
        m = splicer.match(PONYMAIL_URL_RE);
        if (m) {
            url = m[1];
            i = url.length;
            t = splicer.substr(0, i);
            textbits.push(new HTML('a', {
                href: url
            }, url));
            splicer = splicer.substr(i);
        }

        /* Find the next link */
        i = splicer.search(PONYMAIL_URL_RE);
    }

    /* push the remaining text into textbits */
    textbits.push(splicer);
    return textbits;
}


// Simple check to (attempt to) assess whether a trailer should
// remain or get cut out.
function legit_trailer(a) {
    let lines = a.split(/\s*\r?\n/);
    let first_line = lines.shift();
    while (first_line.length == 0 && lines.length) first_line = lines.shift(); // get first meaningful line
    if (!lines.length || first_line == '--') return ''; // likely a simple trailer
    let last_line = lines.pop();
    while (last_line.length == 0 && lines.length) last_line = lines.pop(); // get last meaningful line

    // Check if first and last line are similar, which is usually indictive of a ticket system
    if (last_line == first_line) {
        return a;
    }
    // Otherwise, check if first line has two or more dashes, and it occurs again later (also tix)
    if (first_line.match(/^---+/) && lines.has(first_line)) {
        return "|||" + a + "|||";
    }

    // Lastly, if there is "sufficient" length to the dashes, allow (JIRA etc)
    if (first_line.match(/^-{6,72}$/)) return a;
    return '';
}

// Function for cutting away trailers
function cut_trailer(splicer) {
    if (!G_chatty_layout) return splicer; // only invoke in social rendering mode
    if (typeof splicer == 'object') {
        splicer.innerText = splicer.innerText.replace(PONYMAIL_TRAILER_RE, legit_trailer, 3);
    } else {
        splicer = splicer.replace(PONYMAIL_TRAILER_RE, legit_trailer);

    }
    return splicer;
}

function color_diff_lines(diff) {
    let lines = diff.split(/[\r\n]+/);
    let ret = [];
    for (let z = 0; z < lines.length; z++) {
        let line = lines[z];
        let color = 'grey';
        if (line[0] == '@') color = 'blue';
        if (line[0] == '-') color = 'red';
        if (line[0] == '+') color = 'green';
        if (line[0] == ' ') color = 'black';
        let el = new HTML('span', {
            style: {
                color: color
            }
        }, line);
        ret.push(el);
        ret.push(new HTML('br'));
    }
    return ret;
}

// Function for coloring diffs
function fixup_diffs(splicer) {
    if (!G_chatty_layout) return splicer; // only invoke in social rendering mode
    if (typeof splicer == 'object') {
        splicer = splicer.innerText;
    }
    /* Array holding text and links */
    let i, m, t, diff, diffs;
    let textbits = [];

    /* Find the first link, if any */
    i = splicer.search(PONYMAIL_DIFF_RE);
    diffs = 0;

    /* While we have more links, ... */
    while (i !== -1) {
        diffs++;

        /* Only parse the first 20 diffs... srsly */
        if (diffs > 25) {
            break;
        }
        console.log(i);
        /* Text preceding the diff? add it to textbits frst */
        if (i > 0) {
            t = splicer.substr(0, i);
            textbits.push(t);
            splicer = splicer.substr(i);
        }

        /* Find the URL and cut it out as a link */
        m = splicer.match(PONYMAIL_DIFF_RE);
        if (m) {
            diff = m[1];
            i = diff.length;
            t = splicer.substr(0, i);
            textbits.push(new HTML('pre', {
                class: 'diff'
            }, color_diff_lines(diff)));
            splicer = splicer.substr(i);
        }

        /* Find the next link */
        i = splicer.search(PONYMAIL_DIFF_RE);
    }

    /* push the remaining text into textbits */
    textbits.push(splicer);
    return textbits;
}

// Function for turning quotes into quote segments
function fixup_quotes(splicer) {
    if (splicer[splicer.length - 1] !== "\n") splicer += "\n"; //tweak to make quotes match the last line if no newline on it.
    let hideQuotes, i, m, qdiv, quote, quotes, t, textbits;
    hideQuotes = true;
    if (prefs.compactQuotes === false && !G_chatty_layout) {
        hideQuotes = false;
    }
    if (!hideQuotes) return splicer; // We'll bail here for now. Dunno why not.

    /* Array holding text and quotes */
    textbits = [];

    /* Find the first quote, if any */
    i = splicer.search(PONYMAIL_QUOTE_RE);
    quotes = 0;

    /* While we have more quotes, ... */
    while (i !== -1) {
        quotes++;

        /* Only parse the first 50 quotes... srsly */
        if (quotes > 50) {
            break;
        }

        /* Text preceding the quote? add it to textbits first */
        if (i > 0) {
            t = splicer.substr(0, i);
            let diffed = fixup_diffs(cut_trailer(t));
            if (isArray(diffed)) {
                for (let z = 0; z < diffed.length; z++) textbits.push(fixup_urls(diffed[z]));
            } else textbits.push(fixup_urls(diffed));
            splicer = splicer.substr(i);
        }

        /* Find the quote and cut it out as a div */
        m = splicer.match(PONYMAIL_QUOTE_RE);
        if (m) {
            quote = m[0];
            i = quote.length;
            t = splicer.substr(0, i);
            quote = quote.replace(/(>*\s*\r?\n)+$/g, "");
            qdiv = new HTML('div', {
                "class": "email_quote_parent"
            }, [
                new HTML('button', {
                    title: "Toggle quote",
                    onclick: "toggle_quote(this)"
                }, new HTML('span', {
                    class: 'glyphicon glyphicon-comment'
                }, " ")), new HTML('br'), new HTML('blockquote', {
                    "class": "email_quote",
                    style: {
                        display: hideQuotes ? 'none' : 'block'
                    }
                }, fixup_urls(quote))
            ]);
            textbits.push(qdiv);
            splicer = splicer.substr(i);
        }

        /* Find the next quotes */
        i = splicer.search(PONYMAIL_QUOTE_RE);
    }

    /* push the remaining text into textbits */
    let diffed = fixup_diffs(cut_trailer(splicer));
    if (isArray(diffed)) {
        for (let z = 0; z < diffed.length; z++) diffed[z] = fixup_urls(diffed[z]);
    } else diffed = fixup_urls(diffed);
    textbits.push(new HTML('span', {}, diffed));

    return textbits;
}

function toggle_quote(el) {
    let quote = el.parentNode.childNodes[2];
    if (quote.style.display != 'block') {
        quote.style.display = 'block';
    } else {
        quote.style.display = 'none';
    }
}
