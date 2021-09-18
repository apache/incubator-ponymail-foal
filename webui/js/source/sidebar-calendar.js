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

var months_shortened = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
var default_start_year = 1990;
var default_end_year = 2100;
var calendar_index = 0;
var calendar_years_shown = 4;

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
    for (var Y = SY; Y >= FY; Y--) {
        let ydiv = new HTML('div', {
            class: 'sidebar_calendar_year',
            id: 'sidebar_calendar_' + N++
        });
        ydiv.inject(txt(Y));
        ydiv.inject(new HTML('br'));
        for (var i = 0; i < months_shortened.length; i++) {
            let mon = months_shortened[i];
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
    if (N > calendar_years_shown) {
        for (var i = calendar_years_shown; i < N; i++) {
            let obj = document.getElementById('sidebar_calendar_' + i);
            if (obj) {
                obj.style.display = "none";
            }
        }
        document.getElementById('sidebar_calendar_down').style.display = 'block';
    }
}

function calendar_scroll(me, x) {
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


    for (var i = 0; i < years.length; i++) {
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
    current_year = year;
    current_month = month;
    searching = false;
    let newhref = "list.html?%s@%s:%u-%u".format(current_list, current_domain, year, month);
    if (location.href !== newhref) {
        window.history.pushState({}, null, newhref);
    }
    GET('%sapi/stats.lua?list=%s&domain=%s&d=%u-%u'.format(apiURL, current_list, current_domain, year, month), renderListView, {
        to: '%s@%s'.format(current_list, current_domain),
        update_calendar: false
    });
}
