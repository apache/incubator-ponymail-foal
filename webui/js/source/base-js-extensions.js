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
        let err = "Error interpolating string '%s': Expected at least %u argments, only got %u!".format(t, n+1, args.length);
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
}


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
  var str;
  str = String(this);

  /* Do we need to pad? if so, do it using String.repeat */
  if (str.length < n) {
    str = "0".repeat(n - str.length) + str;
  }
  return str;
};


/* Func for converting a date to YYYY-MM-DD HH:MM */

Date.prototype.ISOBare = function() {
  var M, d, h, m, y;
  y = this.getFullYear();
  m = (this.getMonth() + 1).pad(2);
  d = this.getDate().pad(2);
  h = this.getHours().pad(2);
  M = this.getMinutes().pad(2);
  return y + "-" + m + "-" + d + " " + h + ":" + M;
};


/* isArray: function to detect if an object is an array */

isArray = function(value) {
  return value && typeof value === 'object' && value instanceof Array && typeof value.length === 'number' && typeof value.splice === 'function' && !(value.propertyIsEnumerable('length'));
};


/* isHash: function to detect if an object is a hash */

isHash = function(value) {
  return value && typeof value === 'object' && !isArray(value);
};


/* Remove an array element by value */

Array.prototype.remove = function(val) {
  var i, item, j, len;
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
  var i, item, j, len;
  for (i = j = 0, len = this.length; j < len; i = ++j) {
    item = this[i];
    if (item === val) {
      return true;
    }
  }
  return false;
};


