const SWIPE_THRESHOLD = 50; // Need at least this long a swipe before we register it
let xDown;
let yDown;

// touch/swipe begins                                                                         
function touchStart(evt) {
    let firstTouch = (evt.touches || evt.originalEvent.touches)[0];
    xDown = firstTouch.clientX;
    yDown = firstTouch.clientY;
}

// Touch/swipe ends
function touchEnd(evt) {
    if (!xDown || !yDown) return
    let xUp = evt.changedTouches[0].clientX;
    let yUp = evt.changedTouches[0].clientY;

    let xDiff = Math.abs(xDown - xUp);
    let yDiff = Math.abs(yDown - yUp);
    let coords = {
        detail: {
            swipestart: {
                coords: [xDown, yDown]
            },
            swipestop: {
                coords: [xUp, yUp]
            }
        }
    };
    // If the swipe was too short, abort
    if (Math.sqrt(xDiff ** 2 + yDiff ** 2) < SWIPE_THRESHOLD) return

    // Which direction??
    if (xDiff > yDiff) {
        if (xDiff > 0) {
            document.dispatchEvent(new CustomEvent("swipeleft", coords));
        } else {
            document.dispatchEvent(new CustomEvent("swiperight", coords));
        }
    } else {
        if (yDiff > 0) {
            document.dispatchEvent(new CustomEvent("swipeup", coords));
        } else {
            document.dispatchEvent(new CustomEvent("swipedown", coords));
        }
    }

    xDown = null;
    yDown = null;
};

function attachSwipe(elm) {
    console.log("Attaching swipe detector to element ", elm);
    elm.addEventListener("touchstart", touchStart, false);
    elm.addEventListener("touchend", touchEnd, false);
}

