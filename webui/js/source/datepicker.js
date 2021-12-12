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

const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
let datepicker_spawner = null
let calendarpicker_spawner = null
const DATE_UNITS = {
    w: 'week',
    d: 'day',
    M: 'month',
    y: 'year'
}

function fixupPicker(obj) {
    obj.addEventListener("focus", function(event) {
        $('html').on('hide.bs.dropdown', function(e) {
            return false;
        });
    });
    obj.addEventListener("blur", function(event) {
        $('html').unbind('hide.bs.dropdown')
    });
}
// makeSelect: Creates a <select> object with options
function makeSelect(options, id, selval) {
    let sel = document.createElement('select')
    sel.addEventListener("focus", function(event) {
        $('html').on('hide.bs.dropdown', function(e) {
            return false;
        });
    });
    sel.addEventListener("blur", function(event) {
        $('html').unbind('hide.bs.dropdown')
    });
    sel.setAttribute("name", id)
    sel.setAttribute("id", id)
    // For each options element, create it in the DOM
    for (let key in options) {
        let opt = document.createElement('option')
        // Hash or array?
        if (typeof key == "string") {
            opt.setAttribute("value", key)
            // Option is selected by default?
            if (key == selval) {
                opt.setAttribute("selected", "selected")
            }
        } else {
            // Option is selected by default?
            if (options[key] == selval) {
                opt.setAttribute("selected", "selected")
            }
        }
        opt.text = options[key]
        sel.appendChild(opt)
    }
    return sel
}

// splitDiv: Makes a split div with 2 elements,
// and puts div2 into the right column,
// and 'name' as text in the left one.
function splitDiv(id, name, div2) {
    let div = document.createElement('div')
    let subdiv = document.createElement('div')
    let radio = document.createElement('input')
    radio.setAttribute("type", "radio")
    radio.setAttribute("name", "datepicker_radio")
    radio.setAttribute("value", name)
    radio.setAttribute("id", "datepicker_radio_" + id)
    radio.setAttribute("onclick", "calcTimespan('" + id + "')")
    let label = document.createElement('label')
    label.innerHTML = "&nbsp; " + name + ": "
    label.setAttribute("for", "datepicker_radio_" + id)


    subdiv.appendChild(radio)
    subdiv.appendChild(label)


    subdiv.style.float = "left"
    div2.style.float = "left"

    subdiv.style.width = "120px"
    subdiv.style.height = "48px"
    div2.style.height = "48px"
    div2.style.width = "250px"

    div.appendChild(subdiv)
    div.appendChild(div2)
    return div
}

// calcTimespan: Calculates the value and representational text
// for the datepicker choice and puts it in the datepicker's
// spawning input/select element.
function calcTimespan(what) {
    let wat = ""
    let tval = ""

    // Less than N units ago?
    if (what == 'lt') {
        // Get unit and how many units
        let N = document.getElementById('datepicker_lti').value
        let unit = document.getElementById('datepicker_lts').value
        let unitt = DATE_UNITS[unit]
        if (parseInt(N) != 1) {
            unitt += "s"
        }

        // If this makes sense, construct a humanly readable and a computer version
        // of the timespan
        if (N.length > 0) {
            wat = "Less than " + N + " " + unitt + " ago"
            tval = "lte=" + N + unit
        }
    }

    // More than N units ago?
    if (what == 'mt') {
        // As above, get unit and no of units.
        let N = document.getElementById('datepicker_mti').value
        let unit = document.getElementById('datepicker_mts').value
        let unitt = DATE_UNITS[unit]
        if (parseInt(N) != 1) {
            unitt += "s"
        }

        // construct timespan val + description
        if (N.length > 0) {
            wat = "More than " + N + " " + unitt + " ago"
            tval = "gte=" + N + unit
        }
    }

    // Date range?
    if (what == 'cd') {
        // Get From and To values
        let f = document.getElementById('datepicker_cfrom').value
        let t = document.getElementById('datepicker_cto').value
        // construct timespan val + description if both from and to are valid
        if (f.length > 0 && t.length > 0) {
            wat = "From " + f + " to " + t
            tval = "dfr=" + f + "|dto=" + t
        }
    }

    // If we calc'ed a value and spawner exists, update its key/val
    if (datepicker_spawner && what && wat.length > 0) {
        document.getElementById('datepicker_radio_' + what).checked = true
        if (datepicker_spawner.options) {
            datepicker_spawner.options[0].value = tval
            datepicker_spawner.options[0].text = wat
        } else if (datepicker_spawner.value) {
            datepicker_spawner.value = wat
            datepicker_spawner.setAttribute("data", tval)
        }

    }
}

