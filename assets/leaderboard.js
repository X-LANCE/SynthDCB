(() => {
  const board = document.getElementById("leaderboard");
  const table = board.querySelector("table");
  const bubble = board.querySelector(".board-provenance");
  const scroller = board.querySelector(".board-scroll");
  const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)");
  let anchor = null;
  const movements = new Map();
  const overallRanks = new Map(Array.from(table.tBodies, group => [group, group.querySelector(".board-rank").textContent]));

  function highlightColumn(index) {
    for (const row of table.rows) {
      row.querySelector(".board-selected")?.classList.remove("board-selected");
      row.cells[index].classList.add("board-selected");
    }
  }
  highlightColumn(table.querySelector("[aria-sort]").cellIndex);


  function hideInfo() {
    if (!anchor) return;
    anchor.setAttribute("aria-expanded", "false");
    anchor = null;
    bubble.hidden = true;
  }

  function showInfo(button, group) {
    if (anchor === button) return hideInfo();
    hideInfo();
    anchor = button;
    button.setAttribute("aria-expanded", "true");
    bubble.querySelector("strong").textContent = group.dataset.model;
    bubble.querySelector("dd").textContent = group.dataset.evalDate;
    bubble.hidden = false;
    const box = button.getBoundingClientRect();
    const center = box.left + box.width / 2;
    const left = Math.max(8, Math.min(center - bubble.offsetWidth / 2, board.clientWidth - bubble.offsetWidth - 8));
    const above = box.bottom + 10 + bubble.offsetHeight > board.clientHeight && box.top > bubble.offsetHeight + 10;
    const top = above ? box.top - bubble.offsetHeight - 10 : box.bottom + 10;
    bubble.style.left = left + "px";
    bubble.style.top = Math.max(6, Math.min(top, board.clientHeight - bubble.offsetHeight - 6)) + "px";
    bubble.style.setProperty("--tip-x", (center - left) + "px");
    bubble.classList.toggle("above", above);
  }

  function sortBy(button) {
    hideInfo();
    const col = button.closest("th").cellIndex;
    const groups = Array.from(table.tBodies);
    const oldY = new Map(groups.map(group => [group, group.getBoundingClientRect().top]));
    for (const animation of movements.values()) animation.cancel();
    movements.clear();
    const value = group => col === 0 ? group.dataset.model : Number(group.rows[0].cells[col].dataset.score);
    const header = button.closest("th");
    const previous = header.getAttribute("aria-sort");
    const ascending = previous ? previous === "descending" : col === 0;
    const compare = (a, b) => col === 0 ? a.localeCompare(b, "en", {numeric: true}) : a - b;
    groups.sort((a, b) => (ascending ? 1 : -1) * compare(value(a), value(b)) || Number(a.dataset.order) - Number(b.dataset.order));
    const fragment = document.createDocumentFragment();
    const metricRanks = new Map();
    if (col !== 0) {
      const bestFirst = ascending ? groups.slice().reverse() : groups;
      bestFirst.forEach((group, index) => {
        const score = value(group);
        if (!metricRanks.has(score)) metricRanks.set(score, index + 1);
      });
    }
    groups.forEach(group => {
      group.querySelector(".board-rank").textContent = col === 0 ? overallRanks.get(group) : "#" + metricRanks.get(value(group));
      fragment.append(group);
    });
    table.append(fragment);
    table.querySelector("[aria-sort]")?.removeAttribute("aria-sort");
    header.setAttribute("aria-sort", ascending ? "ascending" : "descending");
    highlightColumn(col);
    if (reducedMotion.matches) return;
    groups.forEach((group, index) => {
      const distance = oldY.get(group) - group.getBoundingClientRect().top;
      if (Math.abs(distance) < 1) return;
      const animation = group.animate([
        {transform: "translateY(" + distance + "px)", opacity: .68},
        {transform: "translateY(0)", opacity: 1}
      ], {duration: 620, delay: Math.min(index * 13, 155), easing: "cubic-bezier(.22,.8,.18,1)", fill: "backwards"});
      movements.set(group, animation);
      animation.onfinish = () => movements.delete(group);
    });
  }

  table.addEventListener("click", event => {
    const button = event.target.closest("button");
    if (!button) return;
    if (button.classList.contains("board-sort")) return sortBy(button);
    const group = button.closest("tbody");
    if (button.classList.contains("board-details")) return showInfo(button, group);
    if (button.classList.contains("board-repeat")) {
      hideInfo();
      const expanded = button.getAttribute("aria-expanded") === "true";
      button.setAttribute("aria-expanded", String(!expanded));
      for (const row of Array.from(group.rows).slice(1)) row.hidden = expanded;
    }
  });
  board.addEventListener("click", event => {
    if (!event.target.closest(".board-details, .board-provenance")) hideInfo();
  });
  board.addEventListener("keydown", event => {
    if (event.key === "Escape" && anchor) {
      event.preventDefault();
      event.stopPropagation();
      hideInfo();
    }
  });
  board.addEventListener("close", hideInfo);
  scroller.addEventListener("scroll", hideInfo, {passive: true});
  window.addEventListener("resize", hideInfo);
})();
