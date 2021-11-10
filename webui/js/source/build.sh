#!/usr/bin/env bash

test -r build.sh || { echo "Must be run from the directory containing build.sh!"; exit 1; }

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
// THIS IS AN AUTOMATICALLY COMBINED FILE. PLEASE EDIT source/*.js!!
' > ../ponymail.js
for f in `ls *.js`; do
    printf "\n\n/******************************************\n Fetched from source/${f}\n******************************************/\n\n" >> ../ponymail.js
    perl -0pe 's/\/\*.*?\*\/[\r\n]*//sm' ${f} >> ../ponymail.js
done
echo "Done!"
