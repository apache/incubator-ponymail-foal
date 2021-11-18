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

/**
 * String formatting prototype
 * A'la printf
 */

String.prototype.format = function() {
    let args = arguments;
    let n = 0;
    let t = this;
    let rtn = this.replace(/(?!%)?%([-+]*)([0-9.]*)([a-zA-Z])/g, function(m, pm, len, fmt) {
        len = parseInt(len || '1');
        // We need the correct number of args, balk otherwise, using ourselves to format the error!
        if (args.length <= n) {
            let err = "Error interpolating string '%s': Expected at least %u argments, only got %u!".format(t, n + 1, args.length);
            console.log(err);
            throw err;
        }
        let varg = args[n];
        n++;
        switch (fmt) {
            case 's':
                if (typeof(varg) == 'function') {
                    varg = '(function)';
                }
                return varg;
                // For now, let u, d and i do the same thing
            case 'd':
            case 'i':
            case 'u':
                varg = parseInt(varg).pad(len); // truncate to Integer, pad if needed
                return varg;
        }
    });
    return rtn;
};


/**
 * Number prettification prototype:
 * Converts 1234567 into 1,234,567 etc
 */

Number.prototype.pretty = function(fix) {
    if (fix) {
        return String(this.toFixed(fix)).replace(/(\d)(?=(\d{3})+\.)/g, '$1,');
    }
    return String(this.toFixed(0)).replace(/(\d)(?=(\d{3})+$)/g, '$1,');
};


/**
 * Number padding
 * usage: 123.pad(6) -> 000123
 */

Number.prototype.pad = function(n) {
    let str = String(this);

    /* Do we need to pad? if so, do it using String.repeat */
    if (str.length < n) {
        str = "0".repeat(n - str.length) + str;
    }
    return str;
};

/* Func for converting TZ offset from minutes to +/-HHMM */

Date.prototype.TZ_HHMM = function() {
    let off_mins = this.getTimezoneOffset();
    let off_hh =   Math.floor(Math.abs(off_mins/60));
    let off_mm =   Math.abs(off_mins%60);
    let sgn = off_mins > 0 ? '-' : '+';
    return sgn + off_hh.pad(2) + ':' + off_mm.pad(2);
};



/* Func for converting a date to YYYY-MM-DD HH:MM TZ */

Date.prototype.ISOBare = function() {
    let M, O, d, h, m, y;
    if (prefs.UTC === true) {
        y = this.getUTCFullYear();
        m = (this.getUTCMonth() + 1).pad(2);
        d = this.getUTCDate().pad(2);
        h = this.getUTCHours().pad(2);
        M = this.getUTCMinutes().pad(2);
        O = 'UTC';
    } else {
        y = this.getFullYear();
        m = (this.getMonth() + 1).pad(2);
        d = this.getDate().pad(2);
        h = this.getHours().pad(2);
        M = this.getMinutes().pad(2);
        O = this.TZ_HHMM();
    }
    return y + "-" + m + "-" + d + " " + h + ":" + M + " " + O;
};


/* isArray: function to detect if an object is an array */

function isArray(value) {
    return value && typeof value === 'object' && value instanceof Array && typeof value.length === 'number' && typeof value.splice === 'function' && !(value.propertyIsEnumerable('length'));
}


/* isHash: function to detect if an object is a hash */

function isHash(value) {
    return value && typeof value === 'object' && !isArray(value);
}


/* Remove an array element by value */

Array.prototype.remove = function(val) {
    let i, item, j, len;
    for (i = j = 0, len = this.length; j < len; i = ++j) {
        item = this[i];
        if (item === val) {
            this.splice(i, 1);
            return this;
        }
    }
    return this;
};


/* Check if array has value */
Array.prototype.has = function(val) {
    for (let item of this) {
        if (item === val) {
            return true;
        }
    }
    return false;
};

function isEmpty(obj) {
    return (
        obj &&
        Object.keys(obj).length === 0 &&
        Object.getPrototypeOf(obj) === Object.prototype
    );
}