// datePicker: spawns a date picker with letious
// timespan options right next to the parent caller.
function datePicker(parent, seedPeriod) {
    datepicker_spawner = parent
    let div = document.getElementById('datepicker_popup')

    // If the datepicker object doesn't exist, spawn it
    if (!div) {
        div = document.createElement('div')
        div.setAttribute("id", "datepicker_popup")
        div.setAttribute("class", "datepicker")
    }

    // Reset the contents of the datepicker object
    div.innerHTML = ""
    div.style.display = "block"

    // Position the datepicker next to whatever called it
    let bb = parent.getBoundingClientRect()
    div.style.top = (bb.bottom + 8) + "px"
    div.style.left = (bb.left + 32) + "px"


    // -- Less than N $units ago
    let ltdiv = document.createElement('div')
    let lti = document.createElement('input')
    lti.setAttribute("id", "datepicker_lti")
    lti.style.width = "48px"
    lti.setAttribute("onkeyup", "calcTimespan('lt')")
    lti.setAttribute("onblur", "calcTimespan('lt')")
    ltdiv.appendChild(lti)

    let lts = makeSelect({
        'd': "Day(s)",
        'w': 'Week(s)',
        'M': "Month(s)",
        'y': "Year(s)"
    }, 'datepicker_lts', 'm')
    lts.setAttribute("onchange", "calcTimespan('lt')")
    ltdiv.appendChild(lts)
    ltdiv.appendChild(document.createTextNode(' ago'))

    div.appendChild(splitDiv('lt', 'Less than', ltdiv))


    // -- More than N $units ago
    let mtdiv = document.createElement('div')

    let mti = document.createElement('input')
    mti.style.width = "48px"
    mti.setAttribute("id", "datepicker_mti")
    mti.setAttribute("onkeyup", "calcTimespan('mt')")
    mti.setAttribute("onblur", "calcTimespan('mt')")
    mtdiv.appendChild(mti)


    let mts = makeSelect({
        'd': "Day(s)",
        'w': 'Week(s)',
        'M': "Month(s)",
        'y': "Year(s)"
    }, 'datepicker_mts', 'm')
    mtdiv.appendChild(mts)
    mts.setAttribute("onchange", "calcTimespan('mt')")
    mtdiv.appendChild(document.createTextNode(' ago'))
    div.appendChild(splitDiv('mt', 'More than', mtdiv))



    // -- Calendar timespan
    // This is just two text fields, the calendarPicker sub-plugin populates them
    let cdiv = document.createElement('div')

    let cfrom = document.createElement('input')
    cfrom.style.width = "90px"
    cfrom.setAttribute("id", "datepicker_cfrom")
    cfrom.setAttribute("onfocus", "showCalendarPicker(this)")
    cfrom.setAttribute("onchange", "calcTimespan('cd')")
    cdiv.appendChild(document.createTextNode('From: '))
    cdiv.appendChild(cfrom)

    let cto = document.createElement('input')
    cto.style.width = "90px"
    cto.setAttribute("id", "datepicker_cto")
    cto.setAttribute("onfocus", "showCalendarPicker(this)")
    cto.setAttribute("onchange", "calcTimespan('cd')")
    cdiv.appendChild(document.createTextNode('To: '))
    cdiv.appendChild(cto)

    div.appendChild(splitDiv('cd', 'Date range', cdiv))



    // -- Magic button that sends the timespan back to the caller
    let okay = document.createElement('input')
    okay.setAttribute("type", "button")
    okay.setAttribute("value", "Okay")
    okay.setAttribute("onclick", "setDatepickerDate()")
    div.appendChild(okay)
    parent.parentNode.appendChild(div)
    document.body.setAttribute("onclick", "")
    window.setTimeout(function() {
        document.body.setAttribute("onclick", "blurDatePicker(event)")
    }, 200)
    lti.focus()

    // This is for recalcing the set options if spawned from a
    // select/input box with an existing value derived from an
    // earlier call to datePicker
    let ptype = ""
    let pvalue = parent.hasAttribute("data") ? parent.getAttribute("data") : parent.value
    if (pvalue.search(/=|-/) != -1) {

        // Less than N units ago?
        if (pvalue.match(/lte/)) {
            let m = pvalue.match(/lte=(\d+)([dMyw])/)
            ptype = 'lt'
            if (m) {
                document.getElementById('datepicker_lti').value = m[1]
                let sel = document.getElementById('datepicker_lts')
                for (let i in sel.options) {
                    if (parseInt(i) >= 0) {
                        if (sel.options[i].value == m[2]) {
                            sel.options[i].selected = "selected"
                        } else {
                            sel.options[i].selected = null
                        }
                    }
                }
            }

        }

        // More than N units ago?
        if (pvalue.match(/gte/)) {
            ptype = 'mt'
            let m = pvalue.match(/gte=(\d+)([dMyw])/)
            if (m) {
                document.getElementById('datepicker_mti').value = m[1]
                let sel = document.getElementById('datepicker_mts')
                // Go through the unit values, select the one we use
                for (let i in sel.options) {
                    if (parseInt(i) >= 0) {
                        if (sel.options[i].value == m[2]) {
                            sel.options[i].selected = "selected"
                        } else {
                            sel.options[i].selected = null
                        }
                    }
                }
            }
        }

        // Date range?
        if (pvalue.match(/dfr/)) {
            ptype = 'cd'
            // Make sure we have both a dfr and a dto here, catch them
            let mf = pvalue.match(/dfr=(\d+-\d+-\d+)/)
            let mt = pvalue.match(/dto=(\d+-\d+-\d+)/)
            if (mf && mt) {
                // easy peasy, just set two text fields!
                document.getElementById('datepicker_cfrom').value = mf[1]
                document.getElementById('datepicker_cto').value = mt[1]
            }
        }
        // Month??
        if (pvalue.match(/(\d{4})-(\d+)/)) {
            ptype = 'cd'
            // Make sure we have both a dfr and a dto here, catch them
            let m = pvalue.match(/(\d{4})-(\d+)/)
            if (m.length == 3) {
                // easy peasy, just set two text fields!
                let dfrom = new Date(parseInt(m[1]), parseInt(m[2]) - 1, 1, 0, 0, 0)
                let dto = new Date(parseInt(m[1]), parseInt(m[2]), 0, 23, 59, 59)
                document.getElementById('datepicker_cfrom').value = m[0] + "-" + dfrom.getDate()
                document.getElementById('datepicker_cto').value = m[0] + "-" + dto.getDate()
            }
        }
        calcTimespan(ptype)
    }
}


