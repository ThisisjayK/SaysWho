/* Scroll reveals and a border on the bar once the page has moved.
   Everything here is decoration: with JS off, .reveal never gets .in, so the
   stylesheet's reduced-motion rule is not the only fallback. See the no-js rule
   applied immediately below. */
document.documentElement.classList.add("js");

const io = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add("in");
      io.unobserve(entry.target);
    });
  },
  { rootMargin: "0px 0px -8% 0px", threshold: 0.08 },
);

document.querySelectorAll(".reveal").forEach((el, i) => {
  // Stagger only within a group, so a long page does not end up with a two
  // second delay at the bottom of it.
  const group = el.closest(".grid, .stat-row, .steps");
  if (group) {
    const peers = [...group.querySelectorAll(".reveal")];
    el.style.setProperty("--d", `${peers.indexOf(el) * 70}ms`);
  }
  io.observe(el);
});

const bar = document.querySelector(".topbar");
const onScroll = () => bar.classList.toggle("scrolled", window.scrollY > 8);
onScroll();
addEventListener("scroll", onScroll, { passive: true });
