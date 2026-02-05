const reveal = () => {
  const observer = new IntersectionObserver(
    entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add("visible");
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.15 }
  );

  document.querySelectorAll("[data-reveal]").forEach(el => observer.observe(el));
};

const canvasFx = () => {};

const cursorFx = () => {
  const cursor = document.createElement("div");
  cursor.className = "cursor";
  const dot = document.createElement("div");
  dot.className = "cursor-dot";
  document.body.appendChild(cursor);
  document.body.appendChild(dot);

  let x = window.innerWidth / 2;
  let y = window.innerHeight / 2;
  let tx = x;
  let ty = y;

  const move = e => {
    tx = e.clientX;
    ty = e.clientY;
    dot.style.transform = `translate(${tx}px, ${ty}px)`;
  };
  window.addEventListener("mousemove", move);

  const tick = () => {
    x += (tx - x) * 0.15;
    y += (ty - y) * 0.15;
    cursor.style.transform = `translate(${x}px, ${y}px)`;
    requestAnimationFrame(tick);
  };
  tick();
};

const updateCartCount = count => {
  const badge = document.getElementById("cartCount");
  if (badge) badge.textContent = count;
};

const addToCart = async productId => {
  const res = await fetch("/api/cart/add", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ product_id: productId, qty: 1 }),
  });
  const data = await res.json();
  if (data.ok) updateCartCount(data.count);
};

const removeFromCart = async productId => {
  const res = await fetch("/api/cart/remove", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ product_id: productId }),
  });
  const data = await res.json();
  if (data.ok) window.location.reload();
};

const bindActions = () => {
  document.querySelectorAll("[data-add-to-cart]").forEach(btn => {
    btn.addEventListener("click", () => addToCart(btn.dataset.addToCart));
  });

  document.querySelectorAll("[data-remove-from-cart]").forEach(btn => {
    btn.addEventListener("click", () => removeFromCart(btn.dataset.removeFromCart));
  });
};

const bindLoader = () => {
  const loader = document.getElementById("pageLoader");
  if (!loader) return;

  // show on first entry
  loader.classList.add("show");
  window.setTimeout(() => loader.classList.remove("show"), 650);

  // show when submitting checkout form
  const checkoutForm = document.querySelector(".checkout-form");
  if (checkoutForm) {
    checkoutForm.addEventListener("submit", () => {
      loader.classList.add("show");
    });
  }
};

window.addEventListener("DOMContentLoaded", () => {
  reveal();
  bindActions();
  canvasFx();
  cursorFx();
  bindLoader();
});
