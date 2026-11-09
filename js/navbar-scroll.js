
const header = document.querySelector(".site-header");

if (header) {
  let lastScrollY = window.scrollY;

  window.addEventListener(
    "scroll",
    () => {
      const currentScrollY = window.scrollY;
      const scrollingDown = currentScrollY > lastScrollY;

      if (currentScrollY <= 10) {
        header.classList.remove("is-hidden");
      } else if (scrollingDown && currentScrollY > 100) {
        header.classList.add("is-hidden");
      } else if (!scrollingDown) {
        header.classList.remove("is-hidden");
      }

      lastScrollY = currentScrollY;
    },
    { passive: true }
  );
}