function datePickerValue(seedPeriod) {
    // This is for recalcing the set options if spawned from a
    // select/input box with an existing value derived from an
    // earlier call to datePicker
    let rv = seedPeriod
    if (seedPeriod && seedPeriod.search && seedPeriod.search(/=|-/) != -1) {

        // Less than N units ago?
        if (seedPeriod.match(/lte/)) {
            let m = seedPeriod.match(/lte=(\d+)([dMyw])/)
            let unitt = DATE_UNITS[m[2]]
            if (parseInt(m[1]) != 1) {
                unitt += "s"
            }
            rv = "Less than " + m[1] + " " + unitt + " ago"
        }

        // More than N units ago?
        if (seedPeriod.match(/gte/)) {
            let m = seedPeriod.match(/gte=(\d+)([dMyw])/)
            let unitt = DATE_UNITS[m[2]]
            if (parseInt(m[1]) != 1) {
                unitt += "s"
            }
            rv = "More than " + m[1] + " " + unitt + " ago"
        }

        // Date range?
        if (seedPeriod.match(/dfr/)) {
            let mf = seedPeriod.match(/dfr=(\d+-\d+-\d+)/)
            let mt = seedPeriod.match(/dto=(\d+-\d+-\d+)/)
            if (mf && mt) {
                rv = "From " + mf[1] + " to " + mt[1]
            }
        }

        // Month??
        if (seedPeriod.match(/^(\d+)-(\d+)$/)) {
            let mr = seedPeriod.match(/(\d+)-(\d+)/)
            if (mr) {
                let dfrom = new Date(parseInt(mr[1]), parseInt(mr[2]) - 1, 1, 0, 0, 0)
                rv = MONTHS[dfrom.getMonth()] + ', ' + mr[1]
            }
        }

    }
    return rv
}

