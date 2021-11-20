const SWIPE_THRESHOLD = 50; // Need at least this long a swipe before we register it

class SwipeDetector {
    constructor(target = document, threshold = SWIPE_THRESHOLD) {
        this.xDown = null;
        this.yDown = null;
        this.xUp = null;
        this.yUp = null;
        this.threshold = threshold;
        this.target = target;

        console.log("Attaching swipe detector to element ", target);
        target.addEventListener("touchstart", this.touchStart, false);
        target.addEventListener("touchend", this.touchEnd, false);
    }

    setCallback(direction, callback_function ) {
        document.addEventListener(`swipe${direction}`, callback_function);
    }

    touchStart(evt) {
        let firstTouch = (evt.touches || evt.originalEvent.touches)[0];
        this.xDown = firstTouch.clientX;
        this.yDown = firstTouch.clientY;
    }

    touchEnd(evt) {
        if (!this.xDown || !this.yDown) return
        this.xUp = evt.changedTouches[0].clientX;
        this.yUp = evt.changedTouches[0].clientY;

        let xDiff = Math.abs(this.xDown - this.xUp);
        let yDiff = Math.abs(this.yDown - this.yUp);
        let coords = {
            detail: {
                swipestart: {
                    coords: [this.xDown, this.yDown]
                },
                swipestop: {
                    coords: [this.xUp, this.yUp]
                }
            }
        };
        // If the swipe was too short, abort
        if (Math.sqrt(xDiff ** 2 + yDiff ** 2) < this.threshold) return

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
        this.xDown = null;
        this.yDown = null;
    }

}
