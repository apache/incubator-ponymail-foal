#!/usr/bin/env bash

# Try to change to correct directory:
cd $(dirname "$0") || exit 1

test -r build.sh || { echo "Must be run from the directory containing build.sh!"; exit 1; }

# Javascript revision (for updating HTML)
JS_REV=$(git log -1 --pretty=%h -- ..)

# Javascript source revision (for creating ponymail.js)
JS_SRCR_EV=$(git log -1 --pretty=%h -- .)

echo "Combining JS..."
echo '/*
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
// THIS IS AN AUTOMATICALLY COMBINED FILE. PLEASE EDIT THE source/ FILES!

const PONYMAIL_REVISION = "'$JS_SRC_REV'";
' > ../ponymail.js
for f in `ls *.js`; do
    printf "\n\n/******************************************\n Fetched from source/${f}\n******************************************/\n\n" >> ../ponymail.js
    perl -0pe 's/\/\*.*?\*\/[\r\n]*//sm' ${f} >> ../ponymail.js
done

# Adjust JS caches in .html
for f in `ls ../../*.html`; do
    echo ${f}
    perl -0pe 's/\?revision=[a-f0-9]+/?revision='${JS_REV}'/smg' ${f} > ${f}.tmp && mv ${f}.tmp ${f}
done

git status
echo "Done!"

