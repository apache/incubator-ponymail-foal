#!/usr/bin/env bash

# Try to change to correct directory:
cd $(dirname "$0") || exit 1

test -r build.sh || { echo "Must be run from the directory containing build.sh!"; exit 1; }

git diff --exit-code -- *.js || echo "Please commit source changes before updating ponymail.js!"

# Javascript revision (for updating HTML)
# Need to include the ponymail sources here, but not ponymail.js itself
JS_REV=$({
    for f in *.js ../*.js
    do
      if [ "$f" != '../ponymail.js' ]
      then
        git log -1 --pretty='%ct %h' -- $f
      fi
    done
} | sort -r | head -1 | cut -d' ' -f 2)

# Javascript source revision (for creating ponymail.js)
# Only check ponymail sources here
JS_SRC_REV=$({
  for f in *.js
  do
    git log -1 --pretty='%ct %h' -- $f
  done
} | sort -r | head -1 | cut -d' ' -f 2)

echo "Combining JS..."
{
cat <<EOD
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
// THIS IS AN AUTOMATICALLY COMBINED FILE. PLEASE EDIT THE source/ FILES!

const PONYMAIL_REVISION = '$JS_SRC_REV';
EOD

for f in `ls *.js`; do
    printf "\n\n/******************************************\n Fetched from source/${f}\n******************************************/\n\n"
    perl -0pe 's/\/\*.*?\*\/[\r\n]*//sm' ${f}
done
} > ../ponymail.js

# Adjust JS caches in .html
for f in `ls ../../*.html`; do
    perl -0pe 's/\?revision=[a-f0-9]+/?revision='${JS_REV}'/smg' ${f} > ${f}.tmp && mv ${f}.tmp ${f}
done

git diff --exit-code