function datePickerDouble(seedPeriod) {
    // This basically takes a date-arg and doubles it backwards
    // so >=3M becomes =>6M etc. Also returns the cutoff for
    // the original date and the span in days of the original
    let dbl = seedPeriod
    let tspan = 1
    let dfrom = new Date()
    let dto = new Date()

    // datepicker range?
    if (seedPeriod && seedPeriod.search && seedPeriod.search(/=/) != -1) {

        // Less than N units ago?
        if (seedPeriod.match(/lte/)) {
            let m = seedPeriod.match(/lte=(\d+)([dMyw])/)
            dbl = "lte=" + (parseInt(m[1]) * 2) + m[2]

            // N months ago
            if (m[2] == "M") {
                dfrom.setMonth(dfrom.getMonth() - parseInt(m[1]), dfrom.getDate())
            }

            // N days ago
            if (m[2] == "d") {
                dfrom.setDate(dfrom.getDate() - parseInt(m[1]))
            }

            // N years ago
            if (m[2] == "y") {
                dfrom.setYear(dfrom.getFullYear() - parseInt(m[1]))
            }

            // N weeks ago
            if (m[2] == "w") {
                dfrom.setDate(dfrom.getDate() - (parseInt(m[1]) * 7))
            }

            // Calc total duration in days for this time span
            tspan = parseInt((dto.getTime() - dfrom.getTime() + 5000) / (1000 * 86400))
        }

        // More than N units ago?
        if (seedPeriod.match(/gte/)) {
            let m = seedPeriod.match(/gte=(\d+)([dMyw])/)
            dbl = "gte=" + (parseInt(m[1]) * 2) + m[2]
            // Can't really figure out a timespan for this, so...null!
            // This also sort of invalidates use on the trend page, but meh..
            tspan = null
            dfrom = null

            // Months
            if (m[2] == "M") {
                dto.setMonth(dto.getMonth() - parseInt(m[1]), dto.getDate())
            }

            // Days
            if (m[2] == "d") {
                dto.setDate(dto.getDate() - parseInt(m[1]))
            }

            // Years
            if (m[2] == "y") {
                dto.setYear(dto.getFullYear() - parseInt(m[1]))
            }

            // Weeks
            if (m[2] == "w") {
                dto.setDate(dto.getDate() - (parseInt(m[1]) * 7))
            }
        }

        // Date range?
        if (seedPeriod.match(/dfr/)) {
            // Find from and to
            let mf = seedPeriod.match(/dfr=(\d+)-(\d+)-(\d+)/)
            let mt = seedPeriod.match(/dto=(\d+)-(\d+)-(\d+)/)
            if (mf && mt) {
                // Starts at 00:00:00 on from date
                dfrom = new Date(parseInt(mf[1]), parseInt(mf[2]) - 1, parseInt(mf[3]), 0, 0, 0)

                // Ends at 23:59:59 on to date
                dto = new Date(parseInt(mt[1]), parseInt(mt[2]) - 1, parseInt(mt[3]), 23, 59, 59)

                // Get duration in days, add 5 seconds to we can floor the value and get an integer
                tspan = parseInt((dto.getTime() - dfrom.getTime() + 5000) / (1000 * 86400))

                // double the distance
                let dpast = new Date(dfrom)
                dpast.setDate(dpast.getDate() - tspan)
                dbl = seedPeriod.replace(/dfr=[^|]+/, "dfr=" + (dpast.getFullYear()) + '-' + (dpast.getMonth() + 1) + '-' + dpast.getDate())
            } else {
                tspan = 0
            }
        }
    }

    // just N days?
    else if (parseInt(seedPeriod).toString() == seedPeriod.toString()) {
        tspan = parseInt(seedPeriod)
        dfrom.setDate(dfrom.getDate() - tspan)
        dbl = "lte=" + (tspan * 2) + "d"
    }

    // Specific month?
    else if (seedPeriod.match(/^(\d+)-(\d+)$/)) {
        // just a made up thing...(month range)
        let mr = seedPeriod.match(/(\d+)-(\d+)/)
        if (mr) {
            // Same as before, start at 00:00:00
            dfrom = new Date(parseInt(mr[1]), parseInt(mr[2]) - 1, 1, 0, 0, 0)
            // end at 23:59:59
            dto = new Date(parseInt(mr[1]), parseInt(mr[2]), 0, 23, 59, 59)

            // B-A, add 5 seconds so we can floor the no. of days into an integer neatly
            tspan = parseInt((dto.getTime() - dfrom.getTime() + 5000) / (1000 * 86400))

            // Double timespan
            let dpast = new Date(dfrom)
            dpast.setDate(dpast.getDate() - tspan)
            dbl = "dfr=" + (dpast.getFullYear()) + '-' + (dpast.getMonth() + 1) + '-' + dpast.getDate() + "|dto=" + (dto.getFullYear()) + '-' + (dto.getMonth() + 1) + '-' + dto.getDate()
        } else {
            tspan = 0
        }
    }

    return [dbl, dfrom, dto, tspan]
}

