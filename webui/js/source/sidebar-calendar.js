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

let calendar_index = 0;

function renderCalendar(FY, FM, LY, LM, activity = null) {
    calendar_index = 0;

    // Only render if calendar div is present
    let cal = document.getElementById('sidebar_calendar');
    if (!cal) {
        return;
    }

    let now = new Date();
    let CY = now.getFullYear();
    let CM = now.getMonth() + 1;
    let SY = Math.min(LY, CY); // last year in calendar, considering current date
    // If Last Year is into the future, set Last Month to this one.
    if (LY > CY) {
        LM = CM;
    }

    let cdiv = new HTML('div', {
        class: 'sidebar_calendar'
    })
    let N = 0;

    // Chevron for moving to later years
    let chevron = new HTML('div', {
        class: 'sidebar_calendar_chevron'
    });
    chevron.inject(new HTML('span', {
        onclick: 'calendar_scroll(this, -4);',
        style: {
            display: 'none'
        },
        id: 'sidebar_calendar_up',
        class: 'glyphicon glyphicon-collapse-up',
        title: "Show later years"
    }, " "));
    cdiv.inject(chevron);

    // Create divs for each year, assign all visible
    for (let Y = SY; Y >= FY; Y--) {
        let ydiv = new HTML('div', {
            class: 'sidebar_calendar_year',
            id: 'sidebar_calendar_' + N++
        });
        ydiv.inject(txt(Y));
        ydiv.inject(new HTML('br'));
        for (let i = 0; i < MONTHS_SHORTENED.length; i++) {
            let mon = MONTHS_SHORTENED[i];
            let mdiv = new HTML('div', {
                onclick: 'calendar_click(%u, %u);'.format(Y, i + 1),
                class: 'sidebar_calendar_month'
            }, mon);

            // Mark out-of-bounds segments
            let ym = '%04u-%02u'.format(Y, i+1);
            let c_active = true;
            if (activity && !activity[ym]) {
                c_active = false;
            }
            if ((Y == SY && i >= LM) || (Y == CY && i > CM)) {
                c_active = false;
            }
            if (Y == FY && ((i + 1) < FM)) {
                c_active = false;
            }
            if (!c_active) {
                mdiv.setAttribute("class", "sidebar_calendar_month_nothing");
                mdiv.setAttribute("onclick", "javascript:void(0);");
            } else if (activity && activity[ym]) {
                let count = activity[ym];
                if (count >= 1000) {
                    count = Math.round(count/100.0); // nearest century
                    count = Math.floor(count/10) + "k" + (count % 10); // thousands and remainder
                } else {
                    count = count.toString();
                }
                mdiv.inject(new HTML('span', {title: `${activity[ym].pretty()} emails this month`, class: 'calendar_count'}, count));
            }
            ydiv.inject(mdiv);
        }
        cdiv.inject(ydiv);
    }

    cal.innerHTML = "<p style='text-align: center;'>Archives (%u - %u):</p>".format(FY, SY);
    cal.inject(cdiv);


    chevron = new HTML('div', {
        class: 'sidebar_calendar_chevron'
    });
    chevron.inject(new HTML('span', {
        onclick: 'calendar_scroll(this, 4);',
        style: {
            display: 'none'
        },
        id: 'sidebar_calendar_down',
        class: 'glyphicon glyphicon-collapse-down',
        title: "Show earlier years"
    }, " "));
    cdiv.inject(chevron);

    // If we have > 4 years, hide the rest
    if (N > CALENDAR_YEARS_SHOWN) {
        for (let i = CALENDAR_YEARS_SHOWN; i < N; i++) {
            let obj = document.getElementById('sidebar_calendar_' + i);
            if (obj) {
                obj.style.display = "none";
            }
        }
        document.getElementById('sidebar_calendar_down').style.display = 'block';
    }
}

function calendar_scroll(me, x) {
    console.log(me)
    let years = document.getElementsByClassName('sidebar_calendar_year');
    calendar_index = Math.max(Math.min(years.length - x, calendar_index + x), 0);
    if (calendar_index > 0) {
        document.getElementById('sidebar_calendar_up').style.display = 'block';
    } else {
        document.getElementById('sidebar_calendar_up').style.display = 'none';
    }
    if (calendar_index < (years.length - x)) {
        document.getElementById('sidebar_calendar_down').style.display = 'block';
    } else {
        document.getElementById('sidebar_calendar_down').style.display = 'none';
    }


    for (let i = 0; i < years.length; i++) {
        let year = years[i];
        if (typeof(year) == 'object') {
            if (i >= calendar_index && i < (calendar_index + Math.abs(x))) {
                year.style.display = "block";
            } else {
                year.style.display = "none";
            }
        }
    }

}


function calendar_click(year, month) {
    G_current_year = year;
    G_current_month = month;
    let searching = false;
    let q = "";
    let calendar_current_list = G_current_list;
    let calendar_current_domain = G_current_domain;
    if (G_current_json && G_current_json.searchParams) {
        q = G_current_json.searchParams.q || "";
        calendar_current_list = G_current_json.searchParams.list;
        calendar_current_domain = G_current_json.searchParams.domain;
        // Weave in header parameters
        for (let key of Object.keys((G_current_json.searchParams || {}))) {
            if (key.match(/^header_/)) {
                let value = G_current_json.searchParams[key];
                q += `&${key}=${value}`;
            }
        }
    }
    let newhref = "list?%s@%s:%u-%u".format(calendar_current_list, calendar_current_domain, year, month);
    if (q && q.length > 0) newhref += ":" + q;

    if (location.href !== newhref) {
        window.history.pushState({}, null, newhref);
    }
    GET('%sapi/stats.lua?list=%s&domain=%s&d=%u-%u&q=%s'.format(G_apiURL, calendar_current_list, calendar_current_domain, year, month, q), renderListView, {
        to: (q && q.length > 0) ? 'search' : '%s@%s'.format(calendar_current_list, calendar_current_domain),
        update_calendar: false,
        search: (q && q.length > 0)
    });
}
