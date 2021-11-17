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

const SVG_NAMESPACE = "http://www.w3.org/2000/svg"


function fastIntersect(x,y,nx,ny) {
    if (x.getAttribute("id") == y.getAttribute("id")) { // can't collide with itself
        return false
    }
    var spacing = 2 // number of pixels to keep elements apart
    nx = nx ? nx : 0
    ny = ny ? ny : 0
    var a = x.getBoundingClientRect()
    var b = y.getBoundingClientRect()
    return !(b.left-spacing > (a.right+nx)
        || b.right+spacing < (a.left+nx)
        || b.top-spacing > (a.bottom+ny)
        || b.bottom+spacing < (a.top+ny));
}

function makeWord(word, size) {
    var textBox = document.createElementNS(SVG_NAMESPACE, "text");
    textBox.setAttribute("font-size", size + "px")
    textBox.setAttribute("x", "0")
    textBox.setAttribute("y", "40")
    textBox.setAttribute("class", "cloudword")
    textBox.setAttribute("onclick", "search(\"" + word + "\", 'lte=1M')")
    textBox.textContent = word
    return textBox
}

async function wordCloud(hash, width, height, obj) {
    var total = 0
    var boxes = []
    var space = width * height
    for (i in hash) {
        total += Math.sqrt(hash[i])
    }
    var hashSorted = []
    for (word in hash) hashSorted.push(word)
    hashSorted = hashSorted.sort(function(a,b) { return hash[a] > hash[b] })
    var svg = document.createElementNS(SVG_NAMESPACE, "svg");
    document.body.appendChild(svg)
    svg.setAttribute("width",  width)
    svg.setAttribute("height",  height)
    svg.setAttribute("class", "wordcloud")
    for (var n = 0; n < hashSorted.length; n++) {
        var word = hashSorted[n]
        var size = 0;
        var expected_area = ( Math.sqrt(hash[word]) / total ) * (space*0.9)
        console.log(expected_area)
        
        var textBox = document.createElementNS(SVG_NAMESPACE, "text");
        textBox.textContent = word
        textBox.setAttribute("font-size", "100px")
        svg.appendChild(textBox)
        
        w = textBox.getBoundingClientRect();
        
        for (var s = 100; s > 0; s-=5) {
                        
            var area = w.width * w.height * ( (s/100)*(s/100) );
            if (area <= expected_area ) {
                size = s;
                svg.removeChild(textBox)
                break
            }
        }
        
        
        
        var theta = 50;
        var prop = height/width
        var popped = false
        
        var angle = 0;
        
        // Try with random placement
        var gw = svg.getBoundingClientRect()
        var w
        
        
        
        var textBox = makeWord(word, ss)
        textBox.setAttribute("id", "svg_wc_" + word)
        svg.appendChild(textBox)
        if (!popped) {
            textBox.setAttribute("x", 0)
            textBox.setAttribute("y", 0)
            for (var ss = size; ss > 5; ss *= 0.9) {
               // alert(ss)
                if (popped) {
                    break
                }
                textBox.setAttribute("font-size", ss + "px")
                
                var w = textBox.getBoundingClientRect()
                for (var l = 0; l < 80; l++) {
                    var nx = 4 + (Math.random() * (width-8-w.width))
                    var ny = 4 + w.height + ((l/80) * (height-8-w.height))
                    var it = false
                    for (var b = 0; b < boxes.length; b++) {
                        if (fastIntersect(textBox, boxes[b], nx, ny)) {
                            it = true
                            break
                        }
                    }
                    if (it == false) {
                        popped = true
                        textBox.setAttribute("x", nx)
                        textBox.setAttribute("y", ny)
                        break
                    } 
                }
            }
        }
        
        
        
        if (popped) {
            var color = 'hsl('+ Math.random()*360 +', 40%, 50%)';
            textBox.setAttribute("fill", color)
            boxes.push(textBox)
        } else {
            //alert("Could not add " + word)
            svg.removeChild(textBox)
        }
        
    }
    
    // Try to size up texts a bit
    var ts = 0
    for (var i =0; i < boxes.length; i++) {
        var textBox = boxes[i]
        var osize = parseFloat(textBox.getAttribute('font-size'))
        var psize = osize
        for (var n = 1; n < 1.4; n+=0.2) {
            var nsize = osize * n
            textBox.setAttribute("font-size", nsize + "px")
            var w = textBox.getBoundingClientRect()
            var good = true
            for (var b =0; b < boxes.length; b++) {
                if (fastIntersect(textBox, boxes[b])) {
                    good = false
                    break
                }
            }
            if (!good || w.right > width-4 || w.top < 4) {
                textBox.setAttribute("font-size", psize + "px")
                break
            }
            psize = nsize
            ts++
        }
    }
    document.body.removeChild(svg)
    console.log("Word Cloud generated");
    obj.inject(svg);
}