// set date in caller and hide datepicker again.
function setDatepickerDate() {
    calcTimespan()
    blurDatePicker()
}

// findParent: traverse DOM and see if we can find a parent to 'el'
// called 'name'. This is used for figuring out whether 'el' has
// lost focus or not.
function findParent(el, name) {
    if (el.getAttribute && el.getAttribute("id") == name) {
        return true
    }
    if (el.parentNode && el.parentNode.getAttribute) {
        if (el.parentNode.getAttribute("id") != name) {
            return findParent(el.parentNode, name)
        } else {
            return true
        }
    } else {
        return false;
    }
}

// function for hiding the date picker
function blurDatePicker(evt) {
    let es = evt ? (evt.target || evt.srcElement) : null;
    if ((!es || !es.parentNode || (!findParent(es, "datepicker_popup") && !findParent(es, "calendarpicker_popup"))) && !(es ? es : "null").toString().match(/javascript:void/)) {
        document.getElementById('datepicker_popup').style.display = "none"
        $('html').trigger('hide.bs.dropdown')
    }
}

// draws the actual calendar inside a calendarPicker object
function drawCalendarPicker(obj, date) {


    obj.focus()

    // Default to NOW for calendar.
    let now = new Date()

    // if called with an existing date (YYYY-MM-DD),
    // convert it to a JS date object and use that for
    // rendering the calendar
    if (date) {
        let ar = date.split(/-/)
        now = new Date(ar[0], parseInt(ar[1]) - 1, ar[2])
    }
    let mat = now

    // Go to first day of the month
    mat.setDate(1)

    obj.innerHTML = "<h3>" + MONTHS[mat.getMonth()] + ", " + mat.getFullYear() + ":</h3>"
    let tm = mat.getMonth()

    // -- Nav buttons --

    // back-a-year button
    let a = document.createElement('a')
    fixupPicker(a)
    a.setAttribute("onclick", "drawCalendarPicker(this.parentNode, '" + (mat.getFullYear() - 1) + '-' + (mat.getMonth() + 1) + '-' + mat.getDate() + "');")
    a.setAttribute("href", "javascript:void(0);")
    a.setAttribute("class", "glyphicon glyphicon-fast-backward");
    obj.appendChild(a)

    // back-a-month button
    a = document.createElement('a')
    fixupPicker(a)
    a.setAttribute("onclick", "drawCalendarPicker(this.parentNode, '" + mat.getFullYear() + '-' + (mat.getMonth()) + '-' + mat.getDate() + "');")
    a.setAttribute("href", "javascript:void(0);")
    a.setAttribute("class", "glyphicon glyphicon-step-backward");
    obj.appendChild(a)

    // forward-a-month button
    a = document.createElement('a')
    fixupPicker(a)
    a.setAttribute("onclick", "drawCalendarPicker(this.parentNode, '" + mat.getFullYear() + '-' + (mat.getMonth() + 2) + '-' + mat.getDate() + "');")
    a.setAttribute("href", "javascript:void(0);")
    a.setAttribute("class", "glyphicon glyphicon-step-forward");
    obj.appendChild(a)

    // forward-a-year button
    a = document.createElement('a')
    fixupPicker(a)
    a.setAttribute("onclick", "drawCalendarPicker(this.parentNode, '" + (mat.getFullYear() + 1) + '-' + (mat.getMonth() + 1) + '-' + mat.getDate() + "');")
    a.setAttribute("href", "javascript:void(0);")
    a.setAttribute("class", "glyphicon glyphicon-fast-forward");
    obj.appendChild(a)
    obj.appendChild(document.createElement('br'))


    // Table containing the dates of the selected month
    let table = document.createElement('table')

    table.setAttribute("border", "1")
    table.style.margin = "0 auto"

    // Add header day names
    let tr = document.createElement('tr');
    for (let m = 0; m < 7; m++) {
        let td = document.createElement('th')
        td.innerHTML = DAYS_SHORTENED[m]
        tr.appendChild(td)
    }
    table.appendChild(tr)

    // Until we hit the first day in a month, add blank days
    tr = document.createElement('tr');
    let weekday = mat.getDay()
    if (weekday == 0) {
        weekday = 7
    }
    weekday--;
    for (let i = 0; i < weekday; i++) {
        let td = document.createElement('td')
        tr.appendChild(td)
    }

    // While still in this month, add day then increment date by 1 day.
    while (mat.getMonth() == tm) {
        weekday = mat.getDay()
        if (weekday == 0) {
            weekday = 7
        }
        weekday--;
        if (weekday == 0) {
            table.appendChild(tr)
            tr = document.createElement('tr');
        }
        let td = document.createElement('td')
        // onclick for setting the calendarPicker's parent to this val.
        td.setAttribute("onclick", "setCalendarDate('" + mat.getFullYear() + '-' + (mat.getMonth() + 1) + '-' + mat.getDate() + "');")
        td.innerHTML = mat.getDate()
        mat.setDate(mat.getDate() + 1)
        tr.appendChild(td)
    }

    table.appendChild(tr)
    obj.appendChild(table)
}

