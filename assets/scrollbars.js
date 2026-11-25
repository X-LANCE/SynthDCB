(() => {
  function install(scroller, host, content, isHome) {
    const track = document.createElement("div");
    const thumb = document.createElement("span");
    track.className = "page-scrollbar";
    track.tabIndex = 0;
    track.setAttribute("role", "scrollbar");
    track.setAttribute("aria-label", isHome ? "Scroll homepage" : "Scroll leaderboard");
    track.setAttribute("aria-controls", content.id);
    track.setAttribute("aria-orientation", "vertical");
    track.setAttribute("aria-valuemin", "0");
    track.setAttribute("aria-valuemax", "100");
    track.append(thumb);
    host.append(track);
    let grab = null;
    let travel = 0;
    let limit = 0;
    const title = document.getElementById("paper-title");
    function refresh() {
      limit = Math.max(0, scroller.scrollHeight - scroller.clientHeight);
      const atTitle = isHome ? title.getBoundingClientRect().bottom > 0 : scroller.scrollTop < 1;
      track.hidden = !limit || (atTitle && grab === null);
      const fraction = limit ? Math.min(1, Math.max(0, scroller.scrollTop / limit)) : 0;
      track.setAttribute("aria-valuenow", Math.round(fraction * 100));
      if (track.hidden) return;
      const height = track.clientHeight;
      const length = Math.min(height, Math.max(34, height * scroller.clientHeight / scroller.scrollHeight));
      travel = height - length;
      thumb.style.height = length + "px";
      thumb.style.transform = "translateY(" + fraction * travel + "px)";
    }
    function seek(event) {
      if (!travel) return;
      const y = event.clientY - track.getBoundingClientRect().top - grab;
      scroller.scrollTop = limit * Math.max(0, Math.min(1, y / travel));
    }
    track.addEventListener("pointerdown", event => {
      if (!event.isPrimary || event.button !== 0) return;
      const box = thumb.getBoundingClientRect();
      grab = event.clientY >= box.top && event.clientY <= box.bottom ? event.clientY - box.top : box.height / 2;
      track.setPointerCapture(event.pointerId);
      seek(event);
    });
    track.addEventListener("pointermove", event => {
      if (track.hasPointerCapture(event.pointerId)) seek(event);
    });
    track.addEventListener("lostpointercapture", () => { grab = null; refresh(); });
    track.addEventListener("keydown", event => {
      const y = scroller.scrollTop, page = scroller.clientHeight * .9;
      const positions = {Home: 0, End: limit, ArrowDown: y + 48, ArrowUp: y - 48, PageDown: y + page, PageUp: y - page};
      if (!Object.hasOwn(positions, event.key)) return;
      event.preventDefault();
      scroller.scrollTop = positions[event.key];
    });
    if (!isHome) track.addEventListener("wheel", event => {
      event.preventDefault();
      const unit = event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? scroller.clientHeight : 1;
      scroller.scrollTop += event.deltaY * unit;
    }, {passive: false});
    (isHome ? window : scroller).addEventListener("scroll", refresh, {passive: true});
    const observer = new ResizeObserver(refresh);
    for (const element of [content, scroller, host]) observer.observe(element);
    window.addEventListener("resize", refresh);
    scroller.classList.add("custom-scroll");
    refresh();
  }
  const board = document.getElementById("leaderboard");
  const table = board.querySelector("table");
  table.id = "board-scores";
  install(document.scrollingElement, document.body, document.getElementById("top"), true);
  install(board.querySelector(".board-scroll"), board, table, false);
})();