// callback for datePicker; sets the cd value to what date was picked
function setCalendarDate(what) {
    $('html').on('hide.bs.dropdown', function(e) {
        return false;
    });
    setTimeout(function() {
        $('html').unbind('hide.bs.dropdown');
    }, 250);


    calendarpicker_spawner.value = what
    let div = document.getElementById('calendarpicker_popup')
    div.parentNode.focus()
    div.style.display = "none"
    calcTimespan('cd')
}

// caller for when someone clicks on a calendarPicker enabled field
function showCalendarPicker(parent, seedDate) {
    calendarpicker_spawner = parent

    // If supplied with a YYYY-MM-DD date, use this to seed the calendar
    if (!seedDate) {
        let m = parent.value.match(/(\d+-\d+(-\d+)?)/)
        if (m) {
            seedDate = m[1]
        }
    }

    // Show or create the calendar object
    let div = document.getElementById('calendarpicker_popup')
    if (!div) {
        div = document.createElement('div')
        div.setAttribute("id", "calendarpicker_popup")
        div.setAttribute("class", "calendarpicker")
        document.getElementById('datepicker_popup').appendChild(div)
        div.innerHTML = "Calendar goes here..."
    }
    div.style.display = "block"
    let bb = parent.getBoundingClientRect()

    // Align with the calling object, slightly below
    div.style.top = (bb.bottom + 8) + "px"
    div.style.left = (bb.right - 32) + "px"

    drawCalendarPicker(div, seedDate)
}
